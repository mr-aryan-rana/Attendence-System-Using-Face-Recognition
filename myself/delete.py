import sqlite3
import os

DB_FILE = r"D:\Attendence-System-Using-Face-Recognition\myself\attendance.db"

def delete_student(roll_no_to_delete):
    """
    Deletes a student and all related attendance records from the database.
    """
    if not os.path.exists(DB_FILE):
        print("[ERROR] Database not found!")
        return False, "Database not found"

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Check if student exists
    cursor.execute("SELECT id, name FROM students WHERE roll_no = ?", (roll_no_to_delete,))
    student = cursor.fetchone()

    if not student:
        conn.close()
        print(f"[WARNING] No student found with roll_no {roll_no_to_delete}")
        return False, "Student not found"

    student_id, name = student

    # Delete attendance records
    cursor.execute("DELETE FROM attendance WHERE student_id = ?", (student_id,))

    # Delete student record
    cursor.execute("DELETE FROM students WHERE id = ?", (student_id,))
    conn.commit()
    conn.close()

    print(f"[INFO] Student '{name}' ({roll_no_to_delete}) deleted successfully with related records.")
    return True, f"Deleted student {name} ({roll_no_to_delete})"
