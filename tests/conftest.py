"""
Pytest configuration for ELF test suite.

Fixtures and configuration for testing the Emergent Learning Framework.
"""
from pathlib import Path
import sys

# Add src directory to path for imports
src_path = Path(__file__).parent.parent / "src" / "emergent-learning"
sys.path.insert(0, str(src_path))
