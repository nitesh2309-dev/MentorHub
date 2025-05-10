"""
Database migration script to update the schema for new feedback columns.
"""

import os
import sys
import logging
import sqlite3
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_db_path():
    """Get the database path from environment or use default."""
    db_url = os.environ.get("DATABASE_URL", "sqlite:///instance/mentorschedule.db")
    if db_url.startswith("sqlite:///"):
        return db_url[10:]
    logger.error("Only SQLite databases are supported by this migration script.")
    sys.exit(1)

def backup_database(db_path):
    """Create a backup of the database before migration."""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    backup_path = f"{db_path}.backup-{timestamp}"
    
    try:
        with open(db_path, 'rb') as src, open(backup_path, 'wb') as dst:
            dst.write(src.read())
        logger.info(f"Database backup created at {backup_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to create database backup: {str(e)}")
        return False

def migrate_feedback_table(db_path):
    """Add new columns to the feedback table."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(feedback)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # Add new columns if they don't exist
        new_columns = {
            "knowledge_rating": "INTEGER",
            "communication_rating": "INTEGER",
            "helpfulness_rating": "INTEGER",
            "strengths": "TEXT",
            "areas_for_improvement": "TEXT",
            "is_anonymous": "BOOLEAN DEFAULT 0"
        }
        
        for column_name, column_type in new_columns.items():
            if column_name not in columns:
                logger.info(f"Adding column {column_name} to feedback table")
                cursor.execute(f"ALTER TABLE feedback ADD COLUMN {column_name} {column_type}")
        
        conn.commit()
        conn.close()
        logger.info("Migration completed successfully")
        return True
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        return False

def main():
    """Run the migration."""
    logger.info("Starting database migration")
    
    db_path = get_db_path()
    logger.info(f"Using database at {db_path}")
    
    if not os.path.exists(db_path):
        logger.error(f"Database file not found at {db_path}")
        sys.exit(1)
    
    if not backup_database(db_path):
        logger.error("Migration aborted due to backup failure")
        sys.exit(1)
    
    if migrate_feedback_table(db_path):
        logger.info("Migration completed successfully")
    else:
        logger.error("Migration failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
