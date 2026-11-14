import os

import pytest

from rpi_harness import mqtt_broker  # noqa: F401


def pytest_collection_modifyitems(config, items):
    if os.environ.get("DEMOL_RUN_INTEGRATION") == "1":
        return
    skip = pytest.mark.skip(reason="integration tests are opt-in: set DEMOL_RUN_INTEGRATION=1")
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip)
