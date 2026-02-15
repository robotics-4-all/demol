"""DeMoL Language Server — diagnostics, completion, hover, go-to-definition."""

import logging
import os
import re
import warnings
from pathlib import Path

from pygls.lsp.server import LanguageServer
from lsprotocol import types

from demol.definitions import (
    BOARD_MODEL_REPO_PATH,
    PERIPHERAL_MODEL_REPO_PATH,
    POWER_SOURCE_MODEL_REPO_PATH,
)

logger = logging.getLogger(__name__)

DSL_KEYWORDS = [
    "DEVICE",
    "WITH",
    "USE",
    "NETWORK",
    "BROKER",
    "CONNECT",
    "SMARTCONNECT",
    "POWER",
    "DATA",
    "SAMPLING",
    "CONSTRAINT",
    "ALERT",
    "WHEN",
    "THEN",
    "ACTIVATE",
    "PUBLISH",
    "COOLDOWN",
    "VIA",
    "MESSAGE",
    "WiFi",
    "Eth",
    "MQTT",
    "AMQP",
    "Redis",
]

PROTOCOL_KEYWORDS = ["i2c", "spi", "uart", "gpio", "pwm"]

SAMPLING_MODES = ["continuous", "on_change", "on_demand", "batch"]

OS_KEYWORDS = [
    "raspbian",
    "riotos",
    "freertos",
    "arduino",
    "esp-idf",
    "esp-idf-rtos",
]


def _scan_hwd_files(directory):
    """Scan a directory for .hwd files and extract component names."""
    components = {}
    if not os.path.isdir(directory):
        return components
    for fname in os.listdir(directory):
        if not fname.endswith(".hwd"):
            continue
        fpath = os.path.join(directory, fname)
        try:
            with open(fpath, "r") as f:
                content = f.read()
            match = re.search(
                r"(?:BOARD|SENSOR|ACTUATOR|POWERSOURCE)\s*\[\s*\w+\s*\]\s+(\w+)",
                content,
            )
            if match:
                name = match.group(1)
                components[name] = {
                    "path": fpath,
                    "content": content,
                    "filename": fname,
                }
        except Exception:
            pass
    return components


def _get_component_library():
    """Build the full component library from builtin models."""
    library = {}
    library.update(_scan_hwd_files(BOARD_MODEL_REPO_PATH))
    library.update(_scan_hwd_files(PERIPHERAL_MODEL_REPO_PATH))
    library.update(_scan_hwd_files(POWER_SOURCE_MODEL_REPO_PATH))
    return library


def _parse_and_validate(source_text, uri=None):
    """Parse and validate a .dev model, returning (model, errors, warnings_list)."""
    from demol.lang import get_device_mm
    from demol.lang.semantics.core import get_validation_errors

    collected_warnings = []
    model = None
    errors = []

    try:
        mm = get_device_mm(skip_semantics=False)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            model = mm.model_from_str(source_text)
            collected_warnings = list(w)
    except Exception as e:
        loc = getattr(e, "line", None)
        col = getattr(e, "col", None)
        errors.append(
            {
                "message": str(e),
                "line": (loc - 1) if loc else 0,
                "col": (col - 1) if col else 0,
            }
        )

    sem_errors = get_validation_errors() if not errors else []
    for se in sem_errors:
        line = 0
        col = 0
        msg = str(se)
        loc_match = re.search(r"at position \((\d+), (\d+)\)", msg)
        if loc_match:
            line = int(loc_match.group(1)) - 1
            col = int(loc_match.group(2)) - 1
        errors.append({"message": msg, "line": line, "col": col})

    return model, errors, collected_warnings


def _extract_instance_names(source_text):
    """Extract component instance names from USE statements."""
    names = []
    for match in re.finditer(r"USE\s+\w+\s*\[\s*(\w+)\s*\]", source_text):
        names.append(match.group(1))
    for match in re.finditer(r"USE\s+\w+\s*\(\s*(\w+)\s*\)", source_text):
        names.append(match.group(1))
    return names


def _extract_broker_names(source_text):
    """Extract broker names from BROKER declarations."""
    names = []
    for match in re.finditer(r"BROKER\s*\[\s*\w+\s*\]\s+(\w+)", source_text):
        names.append(match.group(1))
    return names


def _get_word_at_position(line_text, character):
    """Get the word at a given character position in a line."""
    if character >= len(line_text):
        return None, 0, 0
    start = character
    while start > 0 and re.match(r"\w", line_text[start - 1]):
        start -= 1
    end = character
    while end < len(line_text) and re.match(r"\w", line_text[end]):
        end += 1
    word = line_text[start:end]
    return word if word else None, start, end


def create_server():
    """Create and configure the DeMoL language server."""
    server = LanguageServer("demol-lsp", "v1.0")
    component_library = _get_component_library()

    @server.feature(types.TEXT_DOCUMENT_DID_OPEN)
    def did_open(ls: LanguageServer, params: types.DidOpenTextDocumentParams):
        _publish_diagnostics(ls, params.text_document.uri)

    @server.feature(types.TEXT_DOCUMENT_DID_SAVE)
    def did_save(ls: LanguageServer, params: types.DidSaveTextDocumentParams):
        _publish_diagnostics(ls, params.text_document.uri)

    @server.feature(types.TEXT_DOCUMENT_DID_CHANGE)
    def did_change(ls: LanguageServer, params: types.DidChangeTextDocumentParams):
        _publish_diagnostics(ls, params.text_document.uri)

    def _publish_diagnostics(ls, uri):
        doc = ls.workspace.get_text_document(uri)
        if not uri.endswith(".dev"):
            return

        source = doc.source
        _, errors, warns = _parse_and_validate(source, uri)

        diagnostics = []
        for err in errors:
            diagnostics.append(
                types.Diagnostic(
                    range=types.Range(
                        start=types.Position(
                            line=max(0, err["line"]),
                            character=max(0, err["col"]),
                        ),
                        end=types.Position(
                            line=max(0, err["line"]),
                            character=max(0, err["col"]) + 1,
                        ),
                    ),
                    message=err["message"],
                    severity=types.DiagnosticSeverity.Error,
                    source="demol",
                )
            )

        for w in warns:
            msg = str(w.message)
            line_match = re.search(r"line (\d+)", msg)
            line = int(line_match.group(1)) - 1 if line_match else 0
            diagnostics.append(
                types.Diagnostic(
                    range=types.Range(
                        start=types.Position(line=max(0, line), character=0),
                        end=types.Position(line=max(0, line), character=80),
                    ),
                    message=msg,
                    severity=types.DiagnosticSeverity.Warning,
                    source="demol",
                )
            )

        ls.text_document_publish_diagnostics(
            types.PublishDiagnosticsParams(
                uri=uri,
                diagnostics=diagnostics,
            )
        )

    @server.feature(
        types.TEXT_DOCUMENT_COMPLETION,
        types.CompletionOptions(trigger_characters=[".", " ", "[", ","]),
    )
    def completions(params: types.CompletionParams):
        doc = server.workspace.get_text_document(params.text_document.uri)
        try:
            line_text = doc.lines[params.position.line]
        except IndexError:
            return []

        source = doc.source
        items = []

        stripped = line_text.strip()

        if stripped.startswith("USE") or re.match(r"^\s*USE\b", line_text):
            for name, info in component_library.items():
                items.append(
                    types.CompletionItem(
                        label=name,
                        kind=types.CompletionItemKind.Class,
                        detail=f"Component from {info['filename']}",
                    )
                )
            return items

        if re.match(r".*\b(CONNECT|SMARTCONNECT|SAMPLING|ALERT\s+\w+\s+ON)\b", stripped):
            for inst_name in _extract_instance_names(source):
                items.append(
                    types.CompletionItem(
                        label=inst_name,
                        kind=types.CompletionItemKind.Variable,
                        detail="Component instance",
                    )
                )

        if re.search(r"\bVIA\b", stripped):
            for broker_name in _extract_broker_names(source):
                items.append(
                    types.CompletionItem(
                        label=broker_name,
                        kind=types.CompletionItemKind.Module,
                        detail="Broker",
                    )
                )

        if re.search(r"\bDATA\b", stripped):
            for proto in PROTOCOL_KEYWORDS:
                items.append(
                    types.CompletionItem(
                        label=proto,
                        kind=types.CompletionItemKind.Keyword,
                        detail=f"{proto.upper()} protocol",
                    )
                )

        if re.search(r"\bmode\s*=", stripped):
            for mode in SAMPLING_MODES:
                items.append(
                    types.CompletionItem(
                        label=mode,
                        kind=types.CompletionItemKind.EnumMember,
                        detail=f"Sampling mode: {mode}",
                    )
                )

        if re.search(r"\bos\s*=", stripped):
            for os_name in OS_KEYWORDS:
                items.append(
                    types.CompletionItem(
                        label=os_name,
                        kind=types.CompletionItemKind.EnumMember,
                        detail=f"Operating system: {os_name}",
                    )
                )

        if not items:
            for kw in DSL_KEYWORDS:
                items.append(
                    types.CompletionItem(
                        label=kw,
                        kind=types.CompletionItemKind.Keyword,
                        detail="DeMoL keyword",
                    )
                )

        return items

    @server.feature(types.TEXT_DOCUMENT_HOVER)
    def hover(ls: LanguageServer, params: types.HoverParams):
        doc = ls.workspace.get_text_document(params.text_document.uri)
        try:
            line_text = doc.lines[params.position.line]
        except IndexError:
            return None

        word, start, end = _get_word_at_position(line_text, params.position.character)
        if not word:
            return None

        if word in component_library:
            info = component_library[word]
            content = info["content"]
            return types.Hover(
                contents=types.MarkupContent(
                    kind=types.MarkupKind.Markdown,
                    value=(f"## {word}\n\n" f"**Source**: `{info['filename']}`\n\n" f"```\n{content.strip()}\n```"),
                ),
                range=types.Range(
                    start=types.Position(line=params.position.line, character=start),
                    end=types.Position(line=params.position.line, character=end),
                ),
            )

        keyword_docs = {
            "DEVICE": "Declares a new IoT device model with metadata.",
            "USE": "Imports a hardware component (board, sensor, actuator, power source).",
            "CONNECT": "Defines manual pin-to-pin wiring between a peripheral and the board.",
            "SMARTCONNECT": "Automatic pin assignment — DeMoL resolves wiring automatically.",
            "SAMPLING": "Configures data acquisition rate, mode, and buffering for a sensor.",
            "CONSTRAINT": "User-defined invariant checked at validation time.",
            "ALERT": "Threshold-based trigger: WHEN condition THEN actions.",
            "BROKER": "Declares a message broker (MQTT, AMQP, Redis) for pub/sub.",
            "NETWORK": "Configures network connectivity (WiFi or Ethernet).",
            "VIA": "Routes a connection's messages through a specific broker.",
            "POWER": "Power pin connections (GND, VCC) in a CONNECT block.",
            "DATA": "Data pin connections (I2C, SPI, UART, GPIO, PWM) in a CONNECT block.",
        }

        if word in keyword_docs:
            return types.Hover(
                contents=types.MarkupContent(
                    kind=types.MarkupKind.Markdown,
                    value=f"**{word}** — {keyword_docs[word]}",
                ),
            )

        return None

    @server.feature(types.TEXT_DOCUMENT_DEFINITION)
    def goto_definition(ls: LanguageServer, params: types.DefinitionParams):
        doc = ls.workspace.get_text_document(params.text_document.uri)
        try:
            line_text = doc.lines[params.position.line]
        except IndexError:
            return None

        word, _, _ = _get_word_at_position(line_text, params.position.character)
        if not word:
            return None

        if word in component_library:
            fpath = component_library[word]["path"]
            return types.Location(
                uri=Path(fpath).as_uri(),
                range=types.Range(
                    start=types.Position(line=0, character=0),
                    end=types.Position(line=0, character=0),
                ),
            )

        source = doc.source
        instance_names = _extract_instance_names(source)
        if word in instance_names:
            for i, line in enumerate(doc.lines):
                if re.search(rf"\[\s*{re.escape(word)}\s*\]", line):
                    col = line.index(word)
                    return types.Location(
                        uri=params.text_document.uri,
                        range=types.Range(
                            start=types.Position(line=i, character=col),
                            end=types.Position(line=i, character=col + len(word)),
                        ),
                    )

        return None

    return server


def main():
    """Entry point for the DeMoL language server."""
    logging.basicConfig(level=logging.INFO)
    server = create_server()
    server.start_io()


if __name__ == "__main__":
    main()
