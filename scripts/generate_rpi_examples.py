#!/usr/bin/env python3
"""
DeMoL RPI Code Generator

This script generates Python code for all Raspberry Pi device examples
using the m2t_rpi transformation.
"""

import sys
from pathlib import Path
from dataclasses import dataclass
from typing import List, Tuple
from enum import Enum

# Add project root to path
REPO_PATH = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_PATH))

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
    from rich import box

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

from demol.transformations.m2t_rpi import transform_device_model


class GenerationStatus(Enum):
    """Generation result status"""

    SUCCESS = "success"
    FAILED = "failed"


@dataclass
class GenerationResult:
    """Result of code generation for a single example"""

    dev_model: str
    output_dir: str
    status: GenerationStatus
    error: str = ""

    @property
    def rel_path(self) -> str:
        """Get relative path from examples directory"""
        return self.dev_model


class GenerationReporter:
    """Reporter for code generation with rich formatting"""

    def __init__(self):
        self.use_rich = RICH_AVAILABLE
        if self.use_rich:
            self.console = Console()

    def print(self, message, **kwargs):
        """Print with rich if available, otherwise plain"""
        if self.use_rich:
            self.console.print(message, **kwargs)
        else:
            print(message)

    def print_header(self, title: str):
        """Print a styled header"""
        if self.use_rich:
            self.console.print(Panel(f"[bold cyan]{title}[/bold cyan]", box=box.DOUBLE, border_style="cyan"))
        else:
            print(f"\n{'='*60}")
            print(f"  {title}")
            print(f"{'='*60}\n")

    def create_summary_table(self, results: List[GenerationResult]):
        """Create a rich table summarizing results"""
        table = Table(title="Generation Results", box=box.ROUNDED)

        table.add_column("Example", style="cyan", no_wrap=False)
        table.add_column("Output Directory", style="blue")
        table.add_column("Status", justify="center")

        for result in results:
            if result.status == GenerationStatus.SUCCESS:
                status = "[green]✓ SUCCESS[/green]"
            else:
                status = "[red]✗ FAILED[/red]"

            table.add_row(result.rel_path, result.output_dir, status)

        return table

    def print_summary_panel(self, results: List[GenerationResult]):
        """Print summary panel with statistics"""
        total = len(results)
        successful = sum(1 for r in results if r.status == GenerationStatus.SUCCESS)
        failed = total - successful

        # Calculate percentages
        success_pct = (successful / total * 100) if total > 0 else 0

        # Build summary text
        summary_lines = [
            f"Total Examples:     {total}",
            f"[green]Successful:[/green]        {successful} ({success_pct:.1f}%)",
        ]

        if failed > 0:
            fail_pct = failed / total * 100
            summary_lines.append(f"[red]Failed:[/red]            {failed} ({fail_pct:.1f}%)")

        summary_text = "\n".join(summary_lines)

        if self.use_rich:
            # Choose border color based on results
            border_color = "green" if failed == 0 else ("yellow" if failed < total // 2 else "red")

            self.console.print(
                Panel(summary_text, title="[bold]Summary[/bold]", box=box.ROUNDED, border_style=border_color)
            )
        else:
            print("\n" + "=" * 60)
            print("SUMMARY")
            print("=" * 60)
            print(f"Total: {total}")
            print(f"Successful: {successful}")
            print(f"Failed: {failed}")
            print("=" * 60)

    def print_detailed_issues(self, results: List[GenerationResult]):
        """Print detailed error information for failed generations"""
        failed_results = [r for r in results if r.status == GenerationStatus.FAILED]

        if not failed_results:
            return

        if self.use_rich:
            self.console.print("\n[bold red]Failed Generations:[/bold red]\n")

            for result in failed_results:
                error_panel = Panel(
                    f"[red]{result.error}[/red]",
                    title=f"[bold]{result.rel_path}[/bold]",
                    border_style="red",
                    box=box.ROUNDED,
                )
                self.console.print(error_panel)
        else:
            print("\nFailed Generations:")
            for result in failed_results:
                print(f"\n  {result.rel_path}")
                print(f"    Error: {result.error}")


# RPI device examples identified from the examples directory
RPI_EXAMPLES = [
    # smauto (Smart Automation examples with RPI)
    ("examples/smauto/EntranceLEDs.dev", "rpi_out/smauto/EntranceLEDs"),
    ("examples/smauto/ParkingLeds.dev", "rpi_out/smauto/ParkingLeds"),
    ("examples/smauto/ParkingSensor.dev", "rpi_out/smauto/ParkingSensor"),
    ("examples/smauto/RPiFan.dev", "rpi_out/smauto/RPiFan"),
    ("examples/smauto/SmartWindow.dev", "rpi_out/smauto/SmartWindow"),
    # rpi (Raspberry Pi examples)
    ("examples/rpi/RPi_ADC.dev", "rpi_out/rpi/RPi_ADC"),
    ("examples/rpi/RPi_gas_led.dev", "rpi_out/rpi/RPi_gas_led"),
    ("examples/rpi/rpi5_ToF.dev", "rpi_out/rpi/rpi5_ToF"),
    ("examples/rpi/rpi_5_TCRT.dev", "rpi_out/rpi/rpi_5_TCRT"),
    ("examples/rpi/rpi_constraint_bme.dev", "rpi_out/rpi/rpi_constraint_bme"),
    ("examples/rpi/rpi_iot_device.dev", "rpi_out/rpi/rpi_iot_device"),
]


def generate_with_progress(
    examples: List[Tuple[str, str]], reporter: GenerationReporter, skip_semantics: bool = False
) -> List[GenerationResult]:
    """Generate code for all examples with progress tracking"""
    results = []

    if reporter.use_rich:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=reporter.console,
        ) as progress:
            task = progress.add_task("[cyan]Generating code...", total=len(examples))

            for dev_model, output_dir in examples:
                progress.update(task, description=f"[cyan]Processing {dev_model}...")

                try:
                    transform_device_model(dev_model, output_dir, skip_semantics=skip_semantics)
                    results.append(
                        GenerationResult(dev_model=dev_model, output_dir=output_dir, status=GenerationStatus.SUCCESS)
                    )
                except Exception as e:
                    results.append(
                        GenerationResult(
                            dev_model=dev_model, output_dir=output_dir, status=GenerationStatus.FAILED, error=str(e)
                        )
                    )

                progress.advance(task)
    else:
        # Fallback without progress bar
        for i, (dev_model, output_dir) in enumerate(examples, 1):
            print(f"[{i}/{len(examples)}] Processing {dev_model}...")

            try:
                transform_device_model(dev_model, output_dir, skip_semantics=skip_semantics)
                results.append(
                    GenerationResult(dev_model=dev_model, output_dir=output_dir, status=GenerationStatus.SUCCESS)
                )
                print("  ✓ Success")
            except Exception as e:
                results.append(
                    GenerationResult(
                        dev_model=dev_model, output_dir=output_dir, status=GenerationStatus.FAILED, error=str(e)
                    )
                )
                print(f"  ✗ Failed: {e}")

    return results


import argparse


def main():
    """Run m2t_rpi transformation on all RPI examples."""
    parser = argparse.ArgumentParser(description="DeMoL RPI Code Generator")
    parser.add_argument("--skip-semantics", action="store_true", help="Skip semantic validation")
    args = parser.parse_args()

    # Create reporter
    reporter = GenerationReporter()

    # Print header
    reporter.print_header("DeMoL RPI Code Generator")

    # Show example count
    reporter.print(f"\n[cyan]Found {len(RPI_EXAMPLES)} RPI example(s)[/cyan]\n")

    # Generate code with progress
    results = generate_with_progress(RPI_EXAMPLES, reporter, skip_semantics=args.skip_semantics)

    # Display results
    reporter.print("")

    if reporter.use_rich:
        reporter.console.print(reporter.create_summary_table(results))
    else:
        # Simple text output
        for result in results:
            status = "SUCCESS" if result.status == GenerationStatus.SUCCESS else "FAILED"
            print(f"{status}: {result.rel_path}")

    reporter.print("")
    reporter.print_summary_panel(results)

    # Print detailed issues if any
    failed_count = sum(1 for r in results if r.status == GenerationStatus.FAILED)
    if failed_count > 0:
        reporter.print("")
        reporter.print_detailed_issues(results)

    # Exit with appropriate code
    sys.exit(0 if failed_count == 0 else 1)


if __name__ == "__main__":
    main()
