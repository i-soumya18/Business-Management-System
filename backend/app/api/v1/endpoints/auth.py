"""
Authentication endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_token, get_current_user_token
from app.schemas.auth import (
    UserRegister,
    UserLogin,
    TokenResponse,
    RefreshTokenRequest,
    PasswordResetRequest,
    PasswordReset,
)
from app.schemas.user import UserResponse
from app.services.auth import AuthService

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserRegister,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new user
    
    Creates a new user account with the provided credentials.
    Password must be at least 8 characters with uppercase, lowercase, and digits.
    """
    auth_service = AuthService(db)
    user = await auth_service.register_user(user_data)
    return UserResponse.model_validate(user)


@router.post("/login", response_model=TokenResponse)
async def login(
    credentials: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    """
    User login - returns access and refresh tokens
    
    Authenticates user with email and password, returns JWT tokens.
    """
    auth_service = AuthService(db)
    user, tokens = await auth_service.login(credentials)
    return tokens


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Refresh access token using refresh token
    
    Validates refresh token and issues new access and refresh tokens.
    """
    # Decode and validate refresh token
    payload = decode_token(refresh_data.refresh_token)
    
    # Validate token type
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type"
        )
    
    # Verify user still exists and is active
    auth_service = AuthService(db)
    user = await auth_service.get_current_user(payload)
    
    # Create new tokens
    from app.core.security import create_access_token, create_refresh_token
    
    token_data = {
        "sub": user.email,
        "user_id": str(user.id),
        "is_superuser": user.is_superuser
    }
    
    access_token = create_access_token(token_data)
    new_refresh_token = create_refresh_token(token_data)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer"
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    token_payload: dict = Depends(get_current_user_token),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current authenticated user
    
    Returns the currently authenticated user's profile.
    """
    auth_service = AuthService(db)
    user = await auth_service.get_current_user(token_payload)
    return UserResponse.model_validate(user)


@router.post("/password-reset/request")
async def request_password_reset(
    request_data: PasswordResetRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Request password reset
    
    Sends a password reset email to the user if the email exists.
    """
    auth_service = AuthService(db)
    await auth_service.request_password_reset(request_data.email)
    
    return {
        "message": "If the email exists, a password reset link will be sent"
    }


@router.post("/password-reset/confirm")
async def reset_password(
    reset_data: PasswordReset,
    db: AsyncSession = Depends(get_db)
):
    """
    Reset password with token
    
    Resets user password using the token from the reset email.
    """
    auth_service = AuthService(db)
    await auth_service.reset_password(reset_data.token, reset_data.new_password)
    
    return {"message": "Password reset successfully"}


@router.post("/logout")
async def logout(
    token_payload: dict = Depends(get_current_user_token),
    db: AsyncSession = Depends(get_db)
):
    """
    User logout
    
    Logs out the current user. Token blacklisting will be implemented in future.
    """
    # TODO: Add token to blacklist in Redis
    # TODO: Clear user session
    
    return {"message": "Logged out successfully"}
