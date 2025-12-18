"""Configuration import endpoint for batch importing staves and clefs."""

import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from datametronome_podium.api.schemas.clef import ClefCreate
from datametronome_podium.api.schemas.stave import StaveCreate
from datametronome_podium.core.database import get_db
from datametronome_podium.services.env_interpolator import (
    InterpolationError,
    extract_env_vars,
    interpolate_yaml_data,
    validate_required_vars,
)
from datametronome_podium.services.yaml_loader import (
    YAMLLoadError,
    load_and_parse_yaml,
    load_yaml_file,
    validate_yaml_structure,
)
from datametronome_podium.services.yaml_watcher import (
    ReloadResult,
    get_watcher,
    reload_yaml_file,
)
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel

router = APIRouter()
logger = logging.getLogger(__name__)


class ImportConfig(BaseModel):
    """Schema for importing configuration."""

    staves: List[Dict[str, Any]] = []
    clefs: List[Dict[str, Any]] = []
    clean: bool = False  # Delete existing items with matching IDs


class ImportResult(BaseModel):
    """Result of configuration import."""

    success: bool
    staves_created: int
    clefs_created: int
    staves_deleted: int = 0
    clefs_deleted: int = 0
    errors: List[str] = []
    warnings: List[str] = []


@router.post("/import", response_model=ImportResult)
async def import_configuration(config: ImportConfig) -> ImportResult:
    """Import staves and clefs from configuration.

    This endpoint allows batch creation of staves and clefs from a single request.

    Args:
        config: Configuration containing staves and clefs to import.

    Returns:
        Import result with counts of created items.

    Example:
        ```json
        {
            "staves": [
                {
                    "id": "stave-bigquery-001",
                    "name": "BigQuery Analytics",
                    "data_source_type": "bigquery",
                    "connection_config": {
                        "project_id": "my-project",
                        "credentials_path": "/path/to/creds.json"
                    },
                    "is_active": true
                }
            ],
            "clefs": [
                {
                    "id": "clef-null-check-001",
                    "stave_id": "stave-bigquery-001",
                    "name": "Email NULL Check",
                    "check_type": "null_check",
                    "config": {"table": "users", "column": "email", "threshold": 0.0},
                    "schedule": "0 */6 * * *",
                    "is_active": true
                }
            ],
            "clean": false
        }
        ```
    """
    db = await get_db()

    errors = []
    warnings = []
    staves_created = 0
    clefs_created = 0
    staves_deleted = 0
    clefs_deleted = 0

    try:
        # Clean existing items if requested
        if config.clean:
            stave_ids = [s.get("id") for s in config.staves if s.get("id")]
            clef_ids = [c.get("id") for c in config.clefs if c.get("id")]

            # Delete clefs first (foreign key constraints)
            for clef_id in clef_ids:
                try:
                    await db.execute("DELETE FROM checks WHERE clef_id = ?", [clef_id])
                    await db.execute("DELETE FROM clefs WHERE id = ?", [clef_id])
                    clefs_deleted += 1
                except Exception as e:
                    warnings.append(f"Failed to delete clef {clef_id}: {str(e)}")

            # Delete staves
            for stave_id in stave_ids:
                try:
                    await db.execute(
                        "DELETE FROM checks WHERE stave_id = ?", [stave_id]
                    )
                    await db.execute("DELETE FROM clefs WHERE stave_id = ?", [stave_id])
                    await db.execute("DELETE FROM staves WHERE id = ?", [stave_id])
                    staves_deleted += 1
                except Exception as e:
                    warnings.append(f"Failed to delete stave {stave_id}: {str(e)}")

        # Create staves
        for stave_data in config.staves:
            try:
                stave_id = stave_data.get("id") or str(uuid.uuid4())
                now = datetime.utcnow().isoformat() + "Z"

                await db.write(
                    [
                        {
                            "table": "staves",
                            "id": stave_id,
                            "name": stave_data["name"],
                            "description": stave_data.get("description"),
                            "data_source_type": stave_data["data_source_type"],
                            "connection_config": json.dumps(
                                stave_data["connection_config"]
                            ),
                            "is_active": stave_data.get("is_active", True),
                            "created_at": now,
                            "updated_at": now,
                        }
                    ],
                    "staves",
                )

                staves_created += 1
            except Exception as e:
                errors.append(
                    f"Failed to create stave '{stave_data.get('name')}': {str(e)}"
                )

        # Create clefs
        for clef_data in config.clefs:
            try:
                clef_id = clef_data.get("id") or str(uuid.uuid4())
                now = datetime.utcnow().isoformat() + "Z"

                await db.write(
                    [
                        {
                            "table": "clefs",
                            "id": clef_id,
                            "stave_id": clef_data["stave_id"],
                            "name": clef_data["name"],
                            "description": clef_data.get("description"),
                            "check_type": clef_data["check_type"],
                            "config": json.dumps(clef_data["config"]),
                            "is_active": clef_data.get("is_active", True),
                            "created_at": now,
                            "updated_at": now,
                            "schedule": clef_data.get("schedule"),
                            "warn": clef_data.get("warn"),
                            "fail": clef_data.get("fail"),
                        }
                    ],
                    "clefs",
                )

                clefs_created += 1
            except Exception as e:
                errors.append(
                    f"Failed to create clef '{clef_data.get('name')}': {str(e)}"
                )

        return ImportResult(
            success=len(errors) == 0,
            staves_created=staves_created,
            clefs_created=clefs_created,
            staves_deleted=staves_deleted,
            clefs_deleted=clefs_deleted,
            errors=errors,
            warnings=warnings,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Import failed: {str(e)}",
        )


@router.post("/import/yaml", response_model=ImportResult)
async def import_yaml_file(
    file: UploadFile = File(...), clean: bool = False
) -> ImportResult:
    """Import configuration from a YAML file.

    Upload a YAML file containing staves and clefs configuration.

    Args:
        file: YAML file to import.
        clean: Delete existing items with matching IDs before importing.

    Returns:
        Import result with counts of created items.
    """
    try:
        # Read and parse YAML
        content = await file.read()
        config_data = yaml.safe_load(content)

        # Create ImportConfig from YAML data
        import_config = ImportConfig(
            staves=config_data.get("staves", []),
            clefs=config_data.get("clefs", []),
            clean=clean,
        )

        # Use the main import function
        return await import_configuration(import_config)

    except yaml.YAMLError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid YAML file: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Import failed: {str(e)}",
        )


@router.post("/import/json", response_model=ImportResult)
async def import_json_file(
    file: UploadFile = File(...), clean: bool = False
) -> ImportResult:
    """Import configuration from a JSON file.

    Upload a JSON file containing staves and clefs configuration.

    Args:
        file: JSON file to import.
        clean: Delete existing items with matching IDs before importing.

    Returns:
        Import result with counts of created items.
    """
    try:
        # Read and parse JSON
        content = await file.read()
        config_data = json.loads(content)

        # Create ImportConfig from JSON data
        import_config = ImportConfig(
            staves=config_data.get("staves", []),
            clefs=config_data.get("clefs", []),
            clean=clean,
        )

        # Use the main import function
        return await import_configuration(import_config)

    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid JSON file: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Import failed: {str(e)}",
        )


class YAMLImportRequest(BaseModel):
    """Request model for YAML import with environment variable interpolation."""

    yaml_content: Optional[str] = None
    file_path: Optional[str] = None
    interpolate_env: bool = True
    strict_validation: bool = True
    clean: bool = False


class ValidationResponse(BaseModel):
    """Response model for YAML validation."""

    is_valid: bool
    errors: List[str]
    warnings: List[str]
    env_vars_required: List[str]
    env_vars_optional: List[str]


@router.post("/import/yaml/advanced", response_model=ImportResult)
async def import_yaml_advanced(request: YAMLImportRequest) -> ImportResult:
    """
    Import staves and clefs from YAML with environment variable interpolation.

    Supports both flat format (staves/clefs arrays) and nested format (clef.checks).

    Args:
        request: Import request with YAML content or file path

    Returns:
        Import result with counts and any errors
    """
    try:
        # Load YAML data
        if request.yaml_content:
            yaml_data = yaml.safe_load(request.yaml_content)
        elif request.file_path:
            yaml_data = load_yaml_file(request.file_path)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either 'yaml_content' or 'file_path' must be provided",
            )

        # Interpolate environment variables if requested
        if request.interpolate_env:
            try:
                yaml_data = interpolate_yaml_data(
                    yaml_data, strict=request.strict_validation
                )
            except InterpolationError as e:
                if request.strict_validation:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Environment variable interpolation failed: {str(e)}",
                    )
                else:
                    logger.warning(f"Interpolation warnings: {str(e)}")

        # Validate structure
        validation = validate_yaml_structure(yaml_data)
        if not validation.is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"YAML validation failed: {', '.join(validation.errors)}",
            )

        # Parse staves and clefs using the new loader
        from datametronome_podium.services.yaml_loader import parse_clefs, parse_staves

        staves = parse_staves(yaml_data)
        stave_id_map = {}
        for stave in staves:
            if stave.id:
                stave_id_map[stave.id] = stave.id
                if stave.name:
                    stave_id_map[stave.name] = stave.id

        clefs = parse_clefs(yaml_data, stave_id_map)

        # Convert to ImportConfig format
        staves_data = []
        for stave in staves:
            staves_data.append(
                {
                    "id": stave.id,
                    "name": stave.name,
                    "description": stave.description,
                    "data_source_type": stave.data_source_type,
                    "connection_config": stave.connection_config,
                    "is_active": stave.is_active,
                }
            )

        clefs_data = []
        for clef in clefs:
            clefs_data.append(
                {
                    "id": clef.id,
                    "stave_id": clef.stave_id,
                    "name": clef.name,
                    "description": clef.description,
                    "check_type": clef.check_type,
                    "config": clef.config,
                    "warn": clef.warn,
                    "fail": clef.fail,
                    "schedule": clef.schedule,
                    "is_active": clef.is_active,
                }
            )

        import_config = ImportConfig(
            staves=staves_data,
            clefs=clefs_data,
            clean=request.clean,
        )

        return await import_configuration(import_config)

    except YAMLLoadError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"YAML load error: {str(e)}"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error importing YAML config")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to import YAML config: {str(e)}",
        )


@router.post("/validate", response_model=ValidationResponse)
async def validate_yaml_config(
    yaml_content: Optional[str] = None, file_path: Optional[str] = None
) -> ValidationResponse:
    """
    Validate YAML structure without importing.

    Args:
        yaml_content: YAML content as string
        file_path: Path to YAML file

    Returns:
        Validation result with errors and environment variable info
    """
    try:
        # Load YAML
        if yaml_content:
            yaml_data = yaml.safe_load(yaml_content)
        elif file_path:
            yaml_data = load_yaml_file(file_path)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either 'yaml_content' or 'file_path' must be provided",
            )

        # Validate structure
        validation = validate_yaml_structure(yaml_data)

        # Extract environment variables
        all_vars = extract_env_vars(yaml_data)
        required_vars = validate_required_vars(yaml_data)
        optional_vars = list(all_vars - set(required_vars))

        return ValidationResponse(
            is_valid=validation.is_valid,
            errors=validation.errors,
            warnings=validation.warnings,
            env_vars_required=required_vars,
            env_vars_optional=optional_vars,
        )

    except YAMLLoadError as e:
        return ValidationResponse(
            is_valid=False,
            errors=[str(e)],
            warnings=[],
            env_vars_required=[],
            env_vars_optional=[],
        )
    except Exception as e:
        logger.exception("Error validating YAML")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate YAML: {str(e)}",
        )


@router.post("/reload")
async def reload_config() -> Dict[str, Any]:
    """
    Reload all watched YAML files.

    Returns:
        Reload results for each file
    """
    try:
        watcher = get_watcher()
        results = []

        # Get all watched paths
        for path in watcher.watched_paths:
            path_obj = Path(path)
            if path_obj.is_file() and path_obj.suffix in (".yaml", ".yml"):
                result = reload_yaml_file(str(path_obj))
                results.append(
                    {
                        "file_path": result.file_path,
                        "success": result.success,
                        "staves_count": result.staves_count,
                        "clefs_count": result.clefs_count,
                        "error": result.error,
                    }
                )

        return {"success": all(r["success"] for r in results), "results": results}

    except Exception as e:
        logger.exception("Error reloading config")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reload config: {str(e)}",
        )


@router.get("/files")
async def get_watched_files() -> Dict[str, Any]:
    """
    Get list of currently watched YAML files.

    Returns:
        List of watched file paths
    """
    try:
        watcher = get_watcher()
        files = []

        for path in watcher.watched_paths:
            path_obj = Path(path)
            if path_obj.is_file():
                files.append(str(path_obj))
            elif path_obj.is_dir():
                # List all YAML files in directory
                for yaml_file in path_obj.rglob("*.yaml"):
                    files.append(str(yaml_file))
                for yaml_file in path_obj.rglob("*.yml"):
                    files.append(str(yaml_file))

        return {
            "watched_paths": list(watcher.watched_paths),
            "files": files,
            "count": len(files),
        }

    except Exception as e:
        logger.exception("Error getting watched files")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get watched files: {str(e)}",
        )


@router.post("/watch")
async def watch_directory(path: str) -> Dict[str, Any]:
    """
    Add a directory or file to the watch list for hot reload.

    Args:
        path: Directory or file path to watch

    Returns:
        Success status
    """
    try:
        path_obj = Path(path)
        if not path_obj.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Path does not exist: {path}",
            )

        watcher = get_watcher()
        watcher.watch_path(str(path_obj.absolute()))

        # Start watcher if not already running
        if not watcher.observer or not watcher.observer.is_alive():
            watcher.start(reload_yaml_file)

        return {
            "success": True,
            "path": str(path_obj.absolute()),
            "message": f"Now watching: {path}",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error adding watch path")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add watch path: {str(e)}",
        )
