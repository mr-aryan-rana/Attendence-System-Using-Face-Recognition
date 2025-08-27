import cv2
import face_recognition
import sqlite3
import os
import csv
import numpy as np
from datetime import datetime

DB_FILE = "attendance.db"
EMBEDDINGS_DIR = "embeddings"
SIMILARITY_THRESHOLD = 70  # % similarity to verify

def load_student_embeddings():
    student_encodings = []
    student_info = []
    for file in os.listdir(EMBEDDINGS_DIR):
        if file.endswith(".csv"):
            roll_name = file[:-4]  # remove .csv
            roll_no, name = roll_name.split("_", 1)
            path = os.path.join(EMBEDDINGS_DIR, file)
            embeddings = []
            with open(path, "r") as f:
                reader = csv.reader(f)
                for row in reader:
                    embeddings.append(np.array([float(x) for x in row]))
            if embeddings:
                student_encodings.append(embeddings)
                student_info.append((roll_no, name))
    return student_encodings, student_info

def mark_attendance():
    student_encodings, student_info = load_student_embeddings()
    if not student_encodings:
        print("[INFO] No student embeddings found!")
        return

    cap = cv2.VideoCapture(0)
    verified = False
    matched_student = None
    start_time = datetime.now().timestamp()
    print("[INFO] Please look at the camera for verification...")

    while True:
        ret, frame = cap.read()
        if not ret:
            continue
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        faces = face_recognition.face_locations(rgb_frame)
        encodings_frame = face_recognition.face_encodings(rgb_frame, faces)

        for face_encoding, face_location in zip(encodings_frame, faces):
            best_similarity = 0
            best_index = -1
            for idx, enc_list in enumerate(student_encodings):
                distances = face_recognition.face_distance(enc_list, face_encoding)
                min_distance = min(distances)
                similarity = (1 - min_distance) * 100
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_index = idx

            top, right, bottom, left = face_location
            color = (0, 255, 0) if best_similarity >= SIMILARITY_THRESHOLD else (0, 0, 255)
            text = f"{'MATCH' if best_similarity >= SIMILARITY_THRESHOLD else 'NO MATCH'} {round(best_similarity,2)}%"
            cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
            cv2.putText(frame, text, (left, top-10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

            if best_similarity >= SIMILARITY_THRESHOLD and not verified:
                verified = True
                matched_student = student_info[best_index]

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

    if verified and matched_student:
        roll_no, name = matched_student
        print(f"[SUCCESS] Verification Passed ✅ - {name} ({roll_no})")
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM students WHERE roll_no = ?", (roll_no,))
        student_id = cursor.fetchone()[0]
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("INSERT INTO attendance (student_id, timestamp) VALUES (?, ?)", (student_id, timestamp))
        conn.commit()
        conn.close()
        print(f"[INFO] Attendance recorded at {timestamp}")
    else:
        print("[FAILED] Verification Failed ❌")
