"""T30: Relay RIOT codegen tests.

Verifies that:
- ``demol generate riot`` exits 0 for ``examples/esp/esp_relay.dev``
- The generated driver file ``actuator_relay_0.c`` exists
- The generated ``.c`` contains the ``init_actuator`` function
- The generated ``.c`` contains the ``on_message`` callback
"""

import subprocess
import tempfile
from pathlib import Path

EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples" / "esp"


def test_relay_riot_codegen_succeeds():
    """Generate RIOT code for esp_relay.dev and verify exit code."""
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "out"
        model = EXAMPLES_DIR / "esp_relay.dev"
        assert model.is_file(), f"Model not found: {model}"

        res = subprocess.run(
            ["demol", "generate", "riot", str(model), "--output-dir", str(out)],
            capture_output=True,
            text=True,
        )
        assert res.returncode == 0, (
            f"demol generate riot failed (exit {res.returncode}):\n"
            f"  stderr: {res.stderr}\n"
            f"  stdout: {res.stdout}"
        )


def test_relay_generated_driver_exists():
    """Verify that the generated driver file was produced."""
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "out"
        model = EXAMPLES_DIR / "esp_relay.dev"
        res = subprocess.run(
            ["demol", "generate", "riot", str(model), "--output-dir", str(out)],
            capture_output=True,
            text=True,
        )
        assert res.returncode == 0, f"Codegen failed:\n{res.stderr}"

        driver_file = out / "actuator_relay_0.c"
        assert driver_file.is_file(), (
            f"Expected generated driver at {driver_file}. " f"Contents of {out}: {list(out.iterdir())}"
        )


def test_relay_generated_driver_contains_init():
    """Verify the generated C code contains the expected function names."""
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "out"
        model = EXAMPLES_DIR / "esp_relay.dev"
        res = subprocess.run(
            ["demol", "generate", "riot", str(model), "--output-dir", str(out)],
            capture_output=True,
            text=True,
        )
        assert res.returncode == 0, f"Codegen failed:\n{res.stderr}"

        driver_file = out / "actuator_relay_0.c"
        content = driver_file.read_text()
        assert "init_actuator_relay_0" in content, f"Expected 'init_actuator_relay_0' in generated C file.\n{content}"
        assert "relay_0_on_message" in content, f"Expected 'relay_0_on_message' in generated C file.\n{content}"
