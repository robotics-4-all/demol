#!/usr/bin/env python

"""
m2t_docs.py
Generates professional, styled SVG diagrams and hardware documentation from DeMoL models.
"""

import os
from pathlib import Path

import jinja2

from .base_generator import BaseCodeGenerator
from .device_to_svg import device_to_svg
from .infrastructure_to_svg import infrastructure_to_svg


class DocsGenerator(BaseCodeGenerator):
    """
    Generates hardware documentation (Markdown) from a device model.
    The SVG diagrams are produced by the dedicated device_to_svg /
    infrastructure_to_svg generators; this class owns the markdown half.
    """

    OS = ""

    def __init__(self, device_model, output_dir="."):
        self.output_dir = Path(output_dir)
        super().__init__(device_model, self.output_dir)
        self.env = self.setup_template_environment()
        self.doc_path = self.output_dir / f"{self.device_model.metadata.name}_hardware_doc.md"

    def setup_template_environment(self) -> jinja2.Environment:
        templates_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates", "docs")
        return jinja2.Environment(loader=jinja2.FileSystemLoader(templates_dir))

    def generate(self) -> None:
        template = self.env.get_template("hardware_doc.md.j2")
        self._write_template(template, {"model": self.device_model}, self.doc_path)


def generate_documentation(model, output_dir="."):
    """Generates the high-level system diagram and hardware documentation."""

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
        docs_generator = DocsGenerator(model, Path(output_dir))
        docs_generator.generate()
        print(f"Generated Hardware Documentation: {docs_generator.doc_path}")
        generated_files.append(str(docs_generator.doc_path))
    except Exception as e:
        print(f"Error generating hardware documentation: {e}")

    return generated_files
