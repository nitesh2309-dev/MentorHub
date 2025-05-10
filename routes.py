from datetime import datetime, timedelta
from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user

from app import db, app
from auth import init_auth_routes
from forms import ProfileForm, AvailabilitySlotForm, SessionRequestForm, FeedbackForm
from models import User, AvailabilitySlot, Session, Feedback
from google_meet import create_meeting_for_session

def register_routes(app):
    # Initialize auth routes
    init_auth_routes(app)

    @app.context_processor
    def inject_now():
        return {'now': datetime.now()}

    @app.route('/')
    def index():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        return render_template('index.html', title='Welcome to MentorHub')

    @app.route('/dashboard')
    @login_required
    def dashboard():
        upcoming_sessions = []

        # Generate sessions data for chart
        sessions_data = []
        now = datetime.now()
        for i in range(4):  # Get last 4 weeks
            start_date = now - timedelta(days=now.weekday(), weeks=i)
            end_date = start_date + timedelta(days=6)
            week_label = f"{start_date.strftime('%b %d')} - {end_date.strftime('%b %d')}"

            if current_user.role == 'mentor':
                count = Session.query.filter(
                    Session.mentor_id == current_user.id,
                    Session.status == 'completed',
                    Session.session_date >= start_date.date(),
                    Session.session_date <= end_date.date()
                ).count()
            else:
                count = Session.query.filter(
                    Session.mentee_id == current_user.id,
                    Session.status == 'completed',
                    Session.session_date >= start_date.date(),
                    Session.session_date <= end_date.date()
                ).count()

            sessions_data.append({
                'week': week_label,
                'count': count
            })

        # Reverse to show oldest to newest
        sessions_data.reverse()

        if current_user.role == 'mentor':
            # Get pending session requests
            pending_requests = Session.query.filter_by(
                mentor_id=current_user.id,
                status='pending'
            ).order_by(Session.session_date).all()

            # Get upcoming approved sessions
            upcoming_sessions = Session.query.filter_by(
                mentor_id=current_user.id,
                status='approved'
            ).filter(Session.session_date >= datetime.now().date()).order_by(Session.session_date).all()

            # Get feedback statistics
            try:
                feedbacks = Feedback.query.filter_by(receiver_id=current_user.id).all()
                avg_rating = 0
                if feedbacks:
                    avg_rating = sum(f.rating for f in feedbacks) / len(feedbacks)
            except Exception as e:
                app.logger.error(f"Error fetching feedback: {str(e)}")
                feedbacks = []
                avg_rating = 0

            total_sessions = Session.query.filter_by(
                mentor_id=current_user.id,
                status='completed'
            ).count()

            # Create a stats dictionary for the template
            stats = {
                'total_sessions': total_sessions,
                'upcoming_sessions': len(upcoming_sessions),
                'average_rating': avg_rating
            }

            return render_template(
                'dashboard.html',
                title='Mentor Dashboard',
                pending_requests=pending_requests,
                upcoming_sessions=upcoming_sessions,
                stats=stats,
                sessions_data=sessions_data,
                activity_feed=[] # Empty for now but will be populated in the future
            )
        else:  # Mentee
            # Get pending session requests
            pending_requests = Session.query.filter_by(
                mentee_id=current_user.id,
                status='pending'
            ).order_by(Session.session_date).all()

            # Get upcoming approved sessions
            upcoming_sessions = Session.query.filter_by(
                mentee_id=current_user.id,
                status='approved'
            ).filter(Session.session_date >= datetime.now().date()).order_by(Session.session_date).all()

            # Get list of mentors worked with
            past_sessions = Session.query.filter_by(
                mentee_id=current_user.id,
                status='completed'
            ).all()

            mentor_ids = set(s.mentor_id for s in past_sessions)
            mentors_worked_with = User.query.filter(User.id.in_(mentor_ids)).all() if mentor_ids else []

            # Get total completed sessions
            total_sessions = Session.query.filter_by(
                mentee_id=current_user.id,
                status='completed'
            ).count()

            # Get average rating from feedback given
            try:
                feedbacks_received = Feedback.query.filter_by(receiver_id=current_user.id).all()
                avg_rating = 0
                if feedbacks_received:
                    avg_rating = sum(f.rating for f in feedbacks_received) / len(feedbacks_received)
            except Exception as e:
                app.logger.error(f"Error fetching feedback for mentee: {str(e)}")
                feedbacks_received = []
                avg_rating = 0

            # Create stats dictionary
            stats = {
                'total_sessions': total_sessions,
                'upcoming_sessions': len(upcoming_sessions),
                'average_rating': avg_rating
            }

            return render_template(
                'dashboard.html',
                title='Mentee Dashboard',
                pending_requests=pending_requests,
                upcoming_sessions=upcoming_sessions,
                mentors_worked_with=mentors_worked_with,
                stats=stats,
                sessions_data=sessions_data,
                activity_feed=[] # Empty for now but will be populated in the future
            )

    @app.route('/profile', methods=['GET', 'POST'])
    @login_required
    def profile():
        form = ProfileForm()

        if request.method == 'GET':
            form.username.data = current_user.username
            form.email.data = current_user.email
            form.bio.data = current_user.bio
            form.expertise.data = current_user.expertise

        if form.validate_on_submit():
            current_user.username = form.username.data
            current_user.email = form.email.data
            current_user.bio = form.bio.data
            current_user.expertise = form.expertise.data

            db.session.commit()
            flash('Your profile has been updated!', 'success')
            return redirect(url_for('profile'))

        # For mentors, show availability slots
        availability_slots = []
        availability_form = None

        if current_user.role == 'mentor':
            availability_slots = AvailabilitySlot.query.filter_by(mentor_id=current_user.id).all()
            availability_form = AvailabilitySlotForm()

        return render_template(
            'profile.html',
            title='Profile',
            form=form,
            availability_form=availability_form,
            availability_slots=availability_slots
        )

    @app.route('/availability/add', methods=['POST'])
    @login_required
    def add_availability():
        if current_user.role != 'mentor':
            flash('Only mentors can set availability.', 'danger')
            return redirect(url_for('profile'))

        # Debug logging
        app.logger.debug(f"Form data received: {request.form}")

        # Handle form data
        if request.method == 'POST':
            try:
                # Get form data
                day_of_week = int(request.form.get('day_of_week', 0))
                start_time_str = request.form.get('start_time')
                end_time_str = request.form.get('end_time')
                is_recurring = 'is_recurring' in request.form

                app.logger.debug(f"Parsed form data: day={day_of_week}, start={start_time_str}, end={end_time_str}, recurring={is_recurring}")

                # Validate form data
                if not start_time_str or not end_time_str:
                    flash('Please provide both start and end times.', 'danger')
                    return redirect(url_for('profile'))

                # Convert time strings to time objects
                try:
                    start_time = datetime.strptime(start_time_str, '%H:%M').time()
                    end_time = datetime.strptime(end_time_str, '%H:%M').time()
                except ValueError:
                    flash('Invalid time format. Please use HH:MM format.', 'danger')
                    return redirect(url_for('profile'))

                # Validate time range
                if start_time >= end_time:
                    flash('End time must be after start time.', 'danger')
                    return redirect(url_for('profile'))

                # Create and save the availability slot
                slot = AvailabilitySlot()
                slot.mentor_id = current_user.id
                slot.day_of_week = day_of_week
                slot.start_time = start_time
                slot.end_time = end_time
                slot.is_recurring = is_recurring

                db.session.add(slot)
                db.session.commit()

                app.logger.debug(f"Availability slot added: {slot.id}")
                flash('Availability slot added successfully!', 'success')

            except Exception as e:
                app.logger.error(f"Error adding availability: {str(e)}")
                flash(f'Error adding availability: {str(e)}', 'danger')

        return redirect(url_for('profile'))

    @app.route('/availability/delete/<int:slot_id>', methods=['POST'])
    @login_required
    def delete_availability(slot_id):
        if current_user.role != 'mentor':
            flash('Only mentors can manage availability.', 'danger')
            return redirect(url_for('profile'))

        slot = AvailabilitySlot.query.get_or_404(slot_id)

        if slot.mentor_id != current_user.id:
            flash('You can only delete your own availability slots.', 'danger')
            return redirect(url_for('profile'))

        db.session.delete(slot)
        db.session.commit()

        flash('Availability slot deleted!', 'success')
        return redirect(url_for('profile'))

    @app.route('/mentors')
    @login_required
    def mentors():
        if current_user.role != 'mentee':
            flash('Only mentees can view mentors.', 'warning')
            return redirect(url_for('dashboard'))

        mentors_list = User.query.filter_by(role='mentor').all()

        # For each mentor, get their availability slots
        for mentor in mentors_list:
            mentor.slots = AvailabilitySlot.query.filter_by(mentor_id=mentor.id).all()

        return render_template('mentors.html', title='Find Mentors', mentors=mentors_list, form=SessionRequestForm())

    @app.route('/request-session', methods=['GET', 'POST'])
    @login_required
    def request_session():
        if current_user.role != 'mentee':
            flash('Only mentees can request sessions.', 'danger')
            return redirect(url_for('dashboard'))

        # Handle GET requests (direct links/fallback method)
        if request.method == 'GET':
            mentor_id = request.args.get('mentor_id')
            slot_id = request.args.get('slot_id')

            if not mentor_id or not slot_id:
                flash('Missing required parameters.', 'danger')
                return redirect(url_for('mentors'))

            # Create a form and populate it with the query parameters
            form = SessionRequestForm()
            form.mentor_id.data = mentor_id
            form.slot_id.data = slot_id

            # Get the mentor and slot
            mentor = User.query.get(mentor_id)
            slot = AvailabilitySlot.query.get(slot_id)

            if not mentor or not slot:
                flash('Invalid mentor or slot.', 'danger')
                return redirect(url_for('mentors'))

            # Render a simple form to complete the booking
            return render_template(
                'direct_booking.html',
                title='Book a Session',
                mentor=mentor,
                slot=slot,
                form=form
            )

        # Handle POST requests
        form = SessionRequestForm()

        if form.validate_on_submit():
            mentor = User.query.get(form.mentor_id.data)

            if not mentor or mentor.role != 'mentor':
                flash('Invalid mentor selected.', 'danger')
                return redirect(url_for('mentors'))

            # Get the availability slot
            slot = AvailabilitySlot.query.get(form.slot_id.data)

            if not slot or slot.mentor_id != mentor.id:
                flash('Invalid availability slot selected.', 'danger')
                return redirect(url_for('mentors'))

            # Check if slot is available for the selected date
            if not slot.is_available_for_date(form.session_date.data):
                flash('This time slot is already booked for the selected date.', 'danger')
                return redirect(url_for('mentors'))

            # Create session request
            new_session = Session()
            new_session.mentor_id = mentor.id
            new_session.mentee_id = current_user.id
            new_session.session_date = form.session_date.data
            new_session.start_time = slot.start_time
            new_session.end_time = slot.end_time
            new_session.notes = form.notes.data
            new_session.status = 'pending'

            try:
                db.session.add(new_session)
                db.session.commit()
                flash(f'Session requested with {mentor.username}!', 'success')
                return redirect(url_for('sessions'))
            except Exception as e:
                db.session.rollback()
                app.logger.error(f"Error creating session: {str(e)}")
                flash('There was an error processing your request. Please try again.', 'danger')
                return redirect(url_for('mentors'))

        # If form validation fails
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"Error in {field}: {error}", 'danger')

        return redirect(url_for('mentors'))

    @app.route('/sessions')
    @login_required
    def sessions():
        if current_user.role == 'mentor':
            sessions_list = Session.query.filter_by(mentor_id=current_user.id).order_by(Session.session_date.desc()).all()
        else:
            sessions_list = Session.query.filter_by(mentee_id=current_user.id).order_by(Session.session_date.desc()).all()

        # Group sessions by status
        pending = [s for s in sessions_list if s.status == 'pending']
        approved = [s for s in sessions_list if s.status == 'approved']
        completed = [s for s in sessions_list if s.status == 'completed']
        rejected = [s for s in sessions_list if s.status == 'rejected']

        return render_template(
            'sessions.html',
            title='My Sessions',
            pending=pending,
            approved=approved,
            completed=completed,
            rejected=rejected
        )

    @app.route('/session/<int:session_id>')
    @login_required
    def session_detail(session_id):
        session = Session.query.get_or_404(session_id)

        # Ensure user is part of this session
        if session.mentor_id != current_user.id and session.mentee_id != current_user.id:
            flash('You do not have permission to view this session.', 'danger')
            return redirect(url_for('sessions'))

        # Check if feedback has been given
        if current_user.role == 'mentor':
            feedback = Feedback.query.filter_by(
                session_id=session.id,
                giver_id=current_user.id
            ).first()
            other_user = User.query.get(session.mentee_id)
        else:
            feedback = Feedback.query.filter_by(
                session_id=session.id,
                giver_id=current_user.id
            ).first()
            other_user = User.query.get(session.mentor_id)

        feedback_form = None
        if session.status == 'completed' and not feedback:
            feedback_form = FeedbackForm()
            feedback_form.session_id.data = session.id

        # Get other sessions with the same user
        if current_user.role == 'mentor':
            other_sessions = Session.query.filter_by(
                mentor_id=current_user.id,
                mentee_id=session.mentee_id
            ).all()
        else:
            other_sessions = Session.query.filter_by(
                mentee_id=current_user.id,
                mentor_id=session.mentor_id
            ).all()

        return render_template(
            'session_detail.html',
            title='Session Details',
            session=session,
            other_user=other_user,
            feedback=feedback,
            feedback_form=feedback_form,
            other_sessions=other_sessions
        )

    @app.route('/session/<int:session_id>/update', methods=['POST'])
    @login_required
    def update_session(session_id):
        # Start with a clean session to avoid locking issues
        db.session.rollback()

        try:
            session = Session.query.get_or_404(session_id)

            # Ensure user is the mentor for this session
            if session.mentor_id != current_user.id:
                flash('Only the mentor can update this session.', 'danger')
                return redirect(url_for('sessions'))

            action = request.form.get('action')
            app.logger.debug(f"Session update action: {action}")

            if action == 'approve' and session.status == 'pending':
                try:
                    # First update the session status
                    session.status = 'approved'
                    db.session.commit()

                    # Then create Google Meet meeting in a separate transaction
                    app.logger.info(f"Creating Google Meet for session {session.id}")

                    # First check if we already have a valid meeting URL
                    if session.meeting_url and session.meeting_url.startswith('https://meet.google.com/'):
                        app.logger.info(f"Session already has a valid meeting URL: {session.meeting_url}")
                        flash('Session approved with existing Google Meet link!', 'success')
                        return redirect(url_for('session_detail', session_id=session_id))

                    # Try to create a new meeting
                    meeting_url = create_meeting_for_session(
                        session_date=session.session_date,
                        start_time=session.start_time,
                        end_time=session.end_time,
                        mentor_name=session.mentor.username,
                        mentee_name=session.mentee.username
                    )

                    # Update the meeting URL in a separate transaction
                    if meeting_url:
                        session = Session.query.get(session_id)  # Re-query to avoid stale data
                        session.meeting_url = meeting_url
                        db.session.commit()
                        app.logger.info(f"Google Meet created: {meeting_url}")
                        flash('Session approved with Google Meet link!', 'success')
                    else:
                        # Fallback to generate_meeting_url method
                        app.logger.warning("Google Meet creation failed, using fallback method")
                        session = Session.query.get(session_id)  # Re-query to avoid stale data
                        session.generate_meeting_url()
                        db.session.commit()
                        app.logger.warning("Using fallback method to generate meeting URL")
                        flash('Session approved with fallback meeting link!', 'success')
                except Exception as e:
                    db.session.rollback()
                    app.logger.error(f"Error creating Google Meet: {str(e)}")

                    # Try again with just the status update and fallback URL
                    try:
                        session = Session.query.get(session_id)  # Re-query to avoid stale data
                        session.status = 'approved'
                        session.generate_meeting_url()
                        db.session.commit()
                        flash('Session approved with fallback meeting link!', 'success')
                    except Exception as inner_e:
                        db.session.rollback()
                        app.logger.error(f"Error in fallback approval: {str(inner_e)}")
                        flash('Error approving session. Please try again.', 'danger')

            elif action == 'reject' and session.status == 'pending':
                try:
                    session.status = 'rejected'
                    db.session.commit()
                    flash('Session rejected.', 'info')
                except Exception as e:
                    db.session.rollback()
                    app.logger.error(f"Error rejecting session: {str(e)}")
                    flash('Error rejecting session. Please try again.', 'danger')

            elif action == 'complete' and session.status == 'approved':
                try:
                    session.status = 'completed'
                    db.session.commit()
                    flash('Session marked as completed!', 'success')
                except Exception as e:
                    db.session.rollback()
                    app.logger.error(f"Error completing session: {str(e)}")
                    flash('Error completing session. Please try again.', 'danger')

            elif action == 'generate_meeting':
                try:
                    # Create Google Meet meeting
                    app.logger.info(f"Generating Google Meet for session {session.id}")

                    # First check if we already have a valid meeting URL
                    if session.meeting_url and session.meeting_url.startswith('https://meet.google.com/'):
                        flash('This session already has a valid Google Meet link!', 'info')
                        return redirect(url_for('session_detail', session_id=session_id))

                    # Try to create a new meeting
                    meeting_url = create_meeting_for_session(
                        session_date=session.session_date,
                        start_time=session.start_time,
                        end_time=session.end_time,
                        mentor_name=session.mentor.username,
                        mentee_name=session.mentee.username
                    )

                    if meeting_url:
                        # Update the session with the new meeting URL
                        session = Session.query.get(session_id)  # Re-query to avoid stale data
                        session.meeting_url = meeting_url
                        db.session.commit()
                        app.logger.info(f"Google Meet created: {meeting_url}")
                        flash('Google Meet link generated successfully!', 'success')
                    else:
                        # If Google Meet creation failed, use fallback method
                        app.logger.warning("Google Meet creation failed, using fallback method")
                        session = Session.query.get(session_id)  # Re-query to avoid stale data
                        session.generate_meeting_url()
                        db.session.commit()
                        app.logger.warning("Using fallback method to generate meeting URL")
                        flash('Google Meet link could not be created. Using fallback link instead.', 'warning')
                except Exception as e:
                    db.session.rollback()
                    app.logger.error(f"Error generating meeting: {str(e)}")

                    # Try again with just the fallback URL
                    try:
                        session = Session.query.get(session_id)  # Re-query to avoid stale data
                        session.generate_meeting_url()
                        db.session.commit()
                        flash('Meeting link generated with fallback method!', 'warning')
                    except Exception as inner_e:
                        db.session.rollback()
                        app.logger.error(f"Error in fallback meeting generation: {str(inner_e)}")
                        flash('Error generating meeting link. Please try again.', 'danger')

        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Unexpected error in update_session: {str(e)}")
            flash('An unexpected error occurred. Please try again.', 'danger')

        return redirect(url_for('session_detail', session_id=session_id))

    @app.route('/submit-feedback', methods=['POST'])
    @login_required
    def submit_feedback():
        form = FeedbackForm()

        # Start with a clean session to avoid locking issues
        db.session.rollback()

        try:
            if form.validate_on_submit():
                session = Session.query.get(form.session_id.data)

                if not session:
                    flash('Invalid session.', 'danger')
                    return redirect(url_for('sessions'))

                # Ensure user is part of this session
                if session.mentor_id != current_user.id and session.mentee_id != current_user.id:
                    flash('You do not have permission to submit feedback for this session.', 'danger')
                    return redirect(url_for('sessions'))

                # Determine who is giving and receiving feedback
                if current_user.id == session.mentor_id:
                    giver_id = current_user.id
                    receiver_id = session.mentee_id
                    giver_role = "mentor"
                    receiver_role = "mentee"
                else:
                    giver_id = current_user.id
                    receiver_id = session.mentor_id
                    giver_role = "mentee"
                    receiver_role = "mentor"

                # Check if feedback already exists
                existing_feedback = Feedback.query.filter_by(
                    session_id=session.id,
                    giver_id=giver_id
                ).first()

                if existing_feedback:
                    # Update existing feedback
                    existing_feedback.rating = form.rating.data
                    existing_feedback.knowledge_rating = form.knowledge_rating.data
                    existing_feedback.communication_rating = form.communication_rating.data
                    existing_feedback.helpfulness_rating = form.helpfulness_rating.data
                    existing_feedback.comments = form.comments.data
                    existing_feedback.strengths = form.strengths.data
                    existing_feedback.areas_for_improvement = form.areas_for_improvement.data
                    existing_feedback.is_anonymous = form.is_anonymous.data

                    db.session.commit()
                    flash('Your feedback has been updated!', 'success')
                else:
                    # Create new feedback
                    feedback = Feedback()
                    feedback.session_id = session.id
                    feedback.giver_id = giver_id
                    feedback.receiver_id = receiver_id
                    feedback.rating = form.rating.data
                    feedback.knowledge_rating = form.knowledge_rating.data
                    feedback.communication_rating = form.communication_rating.data
                    feedback.helpfulness_rating = form.helpfulness_rating.data
                    feedback.comments = form.comments.data
                    feedback.strengths = form.strengths.data
                    feedback.areas_for_improvement = form.areas_for_improvement.data
                    feedback.is_anonymous = form.is_anonymous.data

                    db.session.add(feedback)
                    db.session.commit()

                    # Log the feedback submission
                    app.logger.info(f"Feedback submitted: {giver_role} {current_user.username} gave feedback to {receiver_role}")

                    flash('Thank you for your feedback!', 'success')

                return redirect(url_for('session_detail', session_id=session.id))
            else:
                # Log form validation errors
                for field, errors in form.errors.items():
                    app.logger.error(f"Form validation error in {field}: {', '.join(errors)}")

                flash('There was an error processing your feedback. Please check all fields.', 'danger')
                return redirect(url_for('sessions'))

        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error submitting feedback: {str(e)}")
            flash('An error occurred while submitting feedback. Please try again.', 'danger')
            return redirect(url_for('sessions'))

    @app.route('/calendar')
    @login_required
    def calendar():
        return render_template('calendar.html', title='My Calendar')

    @app.route('/api/calendar-events')
    @login_required
    def calendar_events():
        try:
            app.logger.debug(f"Calendar events requested by user {current_user.username} (role: {current_user.role})")
            app.logger.debug(f"Request args: {request.args}")

            # Get start and end dates from request
            start_date = request.args.get('start', datetime.now().strftime('%Y-%m-%d'))
            end_date = request.args.get('end', (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'))

            app.logger.debug(f"Raw date range: {start_date} to {end_date}")

            events = []

            # Handle date format with timezone info by slicing off the extra parts
            if 'T' in start_date:
                start_date = start_date.split('T')[0]
            if 'T' in end_date:
                end_date = end_date.split('T')[0]

            app.logger.debug(f"Processed date range: {start_date} to {end_date}")

            try:
                start = datetime.strptime(start_date, '%Y-%m-%d')
                end = datetime.strptime(end_date, '%Y-%m-%d')
                app.logger.debug(f"Parsed date range: {start} to {end}")
            except ValueError as e:
                app.logger.error(f"Date parsing error: {str(e)}")
                return jsonify({"error": f"Invalid date format: {str(e)}"}), 400

            # Add sessions for both mentors and mentees
            if current_user.role == 'mentor':
                # For mentors, only show approved or completed sessions
                sessions = Session.query.filter_by(mentor_id=current_user.id).filter(
                    Session.status.in_(['approved', 'completed'])
                ).all()
                app.logger.debug(f"Found {len(sessions)} approved/completed sessions for mentor {current_user.username}")
            else:
                # For mentees, show all their sessions
                sessions = Session.query.filter_by(mentee_id=current_user.id).all()
                app.logger.debug(f"Found {len(sessions)} sessions for mentee {current_user.username}")

                # For mentees, also show available slots from mentors for booking
                mentors = User.query.filter_by(role='mentor').all()
                app.logger.debug(f"Found {len(mentors)} mentors for mentee {current_user.username}")

                # Get all booked slots to exclude them
                booked_slots = {}
                for session in sessions:
                    date_key = session.session_date.strftime('%Y-%m-%d')
                    time_key = f"{session.start_time.strftime('%H:%M')}-{session.end_time.strftime('%H:%M')}"
                    mentor_key = session.mentor_id

                    if date_key not in booked_slots:
                        booked_slots[date_key] = {}

                    if mentor_key not in booked_slots[date_key]:
                        booked_slots[date_key][mentor_key] = []

                    booked_slots[date_key][mentor_key].append(time_key)

                # Add available slots that haven't been booked
                for mentor in mentors:
                    slots = AvailabilitySlot.query.filter_by(mentor_id=mentor.id).all()
                    app.logger.debug(f"Found {len(slots)} availability slots for mentor {mentor.username}")

                    for slot in slots:
                        # Get the next occurrence of this day of week
                        days_ahead = slot.day_of_week - start.weekday()
                        if days_ahead < 0:
                            days_ahead += 7

                        next_date = start + timedelta(days=days_ahead)

                        # Add all occurrences within the date range
                        while next_date <= end:
                            date_str = next_date.strftime('%Y-%m-%d')
                            time_key = f"{slot.start_time.strftime('%H:%M')}-{slot.end_time.strftime('%H:%M')}"

                            # Check if this slot is already booked
                            is_booked = False
                            if date_str in booked_slots and mentor.id in booked_slots[date_str]:
                                if time_key in booked_slots[date_str][mentor.id]:
                                    is_booked = True

                            # Only add available slots that haven't been booked
                            if not is_booked:
                                event = {
                                    'id': f'avail_{slot.id}_{date_str}',
                                    'title': f'Available: {mentor.username}',
                                    'start': f'{date_str}T{slot.start_time.strftime("%H:%M:%S")}',
                                    'end': f'{date_str}T{slot.end_time.strftime("%H:%M:%S")}',
                                    'className': 'availability',
                                    'resourceIds': [str(mentor.id)],
                                    'extendedProps': {
                                        'type': 'availability',
                                        'slotId': slot.id,
                                        'mentorId': mentor.id,
                                        'mentorName': mentor.username
                                    }
                                }
                                events.append(event)

                            # Move to next week
                            next_date += timedelta(days=7)

            # Add session events to the calendar
            app.logger.debug(f"Processing sessions for user {current_user.username}")

            for session in sessions:
                other_user = session.mentee if current_user.role == "mentor" else session.mentor
                event = {
                    'id': f'session_{session.id}',
                    'title': f'Session with {other_user.username}',
                    'start': f'{session.session_date.strftime("%Y-%m-%d")}T{session.start_time.strftime("%H:%M:%S")}',
                    'end': f'{session.session_date.strftime("%Y-%m-%d")}T{session.end_time.strftime("%H:%M:%S")}',
                    'className': f'session-{session.status}',
                    'extendedProps': {
                        'type': 'session',
                        'sessionId': session.id,
                        'status': session.status
                    }
                }
                events.append(event)

            app.logger.debug(f"Returning {len(events)} events")
            return jsonify(events)

        except Exception as e:
            app.logger.error(f"Error in calendar_events: {str(e)}")
            return jsonify({"error": str(e)}), 500

    @app.route('/analytics')
    @login_required
    def analytics():
        try:
            # Generate sessions per week data
            now = datetime.now()
            sessions_data = []

            for i in range(8):  # Get last 8 weeks
                start_date = now - timedelta(days=now.weekday(), weeks=i)
                end_date = start_date + timedelta(days=6)
                week_label = f"{start_date.strftime('%b %d')} - {end_date.strftime('%b %d')}"

                if current_user.role == 'mentor':
                    count = Session.query.filter(
                        Session.mentor_id == current_user.id,
                        Session.status == 'completed',
                        Session.session_date >= start_date.date(),
                        Session.session_date <= end_date.date()
                    ).count()
                else:
                    count = Session.query.filter(
                        Session.mentee_id == current_user.id,
                        Session.status == 'completed',
                        Session.session_date >= start_date.date(),
                        Session.session_date <= end_date.date()
                    ).count()

                sessions_data.append({
                    'week': week_label,
                    'count': count
                })

            # Reverse to show oldest to newest
            sessions_data.reverse()

            # Generate session status distribution data
            status_data = {}
            if current_user.role == 'mentor':
                completed = Session.query.filter_by(mentor_id=current_user.id, status='completed').count()
                approved = Session.query.filter_by(mentor_id=current_user.id, status='approved').count()
                pending = Session.query.filter_by(mentor_id=current_user.id, status='pending').count()
                rejected = Session.query.filter_by(mentor_id=current_user.id, status='rejected').count()
            else:
                completed = Session.query.filter_by(mentee_id=current_user.id, status='completed').count()
                approved = Session.query.filter_by(mentee_id=current_user.id, status='approved').count()
                pending = Session.query.filter_by(mentee_id=current_user.id, status='pending').count()
                rejected = Session.query.filter_by(mentee_id=current_user.id, status='rejected').count()

            status_data = {
                'labels': ['Completed', 'Approved', 'Pending', 'Rejected'],
                'data': [completed, approved, pending, rejected]
            }

            # Generate availability data for mentors
            availability_data = {}
            if current_user.role == 'mentor':
                # Get availability slots grouped by day of week
                day_hours = [0] * 7  # Initialize with 0 hours for each day

                slots = AvailabilitySlot.query.filter_by(mentor_id=current_user.id).all()
                for slot in slots:
                    # Calculate hours for this slot
                    start_time = slot.start_time
                    end_time = slot.end_time

                    # Convert to datetime for calculation
                    start_dt = datetime.combine(datetime.today(), start_time)
                    end_dt = datetime.combine(datetime.today(), end_time)

                    # Handle case where end time is on the next day
                    if end_dt < start_dt:
                        end_dt += timedelta(days=1)

                    # Calculate duration in hours
                    duration = (end_dt - start_dt).total_seconds() / 3600

                    # Add to the appropriate day
                    day_hours[slot.day_of_week] += duration

                availability_data = {
                    'labels': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'],
                    'data': day_hours
                }

            # Generate mentor distribution data for mentees
            mentor_distribution = {}
            if current_user.role == 'mentee':
                # Get all completed sessions for this mentee
                completed_sessions = Session.query.filter_by(
                    mentee_id=current_user.id,
                    status='completed'
                ).all()

                # Count sessions per mentor
                mentor_counts = {}
                for session in completed_sessions:
                    mentor_id = session.mentor_id
                    mentor = User.query.get(mentor_id)
                    mentor_name = mentor.username if mentor else f"Mentor {mentor_id}"

                    if mentor_name in mentor_counts:
                        mentor_counts[mentor_name] += 1
                    else:
                        mentor_counts[mentor_name] = 1

                # Sort mentors by session count (descending)
                sorted_mentors = sorted(mentor_counts.items(), key=lambda x: x[1], reverse=True)

                # Take top 3 mentors and group the rest as "Others"
                labels = []
                data = []
                other_count = 0

                for i, (mentor_name, count) in enumerate(sorted_mentors):
                    if i < 3:  # Top 3 mentors
                        labels.append(mentor_name)
                        data.append(count)
                    else:  # Group the rest as "Others"
                        other_count += count

                if other_count > 0:
                    labels.append("Others")
                    data.append(other_count)

                mentor_distribution = {
                    'labels': labels,
                    'data': data
                }

            # Generate feedback data
            feedback_data = {}

            if current_user.role == 'mentor':
                try:
                    feedbacks = Feedback.query.filter_by(receiver_id=current_user.id).all()
                    avg_rating = 0
                    if feedbacks:
                        avg_rating = sum(f.rating for f in feedbacks) / len(feedbacks)

                    feedback_data = {
                        'average': avg_rating,
                        'count': len(feedbacks)
                    }
                except Exception as e:
                    app.logger.error(f"Error processing mentor feedback: {str(e)}")
                    feedback_data = {
                        'average': 0,
                        'count': 0
                    }
            else:
                # For mentees, show both given and received feedback
                try:
                    received = Feedback.query.filter_by(receiver_id=current_user.id).all()
                    given = Feedback.query.filter_by(giver_id=current_user.id).all()

                    received_avg = 0
                    if received:
                        received_avg = sum(f.rating for f in received) / len(received)

                    given_avg = 0
                    if given:
                        given_avg = sum(f.rating for f in given) / len(given)

                    feedback_data = {
                        'received': {
                            'average': received_avg,
                            'count': len(received)
                        },
                        'given': {
                            'average': given_avg,
                            'count': len(given)
                        }
                    }
                except Exception as e:
                    app.logger.error(f"Error processing mentee feedback: {str(e)}")
                    feedback_data = {
                        'received': {
                            'average': 0,
                            'count': 0
                        },
                        'given': {
                            'average': 0,
                            'count': 0
                        }
                    }

            return render_template(
                'analytics.html',
                title='Analytics',
                sessions_data=sessions_data,
                status_data=status_data,
                availability_data=availability_data if current_user.role == 'mentor' else None,
                mentor_distribution=mentor_distribution if current_user.role == 'mentee' else None,
                feedback_data=feedback_data
            )
        except Exception as e:
            app.logger.error(f"Error in analytics route: {str(e)}")
            flash('An error occurred while generating analytics. Please try again.', 'danger')
            return redirect(url_for('dashboard'))

    @app.route('/session/<int:session_id>/template')
    @login_required
    def session_detail_template(session_id):
        """Return the HTML template for a session"""
        session = Session.query.get_or_404(session_id)

        # Ensure user is part of this session
        if session.mentor_id != current_user.id and session.mentee_id != current_user.id:
            return "Unauthorized", 403

        if current_user.role == 'mentor':
            other_user = User.query.get(session.mentee_id)
        else:
            other_user = User.query.get(session.mentor_id)

        return render_template(
            'session_detail.html',
            title='Session Details',
            session=session,
            other_user=other_user,
            modal=True
        )