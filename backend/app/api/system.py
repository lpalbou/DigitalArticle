"""
System information API endpoints.
"""

import os
import getpass
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class UserResponse(BaseModel):
    """Response model for user information."""
    username: str


@router.get("/user", response_model=UserResponse)
async def get_current_user():
    """
    Get the current system user.
    
    Returns:
        UserResponse: Current system user information
    """
    try:
        # Try to get the current user using getpass (more reliable than os.getlogin)
        username = getpass.getuser()
    except Exception:
        # Fallback to environment variables
        username = os.environ.get('USER') or os.environ.get('USERNAME') or 'user'
    
    return UserResponse(username=username)
