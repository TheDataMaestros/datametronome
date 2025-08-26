"""
Authentication endpoints for DataMetronome Podium.
"""

from datetime import datetime, timedelta
from typing import Any
import json

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext

from datametronome_podium.core.config import settings
from datametronome_podium.core.database import get_db, execute_query, insert_data
from datametronome_podium.core.exceptions import AuthenticationError
from datametronome_podium.api.schemas.auth import Token, TokenData, UserCreate, UserLogin

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


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """Create a JWT access token.
    
    Args:
        data: Data to encode in the token.
        expires_delta: Token expiration time.
        
    Returns:
        JWT token string.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
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
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        username: str = payload.get("sub")
        if username is None:
            raise AuthenticationError("Invalid token")
        token_data = TokenData(username=username)
    except JWTError:
        raise AuthenticationError("Invalid token")
    
    # Query user from database using DataPulse
    db = await get_db()
    users = await db.query({"sql": "SELECT * FROM users WHERE username = ?", "params": [username]})
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
    db = await get_db()
    
    # Check if user exists
    users = await db.query({"sql": "SELECT * FROM users WHERE username = ?", "params": [user_credentials.username]})
    user = users[0] if users else None
    
    if not user:
        # Create default user for prototype
        hashed_password = get_password_hash("admin")
        now = datetime.now().isoformat()
        
        user_data = {
            "id": "admin",
            "username": "admin",
            "email": "admin@datametronome.dev",
            "hashed_password": hashed_password,
            "is_active": True,
            "is_superuser": True,
            "created_at": now,
            "updated_at": now
        }
        
        success = await insert_data("users", user_data)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create default user"
            )
        
        user = user_data
    
    if not verify_password(user_credentials.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
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
    db = await get_db()
    
    # Check if user already exists
    existing_users = await db.query({"sql": "SELECT * FROM users WHERE username = ?", "params": [user_data.username]})
    if existing_users:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
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
        "updated_at": now
    }
    
    success = await insert_data("users", new_user_data)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user"
        )
    
    # Generate access token
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user_data.username}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=dict[str, Any])
async def get_current_user_info(current_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    """Get current user information.
    
    Args:
        current_user: Current authenticated user.
        
    Returns:
        Current user information.
    """
    return {
        "username": current_user["username"],
        "email": current_user["email"],
        "is_active": current_user["is_active"],
        "is_superuser": current_user["is_superuser"]
    }
