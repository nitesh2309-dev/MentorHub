FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_ENV=production \
    FLASK_APP=wsgi.py

# Create and set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Make the entrypoint script executable
RUN chmod +x /app/docker-entrypoint.sh

# Create a non-root user to run the application
RUN adduser --disabled-password --gecos "" appuser

# Create necessary directories with correct permissions
RUN mkdir -p /app/logs /app/instance /app/static/css
RUN chown -R appuser:appuser /app /app/logs /app/instance /app/static

# If token.json exists, ensure it has the right permissions
RUN if [ -f /app/token.json ]; then chmod 644 /app/token.json && chown appuser:appuser /app/token.json; fi

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Set the entrypoint script
ENTRYPOINT ["/app/docker-entrypoint.sh"]

# Run the application with Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "--timeout", "120", "wsgi:application"]

