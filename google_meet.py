"""
Google Meet API integration for MentorSchedule application.
This module handles creating Google Meet meetings for mentoring sessions.
"""

import os
import json
import logging
import threading
import time
import socket
import webbrowser
from datetime import datetime, timedelta
from urllib.parse import urlparse

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.apps import meet_v2

# Configure logging
logger = logging.getLogger(__name__)

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/meetings.space.created']

# Global variables for OAuth flow
auth_completed = False
auth_credentials = None
auth_error = None

def is_port_in_use(port):
    """Check if a port is already in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def find_available_port(start_port=8080, max_attempts=10):
    """Find an available port starting from start_port."""
    for i in range(max_attempts):
        port = start_port + i
        if not is_port_in_use(port):
            return port
    return None

def run_auth_flow(client_secret_file):
    """Run the OAuth flow in a separate thread."""
    global auth_completed, auth_credentials, auth_error

    try:
        # Find an available port
        port = find_available_port()
        if not port:
            logger.error("Could not find an available port for OAuth callback")
            auth_error = "Could not find an available port for OAuth callback"
            auth_completed = True
            return

        # Create the flow
        flow = InstalledAppFlow.from_client_secrets_file(
            client_secret_file,
            SCOPES,
            redirect_uri=f'http://localhost:{port}'
        )

        # Run the flow
        auth_credentials = flow.run_local_server(port=port)

        # Save the credentials
        with open('token.json', 'w') as token:
            token.write(auth_credentials.to_json())

        auth_completed = True
    except Exception as e:
        logger.error(f"Error in OAuth flow: {str(e)}")
        auth_error = str(e)
        auth_completed = True

def get_credentials():
    """
    Get Google API credentials.
    Returns credentials object or None if authentication fails.
    """
    creds = None
    
    try:
        # Check for service account key first
        service_account_file = os.environ.get('GOOGLE_SERVICE_ACCOUNT_FILE')
        if service_account_file and os.path.exists(service_account_file):
            return service_account.Credentials.from_service_account_file(
                service_account_file, scopes=SCOPES)
        
        # The file token.json stores the user's access and refresh tokens
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)
            
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                # In Docker, we can't run the interactive flow
                if os.environ.get('RUNNING_IN_DOCKER', '').lower() == 'true':
                    logger.error("No valid credentials found and running in Docker. "
                                "Please authenticate locally first or use a service account.")
                    return None
                
                # Look for client_secret file
                client_secret_file = os.environ.get('GOOGLE_CLIENT_SECRET_FILE')
                if not client_secret_file or not os.path.exists(client_secret_file):
                    # Fallback to looking in current directory
                    for file in os.listdir():
                        if file.startswith('client_secret') and file.endswith('.json'):
                            client_secret_file = file
                            break
                
                if not client_secret_file:
                    logger.error("No client_secret file found in the current directory")
                    return None
                
                flow = InstalledAppFlow.from_client_secrets_file(client_secret_file, SCOPES)
                # Use a fixed port (8080) instead of a random one
                creds = flow.run_local_server(port=8080)
                
            # Save the credentials for the next run
            with open('token.json', 'w') as token:
                token.write(creds.to_json())
                
        return creds
    except Exception as e:
        logger.error(f"Error getting credentials: {str(e)}")
        return None

def create_meeting():
    """
    Create a new Google Meet meeting.
    Returns the meeting URL or None if creation fails.
    """
    try:
        creds = get_credentials()
        if not creds:
            logger.error("Failed to get credentials")
            return None

        client = meet_v2.SpacesServiceClient(credentials=creds)
        request = meet_v2.CreateSpaceRequest()
        response = client.create_space(request=request)

        meeting_url = response.meeting_uri
        logger.info(f"Meeting created: {meeting_url}")

        # Validate the meeting URL
        if not meeting_url or not meeting_url.startswith('https://meet.google.com/'):
            logger.error(f"Invalid meeting URL: {meeting_url}")
            return None

        return meeting_url
    except Exception as e:
        logger.error(f"Error creating meeting: {str(e)}")
        return None

def create_meeting_for_session(session_date, start_time, end_time, mentor_name, mentee_name):
    """
    Create a Google Meet meeting for a specific mentoring session.
    Returns the meeting URL or None if creation fails.

    Args:
        session_date: Date of the session
        start_time: Start time of the session
        end_time: End time of the session
        mentor_name: Name of the mentor
        mentee_name: Name of the mentee
    """
    try:
        # Create a basic meeting
        meeting_url = create_meeting()

        if meeting_url:
            logger.info(f"Created meeting for {mentor_name} and {mentee_name} on {session_date} at {start_time}")
            return meeting_url
        else:
            logger.error(f"Failed to create meeting for {mentor_name} and {mentee_name}")
            return None
    except Exception as e:
        logger.error(f"Error creating meeting for session: {str(e)}")
        return None


