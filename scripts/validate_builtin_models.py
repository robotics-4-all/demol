#!/usr/bin/env python3
"""
DeMoL Builtin Models Validator

This script validates all .hwd files (boards and peripherals) in the builtin_models directory.
Uses the ValidationReporter from demol.lang for consistent formatting.
"""

import sys
import glob
from pathlib import Path
from typing import List

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from demol.lang import (
        get_component_mm,
        ValidationReporter,
        ValidationStatus,
    )
    from demol.lang.validation import ValidationResult
    from demol.lang.validation import validate_model_file
except ImportError as e:
    print(f"Error importing demol package: {e}")
    print("Make sure you are running this script from the repository.")
    print("You may need to install required dependencies:")
    print("  pip install rich")
    sys.exit(1)


def validate_component_models(
    model_files: List[str], mm, show_progress: bool = True, reporter: ValidationReporter = None
) -> List:
    """Validate component model files (.hwd) with progress tracking"""

    results = []

    if show_progress and reporter and reporter.use_rich:
        from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=reporter.console,
        ) as progress:
            task = progress.add_task("[cyan]Validating models...", total=len(model_files))

            for model_file in model_files:
                progress.update(task, description=f"[cyan]Validating {Path(model_file).name}...")
                result = validate_single_component(model_file, mm)
                results.append(result)
                progress.advance(task)
    else:
        # Fallback without progress bar
        for model_file in model_files:
            if reporter:
                reporter.print(f"Validating {Path(model_file).name}...")
            result = validate_single_component(model_file, mm)
            results.append(result)

    return results


def validate_single_component(file_path: str, mm):
    """Validate a single component model file"""
    return validate_model_file(file_path, mm)


def main():
    """Main validation function"""
    # Create reporter
    reporter = ValidationReporter()

    # Print header
    reporter.print_header("DeMoL Builtin Models Validator")

    # Find model files
    repo_root = Path(__file__).parent.parent
    builtin_models_dir = repo_root / "demol" / "builtin_models"

    if not builtin_models_dir.exists():
        reporter.print(f"[red]Error:[/red] Builtin models directory not found at {builtin_models_dir}")
        sys.exit(1)

    # Find all .hwd files (boards and peripherals)
    board_files = sorted(glob.glob(str(builtin_models_dir / "boards" / "*.hwd")))
    peripheral_files = sorted(glob.glob(str(builtin_models_dir / "peripherals" / "*.hwd")))
    all_model_files = board_files + peripheral_files

    if not all_model_files:
        reporter.print("[yellow]No .hwd files found in builtin_models directory.[/yellow]")
        sys.exit(0)

    reporter.print(f"\n[cyan]Found {len(board_files)} board(s) and {len(peripheral_files)} peripheral(s)[/cyan]")
    reporter.print(f"[cyan]Total: {len(all_model_files)} model file(s)[/cyan]\n")

    # Initialize metamodel
    try:
        mm = get_component_mm()
    except Exception as e:
        reporter.print(f"[red]Failed to initialize component metamodel:[/red] {e}")
        sys.exit(1)

    # Validate files with progress bar
    results = validate_component_models(all_model_files, mm, show_progress=True, reporter=reporter)

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
