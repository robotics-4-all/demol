import click
import os
import re
import sys
from demol.lang import build_model
from demol.lang.semantics import (
    get_validation_errors,
    get_passed_rules,
    ValidationError,
)
from textx import TextXSemanticError
from textx.exceptions import TextXSyntaxError
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

_SYNTAX_HINTS = [
    (re.compile(r"Expected.*';'"), "Missing semicolon at end of statement."),
    (re.compile(r"Expected.*'WITH'"), "Missing 'WITH' keyword after declaration."),
    (re.compile(r"Expected.*'DEVICE'"), "Model must start with a DEVICE declaration."),
    (
        re.compile(r"Expected.*'--'"),
        "Pin connections require '--' separator (e.g., gnd -- GND_1).",
    ),
    (re.compile(r"Expected.*']'"), "Unclosed bracket — did you forget a ']'?"),
    (re.compile(r"Expected.*'THEN'"), "ALERT requires WHEN ... THEN ... syntax."),
    (re.compile(r"Expected.*'WHEN'"), "ALERT requires WHEN ... THEN ... syntax."),
    (
        re.compile(r"Expected.*'description'"),
        "DEVICE requires 'description' and 'author' attributes.",
    ),
]


def _format_syntax_error(exc):
    msg = str(exc)
    loc_match = re.match(r"^(.*?):(\d+):(\d+):\s*(.*)", msg)
    if loc_match:
        filename = loc_match.group(1) or "input"
        line = loc_match.group(2)
        col = loc_match.group(3)
        detail = loc_match.group(4)
    else:
        filename, line, col, detail = "input", "?", "?", msg

    hint = ""
    for pattern, suggestion in _SYNTAX_HINTS:
        if pattern.search(detail):
            hint = f"\n  Hint: {suggestion}"
            break

    return filename, line, col, detail, hint


def handle_build_model(model_filepath, skip_semantics=False):
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
            click.secho(f"Found {len(errors)} validation error(s):", fg="red", bold=True)
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
            click.secho(f"\n[!] Semantic Error: {semantic_error_msg}", fg="red", bold=True)

    try:
        model = build_model(model_filepath, skip_semantics=skip_semantics)
        if skip_semantics:
            errors = get_validation_errors()
            if errors:
                print_results(errors)
        return model
    except TextXSyntaxError as e:
        filename, line, col, detail, hint = _format_syntax_error(e)
        click.echo("")
        click.secho("[!] Syntax Error", fg="red", bold=True)
        click.secho("  Location: ", fg="white", nl=False)
        click.secho(f"{os.path.basename(filename)}:{line}:{col}", fg="cyan")
        click.secho(f"  {detail}", fg="red")
        if hint:
            click.secho(hint, fg="yellow")
        click.echo("")
        sys.exit(1)
    except (ValidationError, TextXSemanticError) as e:
        print_results(get_validation_errors(), str(e))
        sys.exit(1)
    except Exception as e:
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
            print(f"[✓] Validation finished with {len(errors)} semantic error(s) (ignored).")
        else:
            print("[✓] Validation passed!")


@cli.group("generate")
def generate():
    """Generate code, documentation, or diagrams from a model"""
    pass


@generate.command("docs")
@click.argument("model_filepath")
@click.option("--output-dir", default=".", help="Output directory for generated documentation")
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
@click.option("--output-dir", default=".", help="Output directory for generated SMAuto model")
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
            filename = os.path.join(output_dir, f"{model.metadata.name}_infrastructure.svg")
            m2t_infrastructure_svg(model, filename)
        else:
            print(f"[*] Generating Wiring SVG for model {model_filepath}")
            filename = os.path.join(output_dir, f"{model.metadata.name}.svg")
            m2t_device_svg(model, filename)
        print("[✓] SVG generated successfully.")


@generate.command("pinmap")
@click.argument("model_filepath")
@click.option("--output-dir", default=".", help="Output directory for pin-mapping report")
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


@cli.group("analyze")
def analyze():
    """Analyze device models (power consumption, autonomy)"""
    pass


def _format_power(mw):
    if mw is None:
        return "N/A"
    if mw >= 1000:
        return f"{mw / 1000:.2f} W"
    return f"{mw:.1f} mW"


def _format_runtime(hours):
    if hours is None:
        return "N/A"
    if hours < 1.0:
        return f"{hours * 60:.0f} minutes"
    if hours < 24.0:
        return f"{hours:.1f} hours"
    days = hours / 24.0
    return f"{days:.1f} days ({hours:.0f} hours)"


@analyze.command("power")
@click.argument("model_filepath")
@click.option(
    "--skip-semantics",
    is_flag=True,
    help="Build model even if semantic rules are failing",
)
@click.option(
    "--json-output",
    is_flag=True,
    help="Output results as JSON instead of formatted text",
)
@click.pass_context
def analyze_power(ctx, model_filepath, skip_semantics, json_output):
    """Analyze power consumption and battery autonomy for a device model"""
    from demol.lang.semantics.validators.power_budget import analyze_power_budget

    model = handle_build_model(model_filepath, skip_semantics=skip_semantics)
    if not model:
        return

    data = analyze_power_budget(model)

    if json_output:
        import json

        click.echo(json.dumps(data, indent=2, default=str))
        return

    click.echo("")
    click.secho(
        f"⚡ Power Analysis: {model.metadata.name}",
        fg="cyan",
        bold=True,
    )
    click.secho("=" * 60, fg="cyan")

    board = data["board"]
    if board:
        click.echo("")
        click.secho("Board: ", bold=True, nl=False)
        click.secho(board["name"], fg="white")
        if board["vcc"]:
            click.echo(f"  VCC:       {board['vcc']}V")
        if board["power_min"] is not None:
            click.echo(f"  Power min: {_format_power(board['power_min'])}")
        if board["power_max"] is not None:
            click.echo(f"  Power max: {_format_power(board['power_max'])}")
        if board["power_avg"] is not None:
            click.echo(f"  Power avg: {_format_power(board['power_avg'])}")

    peripherals = data["peripherals"]
    if peripherals:
        click.echo("")
        click.secho("Peripherals:", bold=True)
        click.secho(
            f"  {'Name':<20} {'Type':<10} {'Max':<12} {'Avg':<12}",
            fg="white",
            bold=True,
        )
        click.secho("  " + "-" * 54, fg="white")
        for p in peripherals:
            name = p["name"]
            ptype = p["type"][:10]
            p_max = _format_power(p["power_max"])
            p_avg = _format_power(p["power_avg"])
            click.echo(f"  {name:<20} {ptype:<10} {p_max:<12} {p_avg:<12}")

    totals = data["totals"]
    click.echo("")
    click.secho("Totals:", bold=True)
    click.echo(f"  Peripherals with power data: {totals['count']}")
    click.echo(f"  Total peak (max):  {_format_power(totals['max_mw'])}")
    click.echo(f"  Total average:     {_format_power(totals['avg_mw'])}")

    budget = data["budget"]
    if budget["supply_mw"] is not None:
        click.echo("")
        click.secho("Supply Budget:", bold=True)
        click.echo(f"  Board supply capability: {_format_power(budget['supply_mw'])}")
        headroom = budget["headroom_mw"]
        if budget["exceeded"]:
            click.secho(
                f"  ⚠  EXCEEDED by {_format_power(abs(headroom))}",
                fg="red",
                bold=True,
            )
        else:
            click.secho(
                f"  ✓  Headroom: {_format_power(headroom)}",
                fg="green",
            )

    sources = data["power_sources"]
    if sources:
        click.echo("")
        click.secho("Battery / Autonomy:", bold=True)
        for ps in sources:
            click.echo(f"  Source: {ps['name']} ({ps['type']})")
            if ps["voltage"]:
                click.echo(f"    Voltage:      {ps['voltage']}V")
            if ps["capacity_mah"]:
                click.echo(f"    Capacity:     {ps['capacity_mah']:.0f} mAh")
            if ps["max_current_ma"]:
                click.echo(f"    Max current:  {ps['max_current_ma']:.0f} mA")
            if ps["avg_current_ma"]:
                click.echo(f"    Avg draw:     {ps['avg_current_ma']:.0f} mA")
            if ps["runtime_hours"] is not None:
                click.secho(
                    f"    Est. runtime: {_format_runtime(ps['runtime_hours'])}",
                    fg="green" if ps["runtime_hours"] >= 1.0 else "yellow",
                    bold=True,
                )
            else:
                click.secho("    Est. runtime: N/A (no avg power data)", fg="yellow")
    else:
        click.echo("")
        click.secho(
            "  No power sources declared — add a POWERSOURCE for autonomy estimates.",
            fg="yellow",
        )

    click.echo("")


@cli.command("diff")
@click.argument("model_a")
@click.argument("model_b")
@click.option(
    "--json-output",
    is_flag=True,
    help="Output diff as JSON",
)
def diff_cmd(model_a, model_b, json_output):
    """Compare two device models and show semantic differences"""
    from demol.cli.modeldiff import compute_diff

    for fp in (model_a, model_b):
        if not os.path.isfile(fp):
            click.secho(f"[!] File not found: {fp}", fg="red")
            sys.exit(1)

    try:
        diffs = compute_diff(model_a, model_b)
    except Exception as e:
        click.secho(f"[!] Error computing diff: {e}", fg="red")
        sys.exit(1)

    if json_output:
        import json

        click.echo(
            json.dumps(
                [
                    {
                        "action": d[0],
                        "category": d[1],
                        "name": d[2],
                        "old": d[3],
                        "new": d[4],
                    }
                    for d in diffs
                ],
                indent=2,
                default=str,
            )
        )
        return

    if not diffs:
        click.secho("[✓] Models are semantically identical.", fg="green")
        return

    click.echo("")
    click.secho(
        f"Found {len(diffs)} difference(s) between models:",
        fg="cyan",
        bold=True,
    )
    click.echo(f"  A: {model_a}")
    click.echo(f"  B: {model_b}")
    click.echo("")

    symbols = {
        "added": ("+", "green"),
        "removed": ("-", "red"),
        "changed": ("~", "yellow"),
    }

    for action, category, name, old, new in diffs:
        sym, color = symbols.get(action, ("?", "white"))
        click.secho(f"  {sym} ", fg=color, bold=True, nl=False)
        click.secho(f"[{category}] ", fg="cyan", nl=False)
        click.secho(f"{name}", bold=True)

        if action == "changed" and old and new:
            for key in set(list(old.keys()) + list(new.keys())):
                ov = old.get(key)
                nv = new.get(key)
                if ov != nv:
                    click.echo(f"      {key}: ", nl=False)
                    click.secho(f"{ov}", fg="red", nl=False)
                    click.echo(" → ", nl=False)
                    click.secho(f"{nv}", fg="green")
        elif action == "added" and new:
            for key, val in new.items():
                click.echo(f"      {key}: {val}")
        elif action == "removed" and old:
            for key, val in old.items():
                click.echo(f"      {key}: {val}")

    click.echo("")


@cli.command("fix")
@click.argument("model_filepath")
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be fixed without modifying the file",
)
@click.option(
    "--output",
    default=None,
    help="Write fixed model to a different file instead of overwriting",
)
def fix_cmd(model_filepath, dry_run, output):
    """Auto-fix common validation errors in a device model"""
    from demol.cli.autofix import apply_fixes

    if not os.path.isfile(model_filepath):
        click.secho(f"[!] File not found: {model_filepath}", fg="red")
        sys.exit(1)

    with open(model_filepath, "r") as f:
        original = f.read()

    fixed, descriptions = apply_fixes(original)

    if not descriptions:
        click.secho("[✓] No auto-fixable issues found.", fg="green")
        return

    click.echo("")
    click.secho(
        f"Found {len(descriptions)} fixable issue(s):",
        fg="cyan",
        bold=True,
    )
    for desc in descriptions:
        click.secho("  ⚡ ", fg="yellow", nl=False)
        click.echo(desc)

    if dry_run:
        click.echo("")
        click.secho("[dry-run] No files modified.", fg="yellow")
        return

    target = output or model_filepath
    with open(target, "w") as f:
        f.write(fixed)

    click.echo("")
    click.secho(f"[✓] Fixed model written to {target}", fg="green", bold=True)


@cli.command("lsp")
def lsp_cmd():
    """Start the DeMoL Language Server (LSP) for IDE integration"""
    from demol.lsp.server import main as lsp_main

    lsp_main()


def main():
    cli(prog_name="demol")


if __name__ == "__main__":
    main()
