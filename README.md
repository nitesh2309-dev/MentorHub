# MentorSchedule

A web application for scheduling and managing mentoring sessions between mentors and mentees.

## Features

- User registration and authentication (mentors and mentees)
- Mentor availability management
- Session scheduling and booking
- Google Meet integration for virtual meetings
- Detailed feedback and rating system
- Calendar view of sessions and availability
- Analytics dashboard

## Technology Stack

- **Backend**: Flask, SQLAlchemy
- **Frontend**: HTML, CSS, JavaScript, Bootstrap
- **Database**: SQLite (development), PostgreSQL/MySQL (production)
- **Authentication**: Flask-Login
- **Forms**: Flask-WTF
- **API Integration**: Google Meet API
- **Deployment**: Docker, Gunicorn

## Installation

### Prerequisites

- Python 3.10+
- pip
- virtualenv (recommended)

### Setup

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/mentorschedule.git
   cd mentorschedule
   ```

2. Create and activate a virtual environment:
   ```
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Create a `.env` file based on `.env.example`:
   ```
   cp .env.example .env
   ```

5. Edit the `.env` file with your configuration.

6. Run the application:
   ```
   python main.py
   ```

   Or for production:
   ```
   gunicorn wsgi:application
   ```

## Docker Deployment

1. Build the Docker image:
   ```
   docker build -t mentorschedule .
   ```

2. Run the container:
   ```
   docker run -p 8000:8000 --env-file .env mentorschedule
   ```

## Google Meet Integration

1. Create a project in the Google Cloud Console
2. Enable the Google Meet API
3. Create OAuth 2.0 credentials
4. Download the client secret JSON file and place it in the project directory
5. Update the `GOOGLE_CLIENT_SECRET_FILE` in your `.env` file

## Database Migrations

For production deployments with PostgreSQL or MySQL:

1. Set the `DATABASE_URL` in your `.env` file
2. Run the application to create the tables

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
