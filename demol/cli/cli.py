import click
import os
import sys
from demol.lang import build_model
from demol.lang.semantics import (
    get_validation_errors,
    get_passed_rules,
    ValidationError,
)
from textx import TextXSemanticError
from demol.transformations import (
    m2t_device_svg,
    m2t_docs,
    m2t_rpi,
    m2t_riot,
    m2m_smauto,
    m2t_infrastructure_svg,
    demol_to_json,
    m2t_pinmap,
)


def handle_build_model(model_filepath, skip_semantics=False):
    """Helper to build model and handle validation errors gracefully"""

    def print_results(errors, semantic_error_msg=None):
        passed = get_passed_rules()
        if passed:
            click.echo("")
            click.secho("Passed Semantic Rules:", fg="green", bold=True)
            for rule in passed:
                click.secho("  ✓ ", fg="green", bold=True, nl=False)
                click.secho(f"{rule['name']}: ", bold=True, nl=False)
                click.secho(f"{rule['description']}")

        if errors:
            click.echo("")
            click.secho(
                f"Found {len(errors)} validation error(s):", fg="red", bold=True
            )
            for err in errors:
                loc = err["loc"]
                line = loc.get("line", "?")
                col = loc.get("col", "?")
                filename = os.path.basename(loc.get("filename", "unknown"))

                click.secho("  ✗ ", fg="red", bold=True, nl=False)
                click.secho(f"{err['msg']} ", nl=False)
                click.secho(f"({filename}:{line}:{col})", fg="cyan")

            click.echo("")
            if not skip_semantics:
                click.secho(
                    f"[!] Validation failed with {len(errors)} error(s).",
                    fg="red",
                    bold=True,
                )
            else:
                click.secho(
                    f"[!] Model built with {len(errors)} error(s) (skip_semantics=True).",
                    fg="yellow",
                    bold=True,
                )
        elif semantic_error_msg:
            # Fallback for other semantic errors not caught by our collector
            click.secho(
                f"\n[!] Semantic Error: {semantic_error_msg}", fg="red", bold=True
            )

    try:
        model = build_model(model_filepath, skip_semantics=skip_semantics)
        if skip_semantics:
            errors = get_validation_errors()
            if errors:
                print_results(errors)
        return model
    except (ValidationError, TextXSemanticError) as e:
        print_results(get_validation_errors(), str(e))
        sys.exit(1)
    except Exception as e:
        import traceback

        traceback.print_exc()
        click.secho(f"\n[!] Unexpected Error: {e}", fg="red", bold=True)
        sys.exit(1)


@click.group("demol")
@click.pass_context
def cli(ctx):
    """DeMoL CLI - A DSL for modeling IoT Devices"""
    pass


@cli.command("validate")
@click.argument("model_filepath")
@click.option(
    "--skip-semantics",
    is_flag=True,
    help="Build model even if semantic rules are failing",
)
@click.pass_context
def validate(ctx, model_filepath, skip_semantics):
    print(f"[*] Running validation for model {model_filepath}")
    model = handle_build_model(model_filepath, skip_semantics=skip_semantics)
    if model:
        errors = get_validation_errors()
        # If skip_semantics was True and there were errors, handle_build_model
        # already printed the passed rules and errors.
        if not errors:
            passed = get_passed_rules()
            if passed:
                click.echo("")
                click.secho("Passed Semantic Rules:", fg="green", bold=True)
                for rule in passed:
                    click.secho("  ✓ ", fg="green", bold=True, nl=False)
                    click.secho(f"{rule['name']}: ", bold=True, nl=False)
                    click.secho(f"{rule['description']}")

        click.echo("")
        if errors:
            print(
                f"[✓] Validation finished with {len(errors)} semantic error(s) (ignored)."
            )
        else:
            print("[✓] Validation passed!")


@cli.group("generate")
def generate():
    """Generate code, documentation, or diagrams from a model"""
    pass


@generate.command("docs")
@click.argument("model_filepath")
@click.option(
    "--output-dir", default=".", help="Output directory for generated documentation"
)
@click.option(
    "--skip-semantics",
    is_flag=True,
    help="Build model even if semantic rules are failing",
)
def generate_docs(model_filepath, output_dir, skip_semantics):
    """Generate hardware documentation (Markdown + SVGs)"""
    print(f"[*] Generating documentation for model {model_filepath}")
    model = handle_build_model(model_filepath, skip_semantics=skip_semantics)
    if model:
        m2t_docs(model, output_dir=output_dir)
        print("[✓] Documentation generated successfully.")


@generate.command("rpi")
@click.argument("model_filepath")
@click.option("--output-dir", default=".", help="Output directory for generated code")
@click.option(
    "--skip-semantics",
    is_flag=True,
    help="Build model even if semantic rules are failing",
)
def generate_rpi(model_filepath, output_dir, skip_semantics):
    """Generate Python code for Raspberry Pi"""
    print(f"[*] Generating Raspberry Pi code for model {model_filepath}")
    model = handle_build_model(model_filepath, skip_semantics=skip_semantics)
    if model:
        m2t_rpi(model, output_dir=output_dir)
        print("[✓] Raspberry Pi code generated successfully.")


@generate.command("riot")
@click.argument("model_filepath")
@click.option("--output-dir", default=".", help="Output directory for generated code")
@click.option(
    "--skip-semantics",
    is_flag=True,
    help="Build model even if semantic rules are failing",
)
def generate_riot(model_filepath, output_dir, skip_semantics):
    """Generate C code for RiotOS"""
    print(f"[*] Generating RiotOS code for model {model_filepath}")
    model = handle_build_model(model_filepath, skip_semantics=skip_semantics)
    if model:
        m2t_riot(model, output_dir=output_dir)
        print("[✓] RiotOS code generated successfully.")


@generate.command("smauto")
@click.argument("model_filepath")
@click.option(
    "--output-dir", default=".", help="Output directory for generated SMAuto model"
)
@click.option(
    "--skip-semantics",
    is_flag=True,
    help="Build model even if semantic rules are failing",
)
def generate_smauto(model_filepath, output_dir, skip_semantics):
    """Generate SMAuto model from DeMoL model"""
    print(f"[*] Generating SMAuto model for model {model_filepath}")
    model = handle_build_model(model_filepath, skip_semantics=skip_semantics)
    if model:
        m2m_smauto(model, output_dir=output_dir)
        print("[✓] SMAuto model generated successfully.")


@generate.command("svg")
@click.argument("model_filepath")
@click.option("--output-dir", default=".", help="Output directory for generated SVG")
@click.option(
    "--infrastructure",
    is_flag=True,
    help="Generate infrastructure diagram instead of wiring diagram",
)
@click.option(
    "--skip-semantics",
    is_flag=True,
    help="Build model even if semantic rules are failing",
)
def generate_svg(model_filepath, output_dir, infrastructure, skip_semantics):
    """Generate SVG diagrams (wiring or infrastructure)"""
    model = handle_build_model(model_filepath, skip_semantics=skip_semantics)
    if model:
        if infrastructure:
            print(f"[*] Generating Infrastructure SVG for model {model_filepath}")
            filename = os.path.join(
                output_dir, f"{model.metadata.name}_infrastructure.svg"
            )
            m2t_infrastructure_svg(model, filename)
        else:
            print(f"[*] Generating Wiring SVG for model {model_filepath}")
            filename = os.path.join(output_dir, f"{model.metadata.name}.svg")
            m2t_device_svg(model, filename)
        print("[✓] SVG generated successfully.")


@generate.command("pinmap")
@click.argument("model_filepath")
@click.option(
    "--output-dir", default=".", help="Output directory for pin-mapping report"
)
@click.option(
    "--skip-semantics",
    is_flag=True,
    help="Build model even if semantic rules are failing",
)
def generate_pinmap_cmd(model_filepath, output_dir, skip_semantics):
    """Generate pin-mapping report (Markdown + JSON)"""
    print(f"[*] Generating pin-mapping report for model {model_filepath}")
    model = handle_build_model(model_filepath, skip_semantics=skip_semantics)
    if model:
        m2t_pinmap(model, output_dir=output_dir)
        print("[✓] Pin-mapping report generated successfully.")


@generate.command("json")
@click.argument("model_filepath")
@click.option("--output-dir", default=".", help="Output directory for generated JSON")
@click.option(
    "--skip-semantics",
    is_flag=True,
    help="Build model even if semantic rules are failing",
)
def generate_json(model_filepath, output_dir, skip_semantics):
    """Generate JSON representation of the model"""
    print(f"[*] Generating JSON for model {model_filepath}")
    model = handle_build_model(model_filepath, skip_semantics=skip_semantics)
    if model:
        filename = os.path.join(output_dir, f"{model.metadata.name}.json")
        import json

        with open(filename, "w") as f:
            json.dump(demol_to_json(model), f, indent=4)
        print(f"[✓] JSON generated successfully: {filename}")


def main():
    cli(prog_name="demol")


if __name__ == "__main__":
    main()
