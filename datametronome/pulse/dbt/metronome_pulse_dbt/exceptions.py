"""Custom exceptions for the dbt artifact connector."""


class DbtConnectorError(Exception):
    """Base exception for all dbt connector errors."""


class ArtifactNotFoundError(DbtConnectorError):
    """Raised when a required artifact (e.g. manifest.json) is missing.

    manifest.json is the only required artifact — run_results and catalog
    are optional and return None instead of raising.
    """


class ArtifactParseError(DbtConnectorError):
    """Raised when an artifact file exists but cannot be parsed as valid JSON."""


class CloudApiError(DbtConnectorError):
    """Raised when the dbt Cloud API returns an unexpected response.

    The HTTP status is in the message. Nothing branches on it, so it is not
    carried as a separate attribute.
    """
