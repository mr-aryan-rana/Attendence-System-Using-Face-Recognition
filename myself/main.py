import init_db as db
import add_student
import attendance
import delete

def main_menu():
    while True:
        print("\n===== FACE RECOGNITION ATTENDANCE SYSTEM =====")
        print("1. Initialize Database")
        print("2. Add New Student")
        print("3. Take Attendance / Verify Student (auto-update embeddings)")
        print("4. Delete Student")
        print("5. Exit")
        choice = input("Enter your choice (1-5): ")

        if choice == "1":
            db.init_db()
        elif choice == "2":
            name = input("Enter student name: ")
            roll_no = input("Enter student roll number: ")
            add_student.add_student(name, roll_no)
        elif choice == "3":
            attendance.mark_attendance()
        elif choice == "4":
            roll_no_to_delete = input("Enter roll number of student to delete: ")
            delete.delete_student(roll_no_to_delete)
        elif choice == "5":
                print("Exiting the program.")
                break
        else:
            print("Invalid choice. Try again.")

if __name__ == "__main__":
    main_menu()
