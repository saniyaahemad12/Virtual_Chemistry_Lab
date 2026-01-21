

import os
import uuid
from datetime import timedelta
from flask import Flask, request, jsonify, send_from_directory, abort
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer
import smtplib
from email.mime.text import MIMEText

# --- Optional simulation module ---
try:
    from simulation import simulate_reaction, reactions_data
except:
    def simulate_reaction(reactants):
        return {"error": "simulation module not available"}
    reactions_data = []

# --- Configuration ---
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
FRONTEND_DIR = os.environ.get("FRONTEND_DIR", os.path.abspath(os.path.join(BASE_DIR, "../Virtual Chemistry Lab")))

app = Flask(__name__, static_folder=None)
CORS(app)

# MySQL DB config
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:Saniya%40123@localhost/virtual_chemistry_lab'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = 'e5b8c3f4a1d2e6f7b9c8d4a3e7f6b5c4d3a2e1f8c7b6a5d4e3f2b1c8d7a6f5e4'
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(days=7)

# Email config (for contact form / password reset)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get("MAIL_USERNAME", "your-email@gmail.com")
app.config['MAIL_PASSWORD'] = os.environ.get("MAIL_PASSWORD", "your-email-password")

mail = Mail(app)
s = URLSafeTimedSerializer(app.config['JWT_SECRET_KEY'])

db = SQLAlchemy(app)
jwt = JWTManager(app)

# --- Models ---
class Teacher(db.Model):
    __tablename__ = "teachers"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)

class Student(db.Model):
    __tablename__ = "students"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)



# --- Routes: Frontend Serving ---
def serve_file(filename):
    path = os.path.join(FRONTEND_DIR, "templates", filename)
    if os.path.exists(path):
        return send_from_directory(os.path.dirname(path), os.path.basename(path))
    return jsonify({"error": f"{filename} not found"}), 404

@app.route("/")
def index():
    return serve_file("index.html")

@app.route("/chatbot")
def chatbot():
    return serve_file("chatbot.html")

@app.route("/lab")
def lab():
    return serve_file("lab.html")

@app.route("/student_dashboard")
def student_dashboard():
    return serve_file("student_dashboard.html")

@app.route("/teacher_dashboard")
def teacher_dashboard():
    return serve_file("teacher_dashboard.html")

@app.route("/<path:filename>")
def static_files(filename):
    file_path = os.path.join(FRONTEND_DIR, filename)
    if os.path.exists(file_path) and os.path.commonpath([os.path.abspath(file_path), FRONTEND_DIR]) == os.path.abspath(FRONTEND_DIR):
        return send_from_directory(FRONTEND_DIR, filename)
    abort(404)

# --- Auth Routes ---
@app.route('/register_teacher', methods=['POST'])
def register_teacher():
    data = request.get_json()
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Missing required fields'}), 400
    if Teacher.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Teacher already exists'}), 400
    teacher = Teacher(name=data.get('name'), email=data['email'], password=generate_password_hash(data['password']))
    db.session.add(teacher)
    db.session.commit()
    return jsonify({'message': 'Teacher registered successfully'}), 201

@app.route('/register_student', methods=['POST'])
def register_student():
    data = request.get_json()
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Missing required fields'}), 400
    if Student.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Student already exists'}), 400
    student = Student(name=data.get('name'), email=data['email'], password=generate_password_hash(data['password']))
    db.session.add(student)
    db.session.commit()
    return jsonify({'message': 'Student registered successfully'}), 201

@app.route('/login_teacher', methods=['POST'])
def login_teacher():
    data = request.get_json()
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Missing fields'}), 400
    teacher = Teacher.query.filter_by(email=data['email']).first()
    if not teacher or not check_password_hash(teacher.password, data['password']):
        return jsonify({'error': 'Invalid email or password'}), 401
    token = create_access_token(identity={'id': teacher.id, 'email': teacher.email, 'role': 'teacher'})
    return jsonify({'token': token}), 200

@app.route('/login_student', methods=['POST'])
def login_student():
    data = request.get_json()
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Missing fields'}), 400
    student = Student.query.filter_by(email=data['email']).first()
    if not student or not check_password_hash(student.password, data['password']):
        return jsonify({'error': 'Invalid email or password'}), 401
    token = create_access_token(identity={'id': student.id, 'email': student.email, 'role': 'student'})
    return jsonify({'token': token}), 200


@app.route('/assign_experiment', methods=['POST'])
@jwt_required()
def assign_experiment():
    current_user = get_jwt_identity()

    # 1️⃣ Role check
    if current_user.get('role') != 'teacher':
        return jsonify({"error": "Only teachers can assign tasks"}), 403

    # 2️⃣ ADD THIS BLOCK HERE ⬇️⬇️⬇️
    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing JSON body"}), 400

    student_emails = data.get('student_emails')
    assignment_type = data.get('assignment_type')
    title = data.get('title')
    instructions = data.get('instructions', '')

    if not student_emails or not assignment_type or not title:
        return jsonify({"error": "Missing required fields"}), 422
    # ⬆️⬆️⬆️ END HERE

    teacher_id = current_user['id']
    created_assignments = []

    for email in student_emails:
        student = Student.query.filter_by(email=email).first()
        if not student:
            continue

        new_assignment = Assignment(
            id=str(uuid.uuid4()),   # IMPORTANT
            teacher_id=teacher_id,
            student_id=student.id,
            assignment_type=assignment_type,
            title=title,
            instructions=instructions
        )

        db.session.add(new_assignment)
        created_assignments.append({
            "student_email": student.email,
            "id": new_assignment.id
        })

    try:
        db.session.commit()
        return jsonify({
            "success": True,
            "assigned_to": [a["student_email"] for a in created_assignments],
            "assignments": created_assignments
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@app.route('/get_students', methods=['GET'])
@jwt_required()
def get_students():
    students = Student.query.all()
    student_list = [{"name": s.name, "email": s.email} for s in students]
    return jsonify(student_list), 200


@app.route("/student_assignments", methods=['GET'])
@jwt_required()
def get_student_assignments():
    user = get_jwt_identity()
    if user.get('role') != 'student':
        return jsonify({"error": "Only students can view assignments"}), 403
    assignments = Assignment.query.filter_by(student_id=user['id']).all()
    return jsonify([{
        'title': a.title,
        'instructions': a.instructions,
        'type': a.assignment_type,
        'result': a.result
    } for a in assignments])

@app.route("/submit_task", methods=['POST'])
@jwt_required()
def submit_task():
    data = request.get_json()
    task_id = data.get('task_id')
    submission = data.get('submission')
    assignment = Assignment.query.get(task_id)
    if not assignment:
        return jsonify({"error": "Assignment not found"}), 404
    assignment.result = submission
    db.session.commit()
    return jsonify({"success": True}), 200
@app.route('/teacher_assignments', methods=['GET'])
@jwt_required()
def teacher_assignments():
    current_user = get_jwt_identity()
    if current_user.get('role') != 'teacher':
        return jsonify({"error": "Only teachers can view assignments"}), 403

    teacher_id = current_user['id']
    assignments = Assignment.query.filter_by(teacher_id=teacher_id).all()

    result = []
    for a in assignments:
        student = Student.query.get(a.student_id)
        result.append({
            "id": a.id,
            "student_email": student.email if student else "Unknown",
            "assignment_type": a.assignment_type,
            "title": a.title,
            "instructions": a.instructions,
            "result": a.result
        })

    return jsonify(result)


@app.route("/evaluate_task", methods=['POST'])
@jwt_required()
def evaluate_task():
    data = request.get_json()
    task_id = data.get('task_id')
    evaluation = data.get('evaluation')
    assignment = Assignment.query.get(task_id)
    if not assignment:
        return jsonify({"error": "Assignment not found"}), 404
    assignment.evaluation = evaluation
    db.session.commit()
    return jsonify({"success": True})

# --- Reactions & Simulation ---
@app.route("/reactions", methods=["GET"])
def reactions():
    return jsonify([{"reactants": r.get("reactants"), "products": r.get("products"), "reactionType": r.get("reactionType")} for r in reactions_data])

@app.route("/simulate", methods=["POST"])
def simulate():
    data = request.get_json()
    if not data or not data.get("reactants"):
        return jsonify({"error": "Missing reactants"}), 400
    result = simulate_reaction(data["reactants"])
    return jsonify(result)

# --- Experiments ---
EXPERIMENTS_BY_CLASS = {9:[{"id":1,"title":"Separation of Mixtures","description":"Learn to separate mixtures."}]}  # Shortened for brevity
@app.route("/experiments", methods=["GET"])
def list_experiments():
    all_exps=[]
    for cls_exps in EXPERIMENTS_BY_CLASS.values():
        all_exps.extend(cls_exps)
    return jsonify(all_exps)

@app.route("/experiments_for_class", methods=["POST"])
def experiments_for_class():
    data=request.get_json(silent=True) or {}
    try: class_num=int(data.get("class",0))
    except: return jsonify([])
    return jsonify(EXPERIMENTS_BY_CLASS.get(class_num,[]))

# --- Contact Form ---
@app.route("/contact", methods=["POST"])
def contact():
    data=request.get_json()
    if not data or not data.get("name") or not data.get("email") or not data.get("message"):
        return jsonify({"error":"Missing fields"}),400
    try:
        with open(os.path.join(BASE_DIR,"contact_submissions.txt"),"a",encoding="utf-8") as f:
            f.write(f"Name:{data['name']}, Email:{data['email']}, Message:{data['message']}\n---\n")
    except Exception as e: app.logger.error(e)
    # Optional: send email
    return jsonify({"message":"Message received"}),200

# --- Forgot / Reset Password ---
@app.route("/forgot_password", methods=['POST'])
def forgot_password():
    data = request.get_json()
    email = data.get("email")
    user = Teacher.query.filter_by(email=email).first()
    if not user:
        return jsonify({"error":"Email not found"}),404
    token = s.dumps(email, salt="password-reset")
    reset_url=f"http://localhost:5000/reset_password/{token}"
    msg = Message(subject="Reset Password", sender=app.config['MAIL_USERNAME'], recipients=[email],
                  body=f"Click to reset: {reset_url}")
    mail.send(msg)
    return jsonify({"message":"Reset link sent"}),200

@app.route("/reset_password/<token>", methods=['GET','POST'])
def reset_password(token):
    try: email = s.loads(token,salt="password-reset",max_age=3600)
    except: return "Invalid or expired link"
    if request.method=="POST":
        new_pass=request.form.get("password")
        user = Teacher.query.filter_by(email=email).first()
        user.password = generate_password_hash(new_pass)
        db.session.commit()
        return "Password updated! <a href='/login_teacher.html'>Login</a>"
    return """<form method='POST'><input type='password' name='password' placeholder='New Password'><button>Reset</button></form>"""

# --- Error Handlers ---
@app.errorhandler(404)
def not_found(e): return jsonify({"error":"Not Found"}),404
@app.errorhandler(500)
def internal_error(e): return jsonify({"error":"Internal Server Error"}),500

# --- Run App ---
if __name__=="__main__":
    with app.app_context(): db.create_all()
    app.run(debug=True)
