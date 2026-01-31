# ingestion_service\tests\conftest.py
# Add src and repo root to sys.path in conftest.py
# This makes imports work without needing environment variables.
import sys
import pathlib

# Path to ingestion_service folder
ROOT = pathlib.Path(__file__).parent.parent.resolve()  # rag-foundry/ingestion_service
SRC = ROOT / "src"
REPO_ROOT = ROOT.parent  # rag-foundry

# Add paths to sys.path
sys.path.insert(0, str(REPO_ROOT))  # so `shared` can be imported
sys.path.insert(0, str(SRC))        # so `src` can be imported