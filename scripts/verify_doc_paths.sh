#!/usr/bin/env bash
set -euo pipefail

DOC="${1:-${DOC:-docs/semantics.md}}"
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

if [[ ! -f "$DOC" ]]; then
    echo "error: doc not found: $DOC" >&2
    exit 2
fi

python3 - "$DOC" "$REPO_ROOT" <<'PY'
import os
import re
import sys

doc_path, repo_root = sys.argv[1], sys.argv[2]

ref_re = re.compile(
    r'((?:demol|tests|docs)/[A-Za-z0-9_./-]+\.(?:py|md|sh)):([0-9]+)'
)

with open(doc_path, 'r', encoding='utf-8') as fh:
    refs = ref_re.findall(fh.read())

if not refs:
    print('verify_doc_paths: no path:line references found in', doc_path)
    sys.exit(0)

line_count_cache: dict[str, int] = {}
stale = 0
total = 0

for path, line_str in refs:
    total += 1
    line_no = int(line_str)
    full = os.path.join(repo_root, path)

    if not os.path.isfile(full):
        print(f'{path}:{line_no}  STALE  (file missing)')
        stale += 1
        continue

    if path not in line_count_cache:
        with open(full, 'rb') as fh:
            line_count_cache[path] = sum(1 for _ in fh)
    max_line = line_count_cache[path]

    if line_no < 1 or line_no > max_line:
        print(f'{path}:{line_no}  STALE  (file has {max_line} lines)')
        stale += 1
    else:
        print(f'{path}:{line_no}  OK')

print(f'verify_doc_paths: {total - stale}/{total} OK, {stale} STALE')
sys.exit(1 if stale else 0)
PY
