# ingestion_service/tests/conftest.py
"""
Pytest configuration for ingestion_service tests.

- Sets up sys.path so imports work from repo root and src
- Provides fixtures for integration tests (DB session)
- Handles environment for test database and Ollama
"""

import sys
import pathlib
import os
import pytest

from ingestion_service.src.core.database_session import get_sessionmaker

# -----------------------
# Path setup
# -----------------------
ROOT = pathlib.Path(__file__).parent.parent.resolve()  # rag-foundry/ingestion_service
SRC = ROOT / "src"
REPO_ROOT = ROOT.parent  # rag-foundry

sys.path.insert(0, str(REPO_ROOT))  # allow imports like `shared`
sys.path.insert(0, str(SRC))        # allow imports like `ingestion_service.src`

# -----------------------
# Environment defaults
# -----------------------
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql://ingestion_user:ingestion_pass@postgres:5432/ingestion_test"
)
os.environ.setdefault("EMBEDDING_PROVIDER", "ollama")
os.environ.setdefault("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
os.environ.setdefault("OLLAMA_EMBED_MODEL", "nomic-embed-text:15")

# -----------------------
# Database fixture
# -----------------------
@pytest.fixture(scope="session")
def db_session():
    """
    Provide a SQLAlchemy session for integration tests.
    Usage: pass `db_session` to any test requiring database access.
    """
    SessionLocal = get_sessionmaker()
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

# -----------------------
# Optional: helper for skipping integration tests if Docker not available
# -----------------------
def pytest_runtest_setup(item):
    if "integration" in item.keywords and os.environ.get("CI", "false") == "true":
        pytest.skip("Skipping integration tests in CI (requires Docker + Postgres + Ollama)")
