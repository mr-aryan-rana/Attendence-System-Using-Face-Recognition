import sqlite3

# 🔹 Change this to your actual database file name/path
db_path = r"D:\Attendence-System-Using-Face-Recognition\myself\attendance.db"  

# Connect to the database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Fetch all tables in the database
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()

# Display the tables
if tables:
    print("📋 Tables in the database:")
    for table in tables:
        print("-", table[0])
else:
    print("⚠️ No tables found in this database.")

# Close the connection
conn.close()
