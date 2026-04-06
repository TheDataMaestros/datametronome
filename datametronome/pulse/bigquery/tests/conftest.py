"""
Pytest configuration and shared fixtures for DataPulse BigQuery tests.

These tests require real BigQuery credentials. Set the following environment variables:
- BIGQUERY_TEST_PROJECT_ID: Your GCP project ID
- BIGQUERY_TEST_CREDENTIALS_PATH: Path to service account JSON file (optional if using Application Default Credentials)
- BIGQUERY_TEST_CREDENTIALS_JSON: JSON string with credentials (optional)
- BIGQUERY_TEST_DATASET: Dataset name for testing (default: datametronome_test)
- BIGQUERY_TEST_LOCATION: BigQuery location (default: US)

Tests will be skipped if credentials are not available.
"""

import asyncio
import json
import os

import pytest
from google.cloud import bigquery  # type: ignore
from google.oauth2 import service_account  # type: ignore


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "integration: Integration tests with real BigQuery"
    )
    config.addinivalue_line("markers", "asyncio: Async tests")
    config.addinivalue_line("markers", "bigquery: BigQuery-specific tests")


def pytest_collection_modifyitems(config, items):
    """Automatically mark async tests with asyncio marker."""
    for item in items:
        if asyncio.iscoroutinefunction(item.function):
            item.add_marker(pytest.mark.asyncio)


def get_bigquery_config():
    """Get BigQuery test configuration from environment variables."""
    project_id = os.getenv("BIGQUERY_TEST_PROJECT_ID")
    credentials_path = os.getenv("BIGQUERY_TEST_CREDENTIALS_PATH")
    credentials_json_str = os.getenv("BIGQUERY_TEST_CREDENTIALS_JSON")
    dataset = os.getenv("BIGQUERY_TEST_DATASET", "datametronome_test")
    location = os.getenv("BIGQUERY_TEST_LOCATION", "US")

    # Parse credentials JSON if provided as string
    credentials_json = None
    if credentials_json_str:
        try:
            credentials_json = json.loads(credentials_json_str)
        except json.JSONDecodeError:
            pytest.skip("Invalid BIGQUERY_TEST_CREDENTIALS_JSON format")  # ty: ignore[too-many-positional-arguments, invalid-argument-type]

    if not project_id:
        pytest.skip("BIGQUERY_TEST_PROJECT_ID environment variable not set")  # ty: ignore[too-many-positional-arguments, invalid-argument-type]

    return {
        "project_id": project_id,
        "credentials_path": credentials_path,
        "credentials_json": credentials_json,
        "dataset": dataset,
        "location": location,
    }


@pytest.fixture(scope="session")
def bigquery_config():
    """Get BigQuery configuration for tests."""
    return get_bigquery_config()


@pytest.fixture(scope="session")
def test_client(bigquery_config):
    """Create a BigQuery client for test setup/teardown."""
    credentials = None
    if bigquery_config["credentials_path"]:
        credentials = service_account.Credentials.from_service_account_file(
            bigquery_config["credentials_path"]
        )
    elif bigquery_config["credentials_json"]:
        credentials = service_account.Credentials.from_service_account_info(
            bigquery_config["credentials_json"]
        )

    client = bigquery.Client(
        project=bigquery_config["project_id"],
        credentials=credentials,
        location=bigquery_config["location"],
    )

    yield client

    client.close()


@pytest.fixture(scope="function")
def test_dataset_id(bigquery_config, test_client):
    """Find an existing dataset to use for testing.

    First tries to find datasets in the user's project.
    Falls back to public datasets if none found.
    """
    # Try to find an existing dataset in the user's project
    try:
        datasets = list(test_client.list_datasets())
        if datasets:
            # Use the first available dataset
            dataset_id = datasets[0].dataset_id
            print(f"Using existing dataset: {dataset_id}")
            return dataset_id
    except Exception as e:
        print(f"Could not list project datasets: {e}")

    # Fallback to public datasets
    public_datasets = [
        "bigquery-public-data.samples",
        "bigquery-public-data.usa_names",
        "bigquery-public-data.wikipedia",
    ]

    for public_dataset in public_datasets:
        try:
            # Extract just the dataset name for the fixture
            parts = public_dataset.split(".")
            project_id = parts[0]
            dataset_name = parts[1]

            # Check if we can access it
            tables = list(test_client.list_tables(f"{project_id}.{dataset_name}"))
            if tables:
                print(f"Using public dataset: {public_dataset}")
                # Return full reference for public datasets
                return public_dataset
        except Exception:
            continue

    pytest.skip("No accessible datasets found (neither in project nor public datasets)")  # ty: ignore[too-many-positional-arguments, invalid-argument-type]


@pytest.fixture(scope="function")
def test_dataset(bigquery_config, test_client, test_dataset_id):
    """Get reference to existing test dataset (project or public)."""
    # Check if it's a public dataset (contains a dot and "bigquery-public-data")
    if "." in test_dataset_id and "bigquery-public-data" in test_dataset_id:
        # For public datasets, we create a mock dataset object
        # The dataset_id will be the full reference like "bigquery-public-data.samples"
        class MockDataset:
            def __init__(self, dataset_ref):
                parts = dataset_ref.split(".")
                self.project = parts[0]
                self.dataset_id = parts[1]
                self.full_id = dataset_ref
                self.location = "US"

        yield MockDataset(test_dataset_id)
    else:
        # Regular project dataset
        try:
            dataset = test_client.get_dataset(test_dataset_id)
            yield dataset
            # Don't delete the dataset - it's shared and we're just using it
        except Exception as e:
            pytest.skip(f"Could not access dataset {test_dataset_id}: {e}")  # ty: ignore[too-many-positional-arguments, invalid-argument-type]
