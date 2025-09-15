# app.py
import streamlit as st
import init_db
import add_student
import attendance
import os
import cv2
import numpy as np
from PIL import Image
import io

# ---------------- Streamlit UI ----------------
st.set_page_config(page_title="Face Recognition Attendance System", page_icon="📝", layout="centered")

st.title("📝 Face Recognition Attendance System")

menu = ["Initialize Database", "Add New Student", "Take Attendance", "Exit"]
choice = st.sidebar.radio("📌 Main Menu", menu)

if choice == "Initialize Database":
    st.subheader("⚙️ Initialize Database")
    if st.button("Initialize Now"):
        init_db.init_db()
        st.success("✅ Database initialized successfully!")

elif choice == "Add New Student":
    st.subheader("👨‍🎓 Add New Student")
    name = st.text_input("Enter Student Name")
    roll_no = st.text_input("Enter Roll Number")

    # Use session state to store captured images
    if "captured_images" not in st.session_state:
        st.session_state.captured_images = []

    img_file = st.camera_input("📸 Take a picture")

    if img_file and st.button("Capture & Save"):
        # Convert to OpenCV format
        image = Image.open(io.BytesIO(img_file.getvalue()))
        img_array = np.array(image)
        st.session_state.captured_images.append(img_array)
        st.success(f"✅ Image {len(st.session_state.captured_images)} captured!")

    st.write(f"Total Captured Images: {len(st.session_state.captured_images)}")

    if st.button("Save Student"):
        if name and roll_no and len(st.session_state.captured_images) >= 5:
            folder = f"students/{roll_no}_{name}"
            os.makedirs(folder, exist_ok=True)

            for idx, img_array in enumerate(st.session_state.captured_images):
                cv2.imwrite(f"{folder}/{idx+1}.jpg", cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR))

            add_student.add_student(name, roll_no)
            st.success(f"✅ Student {name} ({roll_no}) saved with {len(st.session_state.captured_images)} images!")

            # Reset session images after saving
            st.session_state.captured_images = []
        else:
            st.error("⚠️ Please capture at least 5 images before saving.")

elif choice == "Take Attendance":
    st.subheader("📸 Take Attendance")
    if st.button("Start Attendance"):
        attendance.mark_attendance()
        st.success("✅ Attendance process completed! Check the database/records.")

elif choice == "Exit":
    st.info("👋 Exiting... Close the app.")
