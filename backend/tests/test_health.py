"""
Test health check endpoints
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
@pytest.mark.unit
async def test_health_check(client: AsyncClient):
    """
    Test basic health check endpoint
    """
    response = await client.get("/api/v1/health/")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "message" in data


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.database
async def test_detailed_health_check(client: AsyncClient):
    """
    Test detailed health check with service status
    """
    response = await client.get("/api/v1/health/detailed")
    
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "services" in data
    assert "postgresql" in data["services"]
