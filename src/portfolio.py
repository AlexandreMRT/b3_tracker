"""
Portfolio management and calculations
"""
from typing import List, Optional, Dict, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from models import Portfolio, Position, Transaction, TransactionType, Quote, Asset
from datetime import datetime, date, timezone
from decimal import Decimal


# === PORTFOLIO OPERATIONS ===

def get_user_portfolios(db: Session, user_id: str) -> List[Portfolio]:
    """Get all portfolios for a user"""
    return db.query(Portfolio).filter(Portfolio.user_id == user_id).order_by(desc(Portfolio.is_default), Portfolio.created_at).all()


def get_portfolio_by_id(db: Session, portfolio_id: int, user_id: str) -> Optional[Portfolio]:
    """Get portfolio by ID (with user ownership check)"""
    return db.query(Portfolio).filter(
        Portfolio.id == portfolio_id,
        Portfolio.user_id == user_id
    ).first()


def create_portfolio(db: Session, user_id: str, name: str, description: str = None, is_default: bool = False) -> Portfolio:
    """Create a new portfolio"""
    # If setting as default, unset other defaults
    if is_default:
        db.query(Portfolio).filter(Portfolio.user_id == user_id).update({"is_default": 0})
    
    portfolio = Portfolio(
        user_id=user_id,
        name=name,
        description=description,
        is_default=1 if is_default else 0,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    
    db.add(portfolio)
    db.commit()
    db.refresh(portfolio)
    return portfolio


def update_portfolio(db: Session, portfolio_id: int, user_id: str, name: str = None, description: str = None, is_default: bool = None) -> Optional[Portfolio]:
    """Update portfolio details"""
    portfolio = get_portfolio_by_id(db, portfolio_id, user_id)
    if not portfolio:
        return None
    
    if name:
        portfolio.name = name
    if description is not None:
        portfolio.description = description
    if is_default is not None:
        if is_default:
            # Unset other defaults
            db.query(Portfolio).filter(Portfolio.user_id == user_id).update({"is_default": 0})
        portfolio.is_default = 1 if is_default else 0
    
    portfolio.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(portfolio)
    return portfolio


def delete_portfolio(db: Session, portfolio_id: int, user_id: str) -> bool:
    """Delete a portfolio"""
    portfolio = get_portfolio_by_id(db, portfolio_id, user_id)
    if not portfolio:
        return False
    
    db.delete(portfolio)
    db.commit()
    return True


# === POSITION OPERATIONS ===

def get_portfolio_positions(db: Session, portfolio_id: int) -> List[Position]:
    """Get all positions in a portfolio"""
    return db.query(Position).filter(Position.portfolio_id == portfolio_id).all()


def get_position_by_ticker(db: Session, portfolio_id: int, ticker: str) -> Optional[Position]:
    """Get a specific position by ticker"""
    return db.query(Position).filter(
        Position.portfolio_id == portfolio_id,
        Position.ticker == ticker.upper()
    ).first()


def update_position_from_transaction(db: Session, portfolio_id: int, ticker: str, transaction: Transaction):
    """Update or create position based on transaction"""
    position = get_position_by_ticker(db, portfolio_id, ticker)
    
    if transaction.transaction_type == TransactionType.BUY:
        if position:
            # Update existing position
            total_cost = (position.quantity * position.avg_price_brl) + transaction.total_brl
            new_quantity = position.quantity + transaction.quantity
            position.avg_price_brl = total_cost / new_quantity if new_quantity > 0 else 0
            position.quantity = new_quantity
            position.last_transaction_date = transaction.transaction_date
            position.updated_at = datetime.now(timezone.utc)
        else:
            # Create new position
            position = Position(
                portfolio_id=portfolio_id,
                ticker=ticker.upper(),
                quantity=transaction.quantity,
                avg_price_brl=transaction.price_brl,
                first_purchase_date=transaction.transaction_date,
                last_transaction_date=transaction.transaction_date,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            db.add(position)
    
    elif transaction.transaction_type == TransactionType.SELL:
        if position:
            position.quantity -= transaction.quantity
            position.last_transaction_date = transaction.transaction_date
            position.updated_at = datetime.now(timezone.utc)
            
            # Remove position if quantity is zero or negative
            if position.quantity <= 0:
                db.delete(position)
                return None
    
    elif transaction.transaction_type == TransactionType.DIVIDEND:
        # Dividends don't affect position quantity, just recorded in transactions
        pass
    
    db.commit()
    if position and position.id:
        db.refresh(position)
    return position


# === TRANSACTION OPERATIONS ===

def get_portfolio_transactions(db: Session, portfolio_id: int, limit: int = 100) -> List[Transaction]:
    """Get all transactions for a portfolio"""
    return db.query(Transaction).filter(
        Transaction.portfolio_id == portfolio_id
    ).order_by(desc(Transaction.transaction_date)).limit(limit).all()


def get_ticker_transactions(db: Session, portfolio_id: int, ticker: str) -> List[Transaction]:
    """Get all transactions for a specific ticker in a portfolio"""
    return db.query(Transaction).filter(
        Transaction.portfolio_id == portfolio_id,
        Transaction.ticker == ticker.upper()
    ).order_by(desc(Transaction.transaction_date)).all()


def add_transaction(
    db: Session,
    portfolio_id: int,
    ticker: str,
    transaction_type: TransactionType,
    quantity: float,
    price_brl: float,
    fees_brl: float = 0.0,
    transaction_date: datetime = None,
    notes: str = None
) -> Transaction:
    """Add a new transaction"""
    if not transaction_date:
        transaction_date = datetime.now(timezone.utc)
    
    total_brl = (quantity * price_brl) + fees_brl
    
    transaction = Transaction(
        portfolio_id=portfolio_id,
        ticker=ticker.upper(),
        transaction_type=transaction_type,
        quantity=quantity,
        price_brl=price_brl,
        total_brl=total_brl,
        fees_brl=fees_brl,
        transaction_date=transaction_date,
        notes=notes,
        created_at=datetime.now(timezone.utc)
    )
    
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    
    # Update position
    update_position_from_transaction(db, portfolio_id, ticker, transaction)
    
    return transaction


def delete_transaction(db: Session, transaction_id: int, portfolio_id: int) -> bool:
    """Delete a transaction and recalculate positions"""
    transaction = db.query(Transaction).filter(
        Transaction.id == transaction_id,
        Transaction.portfolio_id == portfolio_id
    ).first()
    
    if not transaction:
        return False
    
    ticker = transaction.ticker
    db.delete(transaction)
    db.commit()
    
    # Recalculate position for this ticker
    recalculate_position(db, portfolio_id, ticker)
    
    return True


def recalculate_position(db: Session, portfolio_id: int, ticker: str):
    """Recalculate position from all transactions"""
    # Delete existing position
    position = get_position_by_ticker(db, portfolio_id, ticker)
    if position:
        db.delete(position)
        db.commit()
    
    # Get all transactions for this ticker
    transactions = db.query(Transaction).filter(
        Transaction.portfolio_id == portfolio_id,
        Transaction.ticker == ticker.upper()
    ).order_by(Transaction.transaction_date).all()
    
    # Replay transactions
    for transaction in transactions:
        update_position_from_transaction(db, portfolio_id, ticker, transaction)


# === PORTFOLIO PERFORMANCE CALCULATIONS ===

def calculate_position_performance(db: Session, position: Position) -> Dict:
    """Calculate performance metrics for a single position"""
    # Get latest quote for this ticker
    asset = db.query(Asset).filter(Asset.ticker == position.ticker).first()
    if not asset:
        return None
    
    latest_quote = db.query(Quote).filter(Quote.asset_id == asset.id).order_by(desc(Quote.quote_date)).first()
    if not latest_quote:
        return None
    
    current_price = latest_quote.price_brl
    current_value = position.quantity * current_price
    invested_value = position.quantity * position.avg_price_brl
    
    profit_loss = current_value - invested_value
    profit_loss_pct = ((current_value / invested_value) - 1) * 100 if invested_value > 0 else 0
    
    return {
        "ticker": position.ticker,
        "quantity": position.quantity,
        "avg_price": position.avg_price_brl,
        "current_price": current_price,
        "invested_value": invested_value,
        "current_value": current_value,
        "profit_loss": profit_loss,
        "profit_loss_pct": profit_loss_pct,
        "first_purchase_date": position.first_purchase_date,
        "last_transaction_date": position.last_transaction_date,
    }


def calculate_portfolio_performance(db: Session, portfolio_id: int) -> Dict:
    """Calculate overall portfolio performance"""
    positions = get_portfolio_positions(db, portfolio_id)
    
    total_invested = 0.0
    total_current_value = 0.0
    positions_data = []
    
    for position in positions:
        perf = calculate_position_performance(db, position)
        if perf:
            positions_data.append(perf)
            total_invested += perf["invested_value"]
            total_current_value += perf["current_value"]
    
    total_profit_loss = total_current_value - total_invested
    total_profit_loss_pct = ((total_current_value / total_invested) - 1) * 100 if total_invested > 0 else 0
    
    # Get dividend income
    dividends = db.query(func.sum(Transaction.total_brl)).filter(
        Transaction.portfolio_id == portfolio_id,
        Transaction.transaction_type == TransactionType.DIVIDEND
    ).scalar() or 0.0
    
    return {
        "portfolio_id": portfolio_id,
        "total_invested": total_invested,
        "total_current_value": total_current_value,
        "total_profit_loss": total_profit_loss,
        "total_profit_loss_pct": total_profit_loss_pct,
        "dividend_income": dividends,
        "total_return": total_profit_loss + dividends,
        "total_return_pct": ((total_profit_loss + dividends) / total_invested * 100) if total_invested > 0 else 0,
        "positions_count": len(positions_data),
        "positions": positions_data
    }
