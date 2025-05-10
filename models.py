from datetime import datetime
from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(10), nullable=False)  # 'mentor' or 'mentee'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    bio = db.Column(db.Text, nullable=True)
    expertise = db.Column(db.String(255), nullable=True)

    # Relationships
    availability_slots = db.relationship('AvailabilitySlot', backref='mentor', lazy=True)
    mentor_sessions = db.relationship('Session', backref='mentor', lazy=True, foreign_keys='Session.mentor_id')
    mentee_sessions = db.relationship('Session', backref='mentee', lazy=True, foreign_keys='Session.mentee_id')
    feedback_given = db.relationship('Feedback', backref='giver', lazy=True, foreign_keys='Feedback.giver_id')
    feedback_received = db.relationship('Feedback', backref='receiver', lazy=True, foreign_keys='Feedback.receiver_id')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_average_rating(self):
        feedbacks = Feedback.query.filter_by(receiver_id=self.id).all()
        if not feedbacks:
            return 0
        total = sum(feedback.rating for feedback in feedbacks)
        return round(total / len(feedbacks), 1)

    def get_session_count(self):
        if self.role == 'mentor':
            return Session.query.filter_by(mentor_id=self.id).count()
        else:
            return Session.query.filter_by(mentee_id=self.id).count()


class AvailabilitySlot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mentor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    day_of_week = db.Column(db.Integer, nullable=False)  # 0=Monday, 6=Sunday
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    is_recurring = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def is_available_for_date(self, date):
        # Check if this slot is already booked for the given date
        existing_session = Session.query.filter_by(
            mentor_id=self.mentor_id,
            session_date=date,
            start_time=self.start_time,
            end_time=self.end_time,
            status='approved'
        ).first()

        return existing_session is None


class Session(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mentor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    mentee_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    session_date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    notes = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected, completed
    meeting_url = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    feedback = db.relationship('Feedback', backref='session', lazy=True)

    def generate_meeting_url(self):
        """Generate a Google Meet URL for the session"""
        try:
            # Try to use the Google Meet API integration
            from google_meet import create_meeting_for_session

            meeting_url = create_meeting_for_session(
                session_date=self.session_date,
                start_time=self.start_time,
                end_time=self.end_time,
                mentor_name=self.mentor.username,
                mentee_name=self.mentee.username
            )

            if meeting_url:
                self.meeting_url = meeting_url
                return self.meeting_url
        except Exception as e:
            # If Google Meet API fails, fall back to mock URL
            import logging
            logging.error(f"Error generating Google Meet URL: {str(e)}")

        # Fallback to mock URL
        import uuid
        meet_code = uuid.uuid4().hex[:10]
        self.meeting_url = f"https://meet.google.com/{meet_code}"
        return self.meeting_url


class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('session.id'), nullable=False)
    giver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # 1-5 stars
    knowledge_rating = db.Column(db.Integer, nullable=True)  # 1-5 stars
    communication_rating = db.Column(db.Integer, nullable=True)  # 1-5 stars
    helpfulness_rating = db.Column(db.Integer, nullable=True)  # 1-5 stars
    comments = db.Column(db.Text, nullable=True)
    strengths = db.Column(db.Text, nullable=True)
    areas_for_improvement = db.Column(db.Text, nullable=True)
    is_anonymous = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def calculate_average_rating(self):
        """Calculate the average rating from all rating fields"""
        ratings = [self.rating]
        if self.knowledge_rating:
            ratings.append(self.knowledge_rating)
        if self.communication_rating:
            ratings.append(self.communication_rating)
        if self.helpfulness_rating:
            ratings.append(self.helpfulness_rating)

        return sum(ratings) / len(ratings) if ratings else 0