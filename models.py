# models.py
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from datetime import date
from database import db

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # "HOD" or "Teacher"
    department = db.Column(db.String(50), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Timetable(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    day = db.Column(db.String(10), nullable=False)  # e.g., "Monday"
    date = db.Column(db.Date, nullable=True)  # Specific date, e.g., 2025-04-10
    session = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(10), nullable=False)  # e.g., "Busy", "Free"
    substitute_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    teacher = db.relationship('User', foreign_keys=[teacher_id])
    substitute = db.relationship('User', foreign_keys=[substitute_id])

class LeaveRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    substitute_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    date = db.Column(db.Date, nullable=False)  # Specific date, e.g., 2025-04-10
    session = db.Column(db.Integer, nullable=False)
    teacher = db.relationship('User', foreign_keys=[teacher_id])
    substitute = db.relationship('User', foreign_keys=[substitute_id])