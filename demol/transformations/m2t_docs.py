#!/usr/bin/env python

"""
m2t_docs.py
Generates professional, styled SVG diagrams and hardware documentation from DeMoL models.
"""

import os
from .device_to_svg import device_to_svg
from .infrastructure_to_svg import infrastructure_to_svg
from jinja2 import Environment, FileSystemLoader


def generate_documentation(model, output_dir="."):
    """Generates the high-level system diagram and hardware documentation."""

    # Setup Jinja2 Environment
    # Templates are located in ../templates relative to this file
    templates_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates", "docs")
    env = Environment(loader=FileSystemLoader(templates_dir))

    if output_dir != "." and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    generated_files = []

    # 1. System Diagram (SVG)
    try:
        svg_filename = os.path.join(output_dir, f"{model.metadata.name}.svg")
        device_to_svg(model, svg_filename)
        print(f"Generated System Diagram (SVG): {svg_filename}")
        generated_files.append(svg_filename)
    except Exception as e:
        print(f"Error generating system diagram (SVG): {e}")

    # 2. Infrastructure Diagram (SVG)
    try:
        infra_filename = os.path.join(output_dir, f"{model.metadata.name}_infrastructure.svg")
        infrastructure_to_svg(model, infra_filename)
        print(f"Generated Infrastructure Diagram (SVG): {infra_filename}")
        generated_files.append(infra_filename)
    except Exception as e:
        print(f"Error generating infrastructure diagram (SVG): {e}")

    # 3. Hardware Documentation
    try:
        template_doc = env.get_template("hardware_doc.md.j2")
        doc_content = template_doc.render(model=model)
        doc_filename = os.path.join(output_dir, f"{model.metadata.name}_hardware_doc.md")
        with open(doc_filename, "w") as f:
            f.write(doc_content)
        print(f"Generated Hardware Documentation: {doc_filename}")
        generated_files.append(doc_filename)
    except Exception as e:
        print(f"Error generating hardware documentation: {e}")

    return generated_files
