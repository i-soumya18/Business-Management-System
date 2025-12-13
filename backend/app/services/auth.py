"""
Authentication service for business logic
"""
from typing import Optional, Tuple
from datetime import datetime, timedelta
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
import secrets

from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    validate_password_strength,
)
from app.repositories.user import UserRepository
from app.repositories.role import RoleRepository
from app.models.user import User
from app.schemas.auth import UserRegister, UserLogin, TokenResponse


class AuthService:
    """
    Service for authentication operations
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)
        self.role_repo = RoleRepository(db)
    
    async def register_user(self, user_data: UserRegister) -> User:
        """
        Register a new user
        """
        # Check if user already exists
        existing_user = await self.user_repo.get_by_email(user_data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Validate password strength
        validate_password_strength(user_data.password)
        
        # Hash password
        hashed_password = hash_password(user_data.password)
        
        # Create user
        user_dict = user_data.model_dump(exclude={'password'})
        user_dict['hashed_password'] = hashed_password
        
        user = await self.user_repo.create(user_dict)
        
        # Assign default role (if exists)
        default_role = await self.role_repo.get_by_name("user")
        if default_role:
            user = await self.user_repo.add_role(user, default_role)
        
        # TODO: Send verification email
        
        return user
    
    async def login(self, credentials: UserLogin) -> Tuple[User, TokenResponse]:
        """
        Authenticate user and return tokens
        """
        # Get user by email
        user = await self.user_repo.get_by_email(credentials.email)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password"
            )
        
        # Verify password
        if not verify_password(credentials.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password"
            )
        
        # Check if user is active
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive"
            )
        
        # Update last login
        await self.user_repo.update(user, {"last_login": datetime.utcnow()})
        
        # Create tokens
        token_data = {
            "sub": user.email,
            "user_id": str(user.id),
            "is_superuser": user.is_superuser
        }
        
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)
        
        return user, TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer"
        )
    
    async def get_current_user(self, token_payload: dict) -> User:
        """
        Get current user from token payload
        """
        email = token_payload.get("sub")
        if not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials"
            )
        
        user = await self.user_repo.get_by_email(email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive"
            )
        
        return user
    
    async def request_password_reset(self, email: str) -> bool:
        """
        Request password reset - generates token and sends email
        """
        user = await self.user_repo.get_by_email(email)
        if not user:
            # Don't reveal if email exists
            return True
        
        # Generate reset token
        reset_token = secrets.token_urlsafe(32)
        reset_expires = datetime.utcnow() + timedelta(hours=1)
        
        await self.user_repo.update(user, {
            "password_reset_token": reset_token,
            "password_reset_expires": reset_expires
        })
        
        # TODO: Send password reset email
        
        return True
    
    async def reset_password(self, token: str, new_password: str) -> bool:
        """
        Reset password using reset token
        """
        # Find user by reset token
        from sqlalchemy import select
        from app.models.user import User
        
        query = select(User).where(User.password_reset_token == token)
        result = await self.db.execute(query)
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token"
            )
        
        # Check if token is expired
        if user.password_reset_expires < datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reset token has expired"
            )
        
        # Validate new password
        validate_password_strength(new_password)
        
        # Update password
        hashed_password = hash_password(new_password)
        await self.user_repo.update(user, {
            "hashed_password": hashed_password,
            "password_reset_token": None,
            "password_reset_expires": None
        })
        
        return True
