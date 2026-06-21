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
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any, Callable

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


# ============================================================================
# ProtocolSpec dispatcher (P0 refactor — replaces 5 hand-rolled resolvers)
# ============================================================================


@dataclass(frozen=True)
class ProtocolSpec:
    """Per-protocol configuration driving the unified dispatcher.

    Fields:
        name: protocol identifier ("i2c"/"spi"/"uart"/"pwm"/"gpio").
        find_pin: callable(pool, pin, func, bus, channel) -> board_pin.
        map_function: callable(func.ptype) -> board-side function name
            (UART inverts tx<->rx; others are identity).
        build_props: callable(pin, peripheral_inst, func) -> list[SimpleNamespace].
        group_by_bus: True for bus-grouped protocols (I2C/SPI/UART), False for per-pin (PWM/GPIO).
        all_resolved_gate: True if the DC is suppressed when any mandatory pin
            fails to resolve; False if a DC is emitted per successful pin.
        mark_label: callable(func) -> label string for pool.mark_used
            (e.g. lambda f: f"I2C-{f.ptype.upper()}" for I2C).
        build_dc: callable(spec, pin_mappings, props) -> SimpleNamespace dc.
    """

    name: str
    find_pin: Callable
    map_function: Callable
    build_props: Callable
    group_by_bus: bool
    all_resolved_gate: bool
    mark_label: Callable
    build_dc: Callable


def _find_io_pin(pool, pin, func, bus=None, channel=None):
    return pool.find_io_pin_by_function(func.ptype, bus=bus)


def _find_uart_pin(pool, pin, func, bus=None, channel=None):
    board_func_type = "rx" if func.ptype == "tx" else "tx"
    return pool.find_io_pin_by_function(board_func_type, bus=bus)


def _find_pwm_pin(pool, pin, func, bus=None, channel=None):
    return pool.find_pwm_pin(channel=getattr(func, "channel", None))


def _find_gpio_pin(pool, pin, func, bus=None, channel=None):
    return pool.find_gpio_pin()


def _i2c_props(pin, peripheral_inst, func):
    addr = get_instance_attribute(peripheral_inst, "i2c_address")
    if isinstance(addr, int):
        addr = hex(addr)
    return [SimpleNamespace(name="slave_address", value=addr)]


def _uart_props(pin, peripheral_inst, func):
    baud = get_instance_attribute(peripheral_inst, "uart_baudrate")
    if baud is None:
        baud = 9600
    return [SimpleNamespace(name="baudrate", value=baud)]


def _gpio_props(pin, peripheral_inst, func):
    peripheral_ref = peripheral_inst.ref
    default_mode = infer_gpio_mode(peripheral_ref)
    pin_modes = _get_gpio_modes(peripheral_ref)
    return [SimpleNamespace(name="mode", value=pin_modes.get(pin.name, default_mode))]


def _empty_props(pin, peripheral_inst, func):
    return []


def _build_dc(spec, pin_mappings, props):
    return SimpleNamespace(type=spec.name, props=props, pins=pin_mappings)


_I2C_SPEC = ProtocolSpec(
    name="i2c",
    find_pin=_find_io_pin,
    map_function=lambda ptype: ptype,
    build_props=_i2c_props,
    group_by_bus=True,
    all_resolved_gate=True,
    mark_label=lambda func: f"I2C-{func.ptype.upper()}",
    build_dc=_build_dc,
)

_SPI_SPEC = ProtocolSpec(
    name="spi",
    find_pin=_find_io_pin,
    map_function=lambda ptype: ptype,
    build_props=_empty_props,
    group_by_bus=True,
    all_resolved_gate=True,
    mark_label=lambda func: "SPI",
    build_dc=_build_dc,
)

_UART_SPEC = ProtocolSpec(
    name="uart",
    find_pin=_find_uart_pin,
    map_function=lambda ptype: "rx" if ptype == "tx" else "tx",
    build_props=_uart_props,
    group_by_bus=True,
    all_resolved_gate=True,
    mark_label=lambda func: "UART",
    build_dc=_build_dc,
)

_PWM_SPEC = ProtocolSpec(
    name="pwm",
    find_pin=_find_pwm_pin,
    map_function=lambda ptype: ptype,
    build_props=_empty_props,
    group_by_bus=False,
    all_resolved_gate=False,
    mark_label=lambda func: "PWM",
    build_dc=_build_dc,
)

_GPIO_SPEC = ProtocolSpec(
    name="gpio",
    find_pin=_find_gpio_pin,
    map_function=lambda ptype: ptype,
    build_props=_gpio_props,
    group_by_bus=False,
    all_resolved_gate=False,
    mark_label=lambda func: "GPIO",
    build_dc=_build_dc,
)


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
        _resolve_pins_with_spec(_I2C_SPEC, classified["i2c"], peripheral_inst, peripheral_ref, pool, sc, data_conns)

    if classified["spi"]:
        _resolve_pins_with_spec(_SPI_SPEC, classified["spi"], peripheral_inst, peripheral_ref, pool, sc, data_conns)

    if classified["uart"]:
        _resolve_pins_with_spec(_UART_SPEC, classified["uart"], peripheral_inst, peripheral_ref, pool, sc, data_conns)

    if classified["pwm"]:
        _resolve_pins_with_spec(_PWM_SPEC, classified["pwm"], peripheral_inst, peripheral_ref, pool, sc, data_conns)

    if classified["gpio"]:
        _resolve_pins_with_spec(_GPIO_SPEC, classified["gpio"], peripheral_inst, peripheral_ref, pool, sc, data_conns)

    return power_conns, data_conns


def _resolve_pins_with_spec(spec, pins, peripheral_inst, peripheral_ref, pool, sc, data_conns):
    if not pins:
        return

    if spec.name == "i2c":
        slave_addr = get_instance_attribute(peripheral_inst, "i2c_address")
        if slave_addr is None:
            raise_validation_error(
                sc,
                f"Peripheral '{peripheral_inst.name}' uses I2C but has no "
                f"'i2c_address' attribute. Add i2c_address to its ATTRIBUTES section.",
                f"SmartConnect-{spec.name.upper()}",
            )
            return

    if spec.group_by_bus:
        buses = {}
        for pin, func in pins:
            bus = getattr(func, "bus", 0)
            buses.setdefault(bus, []).append((pin, func))

        for bus_num, pins_on_bus in buses.items():
            pin_mappings = []
            all_resolved = True
            for pin, func in pins_on_bus:
                optional = is_optional(pin)
                channel = getattr(func, "channel", None)
                board_pin = spec.find_pin(pool, pin, func, bus=bus_num, channel=channel)
                if board_pin:
                    pm = SimpleNamespace(function=func.ptype, fromPin=pin.name, toPin=board_pin.name)
                    copy_tx_location(sc, pm)
                    pin_mappings.append(pm)
                    pool.mark_used(board_pin.name, peripheral_inst.name, spec.mark_label(func))
                elif not optional:
                    raise_validation_error(
                        sc,
                        f"No available {spec.map_function(func.ptype)}-{bus_num} board pin "
                        f"for '{pin.name}' of '{peripheral_inst.name}'.",
                        f"SmartConnect-{spec.name.upper()}",
                    )
                    all_resolved = False

            if spec.all_resolved_gate and not all_resolved:
                continue
            if not pin_mappings:
                continue
            first_pin, first_func = pins_on_bus[0]
            props = spec.build_props(first_pin, peripheral_inst, first_func)
            dc = spec.build_dc(spec, pin_mappings, props)
            copy_tx_location(sc, dc)
            data_conns.append(dc)
    else:
        for pin, func in pins:
            optional = is_optional(pin)
            channel = getattr(func, "channel", None)
            board_pin = spec.find_pin(pool, pin, func, channel=channel)
            if board_pin:
                props = spec.build_props(pin, peripheral_inst, func)
                dc = spec.build_dc(spec, [SimpleNamespace(fromPin=pin.name, toPin=board_pin.name)], props)
                copy_tx_location(sc, dc)
                data_conns.append(dc)
                pool.mark_used(board_pin.name, peripheral_inst.name, spec.mark_label(func))
            elif not optional:
                raise_validation_error(
                    sc,
                    f"No available {spec.name.upper()} board pin " f"for '{pin.name}' of '{peripheral_inst.name}'.",
                    f"SmartConnect-{spec.name.upper()}",
                )


def _get_gpio_modes(peripheral_ref):
    """Extract per-pin GPIO mode overrides from gpio_modes dict attribute."""
    gpio_modes_attr = get_peripheral_attribute(peripheral_ref, "gpio_modes")
    if gpio_modes_attr is None:
        return {}
    if hasattr(gpio_modes_attr, "items"):
        return {item.key: item.value for item in gpio_modes_attr.items}
    return {}


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
