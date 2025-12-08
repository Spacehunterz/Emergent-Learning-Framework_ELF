"""
Pytest configuration for ELF test suite.

Fixtures and configuration for testing the Emergent Learning Framework.
"""
import pytest
import tempfile
import shutil
from pathlib import Path
import sys

# Add src directory to path for imports
src_path = Path(__file__).parent.parent / "src" / "emergent-learning"
sys.path.insert(0, str(src_path))


@pytest.fixture
def temp_project_dir():
    """Create a temporary project directory for testing."""
    tmpdir = tempfile.mkdtemp()
    yield tmpdir
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def temp_coordination_dir(temp_project_dir):
    """Create a temporary coordination directory."""
    coord_dir = Path(temp_project_dir) / ".coordination"
    coord_dir.mkdir(parents=True, exist_ok=True)
    yield coord_dir
