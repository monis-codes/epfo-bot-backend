"""
Authentication and other reusable dependencies for API endpoints.
Handles JWT token validation and user authentication with Supabase.
"""

from typing import Annotated, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from supabase import Client, create_client
from gotrue.types import UserResponse

from .api_models import User
from .core.config import get_settings

# Get settings
settings = get_settings()

# Create Supabase client
supabase: Client = create_client(settings.supabase_url, settings.supabase_key)

# Security scheme - only HTTPBearer needed for Supabase JWT tokens
security = HTTPBearer()

# Rate limiter
limiter = Limiter(key_func=get_remote_address)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """
    Dependency to get the current authenticated user by validating the JWT
    with the Supabase Auth service.

    Args:
        credentials: The JWT credentials from Authorization Bearer header.

    Returns:
        User: The authenticated user object.

    Raises:
        HTTPException: If the token is invalid, expired, or validation fails.
    """
    try:
        # Extract token from credentials
        token = credentials.credentials
        
        # Validate token with Supabase
        user_response: UserResponse = supabase.auth.get_user(token)
        
        # Extract user from response
        authenticated_user = user_response.user
        
        if not authenticated_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or token is invalid",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # Return user data as Pydantic model
        return User(
            id=str(authenticated_user.id),
            email=str(authenticated_user.email),
            created_at=str(authenticated_user.created_at)
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"}
        )


def get_rate_limiter() -> Limiter:
    """Get the rate limiter instance."""
    return limiter


def create_rate_limit_exceeded_handler():
    """Create a custom rate limit exceeded handler."""
    def rate_limit_handler(request, exc):
        return JSONResponse(
            status_code=429,
            content={
                "detail": "Rate limit exceeded. Please try again later.",
                "retry_after": getattr(exc, 'retry_after', 60)
            }
        )
    return rate_limit_handler