import os
import sys
import logging
import shutil
import time
from pathlib import Path
import py_compile

# Add current directory to sys.path to import demol
sys.path.append(os.getcwd())

from demol.transformations.m2t_rpi import transform_device_model
from demol.lang.semantics import get_validation_errors, get_validation_warnings, clear_validation_results

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("Evaluator")

# Colors for terminal
GREEN = "\033[92m"
RED = "\033[91m"
BLUE = "\033[94m"
YELLOW = "\033[93m"
RESET = "\033[0m"

def evaluate_examples():
    examples_dir = Path("examples/rpi")
    output_base_dir = Path("temp_gen_output")
    
    if output_base_dir.exists():
        shutil.rmtree(output_base_dir)
    output_base_dir.mkdir()

    if not examples_dir.exists():
        logger.error(f"Examples directory {examples_dir} not found!")
        return

    examples = list(examples_dir.glob("*.dev"))
    results = []

    logger.info(f"{BLUE}Starting evaluation of {len(examples)} examples...{RESET}")
    logger.info("="*60)

    for example_path in examples:
        example_name = example_path.name
        output_dir = output_base_dir / example_path.stem
        output_dir.mkdir()

        logger.info(f"Evaluating {BLUE}{example_name}{RESET}...")
        start_time = time.time()
        
        clear_validation_results()
        try:
            # Run transformation
            # Note: transform_device_model might log its own things
            transform_device_model(str(example_path), str(output_dir), skip_semantics=False)
            
            # Check if files were generated
            generated_files = list(output_dir.glob("*.py"))
            if not generated_files:
                raise Exception("No python files generated")

            # Syntax check generated files
            syntax_errors = []
            for gen_file in generated_files:
                try:
                    # We use a dummy check here because some generated files might 
                    # depend on others that are not in the same dir or not yet installed
                    # But py_compile.compile just checks syntax.
                    py_compile.compile(str(gen_file), doraise=True)
                except py_compile.PyCompileError as e:
                    syntax_errors.append(f"{gen_file.name}: {str(e)}")
                except Exception as e:
                    # Some files might have jinja2 tags if not rendered correctly
                    # but transform_device_model should have rendered them.
                    syntax_errors.append(f"{gen_file.name}: {str(e)}")

            duration = time.time() - start_time
            
            v_warnings = get_validation_warnings()
            warn_msgs = [w['msg'] for w in v_warnings]

            if syntax_errors:
                results.append({
                    "name": example_name,
                    "status": "SYNTAX_ERROR",
                    "duration": duration,
                    "errors": syntax_errors,
                    "warnings": warn_msgs
                })
                logger.error(f"{RED}FAILED{RESET} {example_name} (Syntax Errors)")
                for err in syntax_errors:
                    logger.error(f"  - {err}")
            else:
                results.append({
                    "name": example_name,
                    "status": "SUCCESS",
                    "duration": duration,
                    "files_count": len(generated_files),
                    "warnings": warn_msgs
                })
                logger.info(f"{GREEN}PASSED{RESET} {example_name} in {duration:.2f}s ({len(generated_files)} files)")
                if warn_msgs:
                    for msg in warn_msgs:
                        logger.warning(f"  - {msg}")

        except Exception as e:
            duration = time.time() - start_time
            v_errors = get_validation_errors()
            v_warnings = get_validation_warnings()
            warn_msgs = [w['msg'] for w in v_warnings]

            if v_errors:
                err_msgs = [err['msg'] for err in v_errors]
                results.append({
                    "name": example_name,
                    "status": "VALIDATION_ERROR",
                    "duration": duration,
                    "errors": err_msgs,
                    "warnings": warn_msgs
                })
                logger.error(f"{RED}FAILED{RESET} {example_name} (Validation Errors)")
                for msg in err_msgs:
                    logger.error(f"  - {msg}")
            else:
                results.append({
                    "name": example_name,
                    "status": "FAILED",
                    "duration": duration,
                    "error": str(e),
                    "warnings": warn_msgs
                })
                logger.error(f"{RED}FAILED{RESET} {example_name}: {str(e)}")
            
            if warn_msgs:
                for msg in warn_msgs:
                    logger.warning(f"  - {msg}")

    # Final Report
    print("\n" + "="*60)
    print(f"{BLUE}FINAL EVALUATION REPORT{RESET}")
    print("="*60)
    print(f"{'Example Name':35} | {'Status':15} | {'Duration':10}")
    print("-" * 60)
    
    passed_count = 0
    failed_count = 0
    
    for r in results:
        status = r["status"]
        if status == "SUCCESS":
            status_color = GREEN
            passed_count += 1
        else:
            status_color = RED
            failed_count += 1
            
        print(f"{r['name']:35} | {status_color}{status:15}{RESET} | {r['duration']:.2f}s")

    print("="*60)
    print(f"Total: {len(results)} | {GREEN}Passed: {passed_count}{RESET} | {RED}Failed: {failed_count}{RESET}")
    print("="*60)

    if failed_count > 0:
        sys.exit(1)

if __name__ == "__main__":
    evaluate_examples()
