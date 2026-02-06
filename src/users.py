"""
User management operations
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from models import User, Watchlist
from datetime import datetime, timezone


def get_user_by_id(db: Session, user_id: str) -> Optional[User]:
    """Get user by ID"""
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Get user by email"""
    return db.query(User).filter(User.email == email).first()


def get_user_by_google_id(db: Session, google_id: str) -> Optional[User]:
    """Get user by Google ID"""
    return db.query(User).filter(User.google_id == google_id).first()


def update_user_preferences(db: Session, user_id: str, default_currency: str = None) -> User:
    """Update user preferences"""
    user = get_user_by_id(db, user_id)
    if not user:
        return None
    
    if default_currency:
        user.default_currency = default_currency
    
    db.commit()
    db.refresh(user)
    return user


# === WATCHLIST OPERATIONS ===

def get_user_watchlist(db: Session, user_id: str) -> List[Watchlist]:
    """Get all tickers in user's watchlist"""
    return db.query(Watchlist).filter(Watchlist.user_id == user_id).order_by(Watchlist.created_at.desc()).all()


def add_to_watchlist(db: Session, user_id: str, ticker: str, notes: str = None) -> Watchlist:
    """Add ticker to user's watchlist"""
    # Check if already exists
    existing = db.query(Watchlist).filter(
        Watchlist.user_id == user_id,
        Watchlist.ticker == ticker.upper()
    ).first()
    
    if existing:
        # Update notes if provided
        if notes:
            existing.notes = notes
            db.commit()
            db.refresh(existing)
        return existing
    
    # Create new watchlist entry
    watchlist = Watchlist(
        user_id=user_id,
        ticker=ticker.upper(),
        notes=notes,
        created_at=datetime.now(timezone.utc)
    )
    
    db.add(watchlist)
    db.commit()
    db.refresh(watchlist)
    return watchlist


def remove_from_watchlist(db: Session, user_id: str, ticker: str) -> bool:
    """Remove ticker from user's watchlist"""
    watchlist = db.query(Watchlist).filter(
        Watchlist.user_id == user_id,
        Watchlist.ticker == ticker.upper()
    ).first()
    
    if not watchlist:
        return False
    
    db.delete(watchlist)
    db.commit()
    return True


def is_in_watchlist(db: Session, user_id: str, ticker: str) -> bool:
    """Check if ticker is in user's watchlist"""
    exists = db.query(Watchlist).filter(
        Watchlist.user_id == user_id,
        Watchlist.ticker == ticker.upper()
    ).first()
    
    return exists is not None
