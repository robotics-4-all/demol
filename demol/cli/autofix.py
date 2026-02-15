"""Auto-fix engine for common DeMoL validation errors.

Reads a .dev file, detects fixable problems, and writes the corrected file.
Each fixer operates on the raw text lines so it works even when the model
fails to parse fully.
"""

import re
from typing import List, Tuple

FixResult = Tuple[str, str]  # (description, diff_snippet)


def _find_line(lines, pattern):
    for i, line in enumerate(lines):
        if re.search(pattern, line):
            return i
    return -1


def _find_last_line(lines, pattern):
    last = -1
    for i, line in enumerate(lines):
        if re.search(pattern, line):
            last = i
    return last


def _insert_after(lines, index, new_lines):
    for i, nl in enumerate(new_lines):
        lines.insert(index + 1 + i, nl)


def fix_missing_network(lines):
    """Add a placeholder NETWORK block if none exists."""
    if _find_line(lines, r"^\s*NETWORK\s*\[") >= 0:
        return None

    insert_at = _find_last_line(lines, r"^\s*BROKER\s*\[")
    if insert_at < 0:
        insert_at = _find_last_line(lines, r"^\s*USE\s+")
    if insert_at < 0:
        insert_at = _find_line(lines, r"^\s*DEVICE\s+")
    if insert_at < 0:
        return None

    while insert_at < len(lines) - 1 and not lines[insert_at].rstrip().endswith(";"):
        insert_at += 1

    new = [
        "\n",
        'NETWORK[WiFi] WITH ssid="TODO_SSID", password="TODO_PASSWORD";\n',
    ]
    _insert_after(lines, insert_at, new)
    return "Added placeholder NETWORK[WiFi] block (update ssid/password)"


def fix_missing_broker(lines):
    """Add a placeholder BROKER block if none exists."""
    if _find_line(lines, r"^\s*BROKER\s*\[") >= 0:
        return None

    insert_at = _find_last_line(lines, r"^\s*NETWORK\s*\[")
    if insert_at < 0:
        insert_at = _find_last_line(lines, r"^\s*USE\s+")
    if insert_at < 0:
        insert_at = _find_line(lines, r"^\s*DEVICE\s+")
    if insert_at < 0:
        return None

    while insert_at < len(lines) - 1 and not lines[insert_at].rstrip().endswith(";"):
        insert_at += 1

    new = [
        "\n",
        'BROKER[MQTT] DefaultBroker WITH host="localhost", port=1883;\n',
    ]
    _insert_after(lines, insert_at, new)
    return "Added placeholder BROKER[MQTT] block (update host/port)"


def fix_missing_broker_auth(lines):
    """Add auth placeholders to remote brokers missing authentication."""
    fixes = []
    i = 0
    while i < len(lines):
        match = re.match(r"^(\s*BROKER\s*\[\s*\w+\s*\]\s+\w+\s+WITH\s+)", lines[i])
        if not match:
            i += 1
            continue

        broker_start = i
        broker_end = i
        while broker_end < len(lines) and ";" not in lines[broker_end]:
            broker_end += 1

        broker_block = "".join(lines[broker_start : broker_end + 1])

        has_remote_host = re.search(r'host\s*=\s*"(?!localhost)[^"]+?"', broker_block)
        has_auth = re.search(r"auth\.\w+", broker_block)

        if has_remote_host and not has_auth:
            semi_line = broker_end
            old = lines[semi_line]
            stripped = old.rstrip()
            if stripped.endswith(";"):
                indent = re.match(r"^(\s*)", old).group(1) or "    "
                lines[semi_line] = stripped[:-1].rstrip(",") + ",\n"
                _insert_after(
                    lines,
                    semi_line,
                    [
                        f'{indent}auth.username="TODO_USER", ' f'auth.password="TODO_PASS";\n',
                    ],
                )
                broker_name_m = re.search(r"BROKER\s*\[\s*\w+\s*\]\s+(\w+)", broker_block)
                name = broker_name_m.group(1) if broker_name_m else "broker"
                fixes.append(f"Added auth placeholders to remote broker '{name}'")

        i = broker_end + 1

    return fixes if fixes else None


def fix_sampling_on_change_threshold(lines):
    """Add threshold=1.0 to SAMPLING blocks with mode=on_change missing it."""
    fixes = []
    i = 0
    while i < len(lines):
        match = re.search(r"\bSAMPLING\b", lines[i])
        if not match:
            i += 1
            continue

        block_start = i
        block_end = i
        while block_end < len(lines) and ";" not in lines[block_end]:
            block_end += 1

        block_text = "".join(lines[block_start : block_end + 1])

        has_on_change = re.search(r"mode\s*=\s*on_change", block_text)
        has_threshold = re.search(r"threshold\s*=", block_text)

        if has_on_change and not has_threshold:
            semi_idx = block_end
            old = lines[semi_idx]
            stripped = old.rstrip()
            if stripped.endswith(";"):
                lines[semi_idx] = stripped[:-1].rstrip(",") + ", threshold = 1.0;\n"
                target_m = re.search(r"SAMPLING\s+(\w+)", block_text)
                name = target_m.group(1) if target_m else "target"
                fixes.append(f"Added threshold=1.0 to SAMPLING '{name}' (on_change mode)")

        i = block_end + 1

    return fixes if fixes else None


def fix_sampling_batch_buffer(lines):
    """Add buffer=10 to SAMPLING blocks with mode=batch missing it."""
    fixes = []
    i = 0
    while i < len(lines):
        match = re.search(r"\bSAMPLING\b", lines[i])
        if not match:
            i += 1
            continue

        block_start = i
        block_end = i
        while block_end < len(lines) and ";" not in lines[block_end]:
            block_end += 1

        block_text = "".join(lines[block_start : block_end + 1])

        has_batch = re.search(r"mode\s*=\s*batch", block_text)
        has_buffer = re.search(r"buffer\s*=", block_text)

        if has_batch and not has_buffer:
            semi_idx = block_end
            old = lines[semi_idx]
            stripped = old.rstrip()
            if stripped.endswith(";"):
                lines[semi_idx] = stripped[:-1].rstrip(",") + ", buffer = 10;\n"
                target_m = re.search(r"SAMPLING\s+(\w+)", block_text)
                name = target_m.group(1) if target_m else "target"
                fixes.append(f"Added buffer=10 to SAMPLING '{name}' (batch mode)")

        i = block_end + 1

    return fixes if fixes else None


ALL_FIXERS = [
    fix_missing_network,
    fix_missing_broker,
    fix_missing_broker_auth,
    fix_sampling_on_change_threshold,
    fix_sampling_batch_buffer,
]


def apply_fixes(source_text: str) -> Tuple[str, List[str]]:
    """Apply all auto-fixes to the source text.

    Returns (fixed_text, list_of_descriptions).
    """
    lines = source_text.splitlines(keepends=True)
    if lines and not lines[-1].endswith("\n"):
        lines[-1] += "\n"

    all_descriptions = []

    for fixer in ALL_FIXERS:
        result = fixer(lines)
        if result is None:
            continue
        if isinstance(result, str):
            all_descriptions.append(result)
        elif isinstance(result, list):
            all_descriptions.extend(result)

    return "".join(lines), all_descriptions
