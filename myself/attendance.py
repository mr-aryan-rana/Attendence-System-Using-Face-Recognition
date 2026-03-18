import cv2
import face_recognition
import sqlite3
import pickle
import numpy as np
from datetime import datetime
import os

DB_FILE = r"D:\Attendence-System-Using-Face-Recognition\myself\attendance.db"
SIMILARITY_THRESHOLD = 70  # % match threshold

# -------------------------------
# Load all students' embeddings
# -------------------------------
def load_student_embeddings():
    if not os.path.exists(DB_FILE):
        print("[ERROR] Database not found! Run init_db.py first.")
        return [], []

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT roll_no, name, embedding FROM students WHERE embedding IS NOT NULL")
    rows = cursor.fetchall()
    conn.close()

    student_encodings, student_info = [], []
    for roll_no, name, embedding_blob in rows:
        if embedding_blob:
            embedding = pickle.loads(embedding_blob)
            student_encodings.append([embedding])
            student_info.append((roll_no, name))

    print(f"[INFO] Loaded {len(student_encodings)} embeddings.")
    return student_encodings, student_info


# -------------------------------
# Update student embedding (mean)
# -------------------------------
def update_student_embedding(roll_no, new_encoding):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT embedding FROM students WHERE roll_no = ?", (roll_no,))
    result = cursor.fetchone()

    if result and result[0]:
        old_embedding = pickle.loads(result[0])
        updated_embedding = (old_embedding + new_encoding) / 2.0
    else:
        updated_embedding = new_encoding

    cursor.execute("UPDATE students SET embedding = ? WHERE roll_no = ?", 
                   (pickle.dumps(updated_embedding), roll_no))
    conn.commit()
    conn.close()
    print(f"[INFO] Embedding updated for {roll_no}")


# -------------------------------
# Get or Create Lecture
# -------------------------------
def get_or_create_lecture(subject_name, department, section, group_name):
    """Creates a lecture record if not already present for today."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    today = datetime.now().strftime("%Y-%m-%d")
    cursor.execute("""
        SELECT id FROM lectures
        WHERE subject_name=? AND department=? AND section=? AND group_name=? AND lecture_date=?
    """, (subject_name, department, section, group_name, today))
    lecture = cursor.fetchone()

    if lecture:
        lecture_id = lecture[0]
    else:
        start_time = datetime.now().strftime("%H:%M:%S")
        end_time = (datetime.now()).strftime("%H:%M:%S")
        cursor.execute("""
            INSERT INTO lectures (subject_name, department, section, group_name, lecture_date, start_time, end_time)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (subject_name, department, section, group_name, today, start_time, end_time))
        conn.commit()
        lecture_id = cursor.lastrowid
        print(f"[INFO] Created new lecture: {subject_name} ({today})")

    conn.close()
    return lecture_id


# -------------------------------
# Mark Attendance
# -------------------------------
def mark_attendance(subject_name, department, section, group_name):
    student_encodings, student_info = load_student_embeddings()
    if not student_encodings:
        return

    lecture_id = get_or_create_lecture(subject_name, department, section, group_name)
    cap = cv2.VideoCapture(0)

    print("[INFO] Look at the camera to mark attendance (Press 'q' to quit).")
    verified = False
    matched_student = None
    matched_encoding = None
    start_time = datetime.now().timestamp()

    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        faces = face_recognition.face_locations(rgb_frame)
        encodings_frame = face_recognition.face_encodings(rgb_frame, faces)

        for face_encoding, face_location in zip(encodings_frame, faces):
            best_similarity, best_index = 0, -1

            for idx, enc_list in enumerate(student_encodings):
                distances = face_recognition.face_distance(enc_list, face_encoding)
                similarity = (1 - np.min(distances)) * 100
                if similarity > best_similarity:
                    best_similarity, best_index = similarity, idx

            # Draw result
            top, right, bottom, left = face_location
            color = (0, 255, 0) if best_similarity >= SIMILARITY_THRESHOLD else (0, 0, 255)
            cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
            label = f"{'MATCH' if best_similarity >= SIMILARITY_THRESHOLD else 'NO MATCH'} {round(best_similarity, 2)}%"
            cv2.putText(frame, label, (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

            if best_similarity >= SIMILARITY_THRESHOLD and not verified:
                verified = True
                matched_student = student_info[best_index]
                matched_encoding = face_encoding

        cv2.imshow("Face Verification", frame)
        current_time = datetime.now().timestamp()
        if verified and current_time - start_time >= 3:
            break
        elif not verified and current_time - start_time > 15:
            break
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

    # -------------------------------
    # Record Attendance
    # -------------------------------
    if verified and matched_student:
        roll_no, name = matched_student
        print(f"[SUCCESS] Verified: {name} ({roll_no})")

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM students WHERE roll_no=?", (roll_no,))
        row = cursor.fetchone()

        if row:
            student_id = row[0]
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("""
                INSERT INTO attendance (student_id, lecture_id, status, timestamp)
                VALUES (?, ?, ?, ?)
            """, (student_id, lecture_id, 'Present', timestamp))
            conn.commit()
            print(f"[INFO] Attendance marked at {timestamp}")
        conn.close()

        update_student_embedding(roll_no, matched_encoding)
    else:
        print("[FAILED] Verification failed ❌")


if __name__ == "__main__":
    subject_name = input("Enter subject name: ").strip()
    department = input("Enter department: ").strip()
    section = input("Enter section: ").strip()
    group_name = input("Enter group name: ").strip()
    mark_attendance(subject_name, department, section, group_name)
