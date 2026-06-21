"""
SmartConnection Resolver for DeMoL

Resolves SMARTCONNECT declarations into synthetic connection objects that are
structurally identical to manual CONNECT objects. This allows existing validators,
code generators, and templates to work without any changes.

The resolution algorithm:
1. Build a PinPool from the board, marking pins used by manual CONNECT blocks
2. For each SMARTCONNECT declaration (in declaration order):
   a. Separate peripheral pins into power and IO
   b. Match power pins (GND→GND, VCC→VCC by voltage compatibility)
   c. Match data pins by protocol priority: I2C > SPI > UART > PWM > GPIO
   d. Synthesize a Connect-compatible SimpleNamespace object
   e. Append to model.connections for downstream processing
"""

from __future__ import annotations

import logging
from types import SimpleNamespace
from typing import Any

from demol.lang.semantics.core import raise_validation_error

logger = logging.getLogger(__name__)

# Protocol priority: higher index = higher priority
PROTOCOL_PRIORITY = {"gpio": 0, "pwm": 1, "uart": 2, "spi": 3, "i2c": 4}

# Pin function types that map to each protocol
I2C_FUNCTIONS = {"sda", "scl"}
SPI_FUNCTIONS = {"mosi", "miso", "sck", "cs"}
UART_FUNCTIONS = {"tx", "rx"}


def is_power_pin(pin):
    """Check if pin is a PowerPin (has ptype attribute, not funcs)."""
    return hasattr(pin, "ptype") and not hasattr(pin, "funcs")


def is_io_pin(pin):
    """Check if pin is an IOPin (has funcs attribute)."""
    return hasattr(pin, "funcs")


def is_optional(pin):
    """Check if a pin is marked optional (prefix ? in grammar)."""
    opt = getattr(pin, "optional", None)
    return opt == "?"


def copy_tx_location(source, target):
    """Copy textX location and parent attributes for get_location() compatibility."""
    for attr in (
        "_tx_position",
        "_tx_position_end",
        "_tx_filename",
        "_tx_parser",
        "parent",
    ):
        if hasattr(source, attr):
            setattr(target, attr, getattr(source, attr))


def get_primary_protocol(funcs):
    """Determine the primary protocol for an IO pin from its function list.

    Returns the highest-priority protocol function object and its category.
    Priority: I2C > SPI > UART > PWM > GPIO

    Returns:
        tuple: (func_object, category_string) e.g. (sda_func, 'i2c')
    """
    best_priority = -1
    best_func = None
    best_category = None

    for func in funcs:
        ptype = func.ptype
        if ptype in I2C_FUNCTIONS:
            cat = "i2c"
        elif ptype in SPI_FUNCTIONS:
            cat = "spi"
        elif ptype in UART_FUNCTIONS:
            cat = "uart"
        elif ptype == "pwm":
            cat = "pwm"
        elif ptype == "gpio":
            cat = "gpio"
        else:
            # adc, dac, pcm, etc. — treat as gpio for allocation
            cat = "gpio"

        priority = PROTOCOL_PRIORITY.get(cat, 0)
        if priority > best_priority:
            best_priority = priority
            best_func = func
            best_category = cat

    return best_func, best_category


def classify_peripheral_io_pins(io_pins):
    """Classify peripheral IO pins by their primary protocol.

    Returns dict with keys 'i2c', 'spi', 'uart', 'pwm', 'gpio',
    each mapping to a list of (pin, primary_func, category) tuples.
    """
    classified: dict[str, list[Any]] = {
        "i2c": [],
        "spi": [],
        "uart": [],
        "pwm": [],
        "gpio": [],
    }

    for pin in io_pins:
        func, category = get_primary_protocol(pin.funcs)
        if func and category:
            classified[category].append((pin, func))

    return classified


def get_peripheral_attribute(peripheral_ref, attr_name):
    """Get attribute default value from peripheral type definition.

    Looks through the ATTRIBUTES section of the peripheral .hwd definition.
    """
    if not hasattr(peripheral_ref, "attributes"):
        return None

    for attr in peripheral_ref.attributes:
        if attr.name == attr_name:
            return getattr(attr, "default", None)

    return None


def get_instance_attribute(peripheral_inst, attr_name):
    """Get attribute value from instance WITH overrides, falling back to type defaults.

    Checks the USE ... WITH attributes first, then the peripheral type definition.
    """
    # Check instance-level overrides (from USE ... WITH syntax)
    if hasattr(peripheral_inst, "attributes") and peripheral_inst.attributes:
        for attr in peripheral_inst.attributes:
            if attr.name == attr_name:
                return attr.value

    # Fall back to peripheral type definition defaults
    if hasattr(peripheral_inst, "ref"):
        return get_peripheral_attribute(peripheral_inst.ref, attr_name)

    return None


def infer_gpio_mode(peripheral_ref):
    """Infer GPIO mode from peripheral class type.

    Sensor → 'input'
    Actuator → 'output'
    """
    class_name = type(peripheral_ref).__name__
    if "Sensor" in class_name:
        return "input"
    elif "Actuator" in class_name:
        return "output"
    # Default to input for unknown types
    return "input"


# PinPool was extracted to its own module in the P0 refactor.
# Imported here (AFTER helpers and protocol constants are defined above)
# so that pin_pool.py can import them back without a circular-import error.
from .pin_pool import PinPool  # noqa: E402


def resolve_smart_connections(model):
    """Resolve all SmartConnect declarations into synthetic connections.

    Called from enrich_model() AFTER board/peripherals are extracted
    but BEFORE the connection enrichment loop.
    """
    if not hasattr(model, "smartConnections") or not model.smartConnections:
        return

    board = model.components.board
    if not board:
        return  # Single-board validator will catch this

    pool = PinPool(board)

    # Mark pins already used by manual CONNECT blocks
    pool.mark_used_from_connections(model.connections)

    for sc in model.smartConnections:
        peripheral_inst = sc.target
        peripheral_ref = peripheral_inst.ref

        # Validate target is not a board
        if "Board" in type(peripheral_ref).__name__:
            raise_validation_error(
                sc,
                "SMARTCONNECT cannot target a board. " "Use SMARTCONNECT only for sensors and actuators.",
                "SmartConnect-Target",
            )
            continue

        # Resolve all pins
        power_conns, data_conns = _resolve_peripheral_pins(peripheral_ref, peripheral_inst, board, pool, sc)

        # Synthesize connection object
        synth = _synthesize_connection(sc, peripheral_inst, power_conns, data_conns)

        # Append to model.connections — enrichment loop will process it
        model.connections.append(synth)

        logger.info(
            "SmartConnect resolved '%s': %d power, %d data connections",
            peripheral_inst.name,
            len(power_conns),
            len(data_conns),
        )


def _resolve_peripheral_pins(peripheral_ref, peripheral_inst, board, pool, sc):
    """Resolve all pins for one peripheral.

    Returns:
        tuple: (power_conns, data_conns)
    """
    power_conns: list[Any] = []
    data_conns: list[Any] = []

    # Separate pins into power and IO
    power_pins = [p for p in peripheral_ref.pins if is_power_pin(p)]
    io_pins = [p for p in peripheral_ref.pins if is_io_pin(p)]

    # 1. Resolve power pins
    for ppin in power_pins:
        optional = is_optional(ppin)
        board_pin = pool.find_power_pin(ppin.ptype)

        if board_pin:
            pc = SimpleNamespace(fromPin=ppin.name, toPin=board_pin.name)
            copy_tx_location(sc, pc)
            power_conns.append(pc)
            pool.mark_used(board_pin.name, peripheral_inst.name, "POWER")
        elif not optional:
            raise_validation_error(
                sc,
                f"No available {ppin.ptype} board pin " f"for mandatory pin '{ppin.name}' of '{peripheral_inst.name}'.",
                "SmartConnect-Power",
            )

    # 2. Classify IO pins by protocol priority
    classified = classify_peripheral_io_pins(io_pins)

    # 3. Resolve by priority: I2C > SPI > UART > PWM > GPIO
    if classified["i2c"]:
        _resolve_i2c_pins(classified["i2c"], peripheral_inst, peripheral_ref, pool, sc, data_conns)

    if classified["spi"]:
        _resolve_spi_pins(classified["spi"], peripheral_inst, pool, sc, data_conns)

    if classified["uart"]:
        _resolve_uart_pins(classified["uart"], peripheral_inst, peripheral_ref, pool, sc, data_conns)

    if classified["pwm"]:
        _resolve_pwm_pins(classified["pwm"], peripheral_inst, pool, sc, data_conns)

    if classified["gpio"]:
        _resolve_gpio_pins(classified["gpio"], peripheral_inst, peripheral_ref, pool, sc, data_conns)

    return power_conns, data_conns


def _resolve_i2c_pins(i2c_pins, peripheral_inst, peripheral_ref, pool, sc, data_conns):
    """Resolve I2C pins. Requires i2c_address attribute on the peripheral."""
    slave_addr = get_instance_attribute(peripheral_inst, "i2c_address")
    if slave_addr is None:
        raise_validation_error(
            sc,
            f"Peripheral '{peripheral_inst.name}' uses I2C but has no "
            f"'i2c_address' attribute. Add i2c_address to its ATTRIBUTES section.",
            "SmartConnect-I2C",
        )
        return

    # Group pins by bus number
    buses: dict[int, list[Any]] = {}
    for pin, func in i2c_pins:
        bus = getattr(func, "bus", 0)
        buses.setdefault(bus, []).append((pin, func))

    for bus_num, pins_on_bus in buses.items():
        pin_mappings = []
        all_resolved = True

        for pin, func in pins_on_bus:
            optional = is_optional(pin)
            board_pin = pool.find_io_pin_by_function(func.ptype, bus=bus_num)

            if board_pin:
                pm = SimpleNamespace(
                    function=func.ptype,
                    fromPin=pin.name,
                    toPin=board_pin.name,
                )
                copy_tx_location(sc, pm)
                pin_mappings.append(pm)
                pool.mark_used(board_pin.name, peripheral_inst.name, f"I2C-{func.ptype.upper()}")
            elif not optional:
                raise_validation_error(
                    sc,
                    f"No available {func.ptype}-{bus_num} board pin " f"for '{pin.name}' of '{peripheral_inst.name}'.",
                    "SmartConnect-I2C",
                )
                all_resolved = False

        if pin_mappings and all_resolved:
            # Format slave_address as hex string for compatibility with existing validators
            addr_value = slave_addr
            if isinstance(addr_value, int):
                addr_value = hex(addr_value)

            dc = SimpleNamespace(
                type="i2c",
                props=[SimpleNamespace(name="slave_address", value=addr_value)],
                pins=pin_mappings,
            )
            copy_tx_location(sc, dc)
            data_conns.append(dc)


def _resolve_spi_pins(spi_pins, peripheral_inst, pool, sc, data_conns):
    """Resolve SPI pins."""
    # Group pins by bus number
    buses: dict[int, list[Any]] = {}
    for pin, func in spi_pins:
        bus = getattr(func, "bus", 0)
        buses.setdefault(bus, []).append((pin, func))

    for bus_num, pins_on_bus in buses.items():
        pin_mappings = []
        all_resolved = True

        for pin, func in pins_on_bus:
            optional = is_optional(pin)
            board_pin = pool.find_io_pin_by_function(func.ptype, bus=bus_num)

            if board_pin:
                pm = SimpleNamespace(
                    function=func.ptype,
                    fromPin=pin.name,
                    toPin=board_pin.name,
                )
                copy_tx_location(sc, pm)
                pin_mappings.append(pm)
                pool.mark_used(board_pin.name, peripheral_inst.name, "SPI")
            elif not optional:
                raise_validation_error(
                    sc,
                    f"No available {func.ptype}-{bus_num} board pin " f"for '{pin.name}' of '{peripheral_inst.name}'.",
                    "SmartConnect-SPI",
                )
                all_resolved = False

        if pin_mappings and all_resolved:
            dc = SimpleNamespace(
                type="spi",
                props=[],
                pins=pin_mappings,
            )
            copy_tx_location(sc, dc)
            data_conns.append(dc)


def _resolve_uart_pins(uart_pins, peripheral_inst, peripheral_ref, pool, sc, data_conns):
    """Resolve UART pins with TX/RX crossover.

    UART crossover: peripheral TX connects to board RX line,
    peripheral RX connects to board TX line.
    """
    baudrate = get_instance_attribute(peripheral_inst, "uart_baudrate")
    if baudrate is None:
        baudrate = 9600  # Default

    # Group pins by bus number
    buses: dict[int, list[Any]] = {}
    for pin, func in uart_pins:
        bus = getattr(func, "bus", 0)
        buses.setdefault(bus, []).append((pin, func))

    for bus_num, pins_on_bus in buses.items():
        pin_mappings = []
        all_resolved = True

        for pin, func in pins_on_bus:
            optional = is_optional(pin)
            # CROSSOVER: peripheral TX needs board RX, peripheral RX needs board TX
            board_func_type = "rx" if func.ptype == "tx" else "tx"
            board_pin = pool.find_io_pin_by_function(board_func_type, bus=bus_num)

            if board_pin:
                pm = SimpleNamespace(
                    function=func.ptype,
                    fromPin=pin.name,
                    toPin=board_pin.name,
                )
                copy_tx_location(sc, pm)
                pin_mappings.append(pm)
                pool.mark_used(board_pin.name, peripheral_inst.name, "UART")
            elif not optional:
                raise_validation_error(
                    sc,
                    f"No available {board_func_type}-{bus_num} board pin "
                    f"for '{pin.name}' of '{peripheral_inst.name}'.",
                    "SmartConnect-UART",
                )
                all_resolved = False

        if pin_mappings and all_resolved:
            dc = SimpleNamespace(
                type="uart",
                props=[SimpleNamespace(name="baudrate", value=baudrate)],
                pins=pin_mappings,
            )
            copy_tx_location(sc, dc)
            data_conns.append(dc)


def _resolve_pwm_pins(pwm_pins, peripheral_inst, pool, sc, data_conns):
    """Resolve PWM pins."""
    for pin, func in pwm_pins:
        optional = is_optional(pin)
        channel = getattr(func, "channel", None)
        board_pin = pool.find_pwm_pin(channel=channel)

        if board_pin:
            dc = SimpleNamespace(
                type="pwm",
                props=[],
                pins=[SimpleNamespace(fromPin=pin.name, toPin=board_pin.name)],
            )
            copy_tx_location(sc, dc)
            data_conns.append(dc)
            pool.mark_used(board_pin.name, peripheral_inst.name, "PWM")
        elif not optional:
            raise_validation_error(
                sc,
                f"No available PWM board pin " f"for '{pin.name}' of '{peripheral_inst.name}'.",
                "SmartConnect-PWM",
            )


def _get_gpio_modes(peripheral_ref):
    """Extract per-pin GPIO mode overrides from gpio_modes dict attribute."""
    gpio_modes_attr = get_peripheral_attribute(peripheral_ref, "gpio_modes")
    if gpio_modes_attr is None:
        return {}
    if hasattr(gpio_modes_attr, "items"):
        return {item.key: item.value for item in gpio_modes_attr.items}
    return {}


def _resolve_gpio_pins(gpio_pins, peripheral_inst, peripheral_ref, pool, sc, data_conns):
    """Resolve GPIO pins. Mode from gpio_modes attribute, falling back to type inference."""
    default_mode = infer_gpio_mode(peripheral_ref)
    pin_modes = _get_gpio_modes(peripheral_ref)

    for pin, func in gpio_pins:
        optional = is_optional(pin)
        board_pin = pool.find_gpio_pin()
        mode = pin_modes.get(pin.name, default_mode)

        if board_pin:
            dc = SimpleNamespace(
                type="gpio",
                props=[SimpleNamespace(name="mode", value=mode)],
                pins=[SimpleNamespace(fromPin=pin.name, toPin=board_pin.name)],
            )
            copy_tx_location(sc, dc)
            data_conns.append(dc)
            pool.mark_used(board_pin.name, peripheral_inst.name, "GPIO")
        elif not optional:
            raise_validation_error(
                sc,
                f"No available GPIO board pin " f"for '{pin.name}' of '{peripheral_inst.name}'.",
                "SmartConnect-GPIO",
            )


def _synthesize_connection(sc, peripheral_inst, power_conns, data_conns):
    """Create a SimpleNamespace that looks like a textX Connect object.

    The enrichment loop in enrich_model() processes this identically
    to a real Connect object because:
    - from_comp is a real ComponentInstance (sc.target)
    - to_comp is None (defaults to board)
    - powerConns and dataConns have correct shape
    """
    conn = SimpleNamespace(
        from_comp=peripheral_inst,
        to_comp=None,
        powerConns=power_conns,
        dataConns=data_conns,
        remote=getattr(sc, "remote", None),
        _is_smart_connection=True,
    )
    copy_tx_location(sc, conn)
    return conn
