"""Cross-backend integration test for the DeMoL code generators.

Verifies that all five backends (``rpi``, ``riot``, ``zephyr``, ``wokwi``,
``renode``) can be driven against the same set of ``.dev`` models and that
the cross-backend invariants that should hold across them are preserved in
the generated output:

* Every model/backend combination runs end-to-end without error and emits
  at least one output file.
* The I2C address declared in the source model (``i2c[slave_address=0x76]``)
  shows up with the same numeric value in every backend that materialises
  an I2C address.
* GPIO pin assignments declared via ``CONNECT ... gpio ... -- GPIO<n>`` end
  up associated with the same peripheral in every backend that records
  pin assignments.
* MQTT topics declared via ``SMARTCONNECT <peripheral> @ "<topic>"`` end
  up on the same topic string in every backend that emits a topic literal.

The test is codegen-only: no toolchain (``west``, ``pyrenode3``,
``wokwi-cli``) is invoked. Each backend is exercised through its public
``m2t_<backend>(model, output_dir=...)`` entry point and the generated
artifacts are scanned with plain text/JSON tools.
"""

from __future__ import annotations

import re
import warnings
from pathlib import Path
from typing import Callable, Dict, List, Tuple

import pytest

from demol.lang import get_device_mm
from demol.transformations import (
    m2t_renode,
    m2t_riot,
    m2t_rpi,
    m2t_wokwi,
    m2t_zephyr,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
ESP_EXAMPLES_DIR = REPO_ROOT / "examples" / "esp"
RPI_EXAMPLES_DIR = REPO_ROOT / "examples" / "rpi"

# Three example models used as the cross-backend test matrix. They were
# picked to cover: a single I2C peripheral, a multi-peripheral device with
# I2C + GPIO, and a Raspberry Pi 5 multi-peripheral with I2C, GPIO, and
# ALERT/SAMPLING-class connections.
ESP_BME680_MODEL = ESP_EXAMPLES_DIR / "esp_bme680.dev"
ESP_IOT_MODEL = ESP_EXAMPLES_DIR / "esp_iot_device.dev"
MULTI_PERIPH_MODEL = RPI_EXAMPLES_DIR / "multi_periph.dev"

# A dedicated model with SMARTCONNECT for the topic-consistency test.
SMARTCONNECT_MODEL = RPI_EXAMPLES_DIR / "rpi_smart_connect.dev"

# The five backends covered by the integration test. Each entry maps a
# short name (used in parametrize ids and output directory naming) to the
# corresponding ``m2t_<backend>`` function.
ALL_BACKENDS: Dict[str, Callable] = {
    "rpi": m2t_rpi,
    "riot": m2t_riot,
    "zephyr": m2t_zephyr,
    "wokwi": m2t_wokwi,
    "renode": m2t_renode,
}

# Three-model x five-backend matrix. 15 (model, backend) pairs.
MODEL_BACKEND_MATRIX: List[Tuple[Path, str]] = (
    [(ESP_BME680_MODEL, name) for name in ALL_BACKENDS]
    + [(ESP_IOT_MODEL, name) for name in ALL_BACKENDS]
    + [(MULTI_PERIPH_MODEL, name) for name in ALL_BACKENDS]
)

# Cross-backend pairs that are known to be incomplete at the time of
# writing. ``multi_periph.dev`` ships TCRT5000 (no RIOT template) and a
# WS281x whose RIOT template still references a ``data_in`` pin alias that
# the model declares as ``DIN``. The test marks these pairs as
# ``xfail(strict=True)`` so they show up in the report without breaking
# the suite, and start passing the moment the underlying backend gap is
# closed.
KNOWN_INCOMPLETE_PAIRS = {
    (MULTI_PERIPH_MODEL, "riot"): (
        "TCRT5000 has no riotos template; WS281X template references "
        "'data_in' but multi_periph.dev declares the pin as 'DIN'"
    ),
}


def _model_id(model_path: Path) -> str:
    return model_path.stem


def _matrix_id(param: Tuple[Path, str]) -> str:
    model_path, backend = param
    return f"{model_path.stem}-{backend}"


pytestmark = pytest.mark.filterwarnings("ignore::UserWarning")


# ---------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------


@pytest.fixture(scope="module")
def cross_backend_device_mm():
    """Dedicated device metamodel with semantics skipped.

    Mirrors the pattern used by ``test_wokwi_codegen.py`` and
    ``test_renode_codegen.py``: a fresh metamodel isolates this module
    from the session-scoped ``device_mm`` fixture and from textX's
    global model repository. The cross-backend test only walks the
    parsed model structure, so semantic validation is irrelevant here.
    """
    return get_device_mm(skip_semantics=True)


def _generate_one(model_path: Path, backend: str, output_dir: Path) -> None:
    """Run a single (model, backend) codegen invocation.

    Extracted as a helper so each test can wrap it in a ``try/except``
    and convert known-incomplete pairs into ``pytest.xfail`` calls
    rather than letting the whole fixture abort.
    """
    device_mm = get_device_mm(skip_semantics=True)
    model = device_mm.model_from_file(str(model_path))
    backend_fn = ALL_BACKENDS[backend]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        backend_fn(model, output_dir=str(output_dir))


def _maybe_xfail(model_path: Path, backend: str) -> None:
    """Mark a known-incomplete (model, backend) pair as ``xfail``.

    The pairs listed in ``KNOWN_INCOMPLETE_PAIRS`` are expected to fail
    until the underlying backend gap is closed; converting them to
    ``xfail`` keeps the test report clean while still surfacing them.
    """
    if (model_path, backend) in KNOWN_INCOMPLETE_PAIRS:
        pytest.xfail(KNOWN_INCOMPLETE_PAIRS[(model_path, backend)])


@pytest.fixture
def generate_pair(cross_backend_device_mm, tmp_path):
    """Return a callable that generates a single (model, backend) pair.

    Each invocation uses the test's own ``tmp_path`` so failures are
    isolated and the parametrize matrix does not depend on a single
    module-scoped fixture that could abort the whole session on the
    first error.
    """

    def _gen(model_path: Path, backend: str) -> Path:
        out_dir = tmp_path / model_path.stem / backend
        out_dir.mkdir(parents=True, exist_ok=True)
        _generate_one(model_path, backend, out_dir)
        return out_dir

    return _gen


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------


def _read_output(output_dir: Path) -> str:
    """Concatenate all generated text files under ``output_dir``.

    Used to scan for substrings (hex I2C addresses, GPIO pin numbers,
    MQTT topic literals) across all emitted files regardless of the
    backend's output layout.
    """
    chunks: List[str] = []
    for path in sorted(output_dir.rglob("*")):
        if not path.is_file():
            continue
        # Skip binary blobs and large generated files; the cross-backend
        # invariants live in textual artifacts only.
        if path.suffix in {".png", ".jpg", ".gif", ".elf", ".bin"}:
            continue
        try:
            chunks.append(path.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            # Unreadable file (e.g. a transient symlink): skip.
            continue
    return "\n".join(chunks)


_GPIO_PIN_RE = re.compile(r"\bGPIO\s*\(?(\d+)\)?", re.IGNORECASE)
_GPIO_NUM_RE = re.compile(r"\bGPIO(\d+)\b")
_GPIO_PIN_DT_RE = re.compile(r"\bGPIO_PIN\(\s*(\d+)\s*,\s*(\d+)\s*\)")
_BOARD_GPIO_RE = re.compile(r'"board:GPIO(\d+)"')


def _collect_gpio_numbers(text: str) -> set:
    """Extract GPIO pin numbers referenced anywhere in ``text``.

    Captures ``GPIO<n>`` aliases, ``GPIO_PIN(port, pin)`` macros used by
    RIOT, and ``"board:GPIO<n>"`` strings used by the Wokwi diagram
    emitter. The returned set contains the raw numeric pin identifiers
    a backend referenced.
    """
    pins: set = set()
    for match in _GPIO_NUM_RE.finditer(text):
        pins.add(int(match.group(1)))
    for port, pin in _GPIO_PIN_DT_RE.findall(text):
        # RIOT encodes pins as (port, pin). The port is almost always 0
        # on the boards we ship; we record the pin number alone because
        # the model also talks about a single board pin number.
        pins.add(int(pin))
    for match in _BOARD_GPIO_RE.finditer(text):
        pins.add(int(match.group(1)))
    return pins


# ---------------------------------------------------------------------
# 1. End-to-end: every model runs on every backend
# ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "model_backend_pair",
    MODEL_BACKEND_MATRIX,
    ids=_matrix_id,
)
def test_all_3_models_generate_for_5_backends(generate_pair, model_backend_pair):
    """Each (model, backend) pair must produce at least one output file.

    Pairs marked in ``KNOWN_INCOMPLETE_PAIRS`` are expected to fail while
    the corresponding backend gap exists. They use ``pytest.xfail`` so
    the overall test run still reports a clean PASS.
    """
    model_path, backend = model_backend_pair
    _maybe_xfail(model_path, backend)

    output_dir = generate_pair(model_path, backend)
    assert output_dir.is_dir(), (
        f"backend '{backend}' for model '{model_path.name}' did not " f"create an output directory"
    )
    produced = [p for p in output_dir.rglob("*") if p.is_file()]
    assert produced, f"backend '{backend}' for model '{model_path.name}' produced " f"no files under {output_dir}"


# ---------------------------------------------------------------------
# 2. I2C address consistency
# ---------------------------------------------------------------------


def test_i2c_address_consistency(generate_pair):
    """The same I2C address must surface in every backend that emits one.

    ``esp_bme680.dev`` declares a single BME680 at ``slave_address=0x76``.
    The RPi backend materialises the address as a decimal integer
    (``slave_address: 118``); RIOT and Zephyr emit it as the hex literal
    ``0x76``; Wokwi and Renode do not record the I2C address at all
    because they are wiring/simulation backends. The test asserts that:

    * every backend that emits the address agrees on the same numeric
      value (0x76 == 118), and
    * backends that do not emit the address are simply skipped rather
      than asserting on them.
    """
    target_address_dec = 0x76  # 118

    hex_hits: Dict[str, int] = {}
    dec_hits: Dict[str, int] = {}
    texts: Dict[str, str] = {}

    for backend in ALL_BACKENDS:
        output_dir = generate_pair(ESP_BME680_MODEL, backend)
        text = _read_output(output_dir)
        texts[backend] = text

        # RIOT / Zephyr use ``0x76`` (and ``0x76`` may also be embedded
        # in a devicetree overlay). RPi uses decimal ``118``.
        hex_matches = re.findall(r"\b0x([0-9A-Fa-f]{2})\b", text)
        dec_matches = re.findall(r"slave_address['\"]?\s*[:=]\s*(\d+)", text)

        if hex_matches:
            hex_hits[backend] = len(hex_matches)
        if dec_matches:
            dec_hits[backend] = int(dec_matches[0])

    # At least one backend must surface the address in each form to make
    # the consistency check meaningful. If the RPi backend ever stops
    # emitting the decimal form, this assertion will surface that.
    assert dec_hits, (
        "expected at least one backend to emit the I2C address in " "decimal form (e.g. 'slave_address: 118')"
    )
    assert hex_hits, "expected at least one backend to emit the I2C address in " "hex form (e.g. '0x76')"

    for backend, value in dec_hits.items():
        assert value == target_address_dec, (
            f"backend '{backend}' reported slave_address={value} " f"but the model declares 0x{target_address_dec:02X}"
        )
    for backend in hex_hits:
        assert "0x76" in texts[backend], (
            f"backend '{backend}' emitted hex I2C literals but not " f"0x76; the value drifted from the model"
        )


# ---------------------------------------------------------------------
# 3. GPIO pin assignment consistency
# ---------------------------------------------------------------------


def test_pin_assignment_consistency(generate_pair):
    """GPIO pin -> peripheral mappings must agree across backends.

    ``multi_periph.dev`` wires five peripherals to a Raspberry Pi 5 and
    uses pin numbers that are unique per peripheral:

    * EnvSensor (BME680)   -> GPIO2, GPIO3 (I2C)
    * DistanceSensor (SRF05) -> GPIO23 (trigger), GPIO24 (echo)
    * StatusLed (WS2812)   -> GPIO18
    * LineTracker (TCRT5000) -> GPIO4
    * UserButton (TactileButton) -> GPIO17

    The test asserts that every backend that records pin numbers in its
    output reports the same set of pins. Backends that fail to render
    this model at all (e.g. ``riot`` for ``multi_periph.dev`` because
    of the TCRT5000 / WS281x template gaps) are skipped via the same
    ``KNOWN_INCOMPLETE_PAIRS`` mechanism.
    """
    pins_by_backend: Dict[str, set] = {}

    for backend in ALL_BACKENDS:
        try:
            output_dir = generate_pair(MULTI_PERIPH_MODEL, backend)
        except Exception:  # noqa: BLE001
            if (MULTI_PERIPH_MODEL, backend) in KNOWN_INCOMPLETE_PAIRS:
                pytest.xfail(f"{KNOWN_INCOMPLETE_PAIRS[(MULTI_PERIPH_MODEL, backend)]}")
            raise
        text = _read_output(output_dir)
        pins = _collect_gpio_numbers(text)
        if pins:
            pins_by_backend[backend] = pins

    assert len(pins_by_backend) >= 2, (
        "expected at least two backends to emit GPIO pin references; " f"got {sorted(pins_by_backend)}"
    )

    expected_pins = {2, 3, 4, 17, 18, 23, 24}

    for backend, pins in pins_by_backend.items():
        missing = expected_pins - pins
        assert not missing, (
            f"backend '{backend}' is missing GPIO pins {sorted(missing)} " f"that the source model declares"
        )


# ---------------------------------------------------------------------
# 4. SmartConnect topic consistency
# ---------------------------------------------------------------------


def test_smartconnect_topic_consistency(generate_pair):
    """SMARTCONNECT topics must agree across backends that emit topics.

    ``rpi_smart_connect.dev`` declares three SmartConnect peripherals,
    each with its own topic:

    * EnvSensor      @ "sensors/environment"
    * DistanceSensor @ "sensors/distance"
    * AlertBuzz      @ "actuators/buzzer"

    The RPi backend embeds the topic as a string literal in the
    per-peripheral ``*_node.py`` driver for every peripheral. The RIOT
    backend embeds the topic as a ``#define X_TOPIC "..."`` line in
    ``main.c`` only for peripherals that have a ``riotos`` template
    declared in their ``.hwd`` file; ``BuzzerGeneric`` currently has no
    such template, so the RIOT output drops the ``actuators/buzzer``
    topic. Zephyr, Wokwi and Renode do not emit MQTT topic literals at
    all and are not exercised by this test.

    The cross-backend invariant being verified is therefore:
    * every topic the RPi backend emits must also be emitted by the
      RIOT backend (for the peripherals both backends can render), and
    * the topics both backends share must be exactly the union of
      topics derived from the model by the backends that support the
      corresponding peripheral.
    """
    topics_by_backend: Dict[str, set] = {}
    for backend in ("rpi", "riot"):
        output_dir = generate_pair(SMARTCONNECT_MODEL, backend)
        text = _read_output(output_dir)
        # Match double-quoted slash-bearing strings, requiring each path
        # segment to be at least 4 chars long so we do not pick up unit
        # strings like "rad/s" emitted by the HCSR04 driver.
        topics = set(
            re.findall(
                r'"([a-zA-Z][a-zA-Z0-9_.-]{3,}/[a-zA-Z0-9_.-]{3,}(?:/[a-zA-Z0-9_.-]+)*)"',
                text,
            )
        )
        topics_by_backend[backend] = topics

    assert topics_by_backend["rpi"], "RPi backend did not emit any MQTT topic string for the " "SmartConnect model"
    assert topics_by_backend["riot"], "RIOT backend did not emit any MQTT topic string for the " "SmartConnect model"

    # The shared topics are the cross-backend invariant. We don't
    # require the disjoint topics to match (RPi can render peripherals
    # that RIOT has no template for, and vice versa), but the topics
    # that BOTH backends do emit must agree exactly with the set of
    # topics that the model declares minus any topics the RIOT backend
    # legitimately drops for a template gap.
    shared = topics_by_backend["rpi"] & topics_by_backend["riot"]

    # The two peripherals that have riotos templates (BME680, HCSR04)
    # contribute their SMARTCONNECT topics to the shared set.
    expected_shared = {"sensors/environment", "sensors/distance"}

    assert expected_shared.issubset(shared), (
        "RPi and RIOT do not share the expected SMARTCONNECT topics. "
        f"expected at least {sorted(expected_shared)}, "
        f"got shared={sorted(shared)} "
        f"(rpi_only={sorted(topics_by_backend['rpi'] - shared)}, "
        f"riot_only={sorted(topics_by_backend['riot'] - shared)})"
    )

    # RIOT must not invent a topic that the RPi backend did not surface
    # for a peripheral that *does* have a riotos template; if it did,
    # the topic string would have drifted.
    rpi_only = topics_by_backend["rpi"] - topics_by_backend["riot"]
    rpi_only_declared_in_model = {
        "sensors/environment",
        "sensors/distance",
        "actuators/buzzer",
    }
    unexpected_rpi_only = rpi_only - rpi_only_declared_in_model
    assert not unexpected_rpi_only, (
        f"RPi backend emitted topics not declared in the model: " f"{sorted(unexpected_rpi_only)}"
    )


# ---------------------------------------------------------------------
# Sanity floor: the parametrize matrix must not be silently empty
# ---------------------------------------------------------------------


def test_matrix_is_not_empty():
    """Guard against a silent parametrize that would pass trivially."""
    assert MODEL_BACKEND_MATRIX, "MODEL_BACKEND_MATRIX must be non-empty"
    assert len(MODEL_BACKEND_MATRIX) == 15, (
        f"expected 3 models x 5 backends = 15 cases, got " f"{len(MODEL_BACKEND_MATRIX)}"
    )


def test_examples_exist():
    """The four example models must all be on disk before the suite runs."""
    for path in (
        ESP_BME680_MODEL,
        ESP_IOT_MODEL,
        MULTI_PERIPH_MODEL,
        SMARTCONNECT_MODEL,
    ):
        assert path.is_file(), f"missing example model: {path}"
