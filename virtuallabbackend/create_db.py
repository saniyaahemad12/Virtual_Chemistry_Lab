import json
import os
from app import db, Assignment, app

# Load assignments from JSON file
ASSIGNMENTS_FILE = os.path.join(os.path.dirname(__file__), 'assignments.json')

def migrate_assignments_to_db():
    with open(ASSIGNMENTS_FILE, 'r') as f:
        assignments = json.load(f)

    for assignment in assignments:
        new_assignment = Assignment(
            id=assignment['id'],
            teacher_email=assignment['teacher_email'],
            student_email=assignment['student_email'],
            assignment_type=assignment['assignment_type'],
            title=assignment['title'],
            instructions=assignment['instructions'],
            result=assignment.get('result'),
            evaluation=assignment.get('evaluation')
        )
        db.session.add(new_assignment)

    try:
        db.session.commit()
        print("Assignments migrated successfully.")
    except Exception as e:
        db.session.rollback()
        print(f"Error migrating assignments: {str(e)}")

if __name__ == "__main__":
    with app.app_context():
        migrate_assignments_to_db()


