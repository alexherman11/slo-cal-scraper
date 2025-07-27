#!/usr/bin/env python3
"""
Clear the database to start fresh
"""

import os
from src.config.settings import DATABASE_CONFIG

def clear_database():
    """Remove the database file to start fresh"""
    db_path = DATABASE_CONFIG['path']
    
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"Database cleared: {db_path}")
    else:
        print("Database file not found, already cleared")

if __name__ == "__main__":
    clear_database()