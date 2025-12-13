"""
Test security utilities
"""
import pytest
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    validate_password_strength,
)
from fastapi import HTTPException


@pytest.mark.unit
def test_password_hashing():
    """
    Test password hashing and verification
    """
    password = "SecurePassword123"
    hashed = hash_password(password)
    
    assert hashed != password
    assert verify_password(password, hashed)
    assert not verify_password("WrongPassword", hashed)


@pytest.mark.unit
def test_access_token_creation():
    """
    Test JWT access token creation and decoding
    """
    data = {"sub": "test@example.com", "user_id": "123"}
    token = create_access_token(data)
    
    assert token is not None
    assert isinstance(token, str)
    
    decoded = decode_token(token)
    assert decoded["sub"] == data["sub"]
    assert decoded["user_id"] == data["user_id"]
    assert decoded["type"] == "access"


@pytest.mark.unit
def test_refresh_token_creation():
    """
    Test JWT refresh token creation
    """
    data = {"sub": "test@example.com", "user_id": "123"}
    token = create_refresh_token(data)
    
    assert token is not None
    assert isinstance(token, str)
    
    decoded = decode_token(token)
    assert decoded["sub"] == data["sub"]
    assert decoded["type"] == "refresh"


@pytest.mark.unit
def test_password_strength_validation():
    """
    Test password strength validation
    """
    # Strong password
    assert validate_password_strength("SecurePass123")
    
    # Weak passwords
    with pytest.raises(HTTPException):
        validate_password_strength("weak")
    
    with pytest.raises(HTTPException):
        validate_password_strength("alllowercase123")
    
    with pytest.raises(HTTPException):
        validate_password_strength("ALLUPPERCASE123")
    
    with pytest.raises(HTTPException):
        validate_password_strength("NoNumbers")
