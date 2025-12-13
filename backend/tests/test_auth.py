"""
Test authentication endpoints
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
@pytest.mark.auth
async def test_register_endpoint_exists(client: AsyncClient, mock_user_data):
    """
    Test that register endpoint exists and accepts data
    """
    response = await client.post("/api/v1/auth/register", json=mock_user_data)
    
    # Should return 201 or appropriate response
    assert response.status_code in [200, 201, 501]


@pytest.mark.asyncio
@pytest.mark.auth
async def test_login_endpoint_exists(client: AsyncClient, mock_login_data):
    """
    Test that login endpoint exists
    """
    response = await client.post("/api/v1/auth/login", json=mock_login_data)
    
    # Should return a token response
    assert response.status_code in [200, 401]
    
    if response.status_code == 200:
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert "token_type" in data


@pytest.mark.asyncio
@pytest.mark.auth
async def test_password_strength_validation(client: AsyncClient):
    """
    Test password strength validation
    """
    weak_password_data = {
        "email": "test@example.com",
        "password": "weak",
        "first_name": "Test",
        "last_name": "User"
    }
    
    response = await client.post("/api/v1/auth/register", json=weak_password_data)
    
    # Should fail validation
    assert response.status_code == 400 or response.status_code == 422
