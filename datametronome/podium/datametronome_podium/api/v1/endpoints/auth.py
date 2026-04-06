"""
Authentication endpoints for DataMetronome Podium.
"""

import json
from datetime import datetime, timedelta, timezone
from typing import Any

from datametronome_podium.api.schemas.auth import (
    Token,
    TokenData,
    UserCreate,
    UserLogin,
)
from datametronome_podium.core.config import settings
from datametronome_podium.core.database import execute_query, execute_write
from datametronome_podium.core.exceptions import AuthenticationError
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import ExpiredSignatureError, JWTError, jwt
from passlib.context import CryptContext

router = APIRouter()
security = HTTPBearer()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash.

    Args:
        plain_password: Plain text password.
        hashed_password: Hashed password.

    Returns:
        True if password matches, False otherwise.
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password.

    Args:
        password: Plain text password.

    Returns:
        Hashed password.
    """
    return pwd_context.hash(password)


def create_access_token(
    data: dict[str, Any], expires_delta: timedelta | None = None
) -> str:
    """Create a JWT access token.

    Args:
        data: Data to encode in the token.
        expires_delta: Token expiration time.

    Returns:
        JWT token string.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.access_token_expire_minutes
        )

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, settings.secret_key, algorithm=settings.algorithm
    )
    return encoded_jwt


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict[str, Any]:
    """Get current authenticated user.

    Args:
        credentials: HTTP authorization credentials.

    Returns:
        Current user instance.

    Raises:
        AuthenticationError: If authentication fails.
    """
    try:
        token = credentials.credentials
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )
        username: str = payload.get("sub")
        if username is None:
            raise AuthenticationError("Invalid token")
        token_data = TokenData(username=username)
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Query user from database using DataPulse (execute_query adapts ? to $1 for Postgres)
    users = await execute_query("SELECT * FROM users WHERE username = ?", [username])
    if not users:
        raise AuthenticationError("User not found")

    user = users[0]
    return user


@router.post("/login", response_model=Token)
async def login(user_credentials: UserLogin) -> dict[str, str]:
    """Authenticate user and return access token.

    Args:
        user_credentials: User login credentials.

    Returns:
        Access token.

    Raises:
        HTTPException: If authentication fails.
    """
    # Check if user exists (execute_query adapts ? to $1 for Postgres)
    users = await execute_query(
        "SELECT * FROM users WHERE username = ?", [user_credentials.username]
    )
    user = users[0] if users else None

    if not user or not verify_password(user_credentials.password, str(user["hashed_password"])):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user["username"]}, expires_delta=access_token_expires
    )

    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/register", response_model=Token)
async def register(user_data: UserCreate) -> dict[str, str]:
    """Register a new user.

    Args:
        user_data: User registration data.

    Returns:
        Access token for the new user.

    Raises:
        HTTPException: If registration fails.
    """
    # Check if user already exists (execute_query adapts ? to $1 for Postgres)
    existing_users = await execute_query(
        "SELECT * FROM users WHERE username = ?", [user_data.username]
    )
    if existing_users:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )

    # Create new user
    hashed_password = get_password_hash(user_data.password)
    now = datetime.now().isoformat()

    new_user_data = {
        "id": user_data.username,  # Use username as ID for simplicity
        "username": user_data.username,
        "email": user_data.email,
        "hashed_password": hashed_password,
        "is_active": True,
        "is_superuser": False,
        "created_at": now,
        "updated_at": now,
    }

    success = await insert_data("users", new_user_data)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user",
        )

    # Generate access token
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user_data.username}, expires_delta=access_token_expires
    )

    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=dict[str, Any])
async def get_current_user_info(
    current_user: dict[str, Any] = Depends(get_current_user)
) -> dict[str, Any]:
    """Get current user information.

    Args:
        current_user: Current authenticated user.

    Returns:
        Current user information.
    """
    # Parse dashboard_prefs — stored as JSON text in DB, default to empty prefs
    raw_prefs = current_user.get("dashboard_prefs") or "{}"
    try:
        prefs = json.loads(raw_prefs) if isinstance(raw_prefs, str) else raw_prefs
    except (ValueError, TypeError):
        prefs = {}
    if "pinned_staves" not in prefs:
        prefs["pinned_staves"] = []

    return {
        "username": current_user["username"],
        "email": current_user["email"],
        "is_active": current_user["is_active"],
        "is_superuser": current_user["is_superuser"],
        "dashboard_prefs": prefs,
    }


@router.patch("/me", response_model=dict[str, Any])
async def patch_current_user(
    body: dict[str, Any],
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Update current user preferences.

    Accepts: { "dashboard_prefs": { "pinned_staves": ["id1", "id2", "id3"] } }
    Replaces dashboard_prefs fully (not a merge).
    """
    if "dashboard_prefs" not in body:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="dashboard_prefs is required",
        )
    new_prefs = body["dashboard_prefs"]
    pinned = new_prefs.get("pinned_staves", [])

    if not isinstance(pinned, list):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="pinned_staves must be a list",
        )
    if len(pinned) > 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="pinned_staves cannot exceed 3 entries",
        )

    prefs_to_save = {"pinned_staves": [str(s) for s in pinned]}
    prefs_json = json.dumps(prefs_to_save)

    await execute_write(
        "UPDATE users SET dashboard_prefs = ? WHERE username = ?",
        [prefs_json, current_user["username"]],
    )

    return {
        "username": current_user["username"],
        "email": current_user["email"],
        "is_active": current_user["is_active"],
        "is_superuser": current_user["is_superuser"],
        "dashboard_prefs": prefs_to_save,
    }
