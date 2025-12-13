"""
Create admin user script
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
# from app.models.user import User
# from app.models.role import Role

async def create_admin():
    """
    Create admin user
    """
    async with AsyncSessionLocal() as session:
        try:
            print("Creating admin user...")
            
            # TODO: Implement once User and Role models are created
            # Check if admin exists
            # If not, create admin user with hashed password
            # Assign admin role
            
            print("✅ Admin user will be created in Phase 1")
            print("This is a placeholder script")
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            raise


if __name__ == "__main__":
    asyncio.run(create_admin())
