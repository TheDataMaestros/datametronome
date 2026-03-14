"""Clef endpoints for DataMetronome Podium using DataPulse connectors."""

from datetime import datetime, timezone
from typing import Any, List

from datametronome_podium.api.schemas.clef import ClefCreate, ClefResponse, ClefUpdate
from datametronome_podium.core.database import get_db
from datametronome_podium.core.exceptions import ValidationError
from fastapi import APIRouter, HTTPException, status

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
        clefs = await db.query(
            {
                "sql": "SELECT * FROM clefs ORDER BY created_at DESC LIMIT ? OFFSET ?",
                "params": [limit, skip],
            }
        )
        from datametronome_podium.services.stave_service import deserialize_clef

        response_data = []
        for clef in clefs:
            try:
                deserialized = deserialize_clef(clef)
                clef_dict = deserialized.model_dump()
                # Convert datetime objects to strings for API compatibility
                if isinstance(clef_dict.get("created_at"), datetime):
                    clef_dict["created_at"] = clef_dict["created_at"].isoformat()
                if isinstance(clef_dict.get("updated_at"), datetime):
                    clef_dict["updated_at"] = clef_dict["updated_at"].isoformat()
                response_data.append(
                    ClefResponse(
                        id=clef_dict["id"],
                        stave_id=clef_dict["stave_id"],
                        name=clef_dict["name"],
                        description=clef_dict["description"],
                        check_type=clef_dict["check_type"],
                        config=clef_dict["config"],
                        is_active=clef_dict["is_active"],
                        schedule=clef_dict["schedule"],
                        warn=clef_dict["warn"],
                        fail=clef_dict["fail"],
                        created_at=clef_dict["created_at"],
                        updated_at=clef_dict["updated_at"],
                    )
                )
            except Exception as e:
                # Log the error but continue processing other clefs
                import logging

                logger = logging.getLogger(__name__)
                logger.warning(
                    f"Failed to deserialize clef {clef.get('id', 'unknown')}: {e}"
                )
                continue
        return response_data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch clefs: {str(e)}",
        )


@router.get("/types")
async def get_available_check_types() -> dict[str, Any]:
    """Get list of all available check types with metadata.

    Returns:
        Dictionary containing check types with their metadata (name, description, tier, etc.).
    """
    from datametronome_podium.models.clef import (
        CHECK_LEVEL_MAPPING,
        LEVEL_1_CHECKS,
        LEVEL_2_CHECKS,
        LEVEL_3_CHECKS,
        LEVEL_4_CHECKS,
        SUPPORTED_CHECK_TYPES,
    )
    from datametronome_podium.services.stave_service import get_supported_check_types

    try:
        # Map check types to their metadata
        check_types_metadata = {}
        
        # Helper function to get tier for a check type
        def get_tier(check_type: str) -> int:
            return CHECK_LEVEL_MAPPING.get(check_type, 4)
        
        # Helper function to get description for a check type
        def get_description(check_type: str) -> str:
            descriptions = {
                "row_count": "Monitor the number of rows in a table",
                "freshness": "Check how recent your data is",
                "column_values": "Validate values in a specific column",
                "forecast": "ML-powered anomaly detection",
                "data_profile_drift": "Detect statistical changes in data",
                "lookup_validation": "Validate data across multiple systems",
                "python": "Run custom Python validation scripts",
            }
            return descriptions.get(check_type, f"{check_type.replace('_', ' ').title()} check")
        
        # Helper function to get display name for a check type
        def get_display_name(check_type: str) -> str:
            names = {
                "row_count": "Row Count",
                "freshness": "Data Freshness",
                "column_values": "Column Validation",
                "forecast": "Anomaly Detection",
                "data_profile_drift": "Data Drift",
                "lookup_validation": "Cross-System Check",
                "python": "Custom Python",
            }
            if check_type in names:
                return names[check_type]
            # Convert snake_case to Title Case
            return check_type.replace('_', ' ').title()
        
        for check_type in SUPPORTED_CHECK_TYPES:
            check_types_metadata[check_type] = {
                "type": check_type,
                "name": get_display_name(check_type),
                "description": get_description(check_type),
                "tier": get_tier(check_type),
            }
        
        return {
            "check_types": list(check_types_metadata.values()),
            "by_tier": {
                "1": [ct for ct in check_types_metadata.values() if ct["tier"] == 1],
                "2": [ct for ct in check_types_metadata.values() if ct["tier"] == 2],
                "3": [ct for ct in check_types_metadata.values() if ct["tier"] == 3],
                "4": [ct for ct in check_types_metadata.values() if ct["tier"] == 4],
            },
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch check types: {str(e)}",
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
        clefs = await db.query(
            {"sql": "SELECT * FROM clefs WHERE id = ?", "params": [clef_id]}
        )

        if not clefs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Clef not found"
            )

        from datametronome_podium.services.stave_service import deserialize_clef

        deserialized = deserialize_clef(clefs[0])
        clef_dict = deserialized.model_dump()
        # Convert datetime objects to strings for API compatibility
        if isinstance(clef_dict.get("created_at"), datetime):
            clef_dict["created_at"] = clef_dict["created_at"].isoformat()
        if isinstance(clef_dict.get("updated_at"), datetime):
            clef_dict["updated_at"] = clef_dict["updated_at"].isoformat()
        return ClefResponse(
            id=clef_dict["id"],
            stave_id=clef_dict["stave_id"],
            name=clef_dict["name"],
            description=clef_dict["description"],
            check_type=clef_dict["check_type"],
            config=clef_dict["config"],
            is_active=clef_dict["is_active"],
            schedule=clef_dict["schedule"],
            warn=clef_dict["warn"],
            fail=clef_dict["fail"],
            created_at=clef_dict["created_at"],
            updated_at=clef_dict["updated_at"],
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch clef: {str(e)}",
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
        now = datetime.now(timezone.utc).isoformat() + "Z"

        # Insert the new clef
        import json

        success = await db.write(
            [
                {
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
                    "fail": clef_data.fail,
                }
            ],
            "clefs",
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create clef",
            )

        # Return the created clef
        clef_response_data = {
            "id": clef_id,
            **clef_data.model_dump(),
            "created_at": now,
            "updated_at": now,
        }
        return ClefResponse(
            id=clef_id,
            stave_id=clef_response_data["stave_id"],
            name=clef_data.name,
            description=clef_data.description,
            check_type=clef_data.check_type,
            config=clef_data.config,
            is_active=clef_data.is_active,
            schedule=clef_data.schedule,
            warn=clef_data.warn,
            fail=clef_data.fail,
            created_at=now,
            updated_at=now,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create clef: {str(e)}",
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
        clefs = await db.query(
            {"sql": "SELECT * FROM clefs WHERE id = ?", "params": [clef_id]}
        )

        if not clefs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Clef not found"
            )

        # Update the clef
        update_data = clef_data.model_dump(exclude_unset=True)
        update_data["updated_at"] = datetime.now(timezone.utc).isoformat() + "Z"

        success = await db.write([{"table": "clefs", **update_data}], "clefs")

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update clef",
            )

        # Return the updated clef
        updated_clef = {**clefs[0], **update_data}
        return ClefResponse(
            id=updated_clef["id"],
            stave_id=updated_clef["stave_id"],
            name=updated_clef["name"],
            description=updated_clef["description"],
            check_type=updated_clef["check_type"],
            config=updated_clef["config"],
            is_active=updated_clef["is_active"],
            schedule=updated_clef["schedule"],
            warn=updated_clef["warn"],
            fail=updated_clef["fail"],
            created_at=updated_clef["created_at"],
            updated_at=updated_clef["updated_at"],
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update clef: {str(e)}",
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
        clefs = await db.query(
            {"sql": "SELECT * FROM clefs WHERE id = ?", "params": [clef_id]}
        )

        if not clefs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Clef not found"
            )

        # Delete the clef
        success = await db.execute("DELETE FROM clefs WHERE id = ?", [clef_id])

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete clef",
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete clef: {str(e)}",
        )
