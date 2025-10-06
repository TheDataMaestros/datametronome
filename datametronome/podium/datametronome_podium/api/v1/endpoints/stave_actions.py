"""
Stave action endpoints - Test connection functionality.

This module provides endpoints for testing stave connections and other
stave-specific actions.
"""

import asyncio
import logging
from typing import Any, Dict
from datetime import datetime

from fastapi import APIRouter, HTTPException, status

from datametronome_podium.core.database import get_db
from datametronome_podium.services.stave_service import deserialize_stave
from datametronome_podium.services.connection_tester import ConnectionTester

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/{stave_id}/test-connection")
async def test_stave_connection(stave_id: str) -> Dict[str, Any]:
    """
    Test connection to a stave's data source.
    
    This endpoint attempts to establish a connection to the data source
    specified in the stave configuration and returns the connection status.
    
    Args:
        stave_id: ID of the stave to test
        
    Returns:
        Connection test result with status, message, and metadata
        
    Example Response:
        {
            "success": true,
            "message": "Connection successful",
            "connection_time": 0.123,
            "metadata": {
                "database_version": "PostgreSQL 14.5",
                "schema_count": 5
            }
        }
    """
    try:
        # Get the stave from database
        db = await get_db()
        staves = await db.query({
            "sql": "SELECT * FROM staves WHERE id = ?", 
            "params": [stave_id]
        })
        
        if not staves:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Stave not found"
            )
        
        # Deserialize the stave
        stave = deserialize_stave(staves[0])
        
        # Test the connection
        tester = ConnectionTester()
        result = await tester.test_connection(stave)
        
        # Log the test result
        logger.info(f"Connection test for stave {stave_id}: {result['success']}")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Connection test failed for stave {stave_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Connection test failed: {str(e)}"
        )


