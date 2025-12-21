"""
Environment Variable Interpolation Service.

This service handles replacing environment variable placeholders in YAML configurations
with actual values from the environment.
"""

import logging
import os
import re
from typing import Any, Dict, List, Set

logger = logging.getLogger(__name__)


class InterpolationError(Exception):
    """Exception raised when interpolation fails."""

    pass


def interpolate_values(
    data: Any, env: dict[str, str] | None = None, strict: bool = True
) -> Any:
    """
    Recursively interpolate environment variables in data structures.

    Supports:
    - ${VAR} - Required variable (raises error if missing)
    - ${VAR:-default} - Optional variable with default value

    Args:
        data: Data structure to interpolate (dict, list, str, etc.)
        env: Environment variables dict (defaults to os.environ)
        strict: If True, raise error on missing required variables

    Returns:
        Data structure with interpolated values

    Raises:
        InterpolationError: If required variable is missing and strict=True
    """
    if env is None:
        env = dict(os.environ)

    return _interpolate_recursive(data, env, strict)


def _interpolate_recursive(data: Any, env: Dict[str, str], strict: bool) -> Any:
    """Recursively interpolate values."""
    if isinstance(data, dict):
        return {
            key: _interpolate_recursive(value, env, strict)
            for key, value in data.items()
        }
    elif isinstance(data, list):
        return [_interpolate_recursive(item, env, strict) for item in data]
    elif isinstance(data, str):
        return _interpolate_string(data, env, strict)
    else:
        return data


def _interpolate_string(value: str, env: Dict[str, str], strict: bool) -> str:
    """
    Interpolate environment variables in a string.

    Supports:
    - ${VAR} - Required variable
    - ${VAR:-default} - Optional variable with default
    """
    # Pattern to match ${VAR} or ${VAR:-default}
    pattern = r"\$\{([^}:]+)(?::-([^}]*))?\}"

    def replace_match(match):
        var_name = match.group(1)
        default_value = match.group(2) if match.lastindex >= 2 else None

        # Get value from environment
        if var_name in env:
            return env[var_name]
        elif default_value is not None:
            return default_value
        elif strict:
            raise InterpolationError(
                f"Required environment variable '{var_name}' is not set"
            )
        else:
            logger.warning(
                f"Environment variable '{var_name}' not found, leaving placeholder"
            )
            return match.group(0)  # Return original placeholder

    return re.sub(pattern, replace_match, value)


def extract_env_vars(yaml_data: Dict[str, Any]) -> Set[str]:
    """
    Extract all environment variable names from YAML data.

    Args:
        yaml_data: Parsed YAML data

    Returns:
        Set of environment variable names (without ${} syntax)
    """
    env_vars = set()
    _extract_vars_recursive(yaml_data, env_vars)
    return env_vars


def _extract_vars_recursive(data: Any, env_vars: Set[str]):
    """Recursively extract environment variable names."""
    if isinstance(data, dict):
        for value in data.values():
            _extract_vars_recursive(value, env_vars)
    elif isinstance(data, list):
        for item in data:
            _extract_vars_recursive(item, env_vars)
    elif isinstance(data, str):
        # Find all ${VAR} or ${VAR:-default} patterns
        pattern = r"\$\{([^}:]+)(?::-([^}]*))?\}"
        matches = re.findall(pattern, data)
        for match in matches:
            var_name = match[0]
            env_vars.add(var_name)


def validate_required_vars(
    yaml_data: Dict[str, Any], env: dict[str, str] | None = None
) -> List[str]:
    """
    Validate that all required environment variables are set.

    Args:
        yaml_data: Parsed YAML data
        env: Environment variables dict (defaults to os.environ)

    Returns:
        List of missing required variable names (empty if all present)
    """
    if env is None:
        env = dict(os.environ)

    required_vars = set()
    _extract_required_vars_recursive(yaml_data, required_vars)

    missing = []
    for var in required_vars:
        if var not in env:
            missing.append(var)

    return missing


def _extract_required_vars_recursive(data: Any, required_vars: Set[str]):
    """Recursively extract required (non-defaulted) environment variable names."""
    if isinstance(data, dict):
        for value in data.values():
            _extract_required_vars_recursive(value, required_vars)
    elif isinstance(data, list):
        for item in data:
            _extract_required_vars_recursive(item, required_vars)
    elif isinstance(data, str):
        # Find all ${VAR} patterns (without defaults)
        # Pattern: ${VAR} but not ${VAR:-default}
        pattern = r"\$\{([^}:]+)(?::-[^}]*)?\}"
        matches = re.findall(pattern, data)
        for var_name in matches:
            # Check if this is a required var (no default)
            # If the match includes :- then it has a default
            pattern = r"\$\{" + re.escape(var_name) + r"(?::-[^}]*)?\}"
            full_match = re.search(pattern, data)
            if full_match:
                match_str = full_match.group(0)
                # If it doesn't contain ':-', it's required
                if ":-" not in match_str:
                    required_vars.add(var_name)


def interpolate_yaml_data(
    yaml_data: Dict[str, Any], env: dict[str, str] | None = None, strict: bool = True
) -> Dict[str, Any]:
    """
    Interpolate environment variables in YAML data.

    This is a convenience function that combines interpolation with validation.

    Args:
        yaml_data: Parsed YAML data
        env: Environment variables dict (defaults to os.environ)
        strict: If True, raise error on missing required variables

    Returns:
        YAML data with interpolated values

    Raises:
        InterpolationError: If required variable is missing and strict=True
    """
    if env is None:
        env = dict(os.environ)

    # Validate required vars if strict
    if strict:
        missing = validate_required_vars(yaml_data, env)
        if missing:
            raise InterpolationError(
                f"Missing required environment variables: {', '.join(missing)}"
            )

    # Interpolate
    return interpolate_values(yaml_data, env, strict)
