import init_db
import add_student
import attendance

def main_menu():
    while True:
        print("\n===== FACE RECOGNITION ATTENDANCE SYSTEM =====")
        print("1. Initialize Database")
        print("2. Add New Student")
        print("3. Take Attendance / Verify Student")
        print("4. Exit")
        choice = input("Enter your choice (1-4): ")

        if choice == "1":
            init_db.init_db()
        elif choice == "2":
            name = input("Enter student name: ")
            roll_no = input("Enter student roll number: ")
            add_student.add_student(name, roll_no)
        elif choice == "3":
            attendance.mark_attendance()
        elif choice == "4":
            print("Exiting... Bye!")
            break
        else:
            print("Invalid choice. Try again.")

if __name__ == "__main__":
    main_menu()
