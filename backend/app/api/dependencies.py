"""
API Dependencies

Reusable dependencies for FastAPI routes including authentication,
database sessions, and common query parameters.
"""

from typing import Generator, Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.user import User
from app.repositories.user import UserRepository


# Security scheme for JWT Bearer tokens
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Dependency to get current authenticated user from JWT token
    
    Args:
        credentials: HTTP Bearer token credentials
        db: Database session
        
    Returns:
        Current user object
        
    Raises:
        HTTPException: If token is invalid or user not found
    """
    from jose import JWTError, jwt
    from app.core.config import settings
    
    token = credentials.credentials
    
    try:
        # Decode JWT token
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        
        # Extract user identifier (email or user_id)
        user_email: str = payload.get("sub")
        user_id_str: str = payload.get("user_id")
        
        if not user_email and not user_id_str:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Get user from database
        user_repo = UserRepository(db)
        
        if user_id_str:
            try:
                user_id = UUID(user_id_str)
                user = await user_repo.get(user_id)
            except (ValueError, TypeError):
                user = None
        elif user_email:
            user = await user_repo.get_by_email(user_email)
        else:
            user = None
        
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return user
        
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Dependency to get current active user
    
    Args:
        current_user: Current user from token
        
    Returns:
        Active user object
        
    Raises:
        HTTPException: If user is inactive
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user


class PaginationParams:
    """Common pagination parameters"""
    
    def __init__(
        self,
        skip: int = 0,
        limit: int = 100
    ):
        self.skip = skip
        self.limit = min(limit, 1000)  # Max 1000 items per page


class SearchParams:
    """Common search parameters"""
    
    def __init__(
        self,
        q: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ):
        self.q = q
        self.skip = skip
        self.limit = min(limit, 1000)
