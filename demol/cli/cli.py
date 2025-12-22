import click
from demol.lang import build_model
from demol.transformations import (
    m2t_device_json, 
    m2t_device_svg, 
    m2t_docs, 
    m2t_rpi, 
    m2m_smauto,
    m2t_infrastructure_svg
)


@click.group("demol")
@click.pass_context
def cli(ctx):
   """DeMoL CLI - A DSL for modeling IoT Devices"""
   pass


@cli.command("validate")
@click.argument("model_filepath")
@click.pass_context
def validate(ctx, model_filepath):
    print(f'[*] Running validation for model {model_filepath}')
    model = build_model(model_filepath)
    if model:
        print(f'[✓] Validation passed!')


@cli.group("generate")
def generate():
    """Generate code, documentation, or diagrams from a model"""
    pass


@generate.command("docs")
@click.argument("model_filepath")
def generate_docs(model_filepath):
    """Generate hardware documentation (Markdown + SVGs)"""
    print(f'[*] Generating documentation for model {model_filepath}')
    model = build_model(model_filepath)
    if model:
        m2t_docs(model)
        print(f'[✓] Documentation generated successfully.')


@generate.command("rpi")
@click.argument("model_filepath")
def generate_rpi(model_filepath):
    """Generate Python code for Raspberry Pi"""
    print(f'[*] Generating Raspberry Pi code for model {model_filepath}')
    model = build_model(model_filepath)
    if model:
        m2t_rpi(model)
        print(f'[✓] Raspberry Pi code generated successfully.')


@generate.command("smauto")
@click.argument("model_filepath")
def generate_smauto(model_filepath):
    """Generate SMAuto model from DeMoL model"""
    print(f'[*] Generating SMAuto model for model {model_filepath}')
    model = build_model(model_filepath)
    if model:
        m2m_smauto(model)
        print(f'[✓] SMAuto model generated successfully.')


@generate.command("svg")
@click.argument("model_filepath")
@click.option("--infrastructure", is_flag=True, help="Generate infrastructure diagram instead of wiring diagram")
def generate_svg(model_filepath, infrastructure):
    """Generate SVG diagrams (wiring or infrastructure)"""
    model = build_model(model_filepath)
    if model:
        if infrastructure:
            print(f'[*] Generating Infrastructure SVG for model {model_filepath}')
            m2t_infrastructure_svg(model)
        else:
            print(f'[*] Generating Wiring SVG for model {model_filepath}')
            m2t_device_svg(model)
        print(f'[✓] SVG generated successfully.')


def main():
   cli(prog_name="demol")


if __name__ == '__main__':
   main()
