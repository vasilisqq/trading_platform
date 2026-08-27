import pytest
from src.core.security import (hash_password, 
verify_password, 
create_access_token, create_refresh_token,
decode_access_token, decode_refresh_token,
_create_token)
import jwt
from datetime import datetime, timezone


class TestSecurity:
    def test_verify_password(self):
        password = "1234"
        hashed_password = hash_password(password)
        assert hashed_password != password
        assert verify_password(password, hashed_password) is True
        assert verify_password("wrong", hashed_password) is False

    def test_long_password(self):
        base = "A" * 72
        hashed_password = hash_password(base + "111")
        assert verify_password(base+"999", hashed_password) is False
        assert verify_password(base+"111", hashed_password) is True

    def test_decode_access_token(self):
        token = create_access_token(
            {"name": "test"}
        )
        data = decode_access_token(token)
        assert data["exp"] is not None
        assert data["iat"] is not None
        assert data["exp"] > data["iat"]
        assert data["jti"] is not None
        assert data["type"] == "access"
        assert data["name"] == "test"
        with pytest.raises(jwt.InvalidTokenError):
            decode_refresh_token(token)


    def test_decode_refresh_token(self):
        token = create_refresh_token({"name": "test"})
        data = decode_refresh_token(token)
        assert data["exp"] is not None
        assert data["iat"] is not None
        assert data["exp"] > data["iat"]
        assert data.get("jti") is None
        assert data["type"] == "refresh"
        assert data["name"] == "test"
        with pytest.raises(jwt.InvalidTokenError):
            decode_access_token(token)

    def test_invalid_token_type(self):
        with pytest.raises(ValueError):
            _create_token("wwww", {"data": "test"})

