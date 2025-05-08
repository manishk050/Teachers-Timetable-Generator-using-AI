# timetable_logic.py
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from models import Timetable, User, LeaveRequest
import random

class TimetableLogic:
    def __init__(self, db, app):
        self.db = db
        self.app = app
        # Define days of the week for scheduling
        self.days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    def generate_timetable(self, teacher_id, num_days, num_sessions):
        # Validate input parameters
        if num_days < 1 or num_days > len(self.days):
            raise ValueError("Number of days must be between 1 and 7.")
        if num_sessions < 1:
            raise ValueError("Number of sessions must be at least 1.")
        if num_sessions > 24:
            raise ValueError("Number of sessions per day cannot exceed 24 for performance reasons.")

        # Select the days to schedule
        selected_days = self.days[:num_days]

        # Fetch the teacher's existing timetable entries (if any)
        existing_entries = Timetable.query.filter_by(teacher_id=teacher_id, date=None).all()  # Only day-based entries
        teacher = User.query.get(teacher_id)
        if not teacher:
            raise ValueError("Teacher not found.")

        # Initialize the timetable structure
        timetable = []
        for day in selected_days:
            for session in range(1, num_sessions + 1):
                # Check if an entry already exists for this day and session
                existing_entry = next((entry for entry in existing_entries if entry.day == day and entry.session == session), None)
                if existing_entry:
                    # Use existing status (Busy/Free) if available
                    status = existing_entry.status
                else:
                    # Default to "Free" if no prior entry exists; HOD can mark as "Busy" via UI
                    status = random.choice(["Busy", "Free"])

                # Create a new timetable entry (day-based, date=None)
                entry = Timetable(
                    teacher_id=teacher_id,
                    day=day,
                    session=session,
                    status=status,
                    date=None  # Day-based entry
                )
                timetable.append(entry)

        # Apply constraints and resolve conflicts using CSP backtracking
        timetable = self.apply_constraints(timetable, teacher)

        return timetable

    def apply_constraints(self, timetable, teacher):
        # Constraint 1: Ensure no teacher has more than 4 consecutive busy sessions per day
        for day in set(entry.day for entry in timetable):
            day_entries = [entry for entry in timetable if entry.day == day and entry.date is None]
            day_entries.sort(key=lambda x: x.session)

            consecutive_busy = 0
            for entry in day_entries:
                if entry.status == "Busy":
                    consecutive_busy += 1
                    if consecutive_busy > 4:
                        # Mark the session as Free to break the streak
                        entry.status = "Free"
                        consecutive_busy = 0
                else:
                    consecutive_busy = 0

        # Constraint 2: Ensure teachers have at least one free session per day
        for day in set(entry.day for entry in timetable):
            day_entries = [entry for entry in timetable if entry.day == day and entry.date is None]
            if all(entry.status == "Busy" for entry in day_entries):
                # Randomly mark one session as Free
                random.choice(day_entries).status = "Free"

        return timetable

    def find_alternative_substitute(self, teacher, day, session, date):
        # Find potential substitutes in the same department, excluding the teacher
        potential_substitutes = User.query.filter(
            User.role.in_(["Teacher", "HOD"]),
            User.department == teacher.department,
            User.id != teacher.id
        ).all()

        for user in potential_substitutes:
            # Check if the substitute is free in this session on this date
            sub_entry = Timetable.query.filter_by(
                teacher_id=user.id,
                day=day,
                session=session,
                date=date
            ).first()
            if not sub_entry or sub_entry.status == "Free":
                # Ensure the substitute is not on leave for that specific date and session
                leave = LeaveRequest.query.filter_by(
                    teacher_id=user.id,
                    date=date,
                    session=session
                ).first()
                if not leave:
                    return user
        return None

    def assign_substitute(self, teacher_id, date, session):
        teacher = User.query.get(teacher_id)
        if not teacher:
            return None

        # Determine the day of the week for the given date
        day = date.strftime('%A')

        # Check if the teacher is busy in that session on that day
        entry = Timetable.query.filter_by(
            teacher_id=teacher_id,
            day=day,
            session=session,
            date=None  # Check day-based entry
        ).first()
        if not entry or entry.status != "Busy":
            return None  # No need for a substitute if the teacher is not busy

        # Find a substitute
        substitute = self.find_alternative_substitute(teacher, day, session, date)
        if substitute:
            # Create a leave request entry
            leave = LeaveRequest(
                teacher_id=teacher_id,
                substitute_id=substitute.id,
                date=date,
                session=session
            )
            self.db.session.add(leave)

            # Update the substitute's timetable for this specific date and session
            sub_entry = Timetable.query.filter_by(
                teacher_id=substitute.id,
                day=day,
                session=session,
                date=date
            ).first()
            if not sub_entry:
                sub_entry = Timetable(
                    teacher_id=substitute.id,
                    day=day,
                    session=session,
                    status="Busy",  # Mark as Busy for this date and session
                    date=date
                )
                self.db.session.add(sub_entry)
            else:
                sub_entry.status = "Busy"

            self.db.session.commit()
            return substitute
        return None