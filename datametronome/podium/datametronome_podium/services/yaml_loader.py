"""
YAML Loader Service for DataMetronome Podium.

This service handles loading and parsing YAML configuration files containing
staves (data sources) and clefs (data quality checks).
"""

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml
from datametronome_podium.models.clef import Clef
from datametronome_podium.models.stave import Stave

logger = logging.getLogger(__name__)


class YAMLLoadError(Exception):
    """Exception raised when YAML loading fails."""

    pass


class ValidationResult:
    """Result of YAML structure validation."""

    def __init__(
        self,
        is_valid: bool,
        errors: list[str] | None = None,
        warnings: list[str] | None = None,
    ):
        self.is_valid = is_valid
        self.errors = errors or []
        self.warnings = warnings or []

    def __bool__(self):
        return self.is_valid


def load_yaml_file(file_path: str) -> Dict[str, Any]:
    """
    Load and parse a YAML file.

    Args:
        file_path: Path to the YAML file

    Returns:
        Parsed YAML data as a dictionary

    Raises:
        YAMLLoadError: If file cannot be read or parsed
    """
    try:
        path = Path(file_path)
        if not path.exists():
            raise YAMLLoadError(f"YAML file not found: {file_path}")

        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if data is None:
            return {}

        return data

    except yaml.YAMLError as e:
        raise YAMLLoadError(f"Failed to parse YAML file {file_path}: {str(e)}")
    except Exception as e:
        raise YAMLLoadError(f"Failed to load YAML file {file_path}: {str(e)}")


def validate_yaml_structure(yaml_data: Dict[str, Any]) -> ValidationResult:
    """
    Validate YAML structure against expected format.

    Args:
        yaml_data: Parsed YAML data

    Returns:
        ValidationResult with validation status and any errors/warnings
    """
    errors = []
    warnings = []

    if not isinstance(yaml_data, dict):
        errors.append("YAML root must be a dictionary")
        return ValidationResult(False, errors)

    # Check for flat format (staves and clefs at root)
    has_flat_format = "staves" in yaml_data or "clefs" in yaml_data

    # Check for nested format (clef with checks array)
    has_nested_format = "clef" in yaml_data

    if not has_flat_format and not has_nested_format:
        errors.append(
            "YAML must contain either 'staves'/'clefs' (flat format) or 'clef' (nested format)"
        )
        return ValidationResult(False, errors)

    # Validate staves if present
    if "staves" in yaml_data:
        staves = yaml_data["staves"]
        if not isinstance(staves, list):
            errors.append("'staves' must be a list")
        else:
            for i, stave in enumerate(staves):
                if not isinstance(stave, dict):
                    errors.append(f"Stave at index {i} must be a dictionary")
                else:
                    if "name" not in stave:
                        errors.append(
                            f"Stave at index {i} missing required field 'name'"
                        )
                    if "data_source_type" not in stave:
                        errors.append(
                            f"Stave at index {i} missing required field 'data_source_type'"
                        )

    # Validate clefs if present (flat format)
    if "clefs" in yaml_data:
        clefs = yaml_data["clefs"]
        if not isinstance(clefs, list):
            errors.append("'clefs' must be a list")
        else:
            for i, clef in enumerate(clefs):
                if not isinstance(clef, dict):
                    errors.append(f"Clef at index {i} must be a dictionary")
                else:
                    if "name" not in clef:
                        errors.append(
                            f"Clef at index {i} missing required field 'name'"
                        )
                    if "check_type" not in clef:
                        errors.append(
                            f"Clef at index {i} missing required field 'check_type'"
                        )
                    if "stave_id" not in clef:
                        errors.append(
                            f"Clef at index {i} missing required field 'stave_id'"
                        )

    # Validate nested format (clef with checks)
    if "clef" in yaml_data:
        clef_section = yaml_data["clef"]
        if not isinstance(clef_section, dict):
            errors.append("'clef' must be a dictionary")
        else:
            if "checks" in clef_section:
                checks = clef_section["checks"]
                if not isinstance(checks, list):
                    errors.append("'clef.checks' must be a list")
                else:
                    for i, check in enumerate(checks):
                        if not isinstance(check, dict):
                            errors.append(f"Check at index {i} must be a dictionary")
                        else:
                            if "check" not in check:
                                errors.append(
                                    f"Check at index {i} missing required field 'check'"
                                )

    return ValidationResult(len(errors) == 0, errors, warnings)


def parse_staves(yaml_data: Dict[str, Any]) -> List[Stave]:
    """
    Parse staves from YAML data.

    Args:
        yaml_data: Parsed YAML data

    Returns:
        List of Stave objects

    Raises:
        YAMLLoadError: If parsing fails
    """
    staves = []

    if "staves" not in yaml_data:
        return staves

    staves_data = yaml_data["staves"]
    if not isinstance(staves_data, list):
        raise YAMLLoadError("'staves' must be a list")

    for i, stave_entry in enumerate(staves_data):
        stave_data: dict[str, Any] = stave_entry  # type: ignore[assignment]
        try:
            # Ensure connection_config exists
            if "connection_config" not in stave_data:
                stave_data["connection_config"] = {}

            # Set default timestamps if not present
            now = datetime.now(timezone.utc)
            if "created_at" not in stave_data:
                stave_data["created_at"] = now
            if "updated_at" not in stave_data:
                stave_data["updated_at"] = now

            stave = Stave(**stave_data)
            staves.append(stave)

        except Exception as e:
            raise YAMLLoadError(f"Failed to parse stave at index {i}: {str(e)}")

    return staves


def parse_clefs(
    yaml_data: Dict[str, Any], stave_id_map: Optional[Dict[str, str]] = None
) -> List[Clef]:
    """
    Parse clefs from YAML data.

    Supports both flat format (clefs array) and nested format (clef.checks array).

    Args:
        yaml_data: Parsed YAML data
        stave_id_map: Optional mapping from stave names/IDs to actual stave IDs
                      (for nested format where stave_id might be referenced by name)

    Returns:
        List of Clef objects

    Raises:
        YAMLLoadError: If parsing fails
    """
    clefs = []
    stave_id_map = stave_id_map or {}

    # Handle flat format: clefs array
    if "clefs" in yaml_data:
        clefs_data = yaml_data["clefs"]
        if not isinstance(clefs_data, list):
            raise YAMLLoadError("'clefs' must be a list")

        for i, clef_entry in enumerate(clefs_data):
            clef_data: dict[str, Any] = clef_entry  # type: ignore[assignment]
            try:
                clef = _parse_single_clef(clef_data, stave_id_map)
                if clef:
                    clefs.append(clef)
            except Exception as e:
                raise YAMLLoadError(f"Failed to parse clef at index {i}: {str(e)}")

    # Handle nested format: clef.checks array
    if "clef" in yaml_data:
        clef_section = yaml_data["clef"]
        if not isinstance(clef_section, dict):
            raise YAMLLoadError("'clef' must be a dictionary")

        # Get default context (table, stave_id, etc.)
        default_table = clef_section.get("table")
        default_stave_id = clef_section.get("stave_id")

        # If stave_id is a name, resolve it from stave_id_map
        if default_stave_id and default_stave_id in stave_id_map:
            default_stave_id = stave_id_map[default_stave_id]

        # If no default_stave_id, try to get from staves (assume first stave if only one)
        if not default_stave_id and stave_id_map:
            # Use first stave if only one exists
            stave_ids = list(stave_id_map.values())
            if len(stave_ids) == 1:
                default_stave_id = stave_ids[0]
            else:
                raise YAMLLoadError(
                    "Nested format requires 'stave_id' in clef section or exactly one stave"
                )

        if "checks" in clef_section:
            checks = clef_section["checks"]
            if not isinstance(checks, list):
                raise YAMLLoadError("'clef.checks' must be a list")

            for i, check_entry in enumerate(checks):
                check_data: dict[str, Any] = check_entry  # type: ignore[assignment]
                try:
                    # Convert nested format to flat format
                    nested_clef_data = _convert_nested_check_to_clef(
                        check_data,
                        default_table=default_table,
                        default_stave_id=default_stave_id,
                        stave_id_map=stave_id_map,
                        index=i,
                    )

                    if nested_clef_data:
                        clef = _parse_single_clef(nested_clef_data, stave_id_map)
                        if clef:
                            clefs.append(clef)

                except Exception as e:
                    raise YAMLLoadError(f"Failed to parse check at index {i}: {str(e)}")

    return clefs


def _parse_single_clef(
    clef_data: Dict[str, Any], stave_id_map: Dict[str, str]
) -> Optional[Clef]:
    """
    Parse a single clef from dictionary data.

    Args:
        clef_data: Clef data dictionary
        stave_id_map: Mapping for resolving stave references

    Returns:
        Clef object or None if invalid
    """
    # Resolve stave_id if it's a name reference
    stave_id = clef_data.get("stave_id")
    if stave_id and stave_id in stave_id_map:
        clef_data["stave_id"] = stave_id_map[stave_id]

    # Ensure config exists
    if "config" not in clef_data:
        clef_data["config"] = {}

    # Set default timestamps if not present
    now = datetime.now(timezone.utc)
    if "created_at" not in clef_data:
        clef_data["created_at"] = now
    if "updated_at" not in clef_data:
        clef_data["updated_at"] = now

    try:
        clef = Clef(**clef_data)
        return clef
    except Exception as e:
        logger.warning(f"Failed to create Clef object: {str(e)}")
        return None


def _convert_nested_check_to_clef(
    check_data: Dict[str, Any],
    default_table: Optional[str] = None,
    default_stave_id: Optional[str] = None,
    stave_id_map: Optional[Dict[str, str]] = None,
    index: int = 0,
) -> Optional[Dict[str, Any]]:
    """
    Convert nested format check to flat format clef.

    Args:
        check_data: Check data from nested format
        default_table: Default table from clef context
        default_stave_id: Default stave_id from clef context
        stave_id_map: Mapping for resolving stave references
        index: Index of check in the checks array (for generating ID)

    Returns:
        Clef data dictionary or None if invalid
    """
    if "check" not in check_data:
        return None

    check_type = check_data["check"]

    # Build config from check data
    config = {}

    # Add table if specified in check or use default
    if "table" in check_data:
        config["table"] = check_data["table"]
    elif default_table:
        config["table"] = default_table

    # Add column if specified
    if "column" in check_data:
        config["column"] = check_data["column"]

    # Add other config fields
    for key in [
        "min",
        "max",
        "pattern",
        "query",
        "metric",
        "strategy",
        "lookup",
        "validation",
        "script_path",
        "params",
    ]:
        if key in check_data:
            config[key] = check_data[key]

    # Generate ID if not provided
    import uuid

    clef_id = check_data.get("id")
    if not clef_id:
        # Generate based on check type and index
        name_slug = (
            check_data.get("name", f"{check_type}-{index}").lower().replace(" ", "-")
        )
        clef_id = f"clef-{name_slug}-{str(uuid.uuid4())[:8]}"

    # Build clef data
    clef_data = {
        "id": clef_id,
        "check_type": check_type,
        "name": check_data.get("name", f"{check_type} check"),
        "description": check_data.get("description"),
        "config": config,
        "warn": check_data.get("warn"),
        "fail": check_data.get("fail"),
        "schedule": check_data.get("schedule"),
        "is_active": check_data.get("is_active", True),
    }

    # Add stave_id if available
    if "stave_id" in check_data:
        stave_id = check_data["stave_id"]
        if stave_id_map and stave_id in stave_id_map:
            stave_id = stave_id_map[stave_id]
        clef_data["stave_id"] = stave_id
    elif default_stave_id:
        clef_data["stave_id"] = default_stave_id
    else:
        # Can't create clef without stave_id
        return None

    return clef_data


def load_and_parse_yaml(file_path: str) -> Tuple[List[Stave], List[Clef]]:
    """
    Load YAML file and parse both staves and clefs.

    Args:
        file_path: Path to YAML file

    Returns:
        Tuple of (staves, clefs) lists

    Raises:
        YAMLLoadError: If loading or parsing fails
    """
    # Load YAML
    yaml_data = load_yaml_file(file_path)

    # Validate structure
    validation = validate_yaml_structure(yaml_data)
    if not validation:
        raise YAMLLoadError(f"YAML validation failed: {', '.join(validation.errors)}")

    # Parse staves
    staves = parse_staves(yaml_data)

    # Create stave_id_map for resolving references
    stave_id_map = {}
    for stave in staves:
        if stave.id:
            stave_id_map[stave.id] = stave.id
            if stave.name:
                stave_id_map[stave.name] = stave.id

    # Parse clefs
    clefs = parse_clefs(yaml_data, stave_id_map)

    return staves, clefs
