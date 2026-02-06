"""
Tests for portfolio operations – uses the in-memory DB from conftest.
"""

from datetime import datetime, timezone

import pytest

from models import Position, TransactionType
from portfolio import (
    add_transaction,
    calculate_portfolio_performance,
    calculate_position_performance,
    create_portfolio,
    delete_portfolio,
    delete_transaction,
    get_portfolio_by_id,
    get_portfolio_positions,
    get_portfolio_transactions,
    get_position_by_ticker,
    get_user_portfolios,
    update_portfolio,
)

# ---------------------------------------------------------------------------
# Portfolio CRUD
# ---------------------------------------------------------------------------


class TestPortfolioCRUD:
    def test_create_portfolio(self, db_session, sample_user):
        p = create_portfolio(db_session, str(sample_user.id), "My Portfolio", "desc", is_default=True)
        assert p.id is not None
        assert p.name == "My Portfolio"
        assert p.is_default == 1

    def test_create_second_default_unsets_first(self, db_session, sample_user):
        p1 = create_portfolio(db_session, str(sample_user.id), "First", is_default=True)
        p2 = create_portfolio(db_session, str(sample_user.id), "Second", is_default=True)
        db_session.refresh(p1)
        assert p1.is_default == 0
        assert p2.is_default == 1

    def test_get_user_portfolios(self, db_session, sample_user, sample_portfolio):
        portfolios = get_user_portfolios(db_session, str(sample_user.id))
        assert len(portfolios) >= 1
        names = [p.name for p in portfolios]
        assert "Test Portfolio" in names

    def test_get_portfolio_by_id_with_correct_user(self, db_session, sample_user, sample_portfolio):
        p = get_portfolio_by_id(db_session, sample_portfolio.id, str(sample_user.id))
        assert p is not None
        assert p.id == sample_portfolio.id

    def test_get_portfolio_by_id_wrong_user_returns_none(self, db_session, sample_portfolio):
        p = get_portfolio_by_id(db_session, sample_portfolio.id, "wrong-user-id")
        assert p is None

    def test_update_portfolio_name(self, db_session, sample_user, sample_portfolio):
        updated = update_portfolio(db_session, sample_portfolio.id, str(sample_user.id), name="Renamed")
        assert updated.name == "Renamed"

    def test_delete_portfolio(self, db_session, sample_user):
        p = create_portfolio(db_session, str(sample_user.id), "To Delete")
        assert delete_portfolio(db_session, p.id, str(sample_user.id)) is True
        assert get_portfolio_by_id(db_session, p.id, str(sample_user.id)) is None

    def test_delete_nonexistent_portfolio_returns_false(self, db_session, sample_user):
        assert delete_portfolio(db_session, 99999, str(sample_user.id)) is False


# ---------------------------------------------------------------------------
# Positions
# ---------------------------------------------------------------------------


class TestPositions:
    def test_positions_exist_after_fixture(self, db_session, sample_portfolio):
        positions = get_portfolio_positions(db_session, sample_portfolio.id)
        assert len(positions) == 2
        tickers = {p.ticker for p in positions}
        assert "PETR4.SA" in tickers
        assert "VALE3.SA" in tickers

    def test_get_position_by_ticker(self, db_session, sample_portfolio):
        pos = get_position_by_ticker(db_session, sample_portfolio.id, "PETR4.SA")
        assert pos is not None
        assert pos.quantity == 100
        assert pos.avg_price_brl == 35.00

    def test_get_position_case_insensitive(self, db_session, sample_portfolio):
        pos = get_position_by_ticker(db_session, sample_portfolio.id, "petr4.sa")
        assert pos is not None


# ---------------------------------------------------------------------------
# Transactions
# ---------------------------------------------------------------------------


class TestTransactions:
    def test_add_buy_transaction_creates_position(self, db_session, sample_user):
        p = create_portfolio(db_session, str(sample_user.id), "TX Test")

        tx = add_transaction(
            db=db_session,
            portfolio_id=p.id,
            ticker="ITUB4.SA",
            transaction_type=TransactionType.BUY,
            quantity=200,
            price_brl=25.00,
        )
        assert tx.id is not None
        assert tx.total_brl == 200 * 25.00

        pos = get_position_by_ticker(db_session, p.id, "ITUB4.SA")
        assert pos is not None
        assert pos.quantity == 200
        assert pos.avg_price_brl == 25.00

    def test_second_buy_updates_average_price(self, db_session, sample_user):
        p = create_portfolio(db_session, str(sample_user.id), "Avg Price Test")

        add_transaction(db_session, p.id, "BBDC4.SA", TransactionType.BUY, 100, 20.00)
        add_transaction(db_session, p.id, "BBDC4.SA", TransactionType.BUY, 100, 30.00)

        pos = get_position_by_ticker(db_session, p.id, "BBDC4.SA")
        assert pos.quantity == 200
        # Avg = (100*20 + 100*30) / 200 = 25.0
        assert pos.avg_price_brl == pytest.approx(25.0)

    def test_sell_reduces_position(self, db_session, sample_user):
        p = create_portfolio(db_session, str(sample_user.id), "Sell Test")

        add_transaction(db_session, p.id, "WEGE3.SA", TransactionType.BUY, 100, 40.00)
        add_transaction(db_session, p.id, "WEGE3.SA", TransactionType.SELL, 30, 45.00)

        pos = get_position_by_ticker(db_session, p.id, "WEGE3.SA")
        assert pos.quantity == 70

    def test_sell_all_removes_position(self, db_session, sample_user):
        p = create_portfolio(db_session, str(sample_user.id), "Sell All Test")

        add_transaction(db_session, p.id, "MGLU3.SA", TransactionType.BUY, 50, 10.00)
        add_transaction(db_session, p.id, "MGLU3.SA", TransactionType.SELL, 50, 12.00)

        pos = get_position_by_ticker(db_session, p.id, "MGLU3.SA")
        assert pos is None

    def test_dividend_does_not_affect_position(self, db_session, sample_user):
        p = create_portfolio(db_session, str(sample_user.id), "Div Test")

        add_transaction(db_session, p.id, "TAEE11.SA", TransactionType.BUY, 100, 35.00)
        add_transaction(db_session, p.id, "TAEE11.SA", TransactionType.DIVIDEND, 100, 1.50)

        pos = get_position_by_ticker(db_session, p.id, "TAEE11.SA")
        assert pos.quantity == 100  # unchanged

    def test_get_portfolio_transactions(self, db_session, sample_portfolio):
        txs = get_portfolio_transactions(db_session, sample_portfolio.id)
        assert len(txs) >= 3  # 2 buys + 1 dividend from fixture

    def test_delete_transaction_recalculates(self, db_session, sample_user):
        p = create_portfolio(db_session, str(sample_user.id), "Delete TX Test")

        _tx1 = add_transaction(db_session, p.id, "RENT3.SA", TransactionType.BUY, 100, 50.00)  # noqa: F841
        tx2 = add_transaction(db_session, p.id, "RENT3.SA", TransactionType.BUY, 50, 60.00)

        # Delete second transaction -> should recalculate to just the first buy
        assert delete_transaction(db_session, tx2.id, p.id) is True

        pos = get_position_by_ticker(db_session, p.id, "RENT3.SA")
        assert pos is not None
        assert pos.quantity == 100
        assert pos.avg_price_brl == pytest.approx(50.00)

    def test_add_transaction_with_fees(self, db_session, sample_user):
        p = create_portfolio(db_session, str(sample_user.id), "Fee Test")

        tx = add_transaction(
            db_session,
            p.id,
            "ABEV3.SA",
            TransactionType.BUY,
            quantity=100,
            price_brl=15.00,
            fees_brl=7.50,
        )
        # total_brl = (100 * 15) + 7.50 = 1507.50
        assert tx.total_brl == pytest.approx(1507.50)


# ---------------------------------------------------------------------------
# Performance Calculations
# ---------------------------------------------------------------------------


class TestPerformanceCalculations:
    def test_position_performance(self, db_session, sample_portfolio, sample_assets, sample_quotes):
        """PETR4 bought at 35, current price 38.50 => profit."""
        pos = get_position_by_ticker(db_session, sample_portfolio.id, "PETR4.SA")
        perf = calculate_position_performance(db_session, pos)

        assert perf is not None
        assert perf["ticker"] == "PETR4.SA"
        assert perf["quantity"] == 100
        assert perf["avg_price"] == 35.00
        assert perf["current_price"] == pytest.approx(38.50)
        assert perf["invested_value"] == pytest.approx(3500.00)
        assert perf["current_value"] == pytest.approx(3850.00)
        assert perf["profit_loss"] == pytest.approx(350.00)
        assert perf["profit_loss_pct"] == pytest.approx(10.0)

    def test_position_performance_with_loss(self, db_session, sample_portfolio, sample_assets, sample_quotes):
        """VALE3 bought at 68, current price 62.30 => loss."""
        pos = get_position_by_ticker(db_session, sample_portfolio.id, "VALE3.SA")
        perf = calculate_position_performance(db_session, pos)

        assert perf is not None
        assert perf["profit_loss"] < 0
        assert perf["profit_loss_pct"] < 0

    def test_portfolio_performance_aggregates(self, db_session, sample_portfolio, sample_assets, sample_quotes):
        """Portfolio should aggregate across all positions."""
        perf = calculate_portfolio_performance(db_session, sample_portfolio.id)

        assert perf["portfolio_id"] == sample_portfolio.id
        assert perf["total_invested"] > 0
        assert perf["total_current_value"] > 0
        assert perf["positions_count"] == 2
        # Dividend income should include the 50 BRL from fixture
        assert perf["dividend_income"] == pytest.approx(50.00)
        # total_return = profit_loss + dividends
        assert perf["total_return"] == pytest.approx(perf["total_profit_loss"] + perf["dividend_income"])

    def test_position_performance_no_asset_returns_none(self, db_session, sample_portfolio):
        """Position for a non-existent asset should return None."""
        pos = Position(
            portfolio_id=sample_portfolio.id,
            ticker="FAKE.SA",
            quantity=100,
            avg_price_brl=10.0,
            first_purchase_date=datetime.now(timezone.utc),
            last_transaction_date=datetime.now(timezone.utc),
        )
        db_session.add(pos)
        db_session.flush()

        perf = calculate_position_performance(db_session, pos)
        assert perf is None
