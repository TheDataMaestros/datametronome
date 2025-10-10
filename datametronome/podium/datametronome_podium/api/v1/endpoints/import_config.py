"""Configuration import endpoint for batch importing staves and clefs."""

from typing import Any, Dict, List, Optional
from datetime import datetime
import json
import uuid

from fastapi import APIRouter, HTTPException, status, UploadFile, File
from pydantic import BaseModel
import yaml

from datametronome_podium.core.database import get_db
from datametronome_podium.api.schemas.stave import StaveCreate
from datametronome_podium.api.schemas.clef import ClefCreate

router = APIRouter()


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
            stave_ids = [s.get('id') for s in config.staves if s.get('id')]
            clef_ids = [c.get('id') for c in config.clefs if c.get('id')]
            
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
                    await db.execute("DELETE FROM checks WHERE stave_id = ?", [stave_id])
                    await db.execute("DELETE FROM clefs WHERE stave_id = ?", [stave_id])
                    await db.execute("DELETE FROM staves WHERE id = ?", [stave_id])
                    staves_deleted += 1
                except Exception as e:
                    warnings.append(f"Failed to delete stave {stave_id}: {str(e)}")
        
        # Create staves
        for stave_data in config.staves:
            try:
                stave_id = stave_data.get('id', str(uuid.uuid4()))
                now = datetime.utcnow().isoformat() + "Z"
                
                await db.write([{
                    "table": "staves",
                    "id": stave_id,
                    "name": stave_data['name'],
                    "description": stave_data.get('description'),
                    "data_source_type": stave_data['data_source_type'],
                    "connection_config": json.dumps(stave_data['connection_config']),
                    "is_active": stave_data.get('is_active', True),
                    "created_at": now,
                    "updated_at": now
                }], "staves")
                
                staves_created += 1
            except Exception as e:
                errors.append(f"Failed to create stave '{stave_data.get('name')}': {str(e)}")
        
        # Create clefs
        for clef_data in config.clefs:
            try:
                clef_id = clef_data.get('id', str(uuid.uuid4()))
                now = datetime.utcnow().isoformat() + "Z"
                
                await db.write([{
                    "table": "clefs",
                    "id": clef_id,
                    "stave_id": clef_data['stave_id'],
                    "name": clef_data['name'],
                    "description": clef_data.get('description'),
                    "check_type": clef_data['check_type'],
                    "config": json.dumps(clef_data['config']),
                    "is_active": clef_data.get('is_active', True),
                    "created_at": now,
                    "updated_at": now,
                    "schedule": clef_data.get('schedule'),
                    "warn": clef_data.get('warn'),
                    "fail": clef_data.get('fail')
                }], "clefs")
                
                clefs_created += 1
            except Exception as e:
                errors.append(f"Failed to create clef '{clef_data.get('name')}': {str(e)}")
        
        return ImportResult(
            success=len(errors) == 0,
            staves_created=staves_created,
            clefs_created=clefs_created,
            staves_deleted=staves_deleted,
            clefs_deleted=clefs_deleted,
            errors=errors,
            warnings=warnings
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Import failed: {str(e)}"
        )


@router.post("/import/yaml", response_model=ImportResult)
async def import_yaml_file(file: UploadFile = File(...), clean: bool = False) -> ImportResult:
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
            staves=config_data.get('staves', []),
            clefs=config_data.get('clefs', []),
            clean=clean
        )
        
        # Use the main import function
        return await import_configuration(import_config)
        
    except yaml.YAMLError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid YAML file: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Import failed: {str(e)}"
        )


@router.post("/import/json", response_model=ImportResult)
async def import_json_file(file: UploadFile = File(...), clean: bool = False) -> ImportResult:
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
            staves=config_data.get('staves', []),
            clefs=config_data.get('clefs', []),
            clean=clean
        )
        
        # Use the main import function
        return await import_configuration(import_config)
        
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid JSON file: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Import failed: {str(e)}"
        )

