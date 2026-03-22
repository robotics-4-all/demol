# demol/lsp/ — Language Server Protocol

## OVERVIEW

LSP server for IDE integration. Provides real-time diagnostics, completion, hover, and go-to-definition for `.dev` files. Started via `demol lsp`.

## FILES

| File | Role |
|------|------|
| `server.py` | textX LSP server implementation using the textX-LS framework |
| `__init__.py` | Package init |

## FEATURES

| Feature | Description |
|---------|-------------|
| Diagnostics | Real-time parse and semantic errors as you type |
| Completion | DSL keywords, board names, peripheral names, pin functions |
| Hover | Documentation for `USE`d components and connection properties |
| Go-to-definition | Jump to board/peripheral definition in `.hwd` files |

## USAGE

```bash
demol lsp          # Start LSP on stdio (IDE integration)
```

Configure VS Code, Neovim, Emacs, or any LSP-compatible editor to use `demol lsp` as the language server for `.dev` files.

## CONVENTIONS

- LSP uses the same `get_device_mm()` pipeline as the CLI — no duplicate validation logic
- Errors and warnings come from `ValidationReporter` / `ValidationResult` (same as CLI output)
- Tests in `tests/test_lsp.py` cover: diagnostics (16 tests), completion, hover, go-to-def

## ANTI-PATTERNS

- Do NOT duplicate validation logic from `demol/lang/` — reuse existing metamodel pipeline
- Do NOT add new LSP features without corresponding tests in `tests/test_lsp.py`
- Do NOT hardcode file paths in the LSP server — use `demol/definitions.py` constants
