"""Power budget validator.

Rules:
- [Safety-Power-Budget]: Sum of peripheral power.max must not exceed board supply.
- [Info-Battery-Runtime]: When POWERSOURCE declared, estimate runtime as capacity/avg_current.

Emits warnings (not errors) because power values are theoretical datasheet maximums.
"""

import logging
from ..core import raise_validation_warning
from ..utils import parse_voltage
from .base import BaseValidator

logger = logging.getLogger(__name__)

DEFAULT_BOARD_MAX_CURRENT_A = {
    5.0: 1.5,
    3.3: 0.5,
    12.0: 2.0,
}


def _parse_power_mw(power_consumption):
    if power_consumption is None:
        return None

    value = getattr(power_consumption, "value", None)
    unit = getattr(power_consumption, "unit", None)

    if value is None or unit is None:
        return None

    value = float(value)
    unit_lower = str(unit).lower()

    if unit_lower == "w":
        return value * 1000.0
    elif unit_lower == "mw":
        return value
    elif unit_lower == "uw":
        return value / 1000.0

    return None


def _parse_capacity_mah(operational):
    capacity = getattr(operational, "capacity", None)
    capacity_unit = getattr(operational, "capacity_unit", None)

    if capacity is None or capacity_unit is None:
        return None

    capacity = float(capacity)
    unit_lower = str(capacity_unit).lower()

    if unit_lower == "mah":
        return capacity
    elif unit_lower == "ah":
        return capacity * 1000.0
    elif unit_lower == "wh":
        voltage = getattr(operational, "voltage", None)
        if voltage:
            v = parse_voltage(str(voltage))
            if v and v > 0:
                return (capacity * 1000.0) / v
        return None

    return None


def _get_peripheral_supply_budget_mw(board):
    """Estimate how much power the board can supply to peripherals.

    peripheral_budget = (VCC * max_rail_current) - board_own_consumption
    """
    op = getattr(board, "operational", None)
    if op is None:
        return None

    vcc_str = getattr(op, "vcc", None)
    if not vcc_str:
        return None

    vcc = parse_voltage(str(vcc_str))
    if not vcc or vcc <= 0:
        return None

    max_current = DEFAULT_BOARD_MAX_CURRENT_A.get(vcc, 1.0)
    total_rail_mw = vcc * max_current * 1000.0

    board_own_avg = _parse_power_mw(getattr(op, "avg", None))
    if board_own_avg is not None:
        return total_rail_mw - board_own_avg

    board_own_max = _parse_power_mw(getattr(op, "max", None))
    if board_own_max is not None:
        return total_rail_mw - board_own_max

    return total_rail_mw


class PowerBudgetValidator(BaseValidator):
    @staticmethod
    def get_name() -> str:
        return "Power Budget Analysis"

    @staticmethod
    def get_description() -> str:
        return (
            "Validates total peripheral power consumption against board supply "
            "capability and estimates battery runtime"
        )

    @staticmethod
    def validate(model, **kwargs):
        board = getattr(model.components, "board", None)
        if board is None:
            return

        peripherals = getattr(model.components, "peripherals", [])
        if not peripherals:
            return

        total_max_mw = 0.0
        total_avg_mw = 0.0
        periph_count = 0
        peripherals_with_power = []

        for periph in peripherals:
            ref = periph.ref if hasattr(periph, "ref") else periph
            op = getattr(ref, "operational", None)
            if op is None:
                continue

            p_max = _parse_power_mw(getattr(op, "max", None))
            p_avg = _parse_power_mw(getattr(op, "avg", None))

            if p_max is not None:
                total_max_mw += p_max
                periph_count += 1
                peripherals_with_power.append((getattr(periph, "name", ref.name), p_max, p_avg))

            if p_avg is not None:
                total_avg_mw += p_avg

        if periph_count == 0:
            return

        board_max_mw = _get_peripheral_supply_budget_mw(board)

        if board_max_mw is not None and total_max_mw > board_max_mw:
            breakdown = ", ".join(f"{name}={p_max:.1f}mW" for name, p_max, _ in peripherals_with_power)

            raise_validation_warning(
                model.metadata,
                f"[Safety-Power-Budget] Total peripheral peak power "
                f"({total_max_mw:.1f}mW) exceeds board supply capability "
                f"({board_max_mw:.1f}mW). "
                f"Breakdown: {breakdown}. "
                f"Consider using an external power supply or reducing "
                f"peripheral count.",
                "PowerBudgetWarning",
            )

        power_sources = getattr(model.components, "powerSources", [])
        if not power_sources:
            return

        for ps in power_sources:
            ps_ref = ps.ref if hasattr(ps, "ref") else ps
            ps_op = getattr(ps_ref, "operational", None)
            if ps_op is None:
                continue

            capacity_mah = _parse_capacity_mah(ps_op)
            if capacity_mah is None:
                continue

            voltage_attr = getattr(ps_op, "voltage", None)
            ps_voltage = parse_voltage(str(voltage_attr)) if voltage_attr else None
            if ps_voltage is None or ps_voltage <= 0:
                continue

            if total_avg_mw > 0:
                avg_current_ma = total_avg_mw / ps_voltage
                runtime_hours = capacity_mah / avg_current_ma

                if runtime_hours < 1.0:
                    runtime_str = f"{runtime_hours * 60:.0f} minutes"
                else:
                    runtime_str = f"{runtime_hours:.1f} hours"

                ps_name = getattr(ps, "name", ps_ref.name)

                raise_validation_warning(
                    model.metadata,
                    f"[Info-Battery-Runtime] Estimated runtime on "
                    f"'{ps_name}' ({capacity_mah:.0f}mAh): {runtime_str} "
                    f"(avg draw: {avg_current_ma:.0f}mA at {ps_voltage}V, "
                    f"total avg power: {total_avg_mw:.1f}mW).",
                    "BatteryRuntimeInfo",
                )


def validate_power_budget(model):
    PowerBudgetValidator.validate(model)


def analyze_power_budget(model):
    """Extract structured power analysis data from a parsed model.

    Returns a dict with keys:
        board: {name, vcc, power_min, power_max, power_avg, supply_budget_mw}
        peripherals: [{name, type, power_max, power_avg}]
        totals: {max_mw, avg_mw, count}
        budget: {supply_mw, exceeded, headroom_mw}
        power_sources: [{name, type, voltage, capacity_mah, runtime_hours, avg_current_ma}]
    """
    result = {
        "board": None,
        "peripherals": [],
        "totals": {"max_mw": 0.0, "avg_mw": 0.0, "count": 0},
        "budget": {"supply_mw": None, "exceeded": False, "headroom_mw": None},
        "power_sources": [],
    }

    board = getattr(model.components, "board", None)
    if board is None:
        return result

    op = getattr(board, "operational", None)
    board_info = {
        "name": board.name,
        "vcc": None,
        "power_min": None,
        "power_max": None,
        "power_avg": None,
        "supply_budget_mw": None,
    }
    if op:
        vcc_str = getattr(op, "vcc", None)
        board_info["vcc"] = parse_voltage(str(vcc_str)) if vcc_str else None
        board_info["power_min"] = _parse_power_mw(getattr(op, "min", None))
        board_info["power_max"] = _parse_power_mw(getattr(op, "max", None))
        board_info["power_avg"] = _parse_power_mw(getattr(op, "avg", None))
        board_info["supply_budget_mw"] = _get_peripheral_supply_budget_mw(board)
    result["board"] = board_info

    peripherals = getattr(model.components, "peripherals", [])
    total_max = 0.0
    total_avg = 0.0
    count = 0

    for periph in peripherals:
        ref = periph.ref if hasattr(periph, "ref") else periph
        p_op = getattr(ref, "operational", None)
        p_max = _parse_power_mw(getattr(p_op, "max", None)) if p_op else None
        p_avg = _parse_power_mw(getattr(p_op, "avg", None)) if p_op else None
        p_min = _parse_power_mw(getattr(p_op, "min", None)) if p_op else None

        name = getattr(periph, "name", ref.name)
        ref_class = type(ref).__name__

        entry = {
            "name": name,
            "type": ref_class,
            "ref_name": ref.name,
            "power_min": p_min,
            "power_max": p_max,
            "power_avg": p_avg,
        }
        result["peripherals"].append(entry)

        if p_max is not None:
            total_max += p_max
            count += 1
        if p_avg is not None:
            total_avg += p_avg

    result["totals"] = {"max_mw": total_max, "avg_mw": total_avg, "count": count}

    supply = board_info["supply_budget_mw"]
    if supply is not None:
        result["budget"] = {
            "supply_mw": supply,
            "exceeded": total_max > supply,
            "headroom_mw": supply - total_max,
        }

    power_sources = getattr(model.components, "powerSources", [])
    for ps in power_sources:
        ps_ref = ps.ref if hasattr(ps, "ref") else ps
        ps_op = getattr(ps_ref, "operational", None)
        if ps_op is None:
            continue

        capacity_mah = _parse_capacity_mah(ps_op)
        voltage_attr = getattr(ps_op, "voltage", None)
        ps_voltage = parse_voltage(str(voltage_attr)) if voltage_attr else None
        max_current = getattr(ps_op, "max_current", None)
        max_current_val = float(max_current) if max_current else None
        max_current_unit = getattr(ps_op, "max_current_unit", None)

        runtime_hours = None
        avg_current_ma = None
        if capacity_mah and ps_voltage and ps_voltage > 0 and total_avg > 0:
            avg_current_ma = total_avg / ps_voltage
            runtime_hours = capacity_mah / avg_current_ma

        ps_name = getattr(ps, "name", ps_ref.name)
        ps_type = getattr(ps_ref, "type", "Unknown")

        ps_entry = {
            "name": ps_name,
            "type": str(ps_type),
            "voltage": ps_voltage,
            "capacity_mah": capacity_mah,
            "max_current_ma": (
                max_current_val * 1000.0
                if max_current_val and max_current_unit and str(max_current_unit).lower() == "a"
                else (max_current_val if max_current_val else None)
            ),
            "runtime_hours": runtime_hours,
            "avg_current_ma": avg_current_ma,
        }
        result["power_sources"].append(ps_entry)

    return result


__all__ = [
    "PowerBudgetValidator",
    "validate_power_budget",
    "analyze_power_budget",
]
