"""
MongoDB connection and utilities
"""
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class MongoDB:
    """
    MongoDB client wrapper
    """
    
    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.db = None
    
    async def connect(self):
        """
        Connect to MongoDB
        """
        try:
            self.client = AsyncIOMotorClient(settings.MONGODB_URL)
            self.db = self.client[settings.MONGODB_DATABASE]
            
            # Ping to verify connection
            await self.client.admin.command('ping')
            logger.info("✅ Connected to MongoDB")
        except Exception as e:
            logger.error(f"❌ MongoDB connection error: {str(e)}")
            raise
    
    async def disconnect(self):
        """
        Disconnect from MongoDB
        """
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")
    
    def get_collection(self, collection_name: str):
        """
        Get a collection from the database
        """
        return self.db[collection_name]


# Global MongoDB instance
mongodb = MongoDB()


async def get_mongodb() -> MongoDB:
    """
    Dependency for getting MongoDB instance
    """
    return mongodb
