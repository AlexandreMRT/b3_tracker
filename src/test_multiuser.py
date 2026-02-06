#!/usr/bin/env python3
"""
Test script for multi-user and portfolio features
Run this after starting the services to verify everything works
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import init_db, SessionLocal
from models import User, Portfolio, Transaction, TransactionType
from datetime import datetime
import uuid


def test_database():
    """Test database connectivity and models"""
    print("🔍 Testing database connectivity...")

    try:
        init_db()
        print("✅ Database initialized successfully!")

        db = SessionLocal()

        # Test creating a test user
        test_user_id = uuid.uuid4()
        test_user = User(
            id=test_user_id,
            google_id=f"test_{test_user_id}",
            email=f"test_{test_user_id}@example.com",
            name="Test User",
            picture_url=None,
            created_at=datetime.utcnow(),
            last_login=datetime.utcnow(),
        )

        db.add(test_user)
        db.commit()
        print(f"✅ Test user created: {test_user.email}")

        # Test creating a portfolio
        test_portfolio = Portfolio(
            user_id=test_user_id,
            name="Test Portfolio",
            description="Test portfolio for validation",
            is_default=1,
            created_at=datetime.utcnow(),
        )

        db.add(test_portfolio)
        db.commit()
        db.refresh(test_portfolio)
        print(f"✅ Test portfolio created: ID {test_portfolio.id}")

        # Test creating a transaction
        test_transaction = Transaction(
            portfolio_id=test_portfolio.id,
            ticker="PETR4",
            transaction_type=TransactionType.BUY,
            quantity=100,
            price_brl=35.50,
            total_brl=3550.0,
            fees_brl=10.0,
            transaction_date=datetime.utcnow(),
            notes="Test transaction",
        )

        db.add(test_transaction)
        db.commit()
        print(f"✅ Test transaction created: {test_transaction.ticker}")

        # Query back to verify
        user_check = db.query(User).filter(User.id == test_user_id).first()
        portfolio_check = db.query(Portfolio).filter(Portfolio.user_id == test_user_id).first()
        transaction_check = db.query(Transaction).filter(Transaction.portfolio_id == test_portfolio.id).first()

        if user_check and portfolio_check and transaction_check:
            print("✅ All models successfully created and queried!")
        else:
            print("❌ Error: Could not query back created records")
            return False

        # Cleanup test data
        db.delete(test_transaction)
        db.delete(test_portfolio)
        db.delete(test_user)
        db.commit()
        print("✅ Test data cleaned up")

        db.close()

        print("\n🎉 All tests passed! Database is working correctly.")
        print("\n📋 Next steps:")
        print("   1. Configure Google OAuth credentials in .env file")
        print("   2. Start the API: docker compose up -d api")
        print("   3. Visit http://localhost:8000/docs to see API documentation")
        print("   4. Login via http://localhost:8000/auth/login")

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_database()
    sys.exit(0 if success else 1)
