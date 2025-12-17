"""
System information API endpoints.
"""

import os
import getpass
from fastapi import APIRouter
from pydantic import BaseModel

from .._version import __version__, __release_date__

router = APIRouter()


class UserResponse(BaseModel):
    """Response model for user information."""
    username: str


class VersionResponse(BaseModel):
    """Response model for version information."""
    version: str
    release_date: str


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


@router.get("/version", response_model=VersionResponse)
async def get_version():
    """
    Get the current Digital Article backend version and release date.

    Returns:
        VersionResponse: Current version information including release date
    """
    return VersionResponse(version=__version__, release_date=__release_date__)
