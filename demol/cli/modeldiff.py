"""Semantic model diff for DeMoL .dev files.

Parses two models and compares their structure at the domain level:
peripherals, connections, brokers, sampling, constraints, alerts.
"""

import warnings
from typing import Dict, List, Any, Optional, Tuple


def _safe_model(filepath):
    from demol.lang import get_device_mm

    mm = get_device_mm(skip_semantics=True)
    with warnings.catch_warnings(record=True):
        warnings.simplefilter("always")
        return mm.model_from_file(filepath)


def _peripheral_map(model) -> Dict[str, Any]:
    peripherals = getattr(getattr(model, "components", None), "peripherals", [])
    result = {}
    for p in peripherals:
        name = getattr(p, "name", None)
        if name:
            ref = getattr(p, "ref", None)
            result[name] = {
                "type": ref.__class__.__name__ if ref else "unknown",
                "ref_name": getattr(ref, "name", "unknown") if ref else "unknown",
            }
    return result


def _broker_map(model) -> Dict[str, Dict]:
    brokers = getattr(model, "brokers", [])
    result = {}
    for b in brokers:
        name = getattr(b, "name", "")
        result[name] = {
            "host": getattr(b, "host", ""),
            "port": getattr(b, "port", 0),
            "type": b.__class__.__name__,
        }
    return result


def _connection_set(model) -> Dict[str, Dict]:
    connections = getattr(model, "connections", [])
    result = {}
    for c in connections:
        from_comp = getattr(c, "from_comp", None)
        name = getattr(from_comp, "name", "unknown") if from_comp else "unknown"
        remote = getattr(c, "remote", "")
        via = getattr(c, "via", None)
        data_types = []
        for dc in getattr(c, "dataConns", []):
            data_types.append(getattr(dc, "type", "?"))
        result[name] = {
            "topic": remote or "",
            "via": via,
            "protocols": data_types,
        }
    return result


def _sampling_map(model) -> Dict[str, Dict]:
    samplings = getattr(model, "samplings", [])
    result = {}
    for s in samplings:
        target = getattr(s, "target", None)
        name = getattr(target, "name", "unknown") if target else "unknown"
        result[name] = {
            "rate": getattr(s, "rate", 0),
            "rate_unit": str(getattr(s, "rate_unit", "")),
            "mode": getattr(s, "mode", None),
            "buffer": getattr(s, "buffer", 0),
            "threshold": getattr(s, "threshold", 0),
        }
    return result


def _alert_map(model) -> Dict[str, Dict]:
    alerts = getattr(model, "alerts", [])
    result = {}
    for a in alerts:
        name = getattr(a, "name", "")
        source = getattr(a, "source", None)
        source_name = getattr(source, "name", "unknown") if source else "unknown"
        result[name] = {
            "source": source_name,
            "actions": len(getattr(a, "actions", [])),
            "cooldown": getattr(a, "cooldown", 0),
        }
    return result


def _constraint_map(model) -> Dict[str, Dict]:
    constraints = getattr(model, "constraints", [])
    result = {}
    for c in constraints:
        name = getattr(c, "name", "")
        message = getattr(c, "message", None)
        result[name] = {"message": message or ""}
    return result


def _device_meta(model) -> Dict:
    meta = getattr(model, "metadata", None)
    if not meta:
        return {}
    return {
        "name": getattr(meta, "name", ""),
        "description": getattr(meta, "description", ""),
        "author": getattr(meta, "author", ""),
        "os": str(getattr(meta, "os", "")),
    }


def _diff_dicts(label, a_map, b_map):
    """Compare two dict-of-dicts and return diff entries."""
    diffs = []
    a_keys = set(a_map.keys())
    b_keys = set(b_map.keys())

    for key in sorted(a_keys - b_keys):
        diffs.append(("removed", label, key, a_map[key], None))

    for key in sorted(b_keys - a_keys):
        diffs.append(("added", label, key, None, b_map[key]))

    for key in sorted(a_keys & b_keys):
        if a_map[key] != b_map[key]:
            diffs.append(("changed", label, key, a_map[key], b_map[key]))

    return diffs


DiffEntry = Tuple[str, str, str, Optional[Dict], Optional[Dict]]


def compute_diff(filepath_a: str, filepath_b: str) -> List[DiffEntry]:
    """Compute the semantic diff between two .dev models.

    Returns a list of (action, category, name, old, new) tuples.
    action is one of: 'added', 'removed', 'changed'.
    """
    model_a = _safe_model(filepath_a)
    model_b = _safe_model(filepath_b)

    diffs: List[DiffEntry] = []

    meta_a = _device_meta(model_a)
    meta_b = _device_meta(model_b)
    if meta_a != meta_b:
        diffs.append(("changed", "Device", "metadata", meta_a, meta_b))

    board_a = getattr(getattr(model_a, "components", None), "board", None)
    board_b = getattr(getattr(model_b, "components", None), "board", None)
    name_a = getattr(board_a, "name", None) if board_a else None
    name_b = getattr(board_b, "name", None) if board_b else None
    if name_a != name_b:
        diffs.append(
            (
                "changed",
                "Board",
                "board",
                {"name": name_a},
                {"name": name_b},
            )
        )

    diffs.extend(_diff_dicts("Peripheral", _peripheral_map(model_a), _peripheral_map(model_b)))
    diffs.extend(_diff_dicts("Connection", _connection_set(model_a), _connection_set(model_b)))
    diffs.extend(_diff_dicts("Broker", _broker_map(model_a), _broker_map(model_b)))
    diffs.extend(_diff_dicts("Sampling", _sampling_map(model_a), _sampling_map(model_b)))
    diffs.extend(_diff_dicts("Alert", _alert_map(model_a), _alert_map(model_b)))
    diffs.extend(_diff_dicts("Constraint", _constraint_map(model_a), _constraint_map(model_b)))

    return diffs
