import json
import os
import uuid
from app import db, Assignment

USERS_FILE = os.path.join(os.path.dirname(__file__), 'users.json')
ASSIGNMENTS_FILE = os.path.join(os.path.dirname(__file__), 'assignments.json')

# Helper functions for user and assignment management

def load_json(path):
    if not os.path.exists(path):
        return []
    with open(path, 'r') as f:
        return json.load(f)

def save_json(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)

def add_user(user):
    users = load_json(USERS_FILE)
    users.append(user)
    save_json(USERS_FILE, users)

def get_user(email):
    users = load_json(USERS_FILE)
    for user in users:
        if user['email'] == email:
            return user
    return None

def add_assignment(assignment):
    teacher_email = assignment.get("teacher_email")
    student_email = assignment.get("student_email")
    assignment_type = assignment.get("assignment_type")
    title = assignment.get("title")
    instructions = assignment.get("instructions")

    if not teacher_email or not student_email or not assignment_type or not title:
        raise ValueError("Missing required fields in assignment.")

    new_assignment = Assignment(
        id=str(uuid.uuid4()),
        teacher_email=teacher_email,
        student_email=student_email,
        assignment_type=assignment_type,
        title=title,
        instructions=instructions
    )
    db.session.add(new_assignment)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise Exception(f"Error saving assignment: {str(e)}")

def get_assignments_for_student(student_email):
    assignments = load_json(ASSIGNMENTS_FILE)
    return [a for a in assignments if a['student_email'] == student_email]

def get_assignments_for_teacher(teacher_email):
    assignments = load_json(ASSIGNMENTS_FILE)
    return [a for a in assignments if a['teacher_email'] == teacher_email]

def update_assignment_result(assignment_id, result):
    assignments = load_json(ASSIGNMENTS_FILE)
    for a in assignments:
        if a['id'] == assignment_id:
            a['result'] = result
    save_json(ASSIGNMENTS_FILE, assignments)
