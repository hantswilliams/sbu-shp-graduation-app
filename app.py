# Required Imports
from flask import Flask, request, jsonify, render_template, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
import os
import qrcode
import io
from PIL import Image
import base64
import cv2

# Flask App Setup
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///students.db'
app.config['UPLOAD_FOLDER'] = 'uploads/'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)

# Student Model
class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    department = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    audio_file = db.Column(db.String(200), nullable=True)
    qr_code_file = db.Column(db.String(200), nullable=True)  # New column to store QR code file name

# Routes for Basic CRUD
@app.route('/')
def index():
    students = Student.query.all()
    return render_template('index.html', students=students)

@app.route('/student/add', methods=['GET', 'POST'])
def add_student():
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        department = request.form['department']
        email = request.form['email']
        audio = request.files['audio']

        if audio:
            audio_filename = secure_filename(audio.filename)
            audio.save(os.path.join(app.config['UPLOAD_FOLDER'], audio_filename))
        else:
            audio_filename = None

        new_student = Student(first_name=first_name, last_name=last_name, department=department, email=email, audio_file=audio_filename)
        db.session.add(new_student)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('add_student.html')

@app.route('/student/<int:id>/delete', methods=['POST'])
def delete_student(id):
    student = Student.query.get_or_404(id)
    if student.audio_file:
        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], student.audio_file))
    db.session.delete(student)
    db.session.commit()
    return redirect(url_for('index'))

# API to Create Students
@app.route('/api/student', methods=['POST'])
def api_create_student():
    data = request.get_json()
    new_student = Student(
        first_name=data['first_name'],
        last_name=data['last_name'],
        department=data['department'],
        email=data['email'],
        audio_file=None
    )
    db.session.add(new_student)
    db.session.commit()
    return jsonify({"message": "Student created successfully."}), 201

# QR Code Generation
@app.route('/student/<int:id>/qrcode')
def generate_qr(id):
    student = Student.query.get_or_404(id)
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

    # Convert to base64 for displaying directly in the template
    buf = io.BytesIO()
    img.save(buf)
    buf.seek(0)
    img_base64 = base64.b64encode(buf.getvalue()).decode('ascii')

    return render_template('qrcode.html', student=student, img_data=img_base64)


# QR Code Scanning
@app.route('/scan', methods=['GET', 'POST'])
def scan_qr():
    if request.method == 'POST':
        qr_code = request.files['qr_code']
        if qr_code:
            # Save uploaded file to a temporary path
            temp_path = os.path.join('static/uploads', 'temp_qr.png')
            qr_code.save(temp_path)

            # Use OpenCV to decode the QR code
            img = cv2.imread(temp_path)
            qr_decoder = cv2.QRCodeDetector()
            data, points, _ = qr_decoder.detectAndDecode(img)
            
            if data:
                # Parse the key-value pairs
                student_data = {}
                for part in data.split(','):
                    key, value = part.split(':')
                    student_data[key.strip()] = value.strip()

                # Get the student ID from the parsed data
                if 'id' in student_data:
                    student_id = student_data['id']
                    return redirect(url_for('view_student', id=student_id))
                else:
                    return "QR Code does not contain a valid ID", 400
            else:
                return "QR Code not recognized", 400

    return render_template('scan_qr.html')


@app.route('/student/<int:id>')
def view_student(id):
    student = Student.query.get_or_404(id)
    return render_template('view_student.html', student=student)

@app.route('/student/email')
def view_student_by_email():
    email = request.args.get('email')
    student = Student.query.filter_by(email=email).first_or_404()
    return render_template('view_student.html', student=student)

# Play Audio Route
@app.route('/student/<int:id>/play_audio')
def play_audio(id):
    student = Student.query.get_or_404(id)
    if student.audio_file:
        return redirect(url_for('static', filename='uploads/' + student.audio_file))
    return "Audio not available"

@app.route('/scan/advanced')
def qr_read_advanced():
    return render_template('qr_read_advanced.html')

@app.route('/api/student/<int:id>', methods=['GET'])
def api_get_student(id):
    student = Student.query.get_or_404(id)
    student_data = {
        'id': student.id,
        'first_name': student.first_name,
        'last_name': student.last_name,
        'department': student.department,
        'email': student.email,
        'audio_file': student.audio_file
    }
    return jsonify(student_data)

# Run the App
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)