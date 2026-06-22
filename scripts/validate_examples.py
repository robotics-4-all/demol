#!/usr/bin/env python3
"""
DeMoL Examples Validator

This script validates all .dev files in the examples directory.
Uses the validation functionality from demol.lang.validation.
"""

import sys
import glob
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from demol.lang import (
        get_device_mm,
        ValidationReporter,
        validate_models,
        ValidationStatus,
    )
except ImportError as e:
    print(f"Error importing demol package: {e}")
    print("Make sure you are running this script from the repository.")
    print("You may need to install required dependencies:")
    print("  pip install rich")
    sys.exit(1)


import argparse


def main():
    """Main validation function"""
    parser = argparse.ArgumentParser(description="DeMoL Examples Validator")
    parser.add_argument("--skip-semantics", action="store_true", help="Skip semantic validation")
    args = parser.parse_args()

    # Create reporter
    reporter = ValidationReporter()

    # Print header
    reporter.print_header("DeMoL Examples Validator")

    # Find example files
    repo_root = Path(__file__).parent.parent
    examples_dir = repo_root / "examples"

    if not examples_dir.exists():
        reporter.print(f"[red]Error:[/red] Examples directory not found at {examples_dir}")
        sys.exit(1)

    example_files = sorted(glob.glob(str(examples_dir / "**" / "*.dev"), recursive=True))

    if not example_files:
        reporter.print("[yellow]No .dev files found in examples directory.[/yellow]")
        sys.exit(0)

    reporter.print(f"\n[cyan]Found {len(example_files)} example file(s)[/cyan]\n")

    # Initialize metamodel
    try:
        mm = get_device_mm(skip_semantics=args.skip_semantics)
    except Exception as e:
        reporter.print(f"[red]Failed to initialize metamodel:[/red] {e}")
        sys.exit(1)

    # Validate files with progress bar
    results = validate_models(example_files, mm, show_progress=True, reporter=reporter)

    # Display results
    reporter.print("")

    if reporter.use_rich:
        reporter.console.print(reporter.create_summary_table(results))
    else:
        # Simple text output
        for result in results:
            status = (
                "PASS"
                if result.status == ValidationStatus.PASS
                else ("WARN" if result.status == ValidationStatus.WARN else "FAIL")
            )
            print(f"{status}: {result.rel_path}")

    reporter.print("")
    reporter.print_summary_panel(results)

    # Print detailed issues if any
    if any(r.has_issues for r in results):
        reporter.print("")
        reporter.print_detailed_issues(results)

    # Exit with appropriate code
    failed_count = sum(1 for r in results if r.status == ValidationStatus.FAIL)
    sys.exit(1 if failed_count > 0 else 0)


if __name__ == "__main__":
    main()
