"""
Unit tests for auth module – JWT creation and verification.
No network, no Google OAuth (those require integration tests).
"""
import pytest
import uuid
from datetime import timedelta

from auth import create_access_token, verify_token
from fastapi import HTTPException


class TestJWTTokens:

    def test_create_and_verify_token(self):
        user_id = str(uuid.uuid4())
        token = create_access_token(data={"sub": user_id})
        payload = verify_token(token)
        assert payload["sub"] == user_id

    def test_token_contains_expiration(self):
        token = create_access_token(data={"sub": "test"})
        payload = verify_token(token)
        assert "exp" in payload

    def test_custom_expiry(self):
        token = create_access_token(
            data={"sub": "test"},
            expires_delta=timedelta(minutes=5),
        )
        payload = verify_token(token)
        assert "exp" in payload

    def test_invalid_token_raises(self):
        with pytest.raises(HTTPException) as exc_info:
            verify_token("invalid.token.here")
        assert exc_info.value.status_code == 401

    def test_tampered_token_raises(self):
        token = create_access_token(data={"sub": "test"})
        # Tamper with the token payload
        parts = token.split(".")
        parts[1] = parts[1] + "tampered"
        tampered = ".".join(parts)
        with pytest.raises(HTTPException):
            verify_token(tampered)

    def test_empty_token_raises(self):
        with pytest.raises(HTTPException):
            verify_token("")
