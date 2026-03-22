# demol/cli/ — Click CLI

## OVERVIEW

Click-based CLI providing the `demol` command with subcommands for validation, code generation, power analysis, auto-fix, model diff, and LSP.

## FILES

| File | Role |
|------|------|
| `cli.py` | Main Click group + all command and subcommand definitions |
| `autofix.py` | Auto-fix engine: detects and corrects common validation errors |
| `modeldiff.py` | Semantic diff engine: compares two `.dev` models structurally and semantically |

## COMMANDS REFERENCE

| Command | Description |
|---------|-------------|
| `demol validate <file>` | Parse + semantic validation with rich error display |
| `demol validate <file> --skip-semantics` | Syntax-only validation |
| `demol generate rpi <file> --output-dir <dir>` | Raspberry Pi Python code + deployment artifacts |
| `demol generate riot <file> --output-dir <dir>` | RiotOS C code + Makefile |
| `demol generate svg <file> --output-dir <dir>` | SVG wiring diagram |
| `demol generate docs <file> --output-dir <dir>` | Markdown hardware construction guide |
| `demol generate pinmap <file> --output-dir <dir>` | Pin-mapping report (MD + JSON) |
| `demol generate json <file> --output-dir <dir>` | JSON serialization of model |
| `demol generate smauto <file> --output-dir <dir>` | SmartAuto automation model |
| `demol analyze power <file>` | Power budget & battery runtime report |
| `demol analyze power <file> --json-output` | Power analysis as JSON |
| `demol fix <file>` | Auto-fix common validation errors in-place |
| `demol fix <file> --dry-run` | Preview fixes without modifying the file |
| `demol diff <a.dev> <b.dev>` | Semantic diff between two `.dev` models |
| `demol diff <a.dev> <b.dev> --json-output` | Diff output as JSON |
| `demol lsp` | Start LSP server on stdio for IDE integration |

## CONVENTIONS

- CLI uses `ValidationReporter` from `demol/lang/validation.py` for all error output — no direct printing
- `autofix.py` and `modeldiff.py` are imported by `cli.py`, not used standalone
- `--skip-semantics` is the only supported bypass — never suppress errors silently

## ANTI-PATTERNS

- Do NOT add validation logic directly in `cli.py` — delegate to `demol/lang/` modules
- Do NOT print validation output directly — use `ValidationReporter`
- `autofix.py` must use `--dry-run` as the safe default path for testing
