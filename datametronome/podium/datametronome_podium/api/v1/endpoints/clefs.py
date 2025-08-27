"""Clef endpoints for DataMetronome Podium using DataPulse connectors."""

from typing import Any, List

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
        clefs = await db.query({
            "sql": "SELECT * FROM clefs ORDER BY created_at DESC LIMIT ? OFFSET ?", 
            "params": [limit, skip]
        })
        return [ClefResponse(**clef) for clef in clefs]
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
        
        return ClefResponse(**clefs[0])
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
        
        # Insert the new clef
        success = await db.write([{
            "table": "clefs",
            "id": clef_data.id,
            "stave_id": clef_data.stave_id,
            "name": clef_data.name,
            "description": clef_data.description,
            "check_type": clef_data.check_type,
            "config": clef_data.config,
            "is_active": clef_data.is_active,
            "created_at": clef_data.created_at,
            "updated_at": clef_data.updated_at
        }], "clefs")
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create clef"
            )
        
        # Return the created clef
        return ClefResponse(**clef_data.model_dump())
        
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
        update_data["updated_at"] = clef_data.updated_at
        
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
