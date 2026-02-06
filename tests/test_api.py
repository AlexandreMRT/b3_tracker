"""
Integration tests for the FastAPI REST API.
Uses TestClient with an in-memory SQLite backend.
"""
# ---------------------------------------------------------------------------
# Health / System endpoints
# ---------------------------------------------------------------------------


class TestSystemEndpoints:
    def test_root_health_check(self, app_client):
        resp = app_client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "online"
        assert "endpoints" in data

    def test_docs_accessible(self, app_client):
        resp = app_client.get("/docs")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Quotes endpoints
# ---------------------------------------------------------------------------


class TestQuotesEndpoints:
    def test_get_all_quotes(self, app_client, sample_assets, sample_quotes):
        resp = app_client.get("/api/quotes")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] > 0
        assert isinstance(data["data"], list)

    def test_get_quotes_filter_by_type(self, app_client, sample_assets, sample_quotes):
        resp = app_client.get("/api/quotes?type=stock")
        assert resp.status_code == 200
        data = resp.json()
        for item in data["data"]:
            assert item["type"] == "stock"

    def test_get_single_quote(self, app_client, sample_assets, sample_quotes):
        resp = app_client.get("/api/quotes/PETR4")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["ticker"] == "PETR4.SA"
        assert "signals" in data

    def test_get_single_quote_with_suffix(self, app_client, sample_assets, sample_quotes):
        resp = app_client.get("/api/quotes/PETR4.SA")
        assert resp.status_code == 200

    def test_get_nonexistent_quote_returns_404(self, app_client, sample_assets):
        resp = app_client.get("/api/quotes/INVALID999")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Signals endpoints
# ---------------------------------------------------------------------------


class TestSignalsEndpoints:
    def test_get_signals(self, app_client, sample_assets, sample_quotes):
        resp = app_client.get("/api/signals")
        assert resp.status_code == 200
        data = resp.json()
        assert "by_signal" in data
        assert "data" in data

    def test_get_signals_filter(self, app_client, sample_assets, sample_quotes):
        resp = app_client.get("/api/signals?signal_type=GOLDEN_CROSS")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# News endpoints
# ---------------------------------------------------------------------------


class TestNewsEndpoints:
    def test_get_news(self, app_client, sample_assets, sample_quotes):
        resp = app_client.get("/api/news")
        assert resp.status_code == 200
        data = resp.json()
        assert "summary" in data
        assert "data" in data

    def test_get_news_filter_positive(self, app_client, sample_assets, sample_quotes):
        resp = app_client.get("/api/news?sentiment=positive")
        assert resp.status_code == 200
        for item in resp.json()["data"]:
            assert item["sentiment_score"] > 0.1


# ---------------------------------------------------------------------------
# Movers endpoints
# ---------------------------------------------------------------------------


class TestMoversEndpoints:
    def test_get_movers_default(self, app_client, sample_assets, sample_quotes):
        resp = app_client.get("/api/movers")
        assert resp.status_code == 200
        data = resp.json()
        assert "gainers" in data
        assert "losers" in data

    def test_get_movers_ytd(self, app_client, sample_assets, sample_quotes):
        resp = app_client.get("/api/movers?period=ytd&limit=3")
        assert resp.status_code == 200

    def test_get_movers_invalid_period(self, app_client, sample_assets, sample_quotes):
        resp = app_client.get("/api/movers?period=invalid")
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Sectors endpoints
# ---------------------------------------------------------------------------


class TestSectorsEndpoints:
    def test_get_sectors(self, app_client, sample_assets, sample_quotes):
        resp = app_client.get("/api/sectors")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] > 0


# ---------------------------------------------------------------------------
# Auth endpoints
# ---------------------------------------------------------------------------


class TestAuthEndpoints:
    def test_get_me(self, app_client):
        resp = app_client.get("/auth/me")
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "test@example.com"
        assert "id" in data

    def test_unauthenticated_request(self, unauthenticated_client):
        # No auth header → should be rejected
        resp = unauthenticated_client.get("/auth/me")
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Watchlist endpoints
# ---------------------------------------------------------------------------


class TestWatchlistEndpoints:
    def test_get_empty_watchlist(self, app_client):
        resp = app_client.get("/api/watchlist")
        assert resp.status_code == 200
        assert "watchlist" in resp.json()

    def test_add_and_remove_from_watchlist(self, app_client):
        # Add
        resp = app_client.post("/api/watchlist/PETR4.SA")
        assert resp.status_code == 200

        # Verify it's in the list
        resp = app_client.get("/api/watchlist")
        tickers = [w["ticker"] for w in resp.json()["watchlist"]]
        assert "PETR4.SA" in tickers

        # Remove
        resp = app_client.delete("/api/watchlist/PETR4.SA")
        assert resp.status_code == 200

    def test_remove_nonexistent_returns_404(self, app_client):
        resp = app_client.delete("/api/watchlist/NONEXIST")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Portfolio endpoints
# ---------------------------------------------------------------------------


class TestPortfolioEndpoints:
    def test_create_portfolio(self, app_client):
        resp = app_client.post("/api/portfolios?name=API+Test+Portfolio")
        assert resp.status_code == 200
        data = resp.json()
        assert data["portfolio"]["name"] == "API Test Portfolio"
        assert "id" in data["portfolio"]

    def test_list_portfolios(self, app_client, sample_portfolio):
        resp = app_client.get("/api/portfolios")
        assert resp.status_code == 200
        assert len(resp.json()["portfolios"]) >= 1

    def test_get_portfolio_details(self, app_client, sample_portfolio):
        resp = app_client.get(f"/api/portfolios/{sample_portfolio.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Test Portfolio"

    def test_get_nonexistent_portfolio_returns_404(self, app_client):
        resp = app_client.get("/api/portfolios/99999")
        assert resp.status_code == 404

    def test_update_portfolio(self, app_client, sample_portfolio):
        resp = app_client.put(f"/api/portfolios/{sample_portfolio.id}?name=Updated+Name")
        assert resp.status_code == 200

    def test_delete_portfolio(self, app_client, sample_user, db_session):
        from portfolio import create_portfolio

        p = create_portfolio(db_session, str(sample_user.id), "To Delete via API")
        resp = app_client.delete(f"/api/portfolios/{p.id}")
        assert resp.status_code == 200

    def test_get_positions(self, app_client, sample_portfolio, sample_assets, sample_quotes):
        resp = app_client.get(f"/api/portfolios/{sample_portfolio.id}/positions")
        assert resp.status_code == 200
        assert len(resp.json()["positions"]) == 2

    def test_get_portfolio_performance(self, app_client, sample_portfolio, sample_assets, sample_quotes):
        resp = app_client.get(f"/api/portfolios/{sample_portfolio.id}/performance")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_invested" in data
        assert "total_current_value" in data

    def test_add_transaction_via_api(self, app_client, sample_portfolio):
        resp = app_client.post(
            f"/api/portfolios/{sample_portfolio.id}/transactions",
            json={
                "ticker": "ITUB4.SA",
                "transaction_type": "BUY",
                "quantity": 50,
                "price_brl": 30.0,
                "fees_brl": 0.0,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["transaction"]["ticker"] == "ITUB4.SA"

    def test_add_transaction_invalid_type(self, app_client, sample_portfolio):
        resp = app_client.post(
            f"/api/portfolios/{sample_portfolio.id}/transactions",
            json={
                "ticker": "ITUB4.SA",
                "transaction_type": "INVALID",
                "quantity": 50,
                "price_brl": 30.0,
            },
        )
        assert resp.status_code == 400

    def test_list_transactions(self, app_client, sample_portfolio):
        resp = app_client.get(f"/api/portfolios/{sample_portfolio.id}/transactions")
        assert resp.status_code == 200
        assert "transactions" in resp.json()

    def test_delete_transaction_via_api(self, app_client, sample_portfolio, db_session):
        from models import TransactionType
        from portfolio import add_transaction

        tx = add_transaction(
            db_session,
            sample_portfolio.id,
            "ABEV3.SA",
            TransactionType.BUY,
            10,
            15.0,
        )
        resp = app_client.delete(f"/api/portfolios/{sample_portfolio.id}/transactions/{tx.id}")
        assert resp.status_code == 200
