import cv2
import face_recognition
import os
import numpy as np
import tkinter as tk
from tkinter import messagebox, ttk
import threading
import pyttsx3
from datetime import datetime
import pandas as pd
import yagmail

# Load known faces
known_faces = []
known_names = []

folder_path = r"C:\Users\dell\Desktop\students"  # <- Update this path as needed
for file in os.listdir(folder_path):
    if file.endswith(('.jpg', '.png', '.jpeg')):
        img = face_recognition.load_image_file(os.path.join(folder_path, file))
        encoding = face_recognition.face_encodings(img)
        if encoding:  # ensure encoding is successful
            known_faces.append(encoding[0])
            known_names.append(os.path.splitext(file)[0])

# Initialize Attendance Dictionary
attendance = {}

# Voice engine setup
engine = pyttsx3.init()

# Email Configuration
EMAIL_USER = "joshijigyasu7@gmail.com"
EMAIL_PASS = "drlcogorxcxvrrhv"  # App Password

# Function to speak in background thread
def speak(text):
    engine.say(text)
    engine.runAndWait()

def speak_in_thread(text):
    threading.Thread(target=speak, args=(text,), daemon=True).start()

# Attendance marking function
def mark_attendance(name):
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M:%S")

    if name not in attendance:
        attendance[name] = [date_str, time_str]
        speak_in_thread(f"Welcome {name}, your attendance is marked.")
        update_attendance_table()
    else:
        speak_in_thread(f"{name}, your attendance is already marked.")

# Function to update GUI table
def update_attendance_table():
    for row in tree.get_children():
        tree.delete(row)
    for name in known_names:
        if name in attendance:
            date, time = attendance[name]
            status = "Present"
        else:
            date, time, status = "-", "-", "Absent"
        tree.insert("", "end", values=(name, date, time, status))

# Function to generate and send report
def generate_report():
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")

    records = []
    for name in known_names:
        if name in attendance:
            records.append([name, date_str, attendance[name][1], "Present"])
        else:
            records.append([name, date_str, "-", "Absent"])

    df = pd.DataFrame(records, columns=["Name", "Date", "Time", "Status"])
    df.to_csv("attendance.csv", index=False)

    speak_in_thread("Report generated and sending email...")

    try:
        yag = yagmail.SMTP(EMAIL_USER, EMAIL_PASS)
        yag.send(
            to=EMAIL_USER,
            subject="Attendance Report",
            contents="Attached is today's attendance report.",
            attachments="attendance.csv"
        )
        messagebox.showinfo("Success", "Report sent successfully via email!")
    except Exception as e:
        messagebox.showerror("Email Error", str(e))

# Webcam control
def start_attendance():
    global running, prev_faces
    attendance.clear()
    update_attendance_table()
    prev_faces = set()
    running = True
    threading.Thread(target=run_camera, daemon=True).start()

def stop_attendance():
    global running
    running = False

# Face Recognition Camera Feed
def run_camera():
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    global prev_faces

    while running:
        ret, frame = cap.read()
        if not ret:
            continue

        small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
        rgb_small = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

        face_locations = face_recognition.face_locations(rgb_small)
        face_encodings = face_recognition.face_encodings(rgb_small, face_locations)

        current_faces = set()

        for face_encoding, face_loc in zip(face_encodings, face_locations):
            matches = face_recognition.compare_faces(known_faces, face_encoding)
            face_dist = face_recognition.face_distance(known_faces, face_encoding)

            if len(face_dist) > 0:
                best_match = np.argmin(face_dist)
                if matches[best_match]:
                    name = known_names[best_match]
                    current_faces.add(name)

                    top, right, bottom, left = [v * 4 for v in face_loc]
                    cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
                    cv2.putText(frame, name, (left, top - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

                    if name not in attendance:
                        threading.Thread(target=mark_attendance, args=(name,), daemon=True).start()
                    elif name not in prev_faces:
                        speak_in_thread(f"{name}, your attendance is already marked.")
                else:
                    top, right, bottom, left = [v * 4 for v in face_loc]
                    cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)
                    cv2.putText(frame, "Unknown", (left, top - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

        prev_faces = current_faces.copy()

        cv2.imshow("Face Attendance System", frame)
        if cv2.waitKey(1) == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

# GUI Setup
root = tk.Tk()
root.title("Attendify - Smart Attendance System")
root.geometry("700x600")
root.resizable(False, False)

tk.Label(root, text="Attendify - Smart Attendance System", font=("Helvetica", 16, "bold")).pack(pady=10)

start_btn = tk.Button(root, text="Start Capturing Attendance", font=("Arial", 12), bg="green", fg="white", command=start_attendance)
start_btn.pack(pady=5)

stop_btn = tk.Button(root, text="Stop Capturing Attendance", font=("Arial", 12), bg="red", fg="white", command=stop_attendance)
stop_btn.pack(pady=5)

report_btn = tk.Button(root, text="Generate & Email Report", font=("Arial", 12), bg="blue", fg="white", command=generate_report)
report_btn.pack(pady=10)

# Attendance Status Table
tk.Label(root, text="Attendance Status", font=("Helvetica", 14, "bold")).pack(pady=10)
table_frame = tk.Frame(root)
table_frame.pack()

tree = ttk.Treeview(table_frame, columns=("Name", "Date", "Time", "Status"), show='headings', height=10)
tree.heading("Name", text="Name")
tree.heading("Date", text="Date")
tree.heading("Time", text="Time")
tree.heading("Status", text="Status")

tree.column("Name", width=150)
tree.column("Date", width=100)
tree.column("Time", width=100)
tree.column("Status", width=100)
tree.pack()

root.mainloop()
