from flask import Flask, render_template, request, jsonify, send_file
import cv2
import face_recognition
import sqlite3
import numpy as np
import pickle
import os
import base64
from datetime import datetime
import io
from PIL import Image

app = Flask(__name__)
DB_FILE = "attendance.db"
SIMILARITY_THRESHOLD = 70  # % match threshold

# Initialize database
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Students table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            roll_no TEXT UNIQUE NOT NULL,
            department TEXT NOT NULL,
            section TEXT NOT NULL,
            group_name TEXT NOT NULL,
            embedding BLOB,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Lectures table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS lectures (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_name TEXT NOT NULL,
            department TEXT NOT NULL,
            section TEXT NOT NULL,
            group_name TEXT NOT NULL,
            lecture_date DATE NOT NULL,
            start_time TIME NOT NULL,
            end_time TIME NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Attendance table
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

# Load student embeddings
def load_student_embeddings():
    if not os.path.exists(DB_FILE):
        return [], []

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id, roll_no, name, department, section, group_name, embedding FROM students WHERE embedding IS NOT NULL")
    rows = cursor.fetchall()
    conn.close()

    student_encodings, student_info = [], []
    for student_id, roll_no, name, department, section, group_name, embedding_blob in rows:
        if embedding_blob:
            embedding = pickle.loads(embedding_blob)
            student_encodings.append([embedding])
            student_info.append((student_id, roll_no, name, department, section, group_name))

    return student_encodings, student_info

# Update student embedding
def update_student_embedding(roll_no, new_encoding):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT embedding FROM students WHERE roll_no = ?", (roll_no,))
    result = cursor.fetchone()

    if result and result[0]:
        old_embedding = pickle.loads(result[0])
        updated_embedding = (old_embedding + new_encoding) / 2.0
    else:
        updated_embedding = new_encoding

    cursor.execute("UPDATE students SET embedding = ? WHERE roll_no = ?", 
                   (pickle.dumps(updated_embedding), roll_no))
    conn.commit()
    conn.close()
    return True

# Get or create default lecture
def get_or_create_default_lecture():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    today = datetime.now().strftime("%Y-%m-%d")
    current_time = datetime.now().strftime("%H:%M:%S")
    
    # Create a default lecture for today
    cursor.execute("""
        SELECT id FROM lectures WHERE lecture_date = ? LIMIT 1
    """, (today,))
    lecture = cursor.fetchone()

    if lecture:
        lecture_id = lecture[0]
    else:
        cursor.execute("""
            INSERT INTO lectures (subject_name, department, section, group_name, lecture_date, start_time, end_time)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, ("Daily Lecture", "General", "All", "All", today, current_time, current_time))
        conn.commit()
        lecture_id = cursor.lastrowid

    conn.close()
    return lecture_id

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/init_db', methods=['POST'])
def api_init_db():
    try:
        init_db()
        return jsonify({"success": True, "message": "Database initialized successfully!"})
    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {str(e)}"})

@app.route('/api/add_student', methods=['POST'])
def api_add_student():
    try:
        data = request.json
        name = data.get('name')
        roll_no = data.get('roll_no')
        department = data.get('department')
        section = data.get('section')
        group_name = data.get('group_name')
        images_base64 = data.get('images', [])  # List of base64 encoded images

        if not all([name, roll_no, department, section, group_name]):
            return jsonify({"success": False, "message": "All fields are required"})

        # Check if roll number already exists
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM students WHERE roll_no = ?", (roll_no,))
        if cursor.fetchone():
            conn.close()
            return jsonify({"success": False, "message": f"Roll number '{roll_no}' already exists"})
        conn.close()

        # Process images and create embeddings
        embeddings = []
        for img_base64 in images_base64:
            # Convert base64 to image
            img_data = base64.b64decode(img_base64.split(',')[1])
            img = Image.open(io.BytesIO(img_data))
            img_np = np.array(img)
            
            # Convert RGB to BGR for OpenCV
            rgb_frame = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
            rgb_frame = cv2.cvtColor(rgb_frame, cv2.COLOR_BGR2RGB)
            
            # Get face encoding
            encodings = face_recognition.face_encodings(rgb_frame)
            if encodings:
                embeddings.append(encodings[0])

        if not embeddings:
            return jsonify({"success": False, "message": "No faces detected in the captured images"})

        # Calculate mean embedding
        mean_embedding = np.mean(embeddings, axis=0)
        embedding_blob = pickle.dumps(mean_embedding)

        # Save to database
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO students (name, roll_no, department, section, group_name, embedding)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (name, roll_no, department, section, group_name, embedding_blob))
        conn.commit()
        conn.close()

        return jsonify({
            "success": True, 
            "message": f"Student '{name}' added successfully!",
            "student": {
                "name": name,
                "roll_no": roll_no,
                "department": department,
                "section": section,
                "group_name": group_name
            }
        })

    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {str(e)}"})

@app.route('/api/verify_student', methods=['POST'])
def api_verify_student():
    try:
        data = request.json
        image_base64 = data.get('image')

        if not image_base64:
            return jsonify({"success": False, "message": "No image provided"})

        # Convert base64 to image
        img_data = base64.b64decode(image_base64.split(',')[1])
        img = Image.open(io.BytesIO(img_data))
        img_np = np.array(img)
        
        # Convert RGB to BGR for OpenCV
        rgb_frame = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
        rgb_frame = cv2.cvtColor(rgb_frame, cv2.COLOR_BGR2RGB)

        # Get face encoding from the frame
        face_encodings = face_recognition.face_encodings(rgb_frame)
        if not face_encodings:
            return jsonify({"success": False, "message": "No face detected in the image"})

        face_encoding = face_encodings[0]

        # Load student embeddings
        student_encodings, student_info = load_student_embeddings()
        if not student_encodings:
            return jsonify({"success": False, "message": "No students registered in the system"})

        # Find best match
        best_similarity, best_index = 0, -1
        for idx, enc_list in enumerate(student_encodings):
            distances = face_recognition.face_distance(enc_list, face_encoding)
            similarity = (1 - np.min(distances)) * 100
            if similarity > best_similarity:
                best_similarity, best_index = similarity, idx

        if best_similarity >= SIMILARITY_THRESHOLD and best_index != -1:
            # Student verified
            student_id, roll_no, name, department, section, group_name = student_info[best_index]
            
            # Create default lecture and mark attendance
            lecture_id = get_or_create_default_lecture()
            
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Check if already marked attendance for today's lecture
            cursor.execute("""
                SELECT id FROM attendance 
                WHERE student_id=? AND lecture_id=?
            """, (student_id, lecture_id))
            
            attendance_record = cursor.fetchone()
            
            if not attendance_record:
                cursor.execute("""
                    INSERT INTO attendance (student_id, lecture_id, status, timestamp)
                    VALUES (?, ?, ?, ?)
                """, (student_id, lecture_id, 'Present', timestamp))
                conn.commit()
                
                # Update embedding with new data
                update_student_embedding(roll_no, face_encoding)
                
                message = f"Verified: {name} - Attendance marked successfully!"
                attendance_status = "marked"
            else:
                message = f"Verified: {name} - Attendance already marked for today!"
                attendance_status = "already_marked"
            
            conn.close()
            
            return jsonify({
                "success": True,
                "verified": True,
                "similarity": round(best_similarity, 2),
                "attendance_status": attendance_status,
                "student": {
                    "name": name,
                    "roll_no": roll_no,
                    "department": department,
                    "section": section,
                    "group_name": group_name
                },
                "message": message
            })
        else:
            return jsonify({
                "success": True,
                "verified": False,
                "similarity": round(best_similarity, 2),
                "message": f"Verification failed. No matching student found (Best match: {round(best_similarity, 2)}%)"
            })

    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {str(e)}"})

@app.route('/api/get_students', methods=['GET'])
def api_get_students():
    try:
        search = request.args.get('search', '')
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        if search:
            cursor.execute("""
                SELECT id, name, roll_no, department, section, group_name, created_at 
                FROM students 
                WHERE name LIKE ? OR roll_no LIKE ?
                ORDER BY created_at DESC
            """, (f'%{search}%', f'%{search}%'))
        else:
            cursor.execute("""
                SELECT id, name, roll_no, department, section, group_name, created_at 
                FROM students 
                ORDER BY created_at DESC
            """)
        
        students = []
        for row in cursor.fetchall():
            students.append({
                "id": row[0],
                "name": row[1],
                "roll_no": row[2],
                "department": row[3],
                "section": row[4],
                "group_name": row[5],
                "created_at": row[6]
            })
        
        conn.close()
        return jsonify({"success": True, "students": students})
    
    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {str(e)}"})

@app.route('/api/delete_student', methods=['POST'])
def api_delete_student():
    try:
        data = request.json
        student_id = data.get('student_id')
        
        if not student_id:
            return jsonify({"success": False, "message": "Student ID is required"})
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Get student info before deletion
        cursor.execute("SELECT name, roll_no FROM students WHERE id = ?", (student_id,))
        student = cursor.fetchone()
        
        if not student:
            conn.close()
            return jsonify({"success": False, "message": "Student not found"})
        
        name, roll_no = student
        
        # Delete attendance records
        cursor.execute("DELETE FROM attendance WHERE student_id = ?", (student_id,))
        
        # Delete student
        cursor.execute("DELETE FROM students WHERE id = ?", (student_id,))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            "success": True, 
            "message": f"Student '{name}' ({roll_no}) deleted successfully!"
        })
    
    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {str(e)}"})

@app.route('/api/get_attendance_stats', methods=['GET'])
def api_get_attendance_stats():
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Get total students
        cursor.execute("SELECT COUNT(*) FROM students")
        total_students = cursor.fetchone()[0]
        
        # Get total lectures today
        today = datetime.now().strftime("%Y-%m-%d")
        cursor.execute("SELECT COUNT(*) FROM lectures WHERE lecture_date = ?", (today,))
        total_lectures_today = cursor.fetchone()[0]
        
        # Get attendance records for today
        cursor.execute("""
            SELECT COUNT(DISTINCT student_id) FROM attendance a
            JOIN lectures l ON a.lecture_id = l.id
            WHERE l.lecture_date = ?
        """, (today,))
        attendance_today = cursor.fetchone()[0]
        
        conn.close()
        
        return jsonify({
            "success": True,
            "stats": {
                "total_students": total_students,
                "total_lectures_today": total_lectures_today,
                "attendance_today": attendance_today
            }
        })
    
    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {str(e)}"})

@app.route('/api/reset_db', methods=['POST'])
def api_reset_db():
    try:
        if os.path.exists(DB_FILE):
            os.remove(DB_FILE)
        init_db()
        return jsonify({"success": True, "message": "Database reset successfully!"})
    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {str(e)}"})

@app.route('/api/get_today_attendance', methods=['GET'])
def api_get_today_attendance():
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        today = datetime.now().strftime("%Y-%m-%d")
        
        cursor.execute("""
            SELECT s.name, s.roll_no, s.department, s.section, a.timestamp
            FROM attendance a
            JOIN students s ON a.student_id = s.id
            JOIN lectures l ON a.lecture_id = l.id
            WHERE l.lecture_date = ?
            ORDER BY a.timestamp DESC
        """, (today,))
        
        attendance_records = []
        for row in cursor.fetchall():
            attendance_records.append({
                "name": row[0],
                "roll_no": row[1],
                "department": row[2],
                "section": row[3],
                "timestamp": row[4]
            })
        
        conn.close()
        return jsonify({"success": True, "attendance": attendance_records})
    
    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {str(e)}"})

if __name__ == '__main__':
    # Initialize database on startup
    if not os.path.exists(DB_FILE):
        init_db()
        print("Database initialized successfully!")
    
    app.run(debug=True, host='0.0.0.0', port=5000)