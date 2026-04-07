"""
YAML Configuration Loader for Staves and Clefs.

Load stave and clef configurations from YAML files for easy, declarative
setup of your data monitoring.

Example Usage:
    # Load from YAML file
    staves, clefs = load_staves_from_yaml("staves.yaml")

    # Load and save to database
    import_staves_from_yaml("staves.yaml", db)

    # Single stave file
    stave, clefs = load_single_stave_yaml("production-db.yaml")
"""

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from datametronome_podium.features.clefs.model import Clef
from datametronome_podium.features.staves.model import Stave
from datametronome_podium.services.config_validator import (
    ConfigurationIssue,
    validate_configuration,
)
from datametronome_podium.services.stave_service import (
    generate_clef_id,
    generate_stave_id,
    serialize_clef,
    serialize_stave,
)


def _resolve_env_vars(value: Any) -> Any:
    """
    Resolve environment variables in configuration values.

    Supports:
        ${VAR_NAME} - Required variable
        ${VAR_NAME:-default} - Variable with default value

    Example:
        ${DB_HOST} -> "localhost"
        ${DB_PORT:-5432} -> 5432 (if DB_PORT not set)
    """
    if not isinstance(value, str):
        return value

    # Check if it's an env var reference
    if not value.startswith("${") or not value.endswith("}"):
        return value

    # Extract variable name and default
    var_expr = value[2:-1]  # Remove ${ and }

    if ":-" in var_expr:
        var_name, default = var_expr.split(":-", 1)
        result = os.environ.get(var_name, default)
        # Try to convert to int if it looks like a number
        try:
            return int(result)
        except ValueError:
            return result
    else:
        var_name = var_expr
        result = os.environ.get(var_name)
        if result is None:
            raise ValueError(
                f"Environment variable ${{{var_name}}} is required but not set"
            )
        # Try to convert to int if it looks like a number
        try:
            return int(result)
        except ValueError:
            return result


def _resolve_config_env_vars(config: dict[str, Any]) -> dict[str, Any]:
    """Recursively resolve environment variables in config dict."""
    result = {}
    for key, value in config.items():
        if isinstance(value, dict):
            result[key] = _resolve_config_env_vars(value)
        elif isinstance(value, list):
            result[key] = [_resolve_env_vars(v) for v in value]
        else:
            result[key] = _resolve_env_vars(value)
    return result


def load_staves_from_yaml(
    yaml_path: str | Path, resolve_env: bool = True
) -> tuple[list[Stave], list[Clef]]:
    """
    Load staves and clefs from a YAML file.

    Args:
        yaml_path: Path to YAML file
        resolve_env: Whether to resolve environment variables

    Returns:
        Tuple of (staves_list, clefs_list)

    Example:
        >>> staves, clefs = load_staves_from_yaml("staves.yaml")
        >>> print(f"Loaded {len(staves)} staves and {len(clefs)} clefs")

    YAML Format:
        staves:
          - id: stave-001
            name: "Production DB"
            data_source_type: postgres
            connection_config:
              host: ${DB_HOST}
              port: 5432
        clefs:
          - id: clef-001
            stave_id: stave-001
            name: "Email Check"
            check_type: null_check
            config:
              table: users
              column: email
    """
    yaml_path = Path(yaml_path)

    if not yaml_path.exists():
        raise FileNotFoundError(f"YAML file not found: {yaml_path}")

    with open(yaml_path, "r") as f:
        data = yaml.safe_load(f)

    if not data:
        raise ValueError(f"Empty YAML file: {yaml_path}")

    # Load staves
    staves = []
    staves_data = data.get("staves", [])

    for stave_data in staves_data:
        # Resolve environment variables if enabled
        if resolve_env:
            stave_data = _resolve_config_env_vars(stave_data)

        # Generate ID if not provided
        if "id" not in stave_data or not stave_data["id"]:
            stave_data["id"] = generate_stave_id()

        # Set timestamps if not provided
        if "created_at" not in stave_data:
            stave_data["created_at"] = datetime.now(timezone.utc)
        if "updated_at" not in stave_data:
            stave_data["updated_at"] = datetime.now(timezone.utc)

        # Create Stave object
        stave = Stave(**stave_data)
        staves.append(stave)

    # Load clefs
    clefs = []
    clefs_data = data.get("clefs", [])

    for clef_data in clefs_data:
        # Resolve environment variables if enabled
        if resolve_env:
            clef_data = _resolve_config_env_vars(clef_data)

        # Generate ID if not provided
        if "id" not in clef_data or not clef_data["id"]:
            clef_data["id"] = generate_clef_id()

        # Set timestamps if not provided
        if "created_at" not in clef_data:
            clef_data["created_at"] = datetime.now(timezone.utc)
        if "updated_at" not in clef_data:
            clef_data["updated_at"] = datetime.now(timezone.utc)

        # Create Clef object
        clef = Clef(**clef_data)
        clefs.append(clef)

    return staves, clefs


def load_single_stave_yaml(
    yaml_path: str | Path, resolve_env: bool = True
) -> tuple[Stave, list[Clef]]:
    """
    Load a single stave with its clefs from YAML file.

    Args:
        yaml_path: Path to YAML file
        resolve_env: Whether to resolve environment variables

    Returns:
        Tuple of (stave, clefs_list)

    Example:
        >>> stave, clefs = load_single_stave_yaml("production-db.yaml")
        >>> print(f"Loaded {stave.name} with {len(clefs)} checks")

    YAML Format:
        stave:
          name: "Production DB"
          data_source_type: postgres
          connection_config:
            host: localhost
        clefs:
          - name: "Email Check"
            check_type: null_check
            config:
              table: users
    """
    yaml_path = Path(yaml_path)

    if not yaml_path.exists():
        raise FileNotFoundError(f"YAML file not found: {yaml_path}")

    with open(yaml_path, "r") as f:
        data = yaml.safe_load(f)

    if not data or "stave" not in data:
        raise ValueError(f"YAML file must contain a 'stave' section: {yaml_path}")

    # Load stave
    stave_data = data["stave"]

    # Resolve environment variables if enabled
    if resolve_env:
        stave_data = _resolve_config_env_vars(stave_data)

    # Generate ID if not provided
    if "id" not in stave_data or not stave_data["id"]:
        stave_data["id"] = generate_stave_id()

    # Set timestamps if not provided
    if "created_at" not in stave_data:
        stave_data["created_at"] = datetime.now(timezone.utc)
    if "updated_at" not in stave_data:
        stave_data["updated_at"] = datetime.now(timezone.utc)

    stave = Stave(**stave_data)

    # Load clefs
    clefs = []
    clefs_data = data.get("clefs", [])

    for clef_data in clefs_data:
        # Resolve environment variables if enabled
        if resolve_env:
            clef_data = _resolve_config_env_vars(clef_data)

        # Auto-set stave_id if not provided
        if "stave_id" not in clef_data:
            clef_data["stave_id"] = stave.id

        # Generate ID if not provided
        if "id" not in clef_data or not clef_data["id"]:
            clef_data["id"] = generate_clef_id()

        # Set timestamps if not provided
        if "created_at" not in clef_data:
            clef_data["created_at"] = datetime.now(timezone.utc)
        if "updated_at" not in clef_data:
            clef_data["updated_at"] = datetime.now(timezone.utc)

        clef = Clef(**clef_data)
        clefs.append(clef)

    return stave, clefs


async def import_staves_from_yaml(
    yaml_path: str | Path, db, resolve_env: bool = True, overwrite: bool = False
) -> dict[str, int]:
    """
    Load staves and clefs from YAML and save to database.

    Args:
        yaml_path: Path to YAML file
        db: Database connector instance
        resolve_env: Whether to resolve environment variables
        overwrite: Whether to overwrite existing staves/clefs with same ID

    Returns:
        Dict with counts: {"staves": 3, "clefs": 5}

    Example:
        >>> from datametronome_podium.core.database import get_executor
        >>> db = get_executor().connector
        >>> counts = await import_staves_from_yaml("staves.yaml", db)
        >>> print(f"Imported {counts['staves']} staves, {counts['clefs']} clefs")
    """
    # Load from YAML
    staves, clefs = load_staves_from_yaml(yaml_path, resolve_env=resolve_env)

    staves_imported = 0
    clefs_imported = 0

    # Import staves
    for stave in staves:
        # Check if exists
        existing = await db.query(
            {"sql": "SELECT id FROM staves WHERE id = ?", "params": [stave.id]}
        )

        if existing and not overwrite:
            print(f"⚠️  Skipping existing stave: {stave.name} (id={stave.id})")
            continue

        # Serialize and save
        stave_data = serialize_stave(stave)
        success = await db.write([{"table": "staves", **stave_data}], "staves")

        if success:
            staves_imported += 1
            print(f"✅ Imported stave: {stave.name}")
        else:
            print(f"❌ Failed to import stave: {stave.name}")

    # Import clefs
    for clef in clefs:
        # Check if exists
        existing = await db.query(
            {"sql": "SELECT id FROM clefs WHERE id = ?", "params": [clef.id]}
        )

        if existing and not overwrite:
            print(f"⚠️  Skipping existing clef: {clef.name} (id={clef.id})")
            continue

        # Serialize and save
        clef_data = serialize_clef(clef)
        success = await db.write([{"table": "clefs", **clef_data}], "clefs")

        if success:
            clefs_imported += 1
            print(f"✅ Imported clef: {clef.name}")
        else:
            print(f"❌ Failed to import clef: {clef.name}")

    return {"staves": staves_imported, "clefs": clefs_imported}


def validate_yaml_config(yaml_path: str | Path) -> dict[str, Any]:
    """
    Validate a YAML configuration file with comprehensive conflict detection.

    Args:
        yaml_path: Path to YAML file

    Returns:
        Dict with validation results including conflicts and dissonance detection:
        {
            "valid": bool,
            "issues": [ConfigurationIssue],
            "summary": str,
            "recommendations": [str],
            "stats": {...}
        }

    Example:
        >>> result = validate_yaml_config("staves.yaml")
        >>> if result["valid"]:
        ...     print("✅ Configuration is valid!")
        ... else:
        ...     for issue in result["issues"]:
        ...         print(issue)
    """
    try:
        # Load the configuration
        staves, clefs = load_staves_from_yaml(yaml_path, resolve_env=False)

        # Run comprehensive validation
        validation_result = validate_configuration(staves, clefs)

        # Add environment variable warnings
        env_warnings = []
        yaml_path = Path(yaml_path)
        with open(yaml_path, "r") as f:
            content = f.read()
            # Find all ${VAR} references
            import re

            env_vars = re.findall(r"\$\{([^}:-]+)", content)
            for var in env_vars:
                if var not in os.environ:
                    env_warnings.append(f"Environment variable not set: ${{{var}}}")

        # Add env warnings as info issues
        for warning in env_warnings:
            validation_result["issues"].append(
                ConfigurationIssue(
                    severity="info",
                    issue_type="missing",
                    message=warning,
                    suggestion="Set the environment variable before importing",
                )
            )

        # Update stats to include env warnings
        validation_result["stats"]["env_warnings"] = len(env_warnings)

        return validation_result

    except Exception as e:
        # Return error result
        return {
            "valid": False,
            "issues": [
                ConfigurationIssue(
                    severity="error",
                    issue_type="invalid",
                    message=f"Failed to parse YAML: {str(e)}",
                    suggestion="Check YAML syntax and file format",
                )
            ],
            "summary": f"❌ YAML parsing failed: {str(e)}",
            "recommendations": ["Fix YAML syntax errors"],
            "stats": {"staves": 0, "clefs": 0, "errors": 1, "warnings": 0, "info": 0},
        }
