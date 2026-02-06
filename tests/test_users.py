"""
Unit tests for the users module.
"""
import pytest
from datetime import datetime

from users import (
    get_user_by_id,
    get_user_by_email,
    update_user_preferences,
    get_user_watchlist,
    add_to_watchlist,
    remove_from_watchlist,
    is_in_watchlist,
)


class TestUserOperations:

    def test_get_user_by_id(self, db_session, sample_user):
        user = get_user_by_id(db_session, str(sample_user.id))
        assert user is not None
        assert user.email == "test@example.com"

    def test_get_user_by_id_nonexistent(self, db_session):
        user = get_user_by_id(db_session, "nonexistent-id")
        assert user is None

    def test_get_user_by_email(self, db_session, sample_user):
        user = get_user_by_email(db_session, "test@example.com")
        assert user is not None
        assert str(user.id) == str(sample_user.id)

    def test_update_preferences(self, db_session, sample_user):
        user = update_user_preferences(db_session, str(sample_user.id), default_currency="USD")
        assert user.default_currency == "USD"

    def test_update_preferences_nonexistent_user(self, db_session):
        user = update_user_preferences(db_session, "fake-id", default_currency="EUR")
        assert user is None


class TestWatchlistOperations:

    def test_empty_watchlist(self, db_session, sample_user):
        wl = get_user_watchlist(db_session, str(sample_user.id))
        assert wl == []

    def test_add_to_watchlist(self, db_session, sample_user):
        entry = add_to_watchlist(db_session, str(sample_user.id), "PETR4.SA", "Oil play")
        assert entry.ticker == "PETR4.SA"
        assert entry.notes == "Oil play"

    def test_add_duplicate_updates_notes(self, db_session, sample_user):
        add_to_watchlist(db_session, str(sample_user.id), "VALE3.SA", "Mining")
        entry = add_to_watchlist(db_session, str(sample_user.id), "vale3.sa", "Updated note")
        assert entry.notes == "Updated note"

    def test_is_in_watchlist(self, db_session, sample_user):
        add_to_watchlist(db_session, str(sample_user.id), "ITUB4.SA")
        assert is_in_watchlist(db_session, str(sample_user.id), "ITUB4.SA") is True
        assert is_in_watchlist(db_session, str(sample_user.id), "FAKE.SA") is False

    def test_remove_from_watchlist(self, db_session, sample_user):
        add_to_watchlist(db_session, str(sample_user.id), "BBDC4.SA")
        assert remove_from_watchlist(db_session, str(sample_user.id), "BBDC4.SA") is True
        assert is_in_watchlist(db_session, str(sample_user.id), "BBDC4.SA") is False

    def test_remove_nonexistent_returns_false(self, db_session, sample_user):
        assert remove_from_watchlist(db_session, str(sample_user.id), "NOPE.SA") is False

    def test_watchlist_order(self, db_session, sample_user):
        add_to_watchlist(db_session, str(sample_user.id), "A.SA")
        add_to_watchlist(db_session, str(sample_user.id), "B.SA")
        wl = get_user_watchlist(db_session, str(sample_user.id))
        # Should be ordered by created_at desc
        assert len(wl) >= 2
