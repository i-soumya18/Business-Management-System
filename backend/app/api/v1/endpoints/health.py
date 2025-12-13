"""
Health check endpoints
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import logging

from app.core.database import get_db
from app.core.redis import get_redis, RedisClient
from app.core.mongodb import get_mongodb, MongoDB

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/")
async def health_check():
    """
    Basic health check endpoint
    """
    return {
        "status": "healthy",
        "message": "API is operational"
    }


@router.get("/detailed")
async def detailed_health_check(
    db: AsyncSession = Depends(get_db),
    redis: RedisClient = Depends(get_redis),
    mongo: MongoDB = Depends(get_mongodb)
):
    """
    Detailed health check with database connectivity
    """
    health_status = {
        "status": "healthy",
        "services": {}
    }
    
    # Check PostgreSQL
    try:
        result = await db.execute(text("SELECT 1"))
        health_status["services"]["postgresql"] = {
            "status": "connected",
            "message": "Database is accessible"
        }
    except Exception as e:
        logger.error(f"PostgreSQL health check failed: {str(e)}")
        health_status["services"]["postgresql"] = {
            "status": "error",
            "message": str(e)
        }
        health_status["status"] = "unhealthy"
    
    # Check Redis
    try:
        await redis.redis.ping()
        health_status["services"]["redis"] = {
            "status": "connected",
            "message": "Redis is accessible"
        }
    except Exception as e:
        logger.error(f"Redis health check failed: {str(e)}")
        health_status["services"]["redis"] = {
            "status": "error",
            "message": str(e)
        }
        health_status["status"] = "degraded"
    
    # Check MongoDB
    try:
        await mongo.client.admin.command('ping')
        health_status["services"]["mongodb"] = {
            "status": "connected",
            "message": "MongoDB is accessible"
        }
    except Exception as e:
        logger.error(f"MongoDB health check failed: {str(e)}")
        health_status["services"]["mongodb"] = {
            "status": "error",
            "message": str(e)
        }
        health_status["status"] = "degraded"
    
    return health_status
