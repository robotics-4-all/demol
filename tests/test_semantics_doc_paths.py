import os
import shutil
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DOC = REPO_ROOT / "docs" / "semantics.md"
VERIFY = REPO_ROOT / "scripts" / "verify_doc_paths.sh"
EXTRACT = REPO_ROOT / "scripts" / "extract_doc_rules.sh"
VALIDATORS_DIR = REPO_ROOT / "demol" / "lang" / "semantics" / "validators"


def _run(script: Path, *args: str) -> subprocess.CompletedProcess:
    assert script.is_file() and shutil.which("bash") is not None
    return subprocess.run(
        ["bash", str(script), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_verify_doc_paths_succeeds():
    result = _run(VERIFY, str(DOC))
    assert result.returncode == 0, (
        f"verify_doc_paths.sh failed (rc={result.returncode})\n" f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )


def test_extract_doc_rules_returns_enough():
    result = _run(EXTRACT, str(DOC))
    assert result.returncode == 0, f"extract_doc_rules.sh failed (rc={result.returncode})\n" f"stderr:\n{result.stderr}"
    lines = [ln for ln in result.stdout.splitlines() if ln.strip()]
    min_rules = int(os.environ.get("DOC_RULE_MIN", "5"))
    assert len(lines) >= min_rules, f"expected >= {min_rules} rule labels in {DOC}, got {len(lines)}:\n" + "\n".join(
        lines
    )


def test_doc_rule_names_in_validator_source():
    extract = _run(EXTRACT, str(DOC))
    assert extract.returncode == 0
    rules = [ln.strip() for ln in extract.stdout.splitlines() if ln.strip()]
    assert rules, "extract_doc_rules.sh produced no rule names"

    grep = subprocess.run(
        [
            "grep",
            "-rlE",
            "\\[(" + "|".join(r.strip("[]") for r in rules) + ")\\]",
            str(VALIDATORS_DIR),
            "--include=*.py",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert grep.returncode == 0, (
        f"no validator source references any of the {len(rules)} rule "
        f"names declared in {DOC}.\nrules: {rules}\nstderr: {grep.stderr}"
    )
    matched_files = grep.stdout.strip().splitlines()
    assert matched_files, "grep matched no validator files"
