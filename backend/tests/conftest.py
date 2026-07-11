"""Shared pytest fixtures.

Clears the cached in-memory repository between tests so analyses created in
one test don't leak into another, since `get_repository` is process-cached
via `lru_cache` for reuse across real requests.
"""

import pytest
from fastapi.testclient import TestClient

from app.dependencies import get_repository
from app.main import app


@pytest.fixture
def client() -> TestClient:
    get_repository.cache_clear()
    return TestClient(app)
