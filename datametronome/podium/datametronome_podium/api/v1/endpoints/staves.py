"""Stave endpoints for DataMetronome Podium using DataPulse connectors."""

from typing import Any, List

from fastapi import APIRouter, HTTPException, status

from datametronome_podium.core.database import get_db
from datametronome_podium.core.exceptions import ValidationError
from datametronome_podium.api.schemas.stave import StaveCreate, StaveUpdate, StaveResponse

router = APIRouter()


@router.get("/", response_model=List[StaveResponse])
async def get_staves(skip: int = 0, limit: int = 100) -> List[StaveResponse]:
    """Get all staves using DataPulse connector.
    
    Args:
        skip: Number of staves to skip.
        limit: Maximum number of staves to return.
        
    Returns:
        List of staves.
    """
    try:
        db = await get_db()
        staves = await db.query({
            "sql": "SELECT * FROM staves ORDER BY created_at DESC LIMIT ? OFFSET ?", 
            "params": [limit, skip]
        })
        return [StaveResponse(**stave) for stave in staves]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch staves: {str(e)}"
        )


@router.get("/{stave_id}", response_model=StaveResponse)
async def get_stave(stave_id: str) -> StaveResponse:
    """Get a specific stave by ID using DataPulse connector.
    
    Args:
        stave_id: Stave ID.
        
    Returns:
        Stave instance.
        
    Raises:
        HTTPException: If stave not found.
    """
    try:
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
        
        return StaveResponse(**staves[0])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch stave: {str(e)}"
        )


@router.post("/", response_model=StaveResponse, status_code=status.HTTP_201_CREATED)
async def create_stave(stave_data: StaveCreate) -> StaveResponse:
    """Create a new stave using DataPulse connector.
    
    Args:
        stave_data: Stave creation data.
        
    Returns:
        Created stave instance.
        
    Raises:
        HTTPException: If creation fails.
    """
    try:
        db = await get_db()
        
        # Insert the new stave
        success = await db.write([{
            "table": "staves",
            "id": stave_data.id,
            "name": stave_data.name,
            "description": stave_data.description,
            "data_source_type": stave_data.data_source_type,
            "connection_config": stave_data.connection_config,
            "is_active": stave_data.is_active,
            "created_at": stave_data.created_at,
            "updated_at": stave_data.updated_at
        }], "staves")
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create stave"
            )
        
        # Return the created stave
        return StaveResponse(**stave_data.model_dump())
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create stave: {str(e)}"
        )


@router.put("/{stave_id}", response_model=StaveResponse)
async def update_stave(stave_id: str, stave_data: StaveUpdate) -> StaveResponse:
    """Update a stave using DataPulse connector.
    
    Args:
        stave_id: Stave ID.
        stave_data: Stave update data.
        
    Returns:
        Updated stave instance.
        
    Raises:
        HTTPException: If update fails.
    """
    try:
        db = await get_db()
        
        # Check if stave exists
        staves = await db.query({
            "sql": "SELECT * FROM staves WHERE id = ?", 
            "params": [stave_id]
        })
        
        if not staves:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Stave not found"
            )
        
        # Update the stave
        update_data = stave_data.model_dump(exclude_unset=True)
        update_data["updated_at"] = stave_data.updated_at
        
        success = await db.write([{
            "table": "staves",
            **update_data
        }], "staves")
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update stave"
            )
        
        # Return the updated stave
        updated_stave = {**staves[0], **update_data}
        return StaveResponse(**updated_stave)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update stave: {str(e)}"
        )


@router.delete("/{stave_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_stave(stave_id: str) -> None:
    """Delete a stave using DataPulse connector.
    
    Args:
        stave_id: Stave ID.
        
    Raises:
        HTTPException: If deletion fails.
    """
    try:
        db = await get_db()
        
        # Check if stave exists
        staves = await db.query({
            "sql": "SELECT * FROM staves WHERE id = ?", 
            "params": [stave_id]
        })
        
        if not staves:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Stave not found"
            )
        
        # Delete the stave
        success = await db.execute(
            "DELETE FROM staves WHERE id = ?", 
            [stave_id]
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete stave"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete stave: {str(e)}"
        )
