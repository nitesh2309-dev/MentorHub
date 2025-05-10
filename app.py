import os
import logging
import datetime
from logging.handlers import RotatingFileHandler

from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect

# Configure logging
log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()
log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# Create logs directory if it doesn't exist
if not os.path.exists('logs'):
    os.makedirs('logs')

# Configure file handler
file_handler = RotatingFileHandler(
    'logs/mentorschedule.log',
    maxBytes=10485760,  # 10MB
    backupCount=10
)
file_handler.setFormatter(logging.Formatter(log_format))

# Configure console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter(log_format))

# Setup root logger
root_logger = logging.getLogger()
root_logger.setLevel(getattr(logging, log_level))
root_logger.addHandler(file_handler)
root_logger.addHandler(console_handler)

# Create logger for this module
logger = logging.getLogger(__name__)
logger.info(f"Starting application with log level: {log_level}")

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Create the app
app = Flask(__name__)

# Load configuration from environment variables
app.config.from_mapping(
    SECRET_KEY=os.environ.get("SECRET_KEY", "development-key-change-in-production"),
    SESSION_COOKIE_SECURE=os.environ.get("FLASK_ENV", "development") == "production",
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=datetime.timedelta(days=1),
    SQLALCHEMY_DATABASE_URI=os.environ.get("DATABASE_URL", "sqlite:///mentorschedule.db"),
    SQLALCHEMY_ENGINE_OPTIONS={
        "pool_recycle": 300,
        "pool_pre_ping": True,
    },
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    MAX_CONTENT_LENGTH=16 * 1024 * 1024,  # 16MB max upload size
)

# Setup proxy fix for proper IP handling behind reverse proxies
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1, x_for=1)

# Setup Login Manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'
login_manager.session_protection = "strong"

# Setup CSRF protection
csrf = CSRFProtect(app)

# Request logging middleware
@app.before_request
def log_request_info():
    if app.debug:
        logger.debug(f"Request: {request.method} {request.path} from {request.remote_addr}")

@app.after_request
def add_security_headers(response):
    # Add security headers
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'

    # Add Referrer-Policy header to allow Unsplash images to load
    response.headers['Referrer-Policy'] = 'no-referrer-when-downgrade'

    # Add CORS headers to allow Unsplash images
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'

    # Add Content Security Policy based on environment
    # Check if running in Docker
    if os.environ.get("DOCKER", "false").lower() == "true":
        # Docker environment - more permissive CSP
        csp = (
            "default-src * 'unsafe-inline' 'unsafe-eval'; "
            "script-src * 'unsafe-inline' 'unsafe-eval'; "
            "style-src * 'unsafe-inline'; "
            "img-src * data:; "
            "font-src * data:;"
        )
    elif os.environ.get("FLASK_ENV", "development") == "production":
        # Production environment - stricter CSP but allow necessary resources
        csp = (
            "default-src 'self'; "
            "script-src 'self' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com 'unsafe-inline'; "
            "style-src 'self' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com 'unsafe-inline'; "
            "img-src 'self' data: https://images.unsplash.com https:; "
            "font-src 'self' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com data:; "
            "connect-src 'self';"
        )
    else:
        # Development environment - permissive but still structured CSP
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
            "img-src 'self' data: https://images.unsplash.com https:; "
            "font-src 'self' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com data:; "
            "connect-src 'self';"
        )

    # Set the CSP header
    response.headers['Content-Security-Policy'] = csp

    return response

# initialize the app with the extension, flask-sqlalchemy >= 3.0.x
db.init_app(app)

with app.app_context():
    # Import models and routes
    import models
    from routes import register_routes

    # Register all routes
    register_routes(app)

    # Create database tables
    db.create_all()

    from models import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))
