# app.py
import os
from flask import Flask, render_template, request, redirect, url_for, flash, current_app, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer
from database import db
from timetable_logic import TimetableLogic
import random
from datetime import datetime
from models import User, Timetable, LeaveRequest

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'manishk'  

# Define the path for the database
os.makedirs(os.path.join(os.getcwd(), 'instance'), exist_ok=True)
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(os.getcwd(), 'instance', 'timetable.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'manishpkharatamal@gmail.com'
app.config['MAIL_PASSWORD'] = 'jbhq dzwq hsgi xfev'

# Initialize extensions
db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
mail = Mail(app)
serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])

# Flask-Login user loader
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Timetable logic instance
timetable_logic = TimetableLogic(db, app)

# Initialize database tables before any routes are accessed
with app.app_context():
    try:
        db.create_all()
        print("Database tables created successfully.")
    except Exception as e:
        print(f"Error creating database tables: {e}")

# Root route: Redirect to login if not authenticated
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

# Registration route
@app.route('/register', methods=['GET', 'POST'])
def register():
    from models import User
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        department = request.form['department']

        if not all([username, email, password, department]):
            flash('All fields are required.', 'danger')
            return redirect(url_for('register'))

        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'danger')
            return redirect(url_for('register'))
        if User.query.filter_by(email=email).first():
            flash('Email already exists.', 'danger')
            return redirect(url_for('register'))

        new_hod = User(username=username, email=email, role="HOD", department=department)
        new_hod.set_password(password)
        db.session.add(new_hod)
        db.session.commit()

        login_user(new_hod)
        flash('HOD registered successfully!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('register.html')

# Add Teacher route 
@app.route('/add_teacher', methods=['GET', 'POST'])
@login_required
def add_teacher():
    if current_user.role != "HOD":
        flash('Only HODs can add teachers.', 'danger')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        department = current_user.department  # HOD can only add to their own department

        if not all([username, email, password]):
            flash('All fields are required.', 'danger')
            return redirect(url_for('add_teacher'))

        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'danger')
            return redirect(url_for('add_teacher'))
        if User.query.filter_by(email=email).first():
            flash('Email already exists.', 'danger')
            return redirect(url_for('add_teacher'))

        new_teacher = User(username=username, email=email, role="Teacher", department=department)
        new_teacher.set_password(password)
        db.session.add(new_teacher)
        db.session.commit()

        flash(f'Teacher {username} added successfully!', 'success')
        return redirect(url_for('create_timetable', user_id=new_teacher.id))

    return render_template('add_teacher.html')

# Create Timetable route (Modified to generate and allow editing, with no session limit)
@app.route('/create_timetable/<int:user_id>', methods=['GET', 'POST'])
@app.route('/create_timetable', methods=['GET', 'POST'])
@login_required
def create_timetable(user_id=None):
    if current_user.role != "HOD":
        flash('Only HODs can create timetables.', 'danger')
        return redirect(url_for('dashboard'))

    target_user = current_user if user_id is None else User.query.get_or_404(user_id)
    if user_id and target_user.role != "Teacher":
        flash('You can only create timetables for teachers.', 'danger')
        return redirect(url_for('dashboard'))
    if user_id and target_user.department != current_user.department:
        flash('You can only create timetables for teachers in your department.', 'danger')
        return redirect(url_for('dashboard'))

    # Define the days of the week
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    if request.method == 'POST':
        # Get the number of days and sessions from the form
        num_days = int(request.form.get('num_days', 5))
        num_sessions = int(request.form.get('num_sessions', 5))

        # Validate input
        if num_days < 1 or num_days > 7:
            flash('Number of days must be between 1 and 7.', 'danger')
            return redirect(url_for('create_timetable', user_id=user_id))
        if num_sessions < 1:
            flash('Number of sessions must be at least 1.', 'danger')
            return redirect(url_for('create_timetable', user_id=user_id))
        if num_sessions > 24:
            flash('Number of sessions per day cannot exceed 24 for performance reasons.', 'danger')
            return redirect(url_for('create_timetable', user_id=user_id))

        # Use only the selected number of days
        selected_days = days[:num_days]

        # Check if the form is submitting the initial request to generate the timetable
        if 'generate' in request.form:
            # Generate the initial timetable using TimetableLogic
            try:
                timetable = timetable_logic.generate_timetable(target_user.id, num_days, num_sessions)
            except ValueError as e:
                flash(str(e), 'danger')
                return redirect(url_for('create_timetable', user_id=user_id))

            # Convert timetable to a dictionary for easier rendering in the template
            timetable_dict = {}
            for entry in timetable:
                if entry.day not in timetable_dict:
                    timetable_dict[entry.day] = {}
                timetable_dict[entry.day][entry.session] = entry.status

            # Render the timetable for editing
            return render_template(
                'create_timetable.html',
                target_user=target_user,
                days=selected_days,
                num_sessions=num_sessions,
                timetable_dict=timetable_dict,
                generated=True  # Flag to indicate the timetable has been generated
            )

        # Check if the form is submitting the edited timetable
        if 'save' in request.form:
            # Clear existing day-based timetable for the user (preserve date-specific entries)
            Timetable.query.filter_by(teacher_id=target_user.id, date=None).delete()

            # Save the edited timetable based on checkbox inputs
            for day in selected_days:
                for session in range(1, num_sessions + 1):
                    checkbox_name = f"busy-{day}-{session}"
                    status = "Busy" if checkbox_name in request.form else "Free"
                    entry = Timetable(
                        teacher_id=target_user.id,
                        day=day,
                        session=session,
                        status=status,
                        date=None  # Day-based entry
                    )
                    db.session.add(entry)

            db.session.commit()
            flash(f'Timetable created/updated for {target_user.username}!', 'success')
            return redirect(url_for('dashboard'))

    return render_template('create_timetable.html', target_user=target_user)

# Reset Teacher Password (HOD only, restricted to their department)
@app.route('/reset_teacher_password/<int:teacher_id>', methods=['POST'])
@login_required
def reset_teacher_password(teacher_id):
    from models import User
    if current_user.role != "HOD":
        flash('Only HODs can reset teacher passwords.', 'danger')
        return redirect(url_for('dashboard'))

    teacher = User.query.get_or_404(teacher_id)
    if teacher.role != "Teacher":
        flash('You can only reset passwords for teachers.', 'danger')
        return redirect(url_for('dashboard'))
    if teacher.department != current_user.department:
        flash('You can only reset passwords for teachers in your department.', 'danger')
        return redirect(url_for('dashboard'))

    new_password = request.form['new_password']
    if not new_password:
        flash('New password is required.', 'danger')
        return redirect(url_for('dashboard'))

    teacher.set_password(new_password)
    db.session.commit()
    flash(f'Password reset for {teacher.username}.', 'success')
    return redirect(url_for('dashboard'))

# Remove Teacher (HOD only, restricted to their department)
@app.route('/remove_teacher/<int:teacher_id>', methods=['POST'])
@login_required
def remove_teacher(teacher_id):
    from models import User, Timetable, LeaveRequest
    if current_user.role != "HOD":
        flash('Only HODs can remove teachers.', 'danger')
        return redirect(url_for('dashboard'))

    teacher = User.query.get_or_404(teacher_id)
    if teacher.role != "Teacher":
        flash('You can only remove teachers.', 'danger')
        return redirect(url_for('dashboard'))
    if teacher.department != current_user.department:
        flash('You can only remove teachers in your department.', 'danger')
        return redirect(url_for('dashboard'))

    Timetable.query.filter_by(teacher_id=teacher.id).delete()
    LeaveRequest.query.filter_by(teacher_id=teacher.id).delete()
    LeaveRequest.query.filter_by(substitute_id=teacher.id).delete()
    db.session.delete(teacher)
    db.session.commit()
    flash(f'Teacher {teacher.username} has been removed.', 'success')
    return redirect(url_for('dashboard'))

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    from models import User
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            flash('Logged in successfully!', 'success')
            return redirect(url_for('dashboard'))
        flash('Invalid username or password.', 'danger')
    return render_template('login.html')

# Logout route
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('login'))

# Dashboard route (Updated to show calendar)
@app.route('/dashboard')
@login_required
def dashboard():
    from models import User, Timetable
    teachers = []
    if current_user.role == "HOD":
        teachers = User.query.filter_by(role="Teacher", department=current_user.department).all()
    return render_template('dashboard.html', teachers=teachers)

# Fetch leave events for the calendar
@app.route('/get_leave_events')
@login_required
def get_leave_events():
    from models import LeaveRequest
    leave_requests = LeaveRequest.query.filter_by(teacher_id=current_user.id).all()
    events = [
        {
            'title': 'On Leave',
            'start': leave.date.isoformat(),
            'allDay': True,
            'color': 'red'
        } for leave in leave_requests
    ]
    return jsonify(events)

# Fetch timetable for a specific date (Updated to prioritize date-specific entries)
@app.route('/get_timetable')
@login_required
def get_timetable():
    from models import Timetable, LeaveRequest, User
    date_str = request.args.get('date')
    try:
        selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD.'}), 400

    day_of_week = selected_date.strftime('%A')  # e.g., "Tuesday"

    # Get day-based timetable entries
    day_based_entries = Timetable.query.filter_by(teacher_id=current_user.id, day=day_of_week, date=None).all()
    # Get date-specific timetable entries
    date_specific_entries = Timetable.query.filter_by(teacher_id=current_user.id, date=selected_date).all()
    # Get leave requests for the specific date
    leave_requests = LeaveRequest.query.filter_by(teacher_id=current_user.id, date=selected_date).all()
    on_leave_sessions = {leave.session: leave for leave in leave_requests}

    # Combine and prioritize entries: date-specific > leave requests > day-based
    timetable_data = []
    all_sessions = set(entry.session for entry in day_based_entries + date_specific_entries)
    for session in sorted(all_sessions):
        # Check date-specific entry first
        date_entry = next((entry for entry in date_specific_entries if entry.session == session), None)
        if date_entry:
            status = date_entry.status
            substitute = None
        # Check leave request next
        elif session in on_leave_sessions:
            status = 'On Leave'
            leave = on_leave_sessions[session]
            substitute = User.query.get(leave.substitute_id).username if leave.substitute_id else None
        # Fall back to day-based entry
        else:
            day_entry = next((entry for entry in day_based_entries if entry.session == session), None)
            status = day_entry.status if day_entry else "Free"
            substitute = None
        timetable_data.append({
            'session': session,
            'status': status,
            'substitute': substitute
        })
    return jsonify(timetable_data)

# Apply Leave route (Updated to handle date-specific assignments)
@app.route('/apply_leave', methods=['POST'])
@login_required
def apply_leave():
    from models import User, Timetable, LeaveRequest
    if current_user.role not in ["Teacher", "HOD"]:
        flash('Only teachers and HODs can apply for leave.', 'danger')
        return redirect(url_for('dashboard'))

    date_str = request.form['date']
    session = int(request.form['session'])
    try:
        selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        flash('Invalid date format.', 'danger')
        return redirect(url_for('dashboard'))

    day_of_week = selected_date.strftime('%A')

    # Check if the user is busy on that day
    day_entry = Timetable.query.filter_by(
        teacher_id=current_user.id,
        day=day_of_week,
        session=session,
        date=None
    ).first()
    if not day_entry or day_entry.status != "Busy":
        flash('You are not scheduled for that session on that day.', 'warning')
        return redirect(url_for('dashboard'))

    # Check for existing leave request
    if LeaveRequest.query.filter_by(teacher_id=current_user.id, date=selected_date, session=session).first():
        flash('Leave already requested for that date and session.', 'warning')
        return redirect(url_for('dashboard'))

    # Find a substitute using TimetableLogic
    substitute = timetable_logic.assign_substitute(current_user.id, selected_date, session)
    if not substitute:
        flash('No substitute available.', 'danger')
        return redirect(url_for('dashboard'))

    # Notify HOD and substitute
    if current_user.role == "Teacher":
        hod = User.query.filter_by(role="HOD", department=current_user.department).first()
        if hod:
            msg = Message("New Leave Request", sender=app.config['MAIL_USERNAME'], recipients=[hod.email])
            msg.body = f"Teacher {current_user.username} requested leave on {selected_date}, session {session}."
            try:
                mail.send(msg)
            except Exception as e:
                flash('Leave request submitted, but email notification to HOD failed.', 'warning')
    else:
        other_hod = User.query.filter_by(role="HOD", department=current_user.department).filter(User.id != current_user.id).first()
        if other_hod:
            msg = Message("New Leave Request", sender=app.config['MAIL_USERNAME'], recipients=[other_hod.email])
            msg.body = f"HOD {current_user.username} requested leave on {selected_date}, session {session}."
            try:
                mail.send(msg)
            except Exception as e:
                flash('Leave request submitted, but email notification to other HOD failed.', 'warning')

    msg_sub = Message("Substitute Assignment", sender=app.config['MAIL_USERNAME'], recipients=[substitute.email])
    msg_sub.body = f"You are substituting for {current_user.username} on {selected_date}, session {session}."
    try:
        mail.send(msg_sub)
    except Exception as e:
        flash('Leave request submitted, but email notification to substitute failed.', 'warning')

    flash('Leave request submitted successfully!', 'success')
    return redirect(url_for('dashboard'))

# Report route (HOD only, show leave requests from their department)
@app.route('/report')
@login_required
def report():
    from models import User, LeaveRequest
    if current_user.role != "HOD":
        flash('Only HODs can view reports.', 'danger')
        return redirect(url_for('dashboard'))

    leaves = LeaveRequest.query.join(User, LeaveRequest.teacher_id == User.id).filter(User.department == current_user.department).all()
    return render_template('report.html', leaves=leaves)

# Password reset request route
@app.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    from models import User
    if request.method == 'POST':
        email = request.form['email']
        user = User.query.filter_by(email=email).first()
        if user:
            if user.role != "HOD":
                flash('Please contact the HOD to reset your password.', 'danger')
                return redirect(url_for('login'))
            token = serializer.dumps(user.id, salt='password-reset-salt')
            reset_url = url_for('reset_password', token=token, _external=True)
            msg = Message("Password Reset Request", sender=app.config['MAIL_USERNAME'], recipients=[email])
            msg.body = f"To reset your password, visit this link: {reset_url}\nThis link will expire in 1 hour."
            try:
                mail.send(msg)
                flash('An email has been sent with instructions to reset your password.', 'success')
            except Exception as e:
                flash('Failed to send reset email. Please try again later.', 'danger')
        else:
            flash('No account found with that email address.', 'danger')
        return redirect(url_for('login'))
    return render_template('reset_password_request.html')

# Password reset route
@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    from models import User
    try:
        user_id = serializer.loads(token, salt='password-reset-salt', max_age=3600)
        user = User.query.get(user_id)
    except:
        flash('The reset link is invalid or has expired.', 'danger')
        return redirect(url_for('login'))

    if user.role != "HOD":
        flash('Please contact the HOD to reset your password.', 'danger')
        return redirect(url_for('login'))

    if request.method == 'POST':
        password = request.form['password']
        user.set_password(password)
        db.session.commit()
        flash('Your password has been updated! Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('reset_password.html')

if __name__ == '__main__':
    app.run(debug=True)