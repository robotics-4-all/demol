"""
Validation functionality for DeMoL with enhanced reporting.

This module provides validation utilities with professional output using
the rich library for progress bars, colored output, and formatted tables.
"""

import os
import warnings
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass
from enum import Enum

from textx import TextXSemanticError, TextXSyntaxError

try:
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn
    from rich.table import Table
    from rich.panel import Panel
    from rich import box
    from rich.text import Text
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    Console = None


class ValidationStatus(Enum):
    """Validation result status"""
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"


ACTIVE_VALIDATIONS = [
    ("WF-All-Peripherals-Connected", "All peripherals must be connected"),
    ("WF-Broker-Requirements", "Broker required if endpoints used"),
    ("WF-Common-Ground", "Common ground connection required"),
    ("Conn-Power", "Power connection compatibility"),
    ("Conn-GPIO", "GPIO functionality check"),
    ("Conn-I2C", "I2C functionality and address check"),
    ("Conn-SPI", "SPI functionality check"),
    ("Conn-UART", "UART functionality and baudrate check"),
    ("Safety-Pin-Conflicts", "No pin conflicts (unique pins)"),
    ("Safety-I2C-Address", "Unique I2C addresses"),
    ("Safety-Voltage-Limits", "Voltage limits check"),
    ("Safety-IO-Voltage", "IO Voltage compatibility"),
    ("WF-Unique-Pin-Numbers", "Pin numbers must be unique within a component"),
]


@dataclass
class ValidationResult:
    """Container for validation results"""
    file_path: str
    status: ValidationStatus
    warnings: List[str]
    errors: List[str]
    
    @property
    def rel_path(self) -> str:
        """Get relative path from current directory"""
        return os.path.relpath(self.file_path, os.getcwd())
    
    @property
    def has_issues(self) -> bool:
        """Check if there are any warnings or errors"""
        return len(self.warnings) > 0 or len(self.errors) > 0


class ValidationReporter:
    """Reporter for validation results with rich output"""
    
    def __init__(self, use_rich: bool = True):
        """
        Initialize reporter.
        
        Args:
            use_rich: Whether to use rich output (if available)
        """
        self.use_rich = use_rich and RICH_AVAILABLE
        self.console = Console() if self.use_rich else None
    
    def print(self, message: str, style: Optional[str] = None):
        """Print a message with optional styling"""
        if self.use_rich and self.console:
            self.console.print(message, style=style)
        else:
            print(message)

    def print_active_validations(self) -> None:
        """Print the list of active validations"""
        if self.use_rich:
            table = Table(
                title="Active Validations",
                box=box.SIMPLE,
                show_header=True,
                header_style="bold magenta",
                title_style="bold white",
            )
            table.add_column("Validation ID", style="cyan", width=30)
            table.add_column("Description", style="white")

            for val_id, desc in ACTIVE_VALIDATIONS:
                table.add_row(val_id, desc)
            
            self.console.print(table)
            self.console.print()  # Add empty line
        else:
            print("\nActive Validations:")
            print("=" * 50)
            for val_id, desc in ACTIVE_VALIDATIONS:
                print(f"{val_id:<30} {desc}")
            print("=" * 50 + "\n")
    
    def create_summary_table(self, results: List[ValidationResult]) -> 'Table':
        """Create a formatted summary table of validation results"""
        if not self.use_rich:
            raise RuntimeError("Rich library is not available")
        
        table = Table(
            title="Validation Results",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold cyan",
            title_style="bold white",
        )
        
        table.add_column("Model File", style="white", no_wrap=False, width=40)
        table.add_column("Status", justify="center", width=10)
        table.add_column("Warnings", justify="center", style="yellow", width=10)
        table.add_column("Errors", justify="center", style="red", width=10)
        
        for result in results:
            # Determine status display
            if result.status == ValidationStatus.PASS:
                status_display = Text("✓ PASS", style="bold green")
            elif result.status == ValidationStatus.WARN:
                status_display = Text("⚠ WARN", style="bold yellow")
            else:
                status_display = Text("✗ FAIL", style="bold red")
            
            # Shorten path for display
            file_display = result.rel_path
            if len(file_display) > 38:
                file_display = "..." + file_display[-35:]
            
            table.add_row(
                file_display,
                status_display,
                str(len(result.warnings)) if result.warnings else "-",
                str(len(result.errors)) if result.errors else "-"
            )
        
        return table

    def create_failure_table(self, results: List[ValidationResult]) -> 'Table':
        """Create a table showing specific validation failures"""
        if not self.use_rich:
            raise RuntimeError("Rich library is not available")

        table = Table(
            title="Validation Failures",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold red",
            title_style="bold white",
        )

        table.add_column("Model File", style="white", width=30)
        table.add_column("Failed Validation", style="red", width=25)
        table.add_column("Error Message", style="dim white")

        failed_results = [r for r in results if r.status == ValidationStatus.FAIL]

        for result in failed_results:
            file_display = result.rel_path
            if len(file_display) > 28:
                file_display = "..." + file_display[-25:]

            for error in result.errors:
                # Try to extract validation ID from error message if present
                # Assuming error format "[ValidationID] Message" or similar
                val_id = "Unknown"
                message = error
                
                import re
                match = re.search(r'\[(WF-[^\]]+|Conn-[^\]]+|Safety-[^\]]+)\]', error)
                if match:
                    val_id = match.group(1)
                    # Optional: strip the ID from the message for cleaner display
                    # message = error.replace(f"[{val_id}]", "").strip()
                
                table.add_row(file_display, val_id, message)

        return table
    
    def print_detailed_issues(self, results: List[ValidationResult]) -> None:
        """Print detailed information about warnings and errors"""
        if not self.use_rich:
            # Fallback to simple text output
            self._print_detailed_issues_simple(results)
            return
        
        # Group by status
        warnings_results = [r for r in results if r.status == ValidationStatus.WARN]
        failed_results = [r for r in results if r.status == ValidationStatus.FAIL]
        
        if warnings_results:
            self.console.print("\n[bold yellow]⚠ Files with Warnings:[/bold yellow]")
            for result in warnings_results:
                self.console.print(f"\n[yellow]• {result.rel_path}[/yellow]")
                for i, warning in enumerate(result.warnings, 1):
                    # Display full warning message without truncation
                    # Use wrapping for better readability
                    self.console.print(f"  {i}. {warning}", style="dim yellow", soft_wrap=True)
        
        if failed_results:
            self.console.print("\n[bold red]✗ Failed Files:[/bold red]")
            for result in failed_results:
                self.console.print(f"\n[red]• {result.rel_path}[/red]")
                for i, error in enumerate(result.errors, 1):
                    # Display full error message without truncation
                    # Use wrapping for better readability
                    self.console.print(f"  {i}. {error}", style="dim red", soft_wrap=True)
    
    def _print_detailed_issues_simple(self, results: List[ValidationResult]) -> None:
        """Fallback for printing detailed issues without rich"""
        warnings_results = [r for r in results if r.status == ValidationStatus.WARN]
        failed_results = [r for r in results if r.status == ValidationStatus.FAIL]
        
        if warnings_results:
            print("\n⚠ Files with Warnings:")
            for result in warnings_results:
                print(f"\n• {result.rel_path}")
                for i, warning in enumerate(result.warnings, 1):
                    # Display full warning without truncation
                    print(f"  {i}. {warning}")
        
        if failed_results:
            print("\n✗ Failed Files:")
            for result in failed_results:
                print(f"\n• {result.rel_path}")
                for i, error in enumerate(result.errors, 1):
                    # Display full error without truncation
                    print(f"  {i}. {error}")
    
    def print_summary_panel(self, results: List[ValidationResult]) -> None:
        """Print a summary panel with counts"""
        passed = sum(1 for r in results if r.status == ValidationStatus.PASS)
        warned = sum(1 for r in results if r.status == ValidationStatus.WARN)
        failed = sum(1 for r in results if r.status == ValidationStatus.FAIL)
        
        if self.use_rich:
            summary_text = Text()
            summary_text.append(f"Total: {len(results)} files\n", style="bold white")
            summary_text.append(f"✓ Passed: {passed}\n", style="bold green")
            summary_text.append(f"⚠ Warnings: {warned}\n", style="bold yellow")
            summary_text.append(f"✗ Failed: {failed}", style="bold red")
            
            panel = Panel(
                summary_text,
                title="[bold]Summary[/bold]",
                border_style="cyan",
                padding=(1, 2)
            )
            
            self.console.print(panel)
        else:
            # Simple text output
            print("\n" + "="*50)
            print("SUMMARY")
            print("="*50)
            print(f"Total: {len(results)} files")
            print(f"✓ Passed: {passed}")
            print(f"⚠ Warnings: {warned}")
            print(f"✗ Failed: {failed}")

        if failed > 0 and self.use_rich:
             self.console.print()
             self.console.print(self.create_failure_table(results))
    
    def print_header(self, title: str) -> None:
        """Print a header"""
        if self.use_rich:
            self.console.print(Panel.fit(
                f"[bold cyan]{title}[/bold cyan]",
                border_style="cyan"
            ))
        else:
            print("\n" + "="*50)
            print(title)
            print("="*50)


def validate_model_file(file_path: str, metamodel) -> ValidationResult:
    """
    Validate a single model file.
    
    Args:
        file_path: Path to the model file
        metamodel: TextX metamodel to use for validation
        
    Returns:
        ValidationResult with status and any warnings/errors
    """
    from demol.lang.semantics import (
        get_validation_errors, 
        get_validation_warnings,
        get_passed_rules, 
        clear_validation_results,
        ValidationError
    )
    
    warnings_list = []
    errors_list = []
    status = ValidationStatus.PASS
    
    # Clear previous results
    clear_validation_results()
    
    # Capture warnings during validation
    with warnings.catch_warnings(record=True) as caught_warnings:
        warnings.simplefilter("always")
        
        try:
            # Set skip_semantics on metamodel if we want to collect all errors
            # but we'll respect what's already there.
            metamodel.model_from_file(file_path)
            
            # Check for collected errors even if no exception was raised
            # (this happens if skip_semantics=True)
            collected_errors = get_validation_errors()
            if collected_errors:
                for err in collected_errors:
                    errors_list.append(err['msg'])
                
                # If skip_semantics is enabled, we treat these as warnings
                # so the validation process can continue/pass
                if getattr(metamodel, 'skip_semantics', False):
                    status = ValidationStatus.WARN
                else:
                    status = ValidationStatus.FAIL
            
            # Check for collected semantic warnings
            collected_warnings = get_validation_warnings()
            if collected_warnings:
                for warn in collected_warnings:
                    warnings_list.append(warn['msg'])
                if status == ValidationStatus.PASS:
                    status = ValidationStatus.WARN

            # Check if any Python warnings were captured
            if caught_warnings:
                for w in caught_warnings:
                    warning_msg = str(w.message)
                    warnings_list.append(warning_msg)
                if status == ValidationStatus.PASS:
                    status = ValidationStatus.WARN
            
        except (ValidationError, TextXSemanticError, TextXSyntaxError) as e:
            # Check collected errors first for more detail
            collected_errors = get_validation_errors()
            if collected_errors:
                for err in collected_errors:
                    errors_list.append(err['msg'])
            else:
                errors_list.append(str(e))
            
            # If skip_semantics is enabled and it's a semantic error, treat as warning
            if getattr(metamodel, 'skip_semantics', False) and isinstance(e, (ValidationError, TextXSemanticError)):
                status = ValidationStatus.WARN
            else:
                status = ValidationStatus.FAIL
        except Exception as e:
            errors_list.append(f"Unexpected error: {str(e)}")
            status = ValidationStatus.FAIL
    
    return ValidationResult(
        file_path=file_path,
        status=status,
        warnings=warnings_list,
        errors=errors_list
    )
    

def validate_models(
    file_paths: List[str],
    metamodel,
    show_progress: bool = True,
    reporter: Optional[ValidationReporter] = None
) -> List[ValidationResult]:
    """
    Validate multiple model files with optional progress display.
    
    Args:
        file_paths: List of file paths to validate
        metamodel: TextX metamodel to use
        show_progress: Whether to show progress bar
        reporter: Optional reporter instance (creates default if None)
        
    Returns:
        List of ValidationResult objects
    """
    if reporter is None:
        reporter = ValidationReporter()
    
    # Print active validations at the start
    reporter.print_active_validations()

    results: List[ValidationResult] = []
    
    if show_progress and reporter.use_rich:
        # Use rich progress bar
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=reporter.console
        ) as progress:
            task = progress.add_task("[cyan]Validating...", total=len(file_paths))
            
            for file_path in file_paths:
                rel_path = os.path.relpath(file_path, os.getcwd())
                display_path = rel_path if len(rel_path) < 40 else "..." + rel_path[-37:]
                progress.update(task, description=f"[cyan]Validating {display_path}")
                
                result = validate_model_file(file_path, metamodel)
                results.append(result)
                
                progress.advance(task)
    else:
        # Simple validation without progress bar
        for file_path in file_paths:
            result = validate_model_file(file_path, metamodel)
            results.append(result)
            
            if show_progress:
                status_symbol = "✓" if result.status == ValidationStatus.PASS else ("⚠" if result.status == ValidationStatus.WARN else "✗")
                print(f"{status_symbol} {result.rel_path}")
    
    # Print summary
    reporter.print_summary_panel(results)
    
    return results
