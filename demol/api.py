"""DeMoL compiler HTTP service.

Exposes model validation and code generation over HTTP so that
external platforms (e.g. LCP) can use demol without importing
it as a library.

This module implements the shared LCP compiler-service contract
(see ``sigil-lang/sigil/api.py`` for the reference implementation):

Endpoints:
    GET  /health     - liveness probe
    POST /validate   - parse + semantic validation -> diagnostics
    POST /generate   - parse + validate + generation -> file artifacts

Notes:
    - Single-source strings only. DeMoL ``.dev`` sources are written to
      a temporary file before parsing because the language engine is
      file-oriented (``build_model``).
    - ``generate`` accepts an optional ``target`` (``rpi``, ``riot``,
      ``zephyr``, ``wokwi``, ``renode``, ``docs``, ``pinmap``,
      ``json``, ``svg`` or ``smauto``; defaults to ``rpi``) either
      top level or nested under ``options``. ``options`` may also carry
      ``board`` (zephyr board override).
    - ``generate`` writes files to a temp dir, then returns every file
      base64-encoded so callers without shared storage can persist them.
"""

import base64
import json
import os
import re
import tempfile
import threading

from fastapi import FastAPI
from pydantic import BaseModel, Field

SERVICE_VERSION = "1.0.0"
MAX_GENERATED_BYTES = 2 * 1024 * 1024  # total cap for all artifacts

GENERATOR_VERSION = "0.0.1"

VALID_TARGETS = (
    "rpi",
    "riot",
    "zephyr",
    "wokwi",
    "renode",
    "docs",
    "pinmap",
    "json",
    "svg",
    "smauto",
)
DEFAULT_TARGET = "rpi"

_CONTENT_TYPES = {
    ".py": "text/x-python",
    ".c": "text/x-c",
    ".h": "text/x-c",
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".json": "application/json",
    ".yaml": "application/yaml",
    ".yml": "application/yaml",
    ".toml": "application/toml",
    ".svg": "image/svg+xml",
    ".mk": "text/plain",
}

# DeMoL collects validation results in module-global lists, so serialise
# parse/validate/generate to keep concurrent requests from interleaving.
_PARSE_LOCK = threading.Lock()

app = FastAPI(title="DeMoL Compiler Service", version=SERVICE_VERSION)


class ValidateRequest(BaseModel):
    source: str = Field(..., min_length=1)

    class Config:
        extra = "ignore"


class Diagnostic(BaseModel):
    severity: str
    message: str
    code: str | None = None
    line: int | None = None
    column: int | None = None


class ValidateResponse(BaseModel):
    valid: bool
    diagnostics: list[Diagnostic] = Field(default_factory=list)
    summary: str


class GenerateRequest(BaseModel):
    source: str = Field(..., min_length=1)
    name: str | None = None
    target: str | None = None
    options: dict | None = None

    class Config:
        extra = "ignore"


class Artifact(BaseModel):
    name: str
    kind: str
    size_bytes: int
    content_type: str
    content_base64: str


class GenerateResponse(BaseModel):
    artifacts: list[Artifact]
    metadata: dict = Field(default_factory=dict)
    summary: str


class ErrorResponse(BaseModel):
    error: str
    code: str


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "demol", "version": SERVICE_VERSION}


_SYNTAX_LOC_RE = re.compile(r"^(.*?):(\d+):(\d+):\s*(.*)$", re.DOTALL)


def _parse_error_diagnostic(exc: Exception) -> Diagnostic:
    match = _SYNTAX_LOC_RE.match(str(exc))
    if match:
        _filename, line, col, detail = match.groups()
        try:
            return Diagnostic(
                severity="error",
                message=f"Parse error: {detail.strip()}",
                code="PARSE_ERROR",
                line=int(line),
                column=int(col),
            )
        except ValueError:
            pass
    return Diagnostic(severity="error", message=f"Parse error: {exc}", code="PARSE_ERROR")


def _to_int(value) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _collected_diagnostics() -> tuple[list[Diagnostic], list[Diagnostic]]:
    from demol.lang.semantics import get_validation_errors, get_validation_warnings

    errors = [
        Diagnostic(
            severity="error",
            message=str(err.get("msg", "Semantic error")),
            code=str(err.get("type") or "SEMANTIC_ERROR"),
            line=_to_int((err.get("loc") or {}).get("line")),
            column=_to_int((err.get("loc") or {}).get("col")),
        )
        for err in get_validation_errors()
    ]
    warnings = [
        Diagnostic(
            severity="warning",
            message=str(w.get("msg", "Warning")),
            code=str(w.get("type") or "WARNING"),
            line=_to_int((w.get("loc") or {}).get("line")),
            column=_to_int((w.get("loc") or {}).get("col")),
        )
        for w in get_validation_warnings()
    ]
    return errors, warnings


def _load_model(source: str):
    """Write ``source`` to a temp ``.dev`` file and build the model.

    Raises ``TextXSyntaxError`` on syntax errors and ``ValidationError``
    (with :func:`get_validation_errors` populated) on semantic errors.
    """
    from demol.lang import build_model

    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "model.dev")
        with open(path, "w", encoding="utf-8") as f:
            f.write(source)
        return build_model(path)


def _resolve_target(req: GenerateRequest) -> tuple[str, dict]:
    options = dict(req.options) if isinstance(req.options, dict) else {}
    target = options.get("target")
    if not (isinstance(target, str) and target.strip()) and isinstance(req.target, str):
        target = req.target
    resolved = target.strip() if isinstance(target, str) and target.strip() else DEFAULT_TARGET
    return resolved, options


@app.post("/validate", response_model=ValidateResponse)
def validate_source(req: ValidateRequest) -> ValidateResponse:
    from textx.exceptions import TextXSyntaxError

    from demol.lang.semantics import ValidationError

    with _PARSE_LOCK:
        try:
            model = _load_model(req.source)
        except TextXSyntaxError as exc:
            diag = _parse_error_diagnostic(exc)
            return ValidateResponse(valid=False, diagnostics=[diag], summary="Parse failed.")
        except (ValidationError, Exception) as exc:
            # Semantic failures surface as ValidationError with the
            # collected error list populated; anything else is surfaced
            # as a single diagnostic so the contract always holds.
            from textx import TextXSemanticError

            errors, warnings = _collected_diagnostics()
            if not isinstance(exc, (ValidationError, TextXSemanticError)) or not errors:
                errors = [Diagnostic(severity="error", message=str(exc), code="SEMANTIC_ERROR")]
            return ValidateResponse(
                valid=False,
                diagnostics=[*errors, *warnings],
                summary=f"Validation failed with {len(errors)} error(s), {len(warnings)} warning(s).",
            )
        errors, warnings = _collected_diagnostics()

    n_use = len(getattr(model, "uses", []) or [])
    n_conn = len(getattr(model, "connections", []) or [])
    n_smart = len(getattr(model, "smartConnections", []) or [])
    return ValidateResponse(
        valid=True,
        diagnostics=list(warnings),
        summary=(
            f"Validation passed: {n_use} USE block(s), "
            f"{n_conn + n_smart} CONNECT block(s), {len(warnings)} warning(s)."
        ),
    )


def _artifact_kind(name: str) -> str:
    base = os.path.basename(name)
    if base in ("requirements.txt", "Dockerfile", "CMakeLists.txt", "Makefile"):
        return "manifest"
    return "source"


def _content_type(name: str) -> str:
    _, ext = os.path.splitext(name)
    return _CONTENT_TYPES.get(ext.lower(), "application/octet-stream")


def _run_generator(target: str, model, output_dir: str, options: dict) -> None:
    from demol.transformations import (
        demol_to_json,
        m2m_smauto,
        m2t_device_svg,
        m2t_docs,
        m2t_pinmap,
        m2t_renode,
        m2t_riot,
        m2t_rpi,
        m2t_wokwi,
        m2t_zephyr,
    )

    if target == "rpi":
        m2t_rpi(model, output_dir=output_dir)
    elif target == "riot":
        m2t_riot(model, output_dir=output_dir)
    elif target == "zephyr":
        board = options.get("board")
        m2t_zephyr(model, output_dir=output_dir, board_override=board)
    elif target == "wokwi":
        m2t_wokwi(model, output_dir=output_dir)
    elif target == "renode":
        m2t_renode(model, output_dir=output_dir, elf_path=options.get("elf_path"))
    elif target == "docs":
        m2t_docs(model, output_dir=output_dir)
    elif target == "pinmap":
        m2t_pinmap(model, output_dir=output_dir)
    elif target == "smauto":
        m2m_smauto(model, output_dir=output_dir)
    elif target == "json":
        name = getattr(getattr(model, "metadata", None), "name", "model") or "model"
        filename = os.path.join(output_dir, f"{name}.json")
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(demol_to_json(model), f, indent=4)
    elif target == "svg":
        name = getattr(getattr(model, "metadata", None), "name", "model") or "model"
        filename = os.path.join(output_dir, f"{name}.svg")
        m2t_device_svg(model, filename)
    else:  # pragma: no cover - guarded by target validation
        raise ValueError(f"Unknown target '{target}'")


@app.post("/generate", response_model=GenerateResponse, responses={422: {"model": ErrorResponse}})
def generate_source(req: GenerateRequest):
    from fastapi.responses import JSONResponse
    from textx.exceptions import TextXSyntaxError

    from demol.lang.semantics import ValidationError

    target, options = _resolve_target(req)
    if target not in VALID_TARGETS:
        return JSONResponse(
            status_code=422,
            content={
                "error": f"Unknown target '{target}'. Valid targets: {', '.join(VALID_TARGETS)}.",
                "code": "UNKNOWN_TARGET",
            },
        )
    with _PARSE_LOCK:
        try:
            model = _load_model(req.source)
        except TextXSyntaxError as exc:
            diag = _parse_error_diagnostic(exc)
            return JSONResponse(status_code=422, content={"error": diag.message, "code": "PARSE_ERROR"})
        except Exception as exc:
            from textx import TextXSemanticError

            errors, _warnings = _collected_diagnostics()
            detail = errors[0].message if errors else str(exc)
            if not isinstance(exc, (ValidationError, TextXSemanticError)) and not errors:
                detail = f"Parse error: {exc}"
                code = "PARSE_ERROR"
            else:
                code = "SEMANTIC_ERROR"
            return JSONResponse(status_code=422, content={"error": detail, "code": code})

        with tempfile.TemporaryDirectory() as tmp:
            try:
                _run_generator(target, model, tmp, options)
            except Exception as exc:  # pragma: no cover - defensive
                return JSONResponse(
                    status_code=422,
                    content={"error": f"Generation failed: {exc}", "code": "GENERATION_ERROR"},
                )
            artifacts: list[Artifact] = []
            total = 0
            for root, _dirs, files in os.walk(tmp):
                if "__pycache__" in root:
                    continue
                for fname in sorted(files):
                    if fname.endswith((".pyc", ".pyo")):
                        continue
                    full = os.path.join(root, fname)
                    rel = os.path.relpath(full, tmp).replace(os.sep, "/")
                    with open(full, "rb") as f:
                        data = f.read()
                    total += len(data)
                    if total > MAX_GENERATED_BYTES:
                        return JSONResponse(
                            status_code=413,
                            content={
                                "error": f"Generated output exceeds {MAX_GENERATED_BYTES} bytes.",
                                "code": "OUTPUT_TOO_LARGE",
                            },
                        )
                    artifacts.append(
                        Artifact(
                            name=rel,
                            kind=_artifact_kind(rel),
                            size_bytes=len(data),
                            content_type=_content_type(rel),
                            content_base64=base64.b64encode(data).decode("ascii"),
                        )
                    )

    if not artifacts:
        return JSONResponse(
            status_code=422,
            content={"error": "Generation produced no files.", "code": "GENERATION_ERROR"},
        )
    name = getattr(getattr(model, "metadata", None), "name", "") or req.name or "model"
    return GenerateResponse(
        artifacts=artifacts,
        metadata={
            "device": name,
            "target": target,
            "generator": "demol",
            "version": GENERATOR_VERSION,
        },
        summary=f"Generated {len(artifacts)} file(s) for device '{name}' [{target}].",
    )
