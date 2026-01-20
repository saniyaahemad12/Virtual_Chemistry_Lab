"""
Corrected and self-contained Flask app for Virtual Chemistry Lab.
Features included:
- Static file serving for frontend directory
- Reactions listing and simulation endpoint (expects `simulation.simulate_reaction` and `simulation.reactions_data`)
- User registration and login with SQLAlchemy + JWT
- Assignment create/list/evaluate using a database model
- Contact form that logs submission and (optionally) sends email using env variables
- Basic error handling and input validation

Notes:
- Replace SMTP, FRONTEND_DIR and JWT secret with secure values in production.
- This file assumes there's a `simulation.py` in the project root providing:
    - `simulate_reaction(reactants: list) -> dict`
    - `reactions_data: list[dict]`

Install dependencies: pip install flask flask-cors flask-sqlalchemy flask-jwt-extended werkzeug
"""


import os
import uuid
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, send_from_directory, abort
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    jwt_required,
    get_jwt_identity,
)

from werkzeug.security import generate_password_hash, check_password_hash
from email.mime.text import MIMEText
import smtplib
import logging
from models import db, Assignment

# Replace 'your_secret_key' with a strong, unique key

# Optional import from your simulation module
try:
    from simulation import simulate_reaction, reactions_data  # pragma: no cover
except Exception:
    # Provide fallbacks for local development if simulation isn't available
    def simulate_reaction(reactants):
        return {"error": "simulation module not available"}

    reactions_data = []

# --- Configuration ---
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
FRONTEND_DIR = os.environ.get(
    "FRONTEND_DIR",
    os.path.abspath(os.path.join(BASE_DIR, "../Virtual Chemistry Lab")),
)
print("Database path:", os.path.join(BASE_DIR, 'virtual_lab.db'))

app = Flask(__name__, static_folder=None)
CORS(app)

# Database
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:Saniya%40123@localhost/virtual_chemistry_lab'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# Optional: token expiry
app.config['JWT_SECRET_KEY'] = 'e5b8c3f4a1d2e6f7b9c8d4a3e7f6b5c4d3a2e1f8c7b6a5d4e3f2b1c8d7a6f5e4'  # Replace 'your_secret_key' with a strong, unique key
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(days=7)

db.init_app(app)
jwt = JWTManager(app)

# --- Models ---
class Teacher(db.Model):
    __tablename__ = "teachers"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)


class Student(db.Model):
    __tablename__ = "students"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)

@app.route('/create-assignment', methods=['POST'])
@jwt_required()
def create_assignment():
    teacher_id = get_jwt_identity()
    assignments = request.get_json()

    if not isinstance(assignments, list):
        return jsonify({'error': 'Expected a list of assignments'}), 400

    created = []
    for a in assignments:
        if not all(k in a for k in ('student_email', 'assignment_type', 'title', 'instructions')):
            return jsonify({'error': 'Missing required field in assignment'}), 400

        new_assignment = Assignment(
            teacher_id=teacher_id,
            student_email=a['student_email'],
            assignment_type=a['assignment_type'],
            title=a['title'],
            instructions=a['instructions']
        )
        db.session.add(new_assignment)
        created.append(a)

    db.session.commit()
    return jsonify({'success': True, 'created': created}), 201


# Define the User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)  # Added length for VARCHAR
    email = db.Column(db.String(120), unique=True, nullable=False)
    is_teacher = db.Column(db.Boolean, default=False)

# Create the users table if it doesn't exist

# --- Updated /assign_experiment endpoint ---
@app.route("/assign_experiment", methods=["POST"])
def assign_experiment():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Missing JSON body"}), 400

    teacher_email = data.get("teacher_email")
    student_emails = data.get("student_emails", [])
    assignment_type = data.get("assignment_type")
    title = data.get("title")
    instructions = data.get("instructions")

    if not teacher_email or not student_emails or not assignment_type or not title:
        return jsonify({"error": "teacher_email, student_emails, assignment_type, and title are required"}), 400

    created_assignments = []
    for student_email in student_emails:
        if not student_email.strip():
            continue

        new_assignment = Assignment(
            id=str(uuid.uuid4()),
            teacher_email=teacher_email,
            student_email=student_email.strip(),
            assignment_type=assignment_type,
            title=title,
            instructions=instructions,
            result=None,
            evaluation=None
        )
        db.session.add(new_assignment)
        created_assignments.append(new_assignment.id)

    try:
        db.session.commit()
        return jsonify({
            "success": True,
            "created_assignments": created_assignments,
            "message": f"Assigned to {len(created_assignments)} students",
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Error saving assignments: {str(e)}"}), 500


# --- Updated /student_assignments endpoint ---
@app.route('/student_assignments/<string:email>', methods=['GET'])
def student_assignments(email):
    assignments = Assignment.query.filter_by(student_email=email).all()
    result = [{
        'title': a.title,
        'result': a.result
    } for a in assignments]
    return jsonify(result)


# --- Remove the Assignment model ---
# Delete the `Assignment` class and any related database operations.

# --- Remove other endpoints using the Assignment model ---
# Remove or update endpoints like `/teacher_assignments`, `/evaluate_assignment`, etc., to use JSON files instead of the database.

# --- Ensure the database initialization is updated ---
# Remove any references to the `Assignment` table creation in `db.create_all()`.

# --- Other unchanged code ---
# ...existing code...


@app.route("/clear_assignments", methods=["DELETE"])
def clear_assignments():
    teacher_email = request.args.get("teacher_email")
    if not teacher_email:
        return jsonify({"error": "teacher_email required"}), 400
    
    try:
        count = Assignment.query.filter_by(teacher_email=teacher_email).delete()
        db.session.commit()
        return jsonify({"success": True, "deleted_count": count}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# --- Helper functions ---
def find_user_by_email(email: str):
    return User.query.filter_by(email=email).first()


# --- Routes: static files ---
@app.route("/")
def serve_index():
    index_path = os.path.join(FRONTEND_DIR, "templates", "index.html")
    if os.path.exists(index_path):
        return send_from_directory(os.path.dirname(index_path), os.path.basename(index_path))
    return jsonify({"error": "Frontend not found"}), 404


@app.route("/chatbot")
def serve_chatbot():
    chatbot_path = os.path.join(FRONTEND_DIR, "templates", "chatbot.html")
    if os.path.exists(chatbot_path):
        return send_from_directory(os.path.dirname(chatbot_path), os.path.basename(chatbot_path))
    return jsonify({"error": "chatbot page not found"}), 404


@app.route("/lab")
def serve_lab():
    lab_path = os.path.join(FRONTEND_DIR, "templates", "lab.html")
    if os.path.exists(lab_path):
        return send_from_directory(os.path.dirname(lab_path), os.path.basename(lab_path))
    return jsonify({"error": "lab page not found"}), 404


# Serve other frontend static files safely
@app.route("/<path:filename>")
def serve_static(filename):
    file_path = os.path.join(FRONTEND_DIR, filename)
    if os.path.exists(file_path) and os.path.commonpath([os.path.abspath(file_path), FRONTEND_DIR]) == os.path.abspath(FRONTEND_DIR):
        return send_from_directory(FRONTEND_DIR, filename)
    abort(404)

 
# --- API: Reactions & Simulation ---
@app.route("/reactions", methods=["GET"])
def get_reactions():
    # Only return reactants and products for listing
    reactions_list = [
        {
            "reactants": r.get("reactants"),
            "products": r.get("products"),
            "reactionType": r.get("reactionType"),
        }
        for r in reactions_data
    ]
    return jsonify(reactions_list)


@app.route("/simulate", methods=["POST"])
def simulate():
    data = request.get_json(silent=True)
    if not data or "reactants" not in data:
        return jsonify({"error": "Missing reactants in request"}), 400
    reactants = data.get("reactants", [])
    result = simulate_reaction(reactants)
    if isinstance(result, dict) and "error" in result:
        return jsonify(result), 404
    return jsonify(result)

CORS(app, supports_credentials=True)

# --- API: Experiments listing by class ---
EXPERIMENTS_BY_CLASS = {
    9: [
        {"id": 1, "title": "Separation of Mixtures", "description": "Learn to separate mixtures."},
        {"id": 2, "title": "Physical and Chemical Changes", "description": "Observe different changes."},
    ],
    10: [
        {"id": 3, "title": "Acids, Bases and Salts", "description": "Explore acid-base reactions."},
        {"id": 4, "title": "Metals and Non-metals", "description": "Study properties of metals."},
    ],
    11: [
        {"id": 5, "title": "Titration", "description": "Perform titration experiments."},
        {"id": 6, "title": "Preparation of Solutions", "description": "Prepare chemical solutions."},
    ],
    12: [
        {"id": 7, "title": "Qualitative Analysis", "description": "Analyze unknown samples."},
        {"id": 8, "title": "Electrochemistry", "description": "Study electrochemical cells."},
    ],
}


@app.route("/experiments", methods=["GET"])
def list_experiments():
    # A simple aggregated endpoint
    all_exps = []
    for cls_exps in EXPERIMENTS_BY_CLASS.values():
        all_exps.extend(cls_exps)
    return jsonify(all_exps)


@app.route("/experiments_for_class", methods=["POST"])
def experiments_for_class():
    data = request.get_json(silent=True) or {}
    try:
        class_num = int(data.get("class", 0))
    except (ValueError, TypeError):
        return jsonify([])
    return jsonify(EXPERIMENTS_BY_CLASS.get(class_num, []))

@app.route("/evaluate_assignment", methods=["POST"])
def evaluate_assignment():
    data = request.get_json(silent=True)
    if not data or not all(k in data for k in ("assignment_id", "result")):
        return jsonify({"error": "Missing fields"}), 400
    assignment = Assignment.query.get(data["assignment_id"])
    if not assignment:
        return jsonify({"error": "Assignment not found"}), 404
    assignment.result = data["result"]
    db.session.commit()
    return jsonify({"success": True})


# --- Auth routes ---
from flask import Flask, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
# ... your other imports and app/db setup ...

@app.route('/register_teacher', methods=['POST'])
def register_teacher():
    data = request.get_json()
    if not data or 'email' not in data or 'password' not in data:
        return jsonify({'error': 'Missing required fields'}), 400

    existing_teacher = Teacher.query.filter_by(email=data['email']).first()
    if existing_teacher:
        return jsonify({'error': 'Teacher already exists'}), 400

    hashed_password = generate_password_hash(data['password'])
    new_teacher = Teacher(
        name=data.get('name'),
        email=data['email'],
        password=hashed_password
    )
    db.session.add(new_teacher)
    db.session.commit()
    return jsonify({'message': 'Teacher registered successfully!'}), 201


@app.route('/register_student', methods=['POST'])
def register_student():
    data = request.get_json()
    if not data or 'email' not in data or 'password' not in data:
        return jsonify({'error': 'Missing required fields'}), 400

    existing_student = Student.query.filter_by(email=data['email']).first()
    if existing_student:
        return jsonify({'error': 'Student already exists'}), 400

    hashed_password = generate_password_hash(data['password'])
    new_student = Student(
        name=data.get('name'),
        email=data['email'],
        password=hashed_password
    )
    try:
        db.session.add(new_student)
        db.session.commit()
        return jsonify({'message': 'Student registered successfully!'}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500


@app.route('/login_teacher', methods=['POST'])
def login_teacher():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({'error': 'Missing email or password'}), 400

    teacher = Teacher.query.filter_by(email=email).first()
    if not teacher or not check_password_hash(teacher.password, password):
        return jsonify({'error': 'Invalid email or password'}), 401

    # Ensure the role is included in the token
    token = create_access_token(identity={'id': teacher.id, 'email': teacher.email, 'role': 'teacher'})
    return jsonify({'token': token}), 200

@app.route('/login_student', methods=['POST'])
def login_student():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({'error': 'Missing email or password'}), 400

    student = Student.query.filter_by(email=email).first()
    if not student or not check_password_hash(student.password, password):
        return jsonify({'error': 'Invalid email or password'}), 401

    token = create_access_token(identity={'id': student.id, 'email': student.email, 'role': 'student'})
    return jsonify({'token': token}), 200

@app.route('/students', methods=['GET'])
def get_students():
    students = User.query.filter_by(is_teacher=False).all()
    return jsonify([
        {
            "id": student.id,
            "name": student.name,
            "email": student.email
        }
        for student in students
    ])

@app.route('/assign_task', methods=['POST'])
def assign_task():
    data = request.get_json()
    student_ids = data.get('student_ids')
    task = data.get('task')

    if not student_ids or not task:
        return jsonify({"error": "Missing student_ids or task"}), 400

    created_assignments = []
    for student_id in student_ids:
        student = User.query.get(student_id)
        if student:
            new_assignment = Assignment(
                id=str(uuid.uuid4()),
                teacher_email=data.get('teacher_email'),
                student_email=student.email,
                assignment_type="task",
                title=task,
                instructions="Complete the task as instructed.",
                result=None,
                evaluation=None
            )
            db.session.add(new_assignment)
            created_assignments.append(new_assignment.id)

    try:
        db.session.commit()
        return jsonify({"success": True, "message": "Task assigned successfully", "created_assignments": created_assignments})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to save assignments: {str(e)}"}), 500

# --- Contact form endpoint ---


@app.route('/student_details', methods=['GET'])
@jwt_required()
def student_details():
    print("Student details endpoint hit")  # Debugging
    current_user = get_jwt_identity()
    print(f"Current user from token: {current_user}")  # Debugging

    student_email = current_user.get("email") if isinstance(current_user, dict) else None
    if not student_email:
        return jsonify({"error": "Invalid token identity"}), 401

    user = User.query.filter_by(email=student_email).first()
    if not user:
        return jsonify({"error": "User not found"}), 404

    print(f"User details: {user.name}, {user.email}")  # Debugging
    return jsonify({
        "id": user.id,
        "name": user.name,
        "email": user.email
    })
    
    
    
@app.route("/contact", methods=["POST"])
def contact_form_submit():
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400
    data = request.get_json()
    name = data.get("name")
    email = data.get("email")
    message = data.get("message")

    if not name or not email or not message:
        return jsonify({"error": "All fields (name, email, message) are required."}), 400

    # Log to console and file
    app.logger.info("New Contact Form Submission: %s <%s>", name, email)
    try:
        with open(os.path.join(BASE_DIR, "contact_submissions.txt"), "a", encoding="utf-8") as f:
            f.write(f"Name: {name}, Email: {email}, Message: {message}\n---\n")
    except Exception as e:
        app.logger.error("Error saving submission to file: %s", e)

    # Send email if SMTP config provided
    SENDER_EMAIL = os.environ.get("SENDER_EMAIL")
    SENDER_PASSWORD = os.environ.get("SENDER_PASSWORD")
    RECIPIENT_EMAIL = os.environ.get("RECIPIENT_EMAIL", "zk23273@gmail.com")

    if SENDER_EMAIL and SENDER_PASSWORD:
        try:
            msg = MIMEText(f"From: {name} <{email}>\n\nMessage:\n{message}")
            msg["Subject"] = "New Contact Form Submission from Virtual Chemistry Lab"
            msg["From"] = SENDER_EMAIL
            msg["To"] = RECIPIENT_EMAIL
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
                smtp.login(SENDER_EMAIL, SENDER_PASSWORD)
                smtp.send_message(msg)
            app.logger.info("Email sent successfully to %s", RECIPIENT_EMAIL)
        except Exception as e:
            app.logger.error("Failed to send contact email: %s", e)
            # Do not fail the whole request because email failed

    return jsonify({"message": "Your message has been received."}), 200



# --- Error handlers ---
@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Not Found"}), 404


@app.errorhandler(500)
def internal_error(e):
    return jsonify({"error": "Internal Server Error"}), 500


# --- Store the token in the database for tracking purposes ---
@app.route('/store_token', methods=['POST'])
@jwt_required()
def store_token():
    data = request.get_json()
    token = data.get('token')
    teacher_email = get_jwt_identity()

    if not token:
        return jsonify({'error': 'Token is missing'}), 400

    # Store the token in the database
    new_token = Token(teacher_email=teacher_email, token=token)
    db.session.add(new_token)
    try:
        db.session.commit()
        return jsonify({'message': 'Token stored successfully'}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to store token: {str(e)}'}), 500


# --- Bootstrap DB & run ---
if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Create tables if they don't exist
        print("Database tables created!")  # Debugging
    app.run(debug=True)


# Route to serve the student dashboard
@app.route('/student_dashboard')
def serve_student_dashboard():
    dashboard_path = os.path.join(FRONTEND_DIR, "templates", "student_dashboard.html")
    if os.path.exists(dashboard_path):
        return send_from_directory(os.path.dirname(dashboard_path), os.path.basename(dashboard_path))
    return jsonify({"error": "Student dashboard not found"}), 404

# Route to serve the teacher dashboard
@app.route('/teacher_dashboard')
def serve_teacher_dashboard():
    dashboard_path = os.path.join(FRONTEND_DIR, "templates", "teacher_dashboard.html")
    if os.path.exists(dashboard_path):
        return send_from_directory(os.path.dirname(dashboard_path), os.path.basename(dashboard_path))
    return jsonify({"error": "Teacher dashboard not found"}), 404

# Endpoint for students to fetch their assignments
@app.route('/get_student_assignments', methods=['GET'])
@jwt_required()
def get_student_assignments():
    student_email = get_jwt_identity()
    assignments = Assignment.query.filter_by(student_email=student_email).all()
    return jsonify([{
        "id": a.id,
        "title": a.title,
        "instructions": a.instructions,
        "result": a.result,
        "evaluation": a.evaluation
    } for a in assignments]), 200

# Endpoint for students to submit their tasks
@app.route('/submit_task', methods=['POST'])
@jwt_required()
def submit_task():
    data = request.get_json()
    task_id = data.get('task_id')
    submission = data.get('submission')

    if not task_id or not submission:
        return jsonify({"error": "Missing task_id or submission"}), 400

    assignment = Assignment.query.get(task_id)
    if not assignment:
        return jsonify({"error": "Assignment not found"}), 404

    assignment.result = submission
    db.session.commit()
    return jsonify({"success": True, "message": "Task submitted successfully"}), 200

# Endpoint for teachers to fetch their assignments
from flask_jwt_extended import jwt_required, get_jwt_identity

@app.route('/teacher_assignments', methods=['GET'])
@jwt_required()
def teacher_assignments():
    teacher_id = get_jwt_identity()  # gets logged-in teacher's ID from token
    assignments = Assignment.query.filter_by(teacher_id=teacher_id).all()
    
    result = []
    for a in assignments:
        result.append({
            'student_email': a.student_email,
            'assignment_type': a.assignment_type,
            'title': a.title,
            'instructions': a.instructions,
            'result': a.result
        })
    return jsonify(result)


# Endpoint for teachers to evaluate student submissions
@app.route('/evaluate_task', methods=['POST'])
@jwt_required()
def evaluate_task():
    data = request.get_json()
    task_id = data.get('task_id')
    evaluation = data.get('evaluation')

    if not task_id or not evaluation:
        return jsonify({"error": "Missing task_id or evaluation"}), 400

    assignment = Assignment.query.get(task_id)
    if not assignment:
        return jsonify({"error": "Assignment not found"}), 404

    assignment.evaluation = evaluation
    db.session.commit()
    return jsonify({"success": True, "message": "Task evaluated successfully"}), 200
