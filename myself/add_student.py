import cv2
import face_recognition
import sqlite3
import os
import csv
import numpy as np

DB_FILE = "attendance.db"
EMBEDDINGS_DIR = "embeddings"

def add_student(name, roll_no, num_images=10):
    os.makedirs(EMBEDDINGS_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Check if roll_no already exists
    cursor.execute("SELECT * FROM students WHERE roll_no = ?", (roll_no,))
    if cursor.fetchone():
        print("[ERROR] Roll number already exists!")
        conn.close()
        return

    # Add student to DB
    cursor.execute("INSERT INTO students (name, roll_no) VALUES (?, ?)", (name, roll_no))
    conn.commit()
    student_id = cursor.lastrowid
    conn.close()
    print(f"[INFO] Student '{name}' added with ID {student_id}")

    # CSV file for embeddings
    csv_file = os.path.join(EMBEDDINGS_DIR, f"{roll_no}_{name.replace(' ', '')}.csv")

    cam = cv2.VideoCapture(0)
    print(f"[INFO] Please capture {num_images} images of {name}. Press SPACE to capture.")

    captured = 0
    while captured < num_images:
        ret, frame = cam.read()
        if not ret:
            continue
        cv2.imshow("Capture Student Image", frame)
        k = cv2.waitKey(1)

        if k % 256 == 32:  # SPACE to capture
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            encodings = face_recognition.face_encodings(rgb_frame)
            if encodings:
                encoding = encodings[0]
                with open(csv_file, "a", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow(encoding.tolist())
                captured += 1
                print(f"[INFO] Captured image {captured}/{num_images}")
            else:
                print("[WARNING] No face detected, try again.")

        elif k % 256 == 27:  # ESC to cancel
            print("[INFO] Registration cancelled.")
            break

    cam.release()
    cv2.destroyAllWindows()
    print(f"[SUCCESS] Student '{name}' registration complete. Embeddings stored at {csv_file}")
