"""
Simple API key authentication service.
"""

import secrets
from typing import Optional
from sqlalchemy.orm import Session
from src.database.models import User


def generate_api_key() -> str:
    """Generate a secure API key."""
    return secrets.token_urlsafe(32)


def create_user(db: Session, user_id: str) -> User:
    """Create a new user with API key."""
    api_key = generate_api_key()
    db_user = User(user_id=user_id, api_key=api_key)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def get_user_by_api_key(db: Session, api_key: str) -> Optional[User]:
    """Get user by API key."""
    return db.query(User).filter(User.api_key == api_key).first()


def get_user_by_id(db: Session, user_id: str) -> Optional[User]:
    """Get user by user ID."""
    return db.query(User).filter(User.user_id == user_id).first()


def authenticate_user(db: Session, api_key: str) -> Optional[User]:
    """Authenticate user via API key."""
    user = get_user_by_api_key(db, api_key)
    if user:
        # Update last active timestamp
        from datetime import datetime
        user.last_active = datetime.utcnow()
        db.commit()
    return user
