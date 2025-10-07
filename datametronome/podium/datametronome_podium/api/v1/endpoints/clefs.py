"""Clef endpoints for DataMetronome Podium using DataPulse connectors."""

from typing import Any, List
from datetime import datetime

from fastapi import APIRouter, HTTPException, status

from datametronome_podium.core.database import get_db
from datametronome_podium.core.exceptions import ValidationError
from datametronome_podium.api.schemas.clef import ClefCreate, ClefUpdate, ClefResponse

router = APIRouter()


@router.get("/", response_model=List[ClefResponse])
async def get_clefs(skip: int = 0, limit: int = 100) -> List[ClefResponse]:
    """Get all clefs using DataPulse connector.
    
    Args:
        skip: Number of clefs to skip.
        limit: Maximum number of clefs to return.
        
    Returns:
        List of clefs.
    """
    try:
        db = await get_db()
        import logging
        logger = logging.getLogger(__name__)
        
        # Log which database file we're using
        db_file = getattr(db, 'database_path', 'unknown')
        logger.info(f"Using database file: {db_file}")
        
        # Try a simple count query first
        count_result = await db.query({"sql": "SELECT COUNT(*) as count FROM clefs", "params": []})
        logger.info(f"COUNT query result: {count_result}")
        
        # Try without ORDER BY
        clefs_no_order = await db.query({"sql": "SELECT * FROM clefs LIMIT ? OFFSET ?", "params": [limit, skip]})
        logger.info(f"Query without ORDER BY returned: {len(clefs_no_order)} clefs")
        
        # Try the original query
        clefs = await db.query({
            "sql": "SELECT * FROM clefs ORDER BY created_at DESC LIMIT ? OFFSET ?", 
            "params": [limit, skip]
        })
        logger.info(f"Found {len(clefs)} clefs in database")
        logger.info(f"Query params: limit={limit}, skip={skip}")
        from datametronome_podium.services.stave_service import deserialize_clef
        response_data = []
        for clef in clefs:
            try:
                deserialized = deserialize_clef(clef)
                clef_dict = deserialized.model_dump()
                # Convert datetime objects to strings for API compatibility
                if isinstance(clef_dict.get('created_at'), datetime):
                    clef_dict['created_at'] = clef_dict['created_at'].isoformat()
                if isinstance(clef_dict.get('updated_at'), datetime):
                    clef_dict['updated_at'] = clef_dict['updated_at'].isoformat()
                response_data.append(ClefResponse(**clef_dict))
            except Exception as e:
                # Log the error but continue processing other clefs
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Failed to deserialize clef {clef.get('id', 'unknown')}: {e}")
                logger.exception(e)
                continue
        return response_data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch clefs: {str(e)}"
        )


@router.get("/{clef_id}", response_model=ClefResponse)
async def get_clef(clef_id: str) -> ClefResponse:
    """Get a specific clef by ID using DataPulse connector.
    
    Args:
        clef_id: Clef ID.
        
    Returns:
        Clef instance.
        
    Raises:
        HTTPException: If clef not found.
    """
    try:
        db = await get_db()
        clefs = await db.query({
            "sql": "SELECT * FROM clefs WHERE id = ?", 
            "params": [clef_id]
        })
        
        if not clefs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Clef not found"
            )
        
        from datametronome_podium.services.stave_service import deserialize_clef
        deserialized = deserialize_clef(clefs[0])
        clef_dict = deserialized.model_dump()
        # Convert datetime objects to strings for API compatibility
        if isinstance(clef_dict.get('created_at'), datetime):
            clef_dict['created_at'] = clef_dict['created_at'].isoformat()
        if isinstance(clef_dict.get('updated_at'), datetime):
            clef_dict['updated_at'] = clef_dict['updated_at'].isoformat()
        return ClefResponse(**clef_dict)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch clef: {str(e)}"
        )


@router.post("/", response_model=ClefResponse, status_code=status.HTTP_201_CREATED)
async def create_clef(clef_data: ClefCreate) -> ClefResponse:
    """Create a new clef using DataPulse connector.
    
    Args:
        clef_data: Clef creation data.
        
    Returns:
        Created clef instance.
        
    Raises:
        HTTPException: If creation fails.
    """
    try:
        db = await get_db()
        
        # Generate ID and timestamps
        import uuid
        clef_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat() + "Z"
        
        # Insert the new clef
        import json
        success = await db.write([{
            "table": "clefs",
            "id": clef_id,
            "stave_id": clef_data.stave_id,
            "name": clef_data.name,
            "description": clef_data.description,
            "check_type": clef_data.check_type,
            "config": json.dumps(clef_data.config),
            "is_active": clef_data.is_active,
            "created_at": now,
            "updated_at": now,
            "schedule": clef_data.schedule,
            "warn": clef_data.warn,
            "fail": clef_data.fail
        }], "clefs")
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create clef"
            )
        
        # Return the created clef
        clef_response_data = {
            "id": clef_id,
            **clef_data.model_dump(),
            "created_at": now,
            "updated_at": now
        }
        return ClefResponse(**clef_response_data)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create clef: {str(e)}"
        )


@router.put("/{clef_id}", response_model=ClefResponse)
async def update_clef(clef_id: str, clef_data: ClefUpdate) -> ClefResponse:
    """Update a clef using DataPulse connector.
    
    Args:
        clef_id: Clef ID.
        clef_data: Clef update data.
        
    Returns:
        Updated clef instance.
        
    Raises:
        HTTPException: If update fails.
    """
    try:
        db = await get_db()
        
        # Check if clef exists
        clefs = await db.query({
            "sql": "SELECT * FROM clefs WHERE id = ?", 
            "params": [clef_id]
        })
        
        if not clefs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Clef not found"
            )
        
        # Update the clef
        update_data = clef_data.model_dump(exclude_unset=True)
        update_data["updated_at"] = datetime.utcnow().isoformat() + "Z"
        
        success = await db.write([{
            "table": "clefs",
            **update_data
        }], "clefs")
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update clef"
            )
        
        # Return the updated clef
        updated_clef = {**clefs[0], **update_data}
        return ClefResponse(**updated_clef)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update clef: {str(e)}"
        )


@router.delete("/{clef_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_clef(clef_id: str) -> None:
    """Delete a clef using DataPulse connector.
    
    Args:
        clef_id: Clef ID.
        
    Raises:
        HTTPException: If deletion fails.
    """
    try:
        db = await get_db()
        
        # Check if clef exists
        clefs = await db.query({
            "sql": "SELECT * FROM clefs WHERE id = ?", 
            "params": [clef_id]
        })
        
        if not clefs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Clef not found"
            )
        
        # Delete the clef
        success = await db.execute(
            "DELETE FROM clefs WHERE id = ?", 
            [clef_id]
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete clef"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete clef: {str(e)}"
        )
