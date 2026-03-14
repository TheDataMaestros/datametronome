"""
API schemas for DataMetronome Podium.

Auth schemas stay here. Stave/Clef/Check schemas moved to features/.
"""

from .auth import Token, TokenData, UserCreate, UserLogin

# Re-export from features for backward compatibility
from datametronome_podium.features.staves.schema import StaveCreate, StaveResponse, StaveUpdate
from datametronome_podium.features.clefs.schema import ClefCreate, ClefResponse, ClefUpdate

__all__ = [
    "StaveCreate",
    "StaveResponse",
    "StaveUpdate",
    "ClefCreate",
    "ClefResponse",
    "ClefUpdate",
    "Token",
    "TokenData",
    "UserCreate",
    "UserLogin",
]
