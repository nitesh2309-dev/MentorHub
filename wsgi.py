"""
WSGI entry point for production deployment.
This file is used by production WSGI servers like Gunicorn.
"""

import os
from app import app as application

if __name__ == "__main__":
    # This block is only executed when running this file directly
    # It's not used when running with a WSGI server like Gunicorn
    port = int(os.environ.get("PORT", 5000))
    application.run(host="0.0.0.0", port=port)
