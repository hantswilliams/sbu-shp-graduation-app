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
from pydub import AudioSegment  # Add this import at the top

# Flask App Setup
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///students.db'
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
print(app.config['UPLOAD_FOLDER'])

db = SQLAlchemy(app)

# Student Model
class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    department = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    audio_file = db.Column(db.LargeBinary, nullable=True)  # Change to BLOB to store binary audio data
    audio_filename = db.Column(db.String(200), nullable=True)  # Store filename if needed for extensions
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

        audio_data = None
        audio_filename = None
        if audio and audio.filename != '':
            audio_filename = secure_filename(audio.filename)
            audio_data = audio.read()  # Read file data as binary

        new_student = Student(
            first_name=first_name,
            last_name=last_name,
            department=department,
            email=email,
            audio_file=audio_data,
            audio_filename=audio_filename
        )
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

@app.route('/student/<int:id>/audio')
def get_audio(id):
    student = Student.query.get_or_404(id)
    if student.audio_file:
        return (student.audio_file, {
            'Content-Type': 'audio/mpeg',
            'Content-Disposition': f'inline; filename="{student.audio_filename}"'
        })
    return "Audio not available", 404

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
        'audio_file': f"/student/{student.id}/audio" if student.audio_file else None  # Providing a URL instead of raw binary data
    }
    return jsonify(student_data)

@app.route('/api/student/<int:id>', methods=['PUT'])
def api_update_student(id):
    student = Student.query.get_or_404(id)
    data = request.get_json()

    student.first_name = data.get('first_name', student.first_name)
    student.last_name = data.get('last_name', student.last_name)
    student.department = data.get('department', student.department)
    student.email = data.get('email', student.email)

    if 'audio_file' in data:
        # Note: This assumes audio_file is a string filename; handling file uploads through API may need different logic
        student.audio_file = data['audio_file']

    db.session.commit()
    return jsonify({"message": "Student updated successfully."}), 200


@app.route('/student/<int:id>/edit', methods=['GET', 'POST'])
def edit_student(id):
    student = Student.query.get_or_404(id)
    if request.method == 'POST':
        student.first_name = request.form['first_name']
        student.last_name = request.form['last_name']
        student.department = request.form['department']
        student.email = request.form['email']

        # Handling uploaded audio file
        if 'audio' in request.files:
            audio = request.files['audio']
            if audio and audio.filename != '':
                audio_filename = secure_filename(audio.filename)
                student.audio_file = audio.read()  # Store the binary data in the database
                student.audio_filename = audio_filename

        # Process the recorded audio if provided
        amplified_audio_data = request.form.get('recorded_audio')
        if amplified_audio_data:
            # Decode the base64 encoded data part from Data URL
            header, encoded = amplified_audio_data.split(',', 1)
            audio_data = base64.b64decode(encoded)

            # Determine format based on browser (Safari or other) and save accordingly
            is_safari = 'audio/mp4' in header
            temp_audio_path = os.path.join(app.config['UPLOAD_FOLDER'], 'temp_audio.' + ('mp4' if is_safari else 'webm'))
            
            with open(temp_audio_path, 'wb') as temp_file:
                temp_file.write(audio_data)

            # Convert to MP3 based on format
            try:
                if is_safari:
                    audio = AudioSegment.from_file(temp_audio_path, format="mp4")
                else:
                    audio = AudioSegment.from_file(temp_audio_path, format="webm")
                
                # Save as MP3
                mp3_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{student.id}_audio.mp3")
                audio.export(mp3_path, format="mp3")

                # Save the MP3 data and filename in the database
                with open(mp3_path, 'rb') as mp3_file:
                    student.audio_file = mp3_file.read()
                    student.audio_filename = f"{student.id}_audio.mp3"
            except Exception as e:
                print("Error converting audio file:", e)
                return "Audio conversion error", 500
            finally:
                os.remove(temp_audio_path)  # Clean up temporary audio file

        db.session.commit()
        return redirect(url_for('view_student', id=student.id))

    return render_template('edit_student.html', student=student)


# Run the App
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5005, host='0.0.0.0')