"""
User management endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID

from app.core.database import get_db
from app.core.security import get_current_user_token
from app.schemas.user import (
    UserResponse,
    UserWithRoles,
    UserCreate,
    UserUpdate,
)
from app.services.auth import AuthService
from app.services.user import UserService

router = APIRouter()


async def get_current_active_user(
    token_payload: dict = Depends(get_current_user_token),
    db: AsyncSession = Depends(get_db)
):
    """
    Dependency to get current active user
    """
    auth_service = AuthService(db)
    return await auth_service.get_current_user(token_payload)


async def get_current_superuser(
    token_payload: dict = Depends(get_current_user_token),
    db: AsyncSession = Depends(get_db)
):
    """
    Dependency to verify current user is a superuser
    """
    auth_service = AuthService(db)
    user = await auth_service.get_current_user(token_payload)
    
    if not user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    return user


@router.get("/", response_model=List[UserResponse])
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    is_active: bool = Query(None),
    current_user = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    """
    List all users (superuser only)
    
    Returns a paginated list of all users.
    """
    user_service = UserService(db)
    users = await user_service.get_all_users(skip=skip, limit=limit, is_active=is_active)
    return [UserResponse.model_validate(user) for user in users]


@router.get("/search", response_model=List[UserResponse])
async def search_users(
    q: str = Query(..., min_length=1),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    current_user = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    """
    Search users (superuser only)
    
    Search users by email, first name, or last name.
    """
    user_service = UserService(db)
    users = await user_service.search_users(q, skip=skip, limit=limit)
    return [UserResponse.model_validate(user) for user in users]


@router.get("/{user_id}", response_model=UserWithRoles)
async def get_user(
    user_id: UUID,
    current_user = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    """
    Get user by ID (superuser only)
    
    Returns detailed user information including roles.
    """
    user_service = UserService(db)
    user = await user_service.get_user_by_id(user_id)
    return UserWithRoles.model_validate(user)


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    user_update: UserUpdate,
    current_user = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    """
    Update user (superuser only)
    
    Updates user information.
    """
    user_service = UserService(db)
    user = await user_service.update_user(user_id, user_update)
    return UserResponse.model_validate(user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: UUID,
    current_user = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete user (superuser only)
    
    Permanently deletes a user account.
    """
    user_service = UserService(db)
    await user_service.delete_user(user_id)
    return None


@router.post("/{user_id}/roles/{role_id}", response_model=UserWithRoles)
async def add_role_to_user(
    user_id: UUID,
    role_id: UUID,
    current_user = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    """
    Add role to user (superuser only)
    
    Assigns a role to a user.
    """
    user_service = UserService(db)
    user = await user_service.add_role_to_user(user_id, role_id)
    return UserWithRoles.model_validate(user)


@router.delete("/{user_id}/roles/{role_id}", response_model=UserWithRoles)
async def remove_role_from_user(
    user_id: UUID,
    role_id: UUID,
    current_user = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    """
    Remove role from user (superuser only)
    
    Removes a role from a user.
    """
    user_service = UserService(db)
    user = await user_service.remove_role_from_user(user_id, role_id)
    return UserWithRoles.model_validate(user)
