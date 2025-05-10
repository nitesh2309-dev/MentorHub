from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField, TextAreaField, IntegerField, TimeField, DateField, HiddenField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError, Length, NumberRange
from models import User

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=64)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8)])
    password2 = PasswordField('Repeat Password', validators=[DataRequired(), EqualTo('password')])
    role = SelectField('I want to be a', choices=[('mentee', 'Mentee'), ('mentor', 'Mentor')], validators=[DataRequired()])
    submit = SubmitField('Register')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Please use a different username.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Please use a different email address.')

class ProfileForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=64)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    bio = TextAreaField('Bio', validators=[Length(max=500)])
    expertise = StringField('Areas of Expertise', validators=[Length(max=255)])
    submit = SubmitField('Update Profile')

class AvailabilitySlotForm(FlaskForm):
    day_of_week = SelectField('Day of Week', choices=[
        (0, 'Monday'), (1, 'Tuesday'), (2, 'Wednesday'),
        (3, 'Thursday'), (4, 'Friday'), (5, 'Saturday'), (6, 'Sunday')
    ], coerce=int, validators=[DataRequired()])
    start_time = TimeField('Start Time', validators=[DataRequired()])
    end_time = TimeField('End Time', validators=[DataRequired()])
    is_recurring = BooleanField('Recurring Weekly')
    submit = SubmitField('Add Availability')

class SessionRequestForm(FlaskForm):
    mentor_id = HiddenField('Mentor ID', validators=[DataRequired()])
    slot_id = HiddenField('Slot ID', validators=[DataRequired()])
    session_date = DateField('Session Date', validators=[DataRequired()])
    notes = TextAreaField('Notes for Mentor', validators=[Length(max=500)])
    submit = SubmitField('Request Session')

class FeedbackForm(FlaskForm):
    session_id = HiddenField('Session ID', validators=[DataRequired()])
    rating = IntegerField('Overall Rating (1-5)', validators=[DataRequired(), NumberRange(min=1, max=5)])
    knowledge_rating = IntegerField('Knowledge Rating (1-5)', validators=[NumberRange(min=1, max=5)])
    communication_rating = IntegerField('Communication Rating (1-5)', validators=[NumberRange(min=1, max=5)])
    helpfulness_rating = IntegerField('Helpfulness Rating (1-5)', validators=[NumberRange(min=1, max=5)])
    comments = TextAreaField('General Comments', validators=[Length(max=500)])
    strengths = TextAreaField('Strengths', validators=[Length(max=500)])
    areas_for_improvement = TextAreaField('Areas for Improvement', validators=[Length(max=500)])
    is_anonymous = BooleanField('Submit Anonymously')
    submit = SubmitField('Submit Feedback')