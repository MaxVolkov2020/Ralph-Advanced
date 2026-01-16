#!/usr/bin/env python3
"""
Create Admin User Script for Ralph-Advanced

This script creates the initial admin user for the system.
Run this after deploying the containers.

Usage:
    docker-compose exec orchestrator python /app/scripts/create_admin.py

Or with custom credentials:
    docker-compose exec orchestrator python /app/scripts/create_admin.py --username admin --password 'YourSecurePassword'
"""
import sys
import os
import argparse

# Add the orchestrator directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'orchestrator'))

from database import SessionLocal, init_db
from auth import get_password_hash
from models import User


def create_admin_user(username: str, password: str) -> bool:
    """
    Create an admin user in the database.

    Args:
        username: Admin username
        password: Admin password

    Returns:
        True if user was created, False if user already exists
    """
    # Initialize database
    init_db()

    # Create session
    db = SessionLocal()

    try:
        # Check if user already exists
        existing_user = db.query(User).filter(User.username == username).first()
        if existing_user:
            print(f"User '{username}' already exists.")
            return False

        # Create new admin user
        admin = User(
            username=username,
            password_hash=get_password_hash(password)
        )
        db.add(admin)
        db.commit()

        print(f"Admin user '{username}' created successfully!")
        print(f"You can now log in at the web interface.")
        return True

    except Exception as e:
        print(f"Error creating admin user: {e}")
        db.rollback()
        return False

    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(
        description='Create an admin user for Ralph-Advanced'
    )
    parser.add_argument(
        '--username', '-u',
        default='admin',
        help='Admin username (default: admin)'
    )
    parser.add_argument(
        '--password', '-p',
        default='123LetsBuild@26!',
        help='Admin password (default: 123LetsBuild@26!)'
    )

    args = parser.parse_args()

    print("=" * 50)
    print("Ralph-Advanced Admin User Creation")
    print("=" * 50)
    print()

    success = create_admin_user(args.username, args.password)

    if success:
        print()
        print("Next steps:")
        print(f"1. Navigate to https://app.pressblk.com:5555")
        print(f"2. Log in with username: {args.username}")
        print(f"3. Go to Settings and configure your Claude API key")
        print()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
