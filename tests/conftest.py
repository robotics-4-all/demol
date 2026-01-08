import pytest
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from demol.lang import get_device_mm, get_component_mm

@pytest.fixture(scope="session")
def device_mm():
    return get_device_mm()

@pytest.fixture(scope="session")
def component_mm():
    return get_component_mm()

@pytest.fixture(autouse=True)
def clear_validation_state():
    from demol.lang.semantics import clear_validation_results
    clear_validation_results()
