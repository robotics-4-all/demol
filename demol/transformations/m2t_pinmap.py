"""
m2t_pinmap.py
Generates pin-mapping reports (Markdown + JSON) from DeMoL device models.

Shows the resolved pin assignments for all connections, including
SmartConnect auto-assigned pins that are not visible in the model source.
"""

import json
import logging
import os
from typing import Any, Dict, List, Tuple

logger = logging.getLogger(__name__)


def _is_from_board(connection, board) -> bool:
    """Check if from_comp is the board."""
    from_ref = getattr(connection, "_from_ref", None)
    return from_ref is board


def _get_board_and_periph_pin(connection, pin_map, board) -> Tuple[str, str]:
    """Return (board_pin_name, peripheral_pin_name) for a pin mapping."""
    if _is_from_board(connection, board):
        return pin_map.fromPin, pin_map.toPin
    else:
        return pin_map.toPin, pin_map.fromPin


def _get_pin_number(board_pins_map: Dict[str, Any], pin_name: str) -> int:
    """Get the physical pin number for a board pin name."""
    pin = board_pins_map.get(pin_name)
    if pin and hasattr(pin, "number"):
        return pin.number
    return -1


def _get_power_type(board_pins_map: Dict[str, Any], pin_name: str) -> str:
    """Get the voltage type for a board power pin."""
    pin = board_pins_map.get(pin_name)
    if pin and hasattr(pin, "ptype"):
        return str(pin.ptype)
    return ""


def _extract_props(data_conn) -> Dict[str, Any]:
    """Extract protocol properties from a data connection."""
    props = {}
    for prop in data_conn.props:
        val = prop.value
        if isinstance(val, str) and val.lower().startswith("0x"):
            props[prop.name] = val
        else:
            props[prop.name] = val
    return props


def _format_props(props: Dict[str, Any]) -> str:
    """Format properties dict for Markdown display."""
    if not props:
        return ""
    parts = []
    for k, v in props.items():
        if isinstance(v, str):
            parts.append(f'{k}="{v}"')
        else:
            parts.append(f"{k}={v}")
    return ", ".join(parts)


def _build_connection_data(model) -> List[Dict[str, Any]]:
    """Build structured pin-mapping data from the enriched model."""
    board = model.components.board
    board_pins_map = {pin.name: pin for pin in board.pins}
    result = []

    for conn in model.connections:
        is_smart = getattr(conn, "_is_smart_connection", False)

        # Get peripheral info
        peripheral_inst = getattr(conn, "peripheral", None)
        if not peripheral_inst:
            continue

        periph_name = (
            peripheral_inst.name
            if hasattr(peripheral_inst, "name")
            else str(peripheral_inst)
        )
        periph_ref = (
            peripheral_inst.ref if hasattr(peripheral_inst, "ref") else peripheral_inst
        )
        periph_type = (
            periph_ref.name if hasattr(periph_ref, "name") else str(periph_ref)
        )
        topic = getattr(conn, "remote", None) or ""

        entry = {
            "peripheral": periph_name,
            "peripheral_type": periph_type,
            "source": "smartconnect" if is_smart else "manual",
            "topic": topic,
            "power": [],
            "data": [],
        }

        # Power connections
        for pc in conn.powerConns:
            board_pin, periph_pin = _get_board_and_periph_pin(conn, pc, board)
            pin_num = _get_pin_number(board_pins_map, board_pin)
            ptype = _get_power_type(board_pins_map, board_pin)
            entry["power"].append(
                {
                    "peripheral_pin": periph_pin,
                    "board_pin": board_pin,
                    "board_pin_number": pin_num,
                    "type": ptype,
                }
            )

        # Data connections
        for dc in conn.dataConns:
            protocol = dc.type
            props = _extract_props(dc)

            for pin_map in dc.pins:
                board_pin, periph_pin = _get_board_and_periph_pin(conn, pin_map, board)
                pin_num = _get_pin_number(board_pins_map, board_pin)
                func = getattr(pin_map, "function", "")
                entry["data"].append(
                    {
                        "peripheral_pin": periph_pin,
                        "board_pin": board_pin,
                        "board_pin_number": pin_num,
                        "protocol": protocol,
                        "function": func,
                        "properties": props,
                    }
                )

        result.append(entry)

    return result


def _generate_markdown(model, connections_data: List[Dict[str, Any]]) -> str:
    """Generate Markdown pin-mapping report."""
    board = model.components.board
    device_name = model.metadata.name
    author = getattr(model.metadata, "author", "")

    lines = []
    lines.append(f"# Pin Mapping: {device_name}")
    lines.append("")
    lines.append(f"**Board:** {board.name}")
    if author:
        lines.append(f"**Author:** {author}")
    lines.append(f"**Connections:** {len(connections_data)}")
    lines.append("")

    protocols_used = set()
    total_power = 0
    total_data = 0

    for entry in connections_data:
        source_badge = " 🔌 `SmartConnect`" if entry["source"] == "smartconnect" else ""
        lines.append(
            f"## {entry['peripheral']} ({entry['peripheral_type']}){source_badge}"
        )
        lines.append("")
        if entry["topic"]:
            lines.append(f"**Topic:** `{entry['topic']}`")
            lines.append("")

        # Power table
        if entry["power"]:
            lines.append("### Power")
            lines.append("")
            lines.append("| Peripheral Pin | Board Pin | Pin # | Type |")
            lines.append("|----------------|-----------|-------|------|")
            for p in entry["power"]:
                pin_num = p["board_pin_number"] if p["board_pin_number"] >= 0 else "?"
                lines.append(
                    f"| {p['peripheral_pin']} | {p['board_pin']} | {pin_num} | {p['type']} |"
                )
            lines.append("")
            total_power += len(entry["power"])

        # Data table
        if entry["data"]:
            lines.append("### Data")
            lines.append("")
            lines.append(
                "| Peripheral Pin | Board Pin | Pin # | Protocol | Function | Properties |"
            )
            lines.append(
                "|----------------|-----------|-------|----------|----------|------------|"
            )
            for d in entry["data"]:
                pin_num = d["board_pin_number"] if d["board_pin_number"] >= 0 else "?"
                proto = d["protocol"].upper()
                func = d["function"]
                props_str = _format_props(d["properties"])
                lines.append(
                    f"| {d['peripheral_pin']} | {d['board_pin']} | {pin_num} | {proto} | {func} | {props_str} |"
                )
                protocols_used.add(proto)
            lines.append("")
            total_data += len(entry["data"])

    # Summary
    lines.append("---")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"| Metric | Count |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Peripherals | {len(connections_data)} |")
    lines.append(f"| Power connections | {total_power} |")
    lines.append(f"| Data connections | {total_data} |")
    lines.append(
        f"| Protocols | {', '.join(sorted(protocols_used)) if protocols_used else 'none'} |"
    )

    smart_count = sum(1 for e in connections_data if e["source"] == "smartconnect")
    manual_count = len(connections_data) - smart_count
    lines.append(f"| Manual connections | {manual_count} |")
    lines.append(f"| SmartConnect resolved | {smart_count} |")
    lines.append("")

    return "\n".join(lines)


def _generate_json(model, connections_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate JSON pin-mapping data."""
    board = model.components.board
    return {
        "device": model.metadata.name,
        "board": board.name,
        "author": getattr(model.metadata, "author", ""),
        "connections": connections_data,
    }


def generate_pinmap(model, output_dir="."):
    """Generate pin-mapping report (Markdown + JSON) from device model.

    Produces two files in the output directory:
    - {device_name}_pinmap.md  — Human-readable pin mapping tables
    - {device_name}_pinmap.json — Machine-readable structured data

    Args:
        model: Parsed and enriched textX device model
        output_dir: Output directory (created if needed)

    Returns:
        List of generated file paths
    """
    if output_dir != "." and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    device_name = model.metadata.name
    connections_data = _build_connection_data(model)

    generated_files = []

    # Markdown report
    md_content = _generate_markdown(model, connections_data)
    md_path = os.path.join(output_dir, f"{device_name}_pinmap.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    logger.info(f"Generated pin-mapping report: {md_path}")
    generated_files.append(md_path)

    # JSON report
    json_data = _generate_json(model, connections_data)
    json_path = os.path.join(output_dir, f"{device_name}_pinmap.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=2, default=str)
    logger.info(f"Generated pin-mapping JSON: {json_path}")
    generated_files.append(json_path)

    return generated_files
