# Golden-File Snapshots (Zephyr / Wokwi / Renode)

This directory stores golden-file snapshots for the Zephyr, Wokwi, and Renode code
generation backends (Wave 2/3). Golden-file testing uses
**[syrupy](https://syrupy.readthedocs.io/)** — a pytest plugin for snapshot testing.

## Purpose

- Capture deterministic generator output as committed snapshots.
- Detect unintended changes in generated code across refactors, dependency upgrades,
  or grammar modifications.
- Provide a clear diff when generator output changes intentionally (reviewer inspects
  the snapshot diff).

## Workflow

1. **Update snapshots** — When generator output changes intentionally, run:
   ```bash
   pytest tests/test_<backend>_goldens.py --snapshot-update
   ```
   This writes new snapshot files under `tests/__snapshots__/`.

2. **Commit snapshots** — The updated snapshot files are committed alongside the
   generator change. Reviewers see the diff in the PR.

3. **Verify in CI** — CI runs:
   ```bash
   pytest tests/test_<backend>_goldens.py
   ```
   If snapshots do not match, the test fails with a diff. No `--snapshot-update`
   flag is used in CI — CI must never write snapshots.

## Directory Layout

```
tests/goldens/
├── README.md              # This file
├── zephyr/                # Zephyr codegen snapshots (Wave 2)
│   └── .gitkeep
├── wokwi/                 # Wokwi codegen snapshots (Wave 2)
│   └── .gitkeep
└── renode/                # Renode codegen snapshots (Wave 3)
    └── .gitkeep
```

The `tests/__snapshots__/` directory (created by syrupy at runtime) is also
committed — it contains the actual `.snap` files that form the golden reference.

## Note on Existing Tests

RPi and RIOT code generation tests **are not converted** to golden-file snapshots.
They use inline-DSL patterns and remain unchanged. Golden-file testing is introduced
exclusively for the new Zephyr, Wokwi, and Renode backends.

## References

- [syrupy documentation](https://syrupy.readthedocs.io/)
- [Pytest snapshot testing plugin (syrupy) — GitHub](https://github.com/tophat/syrupy)
