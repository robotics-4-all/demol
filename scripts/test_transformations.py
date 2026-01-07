#!/usr/bin/env python3
"""
DeMoL Transformation Test Script

This script tests code generation for all platforms by generating code
from test models and verifying the output.
"""

import sys
import shutil
from pathlib import Path
from dataclasses import dataclass
from typing import List
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

from demol.transformations import (
    m2t_rpi,
    m2t_riot,
    m2m_smauto,
    demol_to_json,
    m2t_docs
)
import json

class TestStatus(Enum):
    """Test result status"""
    PASS = "pass"
    FAIL = "fail"


@dataclass
class TransformationTestResult:
    """Result of a single transformation test"""
    model_path: str
    platform: str
    output_dir: str
    status: TestStatus
    error_message: str = ""
    files_generated: List[str] = None
    
    def __post_init__(self):
        if self.files_generated is None:
            self.files_generated = []
    
    @property
    def passed(self) -> bool:
        return self.status == TestStatus.PASS


class TransformationTester:
    """Test runner for DeMoL code generation"""
    
    def __init__(self):
        self.use_rich = RICH_AVAILABLE
        if self.use_rich:
            self.console = Console()
        self.results: List[TransformationTestResult] = []
    
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
    
    def test_transformation(
        self,
        model_path: Path,
        platform: str,
        output_dir: Path
    ) -> TransformationTestResult:
        """
        Test code generation for a single model and platform.
        
        Args:
            model_path: Path to the .dev model file
            platform: Target platform (rpi, riot, json, smauto, docs)
            output_dir: Output directory for generated code
            
        Returns:
            TransformationTestResult object
        """
        # Clean output directory if it exists
        if output_dir.exists():
            shutil.rmtree(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # Build model first
            from demol.lang import build_model
            model = build_model(str(model_path), skip_semantics=False)
            
            # Generate code based on platform
            if platform == "rpi":
                m2t_rpi(model, str(output_dir))
                pattern = "*.py"
            elif platform == "riot":
                m2t_riot(model, str(output_dir))
                pattern = "*.*" # Matches .c, .h, Makefile etc.
            elif platform == "json":
                filename = output_dir / f'{model.metadata.name}.json'
                with open(filename, 'w') as f:
                    json.dump(demol_to_json(model), f, indent=4)
                pattern = "*.json"
            elif platform == "smauto":
                m2m_smauto(model, output_dir=str(output_dir))
                pattern = "*.auto"
            elif platform == "docs":
                m2t_docs(model, output_dir=str(output_dir))
                pattern = "*.*" # Matches .md, .svg
            else:
                raise NotImplementedError(f"Platform {platform} not yet implemented in test")
            
            # Check if files were generated
            files_generated = list(output_dir.glob(pattern))
            
            if files_generated:
                status = TestStatus.PASS
                error_msg = ""
            else:
                status = TestStatus.FAIL
                error_msg = f"No files generated matching {pattern}"
            
        except Exception as e:
            status = TestStatus.FAIL
            error_msg = str(e)
            files_generated = []
        
        return TransformationTestResult(
            model_path=str(model_path.relative_to(REPO_PATH)),
            platform=platform,
            output_dir=str(output_dir.relative_to(REPO_PATH)),
            status=status,
            error_message=error_msg,
            files_generated=[str(f.relative_to(REPO_PATH)) for f in files_generated]
        )
    
    def run_tests(
        self,
        test_dir: Path,
        platform: str,
        output_base: Path
    ) -> List[TransformationTestResult]:
        """
        Run transformation tests on all models in a directory.
        
        Args:
            test_dir: Directory containing test models
            platform: Target platform
            output_base: Base directory for generated code
            
        Returns:
            List of TransformationTestResult objects
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
                    f"[cyan]Testing {platform} generation...",
                    total=len(model_files)
                )
                
                for model_file in model_files:
                    progress.update(task, description=f"[cyan]Generating {model_file.name}...")
                    output_dir = output_base / model_file.stem
                    result = self.test_transformation(model_file, platform, output_dir)
                    results.append(result)
                    progress.advance(task)
        else:
            for i, model_file in enumerate(model_files, 1):
                print(f"[{i}/{len(model_files)}] Generating {model_file.name}...")
                output_dir = output_base / model_file.stem
                result = self.test_transformation(model_file, platform, output_dir)
                results.append(result)
                status_symbol = "✓" if result.passed else "✗"
                print(f"  {status_symbol} {result.status.value.upper()}")
        
        return results
    
    def create_results_table(self, results: List[TransformationTestResult]) -> Table:
        """Create a rich table summarizing test results"""
        table = Table(title="Transformation Test Results", box=box.ROUNDED)
        
        table.add_column("Model", style="cyan", no_wrap=False)
        table.add_column("Platform", justify="center")
        table.add_column("Files", justify="center")
        table.add_column("Status", justify="center")
        
        for result in results:
            if result.status == TestStatus.PASS:
                status = "[green]✓ PASS[/green]"
            else:
                status = "[red]✗ FAIL[/red]"
            
            table.add_row(
                result.model_path,
                result.platform,
                str(len(result.files_generated)),
                status
            )
        
        return table
    
    def print_summary(self, results: List[TransformationTestResult]):
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
    
    def print_failures(self, results: List[TransformationTestResult]):
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
                    subtitle=f"Platform: {result.platform}",
                    border_style="red",
                    box=box.ROUNDED
                )
                self.console.print(error_panel)
        else:
            print("\nFailed Tests:")
            for result in failed_results:
                print(f"\n  {result.model_path}")
                print(f"    Platform: {result.platform}")
                if result.error_message:
                    print(f"    Error: {result.error_message}")


def main():
    """Main entry point for transformation testing"""
    tester = TransformationTester()
    
    # Print header
    tester.print_header("DeMoL Transformation Test Suite")
    
    # Define test directories
    valid_dir = REPO_PATH / "tests" / "models" / "valid"
    output_base = REPO_PATH / "tests" / "output"
    
    all_results = []

    # 1. Test RPI Code Generation
    tester.print("\n[bold cyan]Testing RPI Code Generation[/bold cyan]\n")
    rpi_output = output_base / "rpi"
    rpi_results = tester.run_tests(valid_dir, "rpi", rpi_output)
    all_results.extend(rpi_results)

    # 2. Test RIOT Code Generation
    tester.print("\n[bold cyan]Testing RIOT Code Generation[/bold cyan]\n")
    riot_output = output_base / "riot"
    riot_results = tester.run_tests(valid_dir, "riot", riot_output)
    all_results.extend(riot_results)

    # 3. Test JSON Generation
    tester.print("\n[bold cyan]Testing JSON Generation[/bold cyan]\n")
    json_output = output_base / "json"
    json_results = tester.run_tests(valid_dir, "json", json_output)
    all_results.extend(json_results)

    # 4. Test SMAUTO Generation
    tester.print("\n[bold cyan]Testing SMAUTO Generation[/bold cyan]\n")
    smauto_output = output_base / "smauto"
    smauto_results = tester.run_tests(valid_dir, "smauto", smauto_output)
    all_results.extend(smauto_results)

    # 5. Test Documentation Generation
    tester.print("\n[bold cyan]Testing Documentation Generation[/bold cyan]\n")
    docs_output = output_base / "docs"
    docs_results = tester.run_tests(valid_dir, "docs", docs_output)
    all_results.extend(docs_results)
    
    # Display results
    tester.print("")
    if tester.use_rich:
        tester.console.print(tester.create_results_table(all_results))
    else:
        for result in all_results:
            status = "PASS" if result.passed else "FAIL"
            print(f"{status}: {result.model_path} ({result.platform})")
    
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
