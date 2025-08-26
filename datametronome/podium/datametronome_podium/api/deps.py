"""
Dependencies for DataMetronome Podium API.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from typing import Dict, Any

from datametronome_podium.core.config import settings
from datametronome_podium.core.exceptions import AuthenticationError
from datametronome_podium.core.database import get_db

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
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
    except JWTError:
        raise AuthenticationError("Invalid token")
    
    # Query user from database using DataPulse
    db = await get_db()
    users = await db.query({"sql": "SELECT * FROM users WHERE username = ?", "params": [username]})
    if not users:
        raise AuthenticationError("User not found")
    
    user = users[0]
    return user




