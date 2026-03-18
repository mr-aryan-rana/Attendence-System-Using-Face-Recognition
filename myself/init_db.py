import sqlite3
import os

DB_FILE = r"D:\Attendence-System-Using-Face-Recognition\myself\attendance.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # --- STUDENTS TABLE ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            roll_no TEXT UNIQUE NOT NULL,
            department TEXT NOT NULL,
            section TEXT NOT NULL,
            group_name TEXT NOT NULL,
            embedding BLOB
        )
    """)

    # --- LECTURES TABLE ---
    # Stores lecture information for specific subjects / groups
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS lectures (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_name TEXT NOT NULL,
            department TEXT NOT NULL,
            section TEXT NOT NULL,
            group_name TEXT NOT NULL,
            lecture_date DATE NOT NULL,
            start_time TIME NOT NULL,
            end_time TIME NOT NULL
        )
    """)

    # --- ATTENDANCE TABLE ---
    # Connects student and lecture (1 student -> many lectures)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            lecture_id INTEGER NOT NULL,
            status TEXT DEFAULT 'Present',
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(student_id) REFERENCES students(id),
            FOREIGN KEY(lecture_id) REFERENCES lectures(id)
        )
    """)

    conn.commit()
    conn.close()
    print("[INFO] Database initialized successfully with extended schema!")

if __name__ == "__main__":
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
        print("[INFO] Old database removed.")
    init_db()
