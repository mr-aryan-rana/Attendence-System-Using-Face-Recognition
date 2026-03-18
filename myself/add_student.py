import cv2
import face_recognition
import sqlite3
import numpy as np
import pickle
import os

DB_FILE = r"D:\Attendence-System-Using-Face-Recognition\myself\attendance.db"

def add_student(name, roll_no, department, section, group_name, num_images=5):
    """
    Registers a new student with department, section, and group info.
    Stores their mean face embedding in SQLite DB.
    """
    if not os.path.exists(DB_FILE):
        print("[ERROR] Database not found! Run init_db.py first.")
        return

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Check duplicate roll number
    cursor.execute("SELECT * FROM students WHERE roll_no = ?", (roll_no,))
    if cursor.fetchone():
        print(f"[ERROR] Roll number '{roll_no}' already exists!")
        conn.close()
        return

    print(f"[INFO] Capturing {num_images} images for {name} ({roll_no})")
    print("Press SPACE to capture | ESC to cancel")

    cam = cv2.VideoCapture(0)
    embeddings = []
    captured = 0

    while captured < num_images:
        ret, frame = cam.read()
        if not ret:
            continue

        cv2.imshow("Capture Student Face", frame)
        key = cv2.waitKey(1)

        # SPACE = capture
        if key % 256 == 32:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            encodings = face_recognition.face_encodings(rgb_frame)

            if encodings:
                embeddings.append(encodings[0])
                captured += 1
                print(f"[INFO] Captured image {captured}/{num_images}")
            else:
                print("[WARNING] No face detected. Try again.")

        # ESC = cancel
        elif key % 256 == 27:
            print("[INFO] Registration cancelled.")
            cam.release()
            cv2.destroyAllWindows()
            conn.close()
            return

    cam.release()
    cv2.destroyAllWindows()

    if not embeddings:
        print("[ERROR] No embeddings captured.")
        conn.close()
        return

    mean_embedding = np.mean(embeddings, axis=0)
    embedding_blob = pickle.dumps(mean_embedding)

    # Insert into DB
    cursor.execute("""
        INSERT INTO students (name, roll_no, department, section, group_name, embedding)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (name, roll_no, department, section, group_name, embedding_blob))
    conn.commit()
    conn.close()

    print(f"[SUCCESS] Student '{name}' added successfully!")
    print(f"[INFO] Department: {department}, Section: {section}, Group: {group_name}")

if __name__ == "__main__":
    name = input("Enter student name: ").strip()
    roll_no = input("Enter roll number: ").strip()
    department = input("Enter department: ").strip()
    section = input("Enter section: ").strip()
    group_name = input("Enter group name: ").strip()

    add_student(name, roll_no, department, section, group_name, num_images=5)
