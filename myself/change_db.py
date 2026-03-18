import sqlite3

DB_FILE = r"D:\Attendence-System-Using-Face-Recognition\myself\attendance.db"

conn = sqlite3.connect(DB_FILE)
cursor = conn.cursor()

# Check if the column already exists
cursor.execute("PRAGMA table_info(students)")
columns = [col[1] for col in cursor.fetchall()]

cursor.execute("ALTER TABLE students DROP COLUMN embeddding;")

if "embedding" not in columns:
    cursor.execute("ALTER TABLE students ADD COLUMN embedding BLOB")
    conn.commit()
    print("[SUCCESS] Added 'embedding' column to students table.")
else:
    print("[INFO] 'embedding' column already exists.")

conn.close()
