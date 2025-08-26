"""Check endpoints for DataMetronome Podium using DataPulse connectors."""

from typing import Any, List

from fastapi import APIRouter, HTTPException, status

from datametronome_podium.core.database import get_db
from datametronome_podium.core.exceptions import ValidationError
from datametronome_podium.api.schemas.check import CheckCreate, CheckUpdate, CheckResponse

router = APIRouter()


@router.get("/", response_model=List[CheckResponse])
async def get_checks(skip: int = 0, limit: int = 100) -> List[CheckResponse]:
    """Get all checks using DataPulse connector.
    
    Args:
        skip: Number of checks to skip.
        limit: Maximum number of checks to return.
        
    Returns:
        List of checks.
    """
    try:
        db = await get_db()
        checks = await db.query({
            "sql": "SELECT * FROM checks ORDER BY timestamp DESC LIMIT ? OFFSET ?", 
            "params": [limit, skip]
        })
        return [CheckResponse(**check) for check in checks]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch checks: {str(e)}"
        )


@router.get("/{check_id}", response_model=CheckResponse)
async def get_check(check_id: str) -> CheckResponse:
    """Get a specific check by ID using DataPulse connector.
    
    Args:
        check_id: Check ID.
        
    Returns:
        Check instance.
        
    Raises:
        HTTPException: If check not found.
    """
    try:
        db = await get_db()
        checks = await db.query({
            "sql": "SELECT * FROM checks WHERE id = ?", 
            "params": [check_id]
        })
        
        if not checks:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Check not found"
            )
        
        return CheckResponse(**checks[0])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch check: {str(e)}"
        )


@router.post("/", response_model=CheckResponse, status_code=status.HTTP_201_CREATED)
async def create_check(check_data: CheckCreate) -> CheckResponse:
    """Create a new check using DataPulse connector.
    
    Args:
        check_data: Check creation data.
        
    Returns:
        Created check instance.
        
    Raises:
        HTTPException: If creation fails.
    """
    try:
        db = await get_db()
        
        # Insert the new check
        success = await db.write([{
            "table": "checks",
            "id": check_data.id,
            "stave_id": check_data.stave_id,
            "clef_id": check_data.clef_id,
            "check_type": check_data.check_type,
            "status": check_data.status,
            "message": check_data.message,
            "details": check_data.details,
            "timestamp": check_data.timestamp,
            "execution_time": check_data.execution_time,
            "anomalies_count": check_data.anomalies_count,
            "severity": check_data.severity
        }], "checks")
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create check"
            )
        
        # Return the created check
        return CheckResponse(**check_data.model_dump())
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create check: {str(e)}"
        )


@router.put("/{check_id}", response_model=CheckResponse)
async def update_check(check_id: str, check_data: CheckUpdate) -> CheckResponse:
    """Update a check using DataPulse connector.
    
    Args:
        check_id: Check ID.
        check_data: Check update data.
        
    Returns:
        Updated check instance.
        
    Raises:
        HTTPException: If update fails.
    """
    try:
        db = await get_db()
        
        # Check if check exists
        checks = await db.query({
            "sql": "SELECT * FROM checks WHERE id = ?", 
            "params": [check_id]
        })
        
        if not checks:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Check not found"
            )
        
        # Update the check
        update_data = check_data.model_dump(exclude_unset=True)
        
        success = await db.write([{
            "table": "checks",
            **update_data
        }], "checks")
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update check"
            )
        
        # Return the updated check
        updated_check = {**checks[0], **update_data}
        return CheckResponse(**updated_check)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update check: {str(e)}"
        )


@router.delete("/{check_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_check(check_id: str) -> None:
    """Delete a check using DataPulse connector.
    
    Args:
        check_id: Check ID.
        
    Raises:
        HTTPException: If deletion fails.
    """
    try:
        db = await get_db()
        
        # Check if check exists
        checks = await db.query({
            "sql": "SELECT * FROM checks WHERE id = ?", 
            "params": [check_id]
        })
        
        if not checks:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Check not found"
            )
        
        # Delete the check
        success = await db.execute(
            "DELETE FROM checks WHERE id = ?", 
            [check_id]
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete check"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete check: {str(e)}"
        )
