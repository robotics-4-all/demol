#!/usr/bin/env bash
set -euo pipefail

DOC="${1:-${DOC:-docs/semantics.md}}"

if [[ ! -f "$DOC" ]]; then
    echo "error: doc not found: $DOC" >&2
    exit 2
fi

python3 - "$DOC" <<'PY'
import re
import sys

doc_path = sys.argv[1]

rule_re = re.compile(r'\[[A-Z][a-zA-Z0-9_-]+\]')
comment_re = re.compile(r'<!--.*?-->', re.DOTALL)

with open(doc_path, 'r', encoding='utf-8') as fh:
    raw = fh.read()

stripped = comment_re.sub('', raw)
seen = set()
for match in rule_re.finditer(stripped):
    name = match.group(0)
    if name in seen:
        continue
    seen.add(name)
    print(name)
PY
