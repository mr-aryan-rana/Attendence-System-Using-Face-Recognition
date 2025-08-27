import sqlite3

def delete_student(rollno_to_delete):
    conn = sqlite3.connect("attendance.db")
    cursor = conn.cursor()

    # Check if the student exists
    cursor.execute("SELECT * FROM students WHERE roll_no = ?", (rollno_to_delete,))
    student = cursor.fetchone()
    if student:
        cursor.execute("DELETE FROM students WHERE roll_no = ?", (rollno_to_delete,))
        conn.commit()
        print(f"[INFO] Student with roll_no {rollno_to_delete} deleted successfully!")
    else:
        print(f"[WARNING] No student found with roll_no {rollno_to_delete}")

    conn.close()

# Example usage
delete_student(1323223)
