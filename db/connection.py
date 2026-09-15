# db/connection.py
"""
Shared Postgres connection helper. Any module needing a DB connection
imports get_connection() from here rather than rolling its own.
"""

import psycopg
import sys
from pathlib import Path

if __name__ == "__main__" and not __package__:
    project_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(project_root))
    
from app.config import settings


def get_connection():
    return psycopg.connect(settings.database_url)
