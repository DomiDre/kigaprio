import pytest
from fastapi.testclient import TestClient

from kigaprio.main import app


@pytest.fixture(scope="function")
def client():
    with TestClient(app) as test_client:
        yield test_client
