from flask_sqlalchemy import SQLAlchemy
import uuid
import datetime
from datetime import datetime
# Initialize the database
db = SQLAlchemy()

# Define the Assignment model
class Assignment(db.Model):
    __tablename__ = "assignments"

    id = db.Column(db.String(36), primary_key=True)
    
    teacher_id = db.Column(
        db.Integer,
        db.ForeignKey("teachers.id", ondelete="CASCADE"),
        nullable=False
    )

    student_id = db.Column(
        db.Integer,
        db.ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False
    )

    assignment_type = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    instructions = db.Column(db.Text)
    result = db.Column(db.String(255))
