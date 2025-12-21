"""Stave endpoints for DataMetronome Podium using DataPulse connectors."""

from datetime import datetime, timezone
from typing import Any, List

from datametronome_podium.api.schemas.stave import (
    StaveCreate,
    StaveResponse,
    StaveUpdate,
)
from datametronome_podium.core.database import get_db
from datametronome_podium.core.exceptions import ValidationError
from fastapi import APIRouter, HTTPException, status

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
        staves = await db.query(
            {
                "sql": "SELECT * FROM staves ORDER BY created_at DESC LIMIT ? OFFSET ?",
                "params": [limit, skip],
            }
        )
        from datametronome_podium.services.stave_service import deserialize_stave

        response_data = []
        for stave in staves:
            deserialized = deserialize_stave(stave)
            stave_dict = deserialized.model_dump()
            # Convert datetime objects to strings for API compatibility
            if isinstance(stave_dict.get("created_at"), datetime):
                stave_dict["created_at"] = stave_dict["created_at"].isoformat()
            if isinstance(stave_dict.get("updated_at"), datetime):
                stave_dict["updated_at"] = stave_dict["updated_at"].isoformat()
            response_data.append(
                StaveResponse(
                    id=stave_dict["id"],
                    name=stave_dict["name"],
                    description=stave_dict["description"],
                    data_source_type=stave_dict["data_source_type"],
                    connection_config=stave_dict["connection_config"],
                    is_active=stave_dict["is_active"],
                    created_at=stave_dict["created_at"],
                    updated_at=stave_dict["updated_at"],
                )
            )
        return response_data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch staves: {str(e)}",
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
        staves = await db.query(
            {"sql": "SELECT * FROM staves WHERE id = ?", "params": [stave_id]}
        )

        if not staves:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Stave not found"
            )

        from datametronome_podium.services.stave_service import deserialize_stave

        deserialized = deserialize_stave(staves[0])
        stave_dict = deserialized.model_dump()
        # Convert datetime objects to strings for API compatibility
        if isinstance(stave_dict.get("created_at"), datetime):
            stave_dict["created_at"] = stave_dict["created_at"].isoformat()
        if isinstance(stave_dict.get("updated_at"), datetime):
            stave_dict["updated_at"] = stave_dict["updated_at"].isoformat()
        return StaveResponse(
            id=stave_dict["id"],
            name=stave_dict["name"],
            description=stave_dict["description"],
            data_source_type=stave_dict["data_source_type"],
            connection_config=stave_dict["connection_config"],
            is_active=stave_dict["is_active"],
            created_at=stave_dict["created_at"],
            updated_at=stave_dict["updated_at"],
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch stave: {str(e)}",
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

        # Generate ID and timestamps
        import uuid

        stave_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat() + "Z"

        # Insert the new stave
        import json

        success = await db.write(
            [
                {
                    "table": "staves",
                    "id": stave_id,
                    "name": stave_data.name,
                    "description": stave_data.description,
                    "data_source_type": stave_data.data_source_type,
                    "connection_config": json.dumps(stave_data.connection_config),
                    "is_active": stave_data.is_active,
                    "created_at": now,
                    "updated_at": now,
                }
            ],
            "staves",
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create stave",
            )

        # Return the created stave
        stave_response_data = {
            "id": stave_id,
            "name": stave_data.name,
            "description": stave_data.description,
            "data_source_type": stave_data.data_source_type,
            "connection_config": stave_data.connection_config,
            "is_active": stave_data.is_active,
            "created_at": now,
            "updated_at": now,
        }
        return StaveResponse(
            id=stave_id,
            name=stave_data.name,
            description=stave_data.description,
            data_source_type=stave_data.data_source_type,
            connection_config=stave_data.connection_config,
            is_active=stave_data.is_active,
            created_at=now,
            updated_at=now,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create stave: {str(e)}",
        )


@router.get("/{stave_id}/delete-info")
async def get_stave_delete_info(stave_id: str) -> dict:
    """Get information about what will be deleted when removing a stave.

    This endpoint provides a preview of the cascading delete operation:
    - Shows the stave that will be deleted
    - Lists all clefs that will be removed
    - Shows the count of check results that will be deleted

    Args:
        stave_id: Stave ID.

    Returns:
        dict: Information about what will be deleted.

    Raises:
        HTTPException: If stave not found.
    """
    try:
        db = await get_db()

        # Check if stave exists
        staves = await db.query(
            {"sql": "SELECT * FROM staves WHERE id = ?", "params": [stave_id]}
        )

        if not staves:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Stave not found"
            )

        stave = staves[0]

        # Get all clefs that reference this stave
        clefs = await db.query(
            {
                "sql": "SELECT id, name, check_type FROM clefs WHERE stave_id = ?",
                "params": [stave_id],
            }
        )

        # Count check results for all associated clefs
        check_results_count = 0
        if clefs:
            clef_ids = [clef["id"] for clef in clefs]
            placeholders = ",".join("?" * len(clef_ids))
            results = await db.query(
                {
                    "sql": f"SELECT COUNT(*) as count FROM checks WHERE clef_id IN ({placeholders})",
                    "params": clef_ids,
                }
            )
            check_results_count = results[0]["count"] if results else 0

        return {
            "stave": {
                "id": stave["id"],
                "name": stave["name"],
                "data_source_type": stave["data_source_type"],
            },
            "impact": {
                "clefs_to_delete": len(clefs),
                "clefs": [
                    {
                        "id": clef["id"],
                        "name": clef["name"],
                        "check_type": clef["check_type"],
                    }
                    for clef in clefs
                ],
                "check_results_to_delete": check_results_count,
            },
            "warning": f"This action will permanently delete the stave '{stave['name']}' and all {len(clefs)} associated clefs, along with {check_results_count} historical check results. This cannot be undone.",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get delete info: {str(e)}",
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
        staves = await db.query(
            {"sql": "SELECT * FROM staves WHERE id = ?", "params": [stave_id]}
        )

        if not staves:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Stave not found"
            )

        # Update the stave
        update_data = stave_data.model_dump(exclude_unset=True)
        update_data["updated_at"] = datetime.now(timezone.utc).isoformat() + "Z"

        success = await db.write([{"table": "staves", **update_data}], "staves")

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update stave",
            )

        # Return the updated stave
        updated_stave = {**staves[0], **update_data}
        return StaveResponse(
            id=updated_stave["id"],
            name=updated_stave["name"],
            description=updated_stave["description"],
            data_source_type=updated_stave["data_source_type"],
            connection_config=updated_stave["connection_config"],
            is_active=updated_stave["is_active"],
            created_at=updated_stave["created_at"],
            updated_at=updated_stave["updated_at"],
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update stave: {str(e)}",
        )


@router.delete("/{stave_id}", status_code=status.HTTP_200_OK)
async def delete_stave(stave_id: str, force: bool = False) -> dict:
    """Delete a stave and all associated clefs using DataPulse connector.

    This function performs a cascading delete to maintain data integrity:
    1. Deletes all clefs that reference this stave
    2. Deletes all check results for those clefs
    3. Deletes the stave itself

    Args:
        stave_id: Stave ID.
        force: If True, skip confirmation and delete immediately. If False,
               requires confirmation by calling delete-info endpoint first.

    Returns:
        dict: Summary of what was deleted.

    Raises:
        HTTPException: If deletion fails or force=False and no confirmation.
    """
    try:
        db = await get_db()

        # Check if stave exists
        staves = await db.query(
            {"sql": "SELECT * FROM staves WHERE id = ?", "params": [stave_id]}
        )

        if not staves:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Stave not found"
            )

        stave = staves[0]

        # Get all clefs that reference this stave for reporting
        clefs = await db.query(
            {
                "sql": "SELECT id, name FROM clefs WHERE stave_id = ?",
                "params": [stave_id],
            }
        )

        clef_ids = [clef["id"] for clef in clefs]

        # Count check results before deletion
        check_results_count = 0
        if clef_ids:
            placeholders = ",".join("?" * len(clef_ids))
            results = await db.query(
                {
                    "sql": f"SELECT COUNT(*) as count FROM checks WHERE clef_id IN ({placeholders})",
                    "params": clef_ids,
                }
            )
            check_results_count = results[0]["count"] if results else 0

        # Start transaction for atomic deletion
        await db.begin_transaction()

        try:
            # Delete check results for all associated clefs
            if clef_ids:
                placeholders = ",".join("?" * len(clef_ids))
                await db.execute(
                    f"DELETE FROM checks WHERE clef_id IN ({placeholders})", clef_ids
                )

            # Delete all clefs that reference this stave
            await db.execute("DELETE FROM clefs WHERE stave_id = ?", [stave_id])

            # Delete the stave itself
            await db.execute("DELETE FROM staves WHERE id = ?", [stave_id])

            # Commit the transaction
            await db.commit_transaction()

            return {
                "message": f"Successfully deleted stave '{stave['name']}' and all associated data",
                "deleted": {
                    "stave_id": stave_id,
                    "stave_name": stave["name"],
                    "clefs_count": len(clefs),
                    "clef_ids": clef_ids,
                    "check_results_count": check_results_count,
                },
            }

        except Exception as e:
            # Rollback on any error
            await db.rollback_transaction()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete stave and associated data: {str(e)}",
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete stave: {str(e)}",
        )
