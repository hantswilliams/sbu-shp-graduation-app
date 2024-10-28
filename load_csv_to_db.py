# Required Imports
import csv
import os
import qrcode
from flask_sqlalchemy import SQLAlchemy
from app import db, Student, app  # Assuming your main Flask app is called 'app.py'

# CSV Loading Script
def load_students_from_csv(csv_file_path):
    # Use application context to avoid RuntimeError
    with app.app_context():
        # Check if the database tables exist, if not create them
        try:
            db.create_all()
        except Exception as e:
            print(f"Error creating tables: {e}")

        # Check if the CSV file exists
        if not os.path.exists(csv_file_path):
            print(f"File {csv_file_path} does not exist.")
            return
        
        # Read the CSV file and load students into the database
        with open(csv_file_path, newline='') as csvfile:
            csv_reader = csv.DictReader(csvfile)
            for row in csv_reader:
                # Extracting fields from CSV
                first_name = row.get('first_name')
                last_name = row.get('last_name')
                department = row.get('department')
                email = row.get('email')

                if not first_name or not last_name or not department or not email:
                    print(f"Skipping row due to missing fields: {row}")
                    continue

                # Check if student already exists in the database by email
                existing_student = Student.query.filter_by(email=email).first()
                if existing_student:
                    print(f"Student with email {email} already exists. Skipping...")
                    continue

                # Creating new student object
                new_student = Student(
                    first_name=first_name,
                    last_name=last_name,
                    department=department,
                    email=email,
                    audio_file=None,
                    audio_filename=None
                )
                db.session.add(new_student)
                db.session.commit()

                # Generate QR Code for the new student
                generate_qr_code(new_student)
                print(f"Added student: {first_name} {last_name}")

def generate_qr_code(student):
    # Store the QR data in a key-value format
    qr_data = f"id:{student.id},first_name:{student.first_name},last_name:{student.last_name},department:{student.department},email:{student.email}"
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(qr_data)
    qr.make(fit=True)
    img = qr.make_image(fill='black', back_color='white')

    # Save QR Code to file
    qr_filename = f"{student.id}_qrcode.png"
    qr_path = os.path.join('static/qrcodes', qr_filename)
    os.makedirs('static/qrcodes', exist_ok=True)
    img.save(qr_path)

    # Update student record with QR code file path
    student.qr_code_file = qr_filename
    db.session.commit()

if __name__ == "__main__":
    # Assuming your CSV file is called 'students.csv' and is in the same directory
    csv_file_path = 'students.csv'
    load_students_from_csv(csv_file_path)
    print("CSV data loaded successfully.")
