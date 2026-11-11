"""
conftest.py — Pytest fixtures for TRAMA backend tests.
Ensures tests use an isolated temporary SQLite database rather than production/local data.
"""

import os
import pytest
from app.storage import init_db


@pytest.fixture(autouse=True, scope="session")
def setup_test_database(tmp_path_factory):
    test_dir = tmp_path_factory.mktemp("trama_test")
    test_db_file = test_dir / "test_trama.db"
    os.environ["TRAMA_DB_PATH"] = str(test_db_file)
    init_db()
    yield
