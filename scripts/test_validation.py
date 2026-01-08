#!/usr/bin/env python3
"""
DeMoL Validation Test Script

This script tests the validation functionality of the DeMoL DSL by running
validation on both valid and invalid test models and verifying the results.
"""

import sys
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Optional
from enum import Enum

# Add project root to path
REPO_PATH = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_PATH))

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

from demol.lang import build_model


class TestStatus(Enum):
    """Test result status"""
    PASS = "pass"
    FAIL = "fail"
    ERROR = "error"


@dataclass
class ValidationTestResult:
    """Result of a single validation test"""
    model_path: str
    expected_result: str  # "valid" or "invalid"
    actual_result: str    # "valid" or "invalid"
    status: TestStatus
    error_message: str = ""
    validation_errors: List[str] = None
    
    def __post_init__(self):
        if self.validation_errors is None:
            self.validation_errors = []
    
    @property
    def passed(self) -> bool:
        return self.status == TestStatus.PASS


class ValidationTester:
    """Test runner for DeMoL validation"""
    
    def __init__(self):
        self.use_rich = RICH_AVAILABLE
        if self.use_rich:
            self.console = Console()
        self.results: List[ValidationTestResult] = []
    
    def print(self, message, **kwargs):
        """Print with rich if available, otherwise plain"""
        if self.use_rich:
            self.console.print(message, **kwargs)
        else:
            print(message)
    
    def print_header(self, title: str):
        """Print a styled header"""
        if self.use_rich:
            self.console.print(Panel(
                f"[bold cyan]{title}[/bold cyan]",
                box=box.DOUBLE,
                border_style="cyan"
            ))
        else:
            print(f"\n{'='*60}")
            print(f"  {title}")
            print(f"{'='*60}\n")
    
    def validate_model(self, model_path: Path, expected_result: str) -> ValidationTestResult:
        """
        Validate a single model and check if result matches expectation.
        
        Args:
            model_path: Path to the .dev model file
            expected_result: Either "valid" or "invalid"
            
        Returns:
            ValidationTestResult object
        """
        try:
            # Try to build the model
            model = build_model(str(model_path), skip_semantics=False)
            actual_result = "valid"
            error_msg = ""
            validation_errors = []
            
        except Exception as e:
            actual_result = "invalid"
            error_msg = str(e)
            validation_errors = [error_msg]
        
        # Determine test status
        if actual_result == expected_result:
            status = TestStatus.PASS
        else:
            status = TestStatus.FAIL
        
        return ValidationTestResult(
            model_path=str(model_path.relative_to(REPO_PATH)),
            expected_result=expected_result,
            actual_result=actual_result,
            status=status,
            error_message=error_msg,
            validation_errors=validation_errors
        )
    
    def run_tests(self, test_dir: Path, expected_result: str) -> List[ValidationTestResult]:
        """
        Run validation tests on all models in a directory.
        
        Args:
            test_dir: Directory containing test models
            expected_result: Expected validation result ("valid" or "invalid")
            
        Returns:
            List of ValidationTestResult objects
        """
        results = []
        model_files = sorted(test_dir.glob("*.dev"))
        
        if not model_files:
            self.print(f"[yellow]No test models found in {test_dir}[/yellow]")
            return results
        
        if self.use_rich:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console
            ) as progress:
                task = progress.add_task(
                    f"[cyan]Testing {expected_result} models...",
                    total=len(model_files)
                )
                
                for model_file in model_files:
                    progress.update(task, description=f"[cyan]Testing {model_file.name}...")
                    result = self.validate_model(model_file, expected_result)
                    results.append(result)
                    progress.advance(task)
        else:
            for i, model_file in enumerate(model_files, 1):
                print(f"[{i}/{len(model_files)}] Testing {model_file.name}...")
                result = self.validate_model(model_file, expected_result)
                results.append(result)
                status_symbol = "✓" if result.passed else "✗"
                print(f"  {status_symbol} {result.status.value.upper()}")
        
        return results
    
    def create_results_table(self, results: List[ValidationTestResult]) -> "Table":
        """Create a rich table summarizing test results"""
        table = Table(title="Validation Test Results", box=box.ROUNDED)
        
        table.add_column("Model", style="cyan", no_wrap=False)
        table.add_column("Expected", justify="center")
        table.add_column("Actual", justify="center")
        table.add_column("Status", justify="center")
        
        for result in results:
            if result.status == TestStatus.PASS:
                status = "[green]✓ PASS[/green]"
            elif result.status == TestStatus.FAIL:
                status = "[red]✗ FAIL[/red]"
            else:
                status = "[yellow]⚠ ERROR[/yellow]"
            
            expected_color = "green" if result.expected_result == "valid" else "red"
            actual_color = "green" if result.actual_result == "valid" else "red"
            
            table.add_row(
                result.model_path,
                f"[{expected_color}]{result.expected_result}[/{expected_color}]",
                f"[{actual_color}]{result.actual_result}[/{actual_color}]",
                status
            )
        
        return table
    
    def print_summary(self, results: List[ValidationTestResult]):
        """Print summary statistics"""
        total = len(results)
        passed = sum(1 for r in results if r.passed)
        failed = total - passed
        
        success_pct = (passed / total * 100) if total > 0 else 0
        
        summary_lines = [
            f"Total Tests:        {total}",
            f"[green]Passed:[/green]            {passed} ({success_pct:.1f}%)",
        ]
        
        if failed > 0:
            fail_pct = (failed / total * 100)
            summary_lines.append(f"[red]Failed:[/red]            {failed} ({fail_pct:.1f}%)")
        
        summary_text = "\n".join(summary_lines)
        
        if self.use_rich:
            border_color = "green" if failed == 0 else "red"
            self.console.print(Panel(
                summary_text,
                title="[bold]Summary[/bold]",
                box=box.ROUNDED,
                border_style=border_color
            ))
        else:
            print("\n" + "="*60)
            print("SUMMARY")
            print("="*60)
            print(f"Total: {total}")
            print(f"Passed: {passed}")
            print(f"Failed: {failed}")
            print("="*60)
    
    def print_failures(self, results: List[ValidationTestResult]):
        """Print detailed information about failed tests"""
        failed_results = [r for r in results if not r.passed]
        
        if not failed_results:
            return
        
        if self.use_rich:
            self.console.print("\n[bold red]Failed Tests:[/bold red]\n")
            
            for result in failed_results:
                error_text = result.error_message if result.error_message else "No error message"
                error_panel = Panel(
                    f"[red]{error_text}[/red]",
                    title=f"[bold]{result.model_path}[/bold]",
                    subtitle=f"Expected: {result.expected_result}, Got: {result.actual_result}",
                    border_style="red",
                    box=box.ROUNDED
                )
                self.console.print(error_panel)
        else:
            print("\nFailed Tests:")
            for result in failed_results:
                print(f"\n  {result.model_path}")
                print(f"    Expected: {result.expected_result}, Got: {result.actual_result}")
                if result.error_message:
                    print(f"    Error: {result.error_message}")


def main():
    """Main entry point for validation testing"""
    tester = ValidationTester()
    
    # Print header
    tester.print_header("DeMoL Validation Test Suite")
    
    # Define test directories
    valid_dir = REPO_PATH / "tests" / "models" / "valid"
    invalid_dir = REPO_PATH / "tests" / "models" / "invalid"
    
    # Run tests on valid models
    tester.print("\n[bold cyan]Testing Valid Models[/bold cyan]\n")
    valid_results = tester.run_tests(valid_dir, "valid")
    
    # Run tests on invalid models
    tester.print("\n[bold cyan]Testing Invalid Models[/bold cyan]\n")
    invalid_results = tester.run_tests(invalid_dir, "invalid")
    
    # Combine results
    all_results = valid_results + invalid_results
    
    # Display results
    tester.print("")
    if tester.use_rich:
        tester.console.print(tester.create_results_table(all_results))
    else:
        for result in all_results:
            status = "PASS" if result.passed else "FAIL"
            print(f"{status}: {result.model_path}")
    
    tester.print("")
    tester.print_summary(all_results)
    
    # Print failures if any
    if any(not r.passed for r in all_results):
        tester.print("")
        tester.print_failures(all_results)
    
    # Exit with appropriate code
    sys.exit(0 if all(r.passed for r in all_results) else 1)


if __name__ == "__main__":
    main()
