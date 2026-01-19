from flask_sqlalchemy import SQLAlchemy
import uuid

# Initialize the database
db = SQLAlchemy()

# Define the Assignment model
class Assignment(db.Model):
    __tablename__ = "assignments"
    id = db.Column(db.String, primary_key=True, default=lambda: str(uuid.uuid4()))
    teacher_email = db.Column(db.String, nullable=False)
    student_email = db.Column(db.String, nullable=False)
    assignment_type = db.Column(db.String, nullable=False)
    title = db.Column(db.String, nullable=False)
    instructions = db.Column(db.Text, nullable=True)
    result = db.Column(db.Text, nullable=True)
    evaluation = db.Column(db.Text, nullable=True)