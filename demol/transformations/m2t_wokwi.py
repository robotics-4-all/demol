"""Model-to-Text transformation for Wokwi simulation diagrams.

This module transforms DeMoL device models into Wokwi-compatible
simulation projects. The generator emits the two artifacts the Wokwi
simulator expects at the project root:

* ``diagram.json`` — parts + connections array (Wokwi diagram format).
* ``wokwi.toml``   — project manifest with ``[wokwi]`` and ``[net]`` tables.

Board and peripheral types are mapped to Wokwi's canonical part IDs via
``_BOARD_PART_IDS`` / ``_PERIPHERAL_PART_IDS``; the dictionaries are
deliberately explicit (one entry per supported component) so the mapping
is auditable. Connection colouring follows the convention used across
the project: I2C=blue, SPI=green, UART=yellow, GPIO=red, VCC=red,
GND=black.

The backend renders both files through the Jinja2 templates in
``demol/templates/wokwi/`` (``diagram.json.j2``, ``wokwi.toml.j2``).
No Wokwi CLI / token / network call is required.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List

import jinja2

from demol.definitions import TEMPLATES_WOKWI
from .base_generator import BaseCodeGenerator

__all__ = ["WokwiCodeGenerator"]


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Map DeMoL component type names to the canonical Wokwi part IDs from
# https://docs.wokwi.com/parts. Unmapped components fall back to a generic
# placeholder so the diagram still loads in the simulator and the user can
# swap the type in the JSON. Keys are the *class name* of the parsed
# object (``type(board).__name__`` for boards, ``type(peripheral.ref).__name__``
# for peripherals); add new entries here when adding new boards/peripherals.

_BOARD_PART_IDS: Dict[str, str] = {
    "RaspberryPi_4_Model_B": "board-raspberry-pi-4b",
    "RaspberryPi_3B_Plus": "board-raspberry-pi-4b",
    "RaspberryPi_3B": "board-raspberry-pi-4b",
    "RaspberryPi_3A_Plus": "board-raspberry-pi-4b",
    "RaspberryPi_5": "board-raspberry-pi-5",
    "RaspberryPi_Pico": "wokwi-pi-pico",
    "WemosD1Mini": "board-wemos-d1-r32",
    "WemosD1R32": "board-wemos-d1-r32",
    "ESP32Wroom32": "board-esp32-devkit-c-v4",
    "NodeMCUESP8266": "wokwi-nodemcu",
    "ArduinoUno": "wokwi-arduino-uno",
}

_PERIPHERAL_PART_IDS: Dict[str, str] = {
    "BME680": "bme680",
    "BME280": "wokwi-bme280",
    "LedGeneric": "wokwi-led",
    "TactileButton": "wokwi-pushbutton",
    "WS281X": "wokwi-neopixel",
    "HCSR04": "wokwi-hc-sr04",
    "SRF04": "wokwi-hc-sr04",
    "SRF05": "wokwi-hc-sr05",
    "MPL3115A2": "wokwi-mpl3115a2",
    "SSD1306": "wokwi-ssd1306",
    "DHT22": "wokwi-dht22",
    "DS18B20": "wokwi-ds18b20",
    "PIR_HCSR501": "wokwi-pir",
    "Buzzer": "wokwi-buzzer",
    "Relay": "wokwi-relay-module",
    "Servo": "wokwi-servo",
}

# Default Wokwi part type when a component has no explicit mapping.
_DEFAULT_BOARD_PART = "wokwi-pi-pico"
_DEFAULT_PERIPHERAL_PART = "wokwi-resistor"

# Connection colour codes (Wokwi accepts any CSS color name).
_DATA_COLORS: Dict[str, str] = {
    "i2c": "blue",
    "spi": "green",
    "uart": "yellow",
    "gpio": "red",
    "pwm": "red",
}
_GND_PIN_NAMES = {"gnd", "GND", "Gnd"}
_VCC_PIN_NAMES = {"vcc", "VCC", "Vcc", "vin", "VIN", "Vin", "power_3v3", "power_5v", "3v3", "5v"}


class WokwiCodeGenerator(BaseCodeGenerator):
    """Generates a Wokwi simulation project (``diagram.json`` + ``wokwi.toml``).

    The generator walks the parsed device model, emits one ``parts`` entry
    per board/peripheral using the canonical Wokwi part IDs, and produces
    one ``connections`` entry per pin map in every ``CONNECT`` block.
    Power and data connections are coloured per ``_DATA_COLORS`` and the
    GND/VCC convention.
    """

    OS = "wokwi"

    def os_name(self) -> str:
        return self.OS

    def __init__(self, device_model, output_dir: Path):
        """Initialize code generator with device model.

        Args:
            device_model: Parsed textX device model.
            output_dir: Output directory for generated artifacts. Wokwi
                files are written directly into ``<output_dir>/`` (the
                simulator expects ``diagram.json`` and ``wokwi.toml`` at
                the project root, not in a subdirectory).
        """
        super().__init__(device_model, output_dir)
        self.env = self.setup_template_environment()

    def setup_template_environment(self) -> jinja2.Environment:
        """Setup Jinja2 environment with Wokwi-specific templates.

        ``trim_blocks``/``lstrip_blocks`` keep the rendered ``diagram.json``
        and ``wokwi.toml`` tight (no stray whitespace from control tags).
        """
        fsloader = jinja2.FileSystemLoader(TEMPLATES_WOKWI)
        return jinja2.Environment(
            loader=fsloader,
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True,
        )

    # ------------------------------------------------------------------
    # Part/connection helpers
    # ------------------------------------------------------------------

    def _board_part_id(self, board) -> str:
        """Resolve Wokwi part ID for a board object."""
        type_name = type(board).__name__
        return _BOARD_PART_IDS.get(type_name, _DEFAULT_BOARD_PART)

    def _peripheral_part_id(self, peripheral_ref) -> str:
        """Resolve Wokwi part ID for a peripheral ComponentInstance."""
        type_name = type(peripheral_ref.ref).__name__
        return _PERIPHERAL_PART_IDS.get(type_name, _DEFAULT_PERIPHERAL_PART)

    @staticmethod
    def _board_id(board) -> str:
        """Stable Wokwi part ID for the board (single instance per project)."""
        return "board"

    @staticmethod
    def _peripheral_id(peripheral_ref) -> str:
        """Stable Wokwi part ID for a peripheral ComponentInstance.

        Uses the instance name when one is declared (``USE BME680[BME]`` ->
        ``BME``); falls back to the type name in lower case so unnamed
        ``USE`` statements still get a unique identifier.
        """
        if getattr(peripheral_ref, "name", None):
            return str(peripheral_ref.name)
        return str(type(peripheral_ref.ref).__name__).lower()

    @staticmethod
    def _map_data_pin_name(pin_name: str) -> str:
        """Map a DeMoL data-pin name to the Wokwi convention (uppercase).

        Wokwi parts use uppercase SDA / SCL / MOSI / MISO / SCK / CS /
        TX / RX for protocol signal pins; peripheral boards in the
        DeMoL catalogue use lowercase. We normalise here so the rendered
        connection references resolve to the Wokwi part's actual pin
        labels. Unknown pin names pass through unchanged.
        """
        upper = {"sda", "scl", "mosi", "miso", "sck", "cs", "tx", "rx"}
        if pin_name in upper:
            return pin_name.upper()
        return pin_name

    @staticmethod
    def _power_color(periph_pin: str, board_pin: str) -> str:
        """Return the Wokwi connection colour for a power pin pair."""
        # GND side: black; everything else (VCC / 3V3 / 5V / Vin) red.
        if periph_pin in _GND_PIN_NAMES or board_pin in _GND_PIN_NAMES:
            return "black"
        return "red"

    # ------------------------------------------------------------------
    # Context assembly
    # ------------------------------------------------------------------

    def build_global_context(self) -> Dict[str, Any]:
        """Build the global Jinja context for Wokwi templates.

        Returns:
            Dict with keys ``device_name`` (for human-readable filenames),
            ``parts`` (list of ``{type, id, attrs}`` dicts), ``connections``
            (list of ``{from, to, color}`` dicts) and ``nets`` (list of
            ``{name, value}`` dicts for the ``wokwi.toml`` ``[net]`` table).
        """
        board = self.get_board()
        connections = self.get_connections()

        parts: List[Dict[str, Any]] = []
        connections_list: List[Dict[str, Any]] = []
        nets: List[Dict[str, Any]] = []

        # Board is always present (Wokwi diagrams require at least one
        # controller part). Emit it first so its id appears before any
        # references in ``connections``.
        board_id = self._board_id(board)
        parts.append(
            {
                "type": self._board_part_id(board),
                "id": board_id,
                "attrs": "",
            }
        )

        seen_periph_ids: set = set()
        for conn in connections:
            periph = conn.peripheral
            periph_id = self._peripheral_id(periph)

            # Emit one part entry per unique peripheral instance.
            if periph_id not in seen_periph_ids:
                seen_periph_ids.add(periph_id)
                parts.append(
                    {
                        "type": self._peripheral_part_id(periph),
                        "id": periph_id,
                        "attrs": "",
                    }
                )

            # Data connections (i2c/spi/uart use PinMapping, gpio/pwm use
            # PinConnection). In both cases ``toPin`` is the board-side
            # pin name and ``fromPin`` is the peripheral-side pin name
            # (see ``_get_board_and_periph_pins`` in base_generator.py).
            for data_conn in conn.dataConns:
                conn_type = data_conn.type
                color = _DATA_COLORS.get(conn_type, "gray")
                if conn_type in ("i2c", "spi", "uart"):
                    for pin_map in data_conn.pins:
                        board_pin = self._map_data_pin_name(pin_map.toPin)
                        periph_pin = self._map_data_pin_name(pin_map.fromPin)
                        connections_list.append(
                            {
                                "from": f"{board_id}:{board_pin}",
                                "to": f"{periph_id}:{periph_pin}",
                                "color": color,
                            }
                        )
                else:  # gpio / pwm
                    for pin_conn in data_conn.pins:
                        connections_list.append(
                            {
                                "from": f"{board_id}:{pin_conn.toPin}",
                                "to": f"{periph_id}:{pin_conn.fromPin}",
                                "color": color,
                            }
                        )

            # Power connections (GND, VCC, ...). The colour follows the
            # Wokwi convention of red for positive rails and black for GND.
            for power_conn in conn.powerConns:
                color = self._power_color(power_conn.fromPin, power_conn.toPin)
                connections_list.append(
                    {
                        "from": f"{board_id}:{power_conn.toPin}",
                        "to": f"{periph_id}:{power_conn.fromPin}",
                        "color": color,
                    }
                )

        # Mirror the data-connection colour map into the ``[net]`` table
        # of wokwi.toml so the rendered project can override the default
        # wire colours per protocol. ``[net]`` is optional in the Wokwi
        # project format; emitting the section keeps the file symmetric
        # with the diagram.json colour choices.
        for protocol, color in _DATA_COLORS.items():
            nets.append({"name": protocol, "value": color})
        nets.append({"name": "gnd", "value": "black"})
        nets.append({"name": "vcc", "value": "red"})

        return {
            "device_name": self.device_model.metadata.name,
            "parts": parts,
            "connections": connections_list,
            "nets": nets,
        }

    # ------------------------------------------------------------------
    # Generation
    # ------------------------------------------------------------------

    def generate(self) -> None:
        """Render ``diagram.json`` and ``wokwi.toml`` for the device model.

        Both files are written at the root of ``output_dir`` because the
        Wokwi simulator expects the project manifest next to the diagram.
        """
        logger.info("Generating Wokwi simulation project...")
        global_context = self.build_global_context()

        # diagram.json: render through Jinja2 so the parts/connections
        # arrays come from the model, not from a hard-coded skeleton.
        template = self.env.get_template("diagram.json.j2")
        self._write_template(template, global_context, self.output_dir / "diagram.json")

        # wokwi.toml: project manifest. The ``[wokwi] version = 1`` table
        # is the only required key per the Wokwi project format spec; the
        # ``[net]`` table is optional and carries the per-protocol colour
        # overrides produced from the connection map.
        template = self.env.get_template("wokwi.toml.j2")
        self._write_template(template, global_context, self.output_dir / "wokwi.toml")

        logger.info("Wokwi code generation complete!")


def m2t_wokwi(model, output_dir="."):
    """Transform a DeMoL device model object to a Wokwi simulation project.

    Args:
        model: Parsed textX device model.
        output_dir: Output directory for the generated Wokwi artifacts.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    generator = WokwiCodeGenerator(model, output_path)
    generator.generate()
