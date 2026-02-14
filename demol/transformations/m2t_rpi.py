"""Model-to-Text transformation for Raspberry Pi devices.

This module provides functionality to transform DeMoL device models into
Python code for Raspberry Pi, including sensor/actuator classes and MQTT
publisher/subscriber processes.
"""

import os
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging

import jinja2

from demol.definitions import TEMPLATES_RPI
from demol.lang import build_model
from .base_generator import BaseCodeGenerator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PeripheralTemplateMapper:
    """Maps peripheral types to their corresponding Jinja2 templates."""

    @classmethod
    def get_template(cls, peripheral_ref) -> Optional[str]:
        """Get template name for a peripheral from its templates section.

        Args:
            peripheral_ref: Reference to the peripheral object (has .name and .templates)

        Returns:
            Template filename for raspbian OS, or None if not found
        """
        # Check peripheral's templates section for raspbian
        if hasattr(peripheral_ref, "templates") and peripheral_ref.templates:
            for template_mapping in peripheral_ref.templates:
                if template_mapping.os == "raspbian":
                    return str(template_mapping.template)

        # No template found
        logger.warning(
            f"No raspbian template found for peripheral '{peripheral_ref.name}'. "
            f"Please add a templates section with raspbian mapping to the peripheral model."
        )
        return None


class UnitConverter:
    """Utility class for unit conversions."""

    FREQUENCY_TO_HZ = {
        "ghz": 1_000_000_000,
        "mhz": 1_000_000,
        "khz": 1_000,
        "hz": 1,
    }

    DISTANCE_TO_CM = {
        "m": 0.01,
        "cm": 1,
        "mm": 10,
    }

    @classmethod
    def convert_frequency(cls, value: float, unit: str) -> float:
        """Convert frequency to Hz."""
        multiplier = cls.FREQUENCY_TO_HZ.get(unit.lower(), 1)
        return value * multiplier

    @classmethod
    def convert_distance(cls, value: float, unit: str) -> float:
        """Convert distance to cm."""
        multiplier = cls.DISTANCE_TO_CM.get(unit.lower(), 1)
        return value * multiplier


class RPiCodeGenerator(BaseCodeGenerator):
    """Generates Raspberry Pi code from device model."""

    def __init__(self, device_model, output_dir: Path):
        """Initialize code generator with device model.

        Args:
            device_model: Parsed textX device model
            output_dir: Output directory for generated code
        """
        super().__init__(device_model, output_dir)
        self.env = self.setup_template_environment()

    def setup_template_environment(self) -> jinja2.Environment:
        """Setup Jinja2 environment with RPI-specific templates.

        Returns:
            Configured Jinja2 Environment
        """
        fsloader = jinja2.FileSystemLoader(TEMPLATES_RPI)
        return jinja2.Environment(loader=fsloader)

    def build_template_context(self, connection) -> Dict[str, Any]:
        """Build structured context dictionary by querying model.

        Args:
            connection: Connection object from device model

        Returns:
            Structured context dictionary for templates
        """
        # Query model for all needed information
        peripheral_ref = connection.peripheral.ref
        board = self.get_board()
        broker_config = self.get_broker_config()
        pins = self.get_pin_mappings(connection, board)
        attributes = self.get_peripheral_attributes(peripheral_ref)
        op_attributes = self.get_operational_attributes(peripheral_ref)

        # Build base context
        driver_class_name = f"{peripheral_ref.name}_{connection.peripheral.name}"
        driver_module_name = (
            f"{peripheral_ref.name.lower()}_{connection.peripheral.name.lower()}"
        )

        context = {
            "name": peripheral_ref.name,
            "instance": connection.peripheral.name,
            "type": type(peripheral_ref).__name__,
            "class": peripheral_ref.type,
            "driver_class_name": driver_class_name,
            "driver_module_name": driver_module_name,
            "board": board,
            "peripheral": peripheral_ref,
            "broker": broker_config,
            "topic": connection.remote,
            "conn": {},
            "attributes": attributes,
            "op": op_attributes,
            "max_frequency": op_attributes.get("freq_max", {}).get("value", 100.0),
        }

        # Build structured connection info
        context["conn"] = self._build_conn_info(pins, board)

        return context

    def generate(self) -> None:
        """Generate all RPI code from device model."""
        logger.info("Generating RPI code...")
        self.generate_peripheral_classes()
        self.generate_peripheral_nodes()
        self.generate_common()
        self.generate_messages()
        self.generate_docker_files()
        logger.info("Code generation complete!")

    def generate_peripheral_classes(self) -> None:
        """Generate peripheral class files by querying model."""
        for connection in self.get_connections():
            self._generate_peripheral_class(connection)

    def generate_peripheral_nodes(self) -> None:
        """Generate peripheral node files by querying model."""
        for connection in self.get_connections():
            self._generate_peripheral_node(connection)

    def _generate_peripheral_node(self, connection) -> None:
        """Generate peripheral node file (sensor or actuator).

        Args:
            connection: Connection object from device model
        """
        peripheral_ref = connection.peripheral.ref
        peripheral_type = type(peripheral_ref).__name__

        # Select template based on peripheral type
        if peripheral_type == "Sensor":
            template_name = "sensor_node.py.j2"
        elif peripheral_type == "Actuator":
            template_name = "actuator_node.py.j2"
        else:
            logger.warning(
                f"Unknown peripheral type: {peripheral_type}, skipping node generation"
            )
            return

        template = self.env.get_template(template_name)
        context = self.build_template_context(connection)
        self._write_template(
            template,
            context,
            self.output_dir / f"{connection.peripheral.name.lower()}_node.py",
        )

    def _generate_peripheral_class(self, connection) -> None:
        """Generate a single peripheral class file.

        Args:
            connection: Connection object from device model
        """
        peripheral_ref = connection.peripheral.ref

        # Get template using peripheral reference
        template_name = PeripheralTemplateMapper.get_template(peripheral_ref)

        if not template_name:
            logger.warning(
                f"Skipping peripheral {connection.peripheral.name}: no template available"
            )
            return

        template = self.env.get_template(template_name)

        # Build context by querying model
        context = self.build_template_context(connection)
        # Render and write
        output = template.render(**context)

        # Use unique module name
        output_path = self.output_dir / f"{context['driver_module_name']}.py"

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(output)

        logger.info(f"Generated peripheral class: {output_path}")

    def generate_messages(self) -> None:
        """Generate MQTT messages module."""
        template = self.env.get_template("msg.py.j2")
        self._write_template(template, {}, self.output_dir / "msg.py")

    def generate_common(self) -> None:
        """Generate common module."""
        template = self.env.get_template("common.py.j2")
        self._write_template(template, {}, self.output_dir / "common.py")

    def get_dependencies(self) -> Dict[str, List[str]]:
        """Collect dependencies from all used peripherals.

        Returns:
            Dict with 'pip' and 'apt' keys containing lists of package strings.
        """
        pip_deps = set()
        apt_deps = set()

        for connection in self.get_connections():
            peripheral_ref = connection.peripheral.ref
            if hasattr(peripheral_ref, "dependencies"):
                for dep_mapping in peripheral_ref.dependencies:
                    if dep_mapping.target == "raspbian":
                        for item in dep_mapping.items:
                            if isinstance(item, str):
                                # Default to pip if just a string
                                pip_deps.add(item)
                            else:
                                # Structured dependency
                                pkg = item.name
                                if item.version:
                                    # Check if version already contains an operator
                                    version_str = item.version.strip('"').strip("'")
                                    has_operator = any(
                                        op in version_str
                                        for op in [
                                            ">=",
                                            "<=",
                                            "==",
                                            "!=",
                                            "~=",
                                            "<",
                                            ">",
                                        ]
                                    )

                                    if item.source and item.source == "apt":
                                        # APT uses single '=' for version pinning
                                        pkg = (
                                            f"{pkg}={version_str}"
                                            if not has_operator
                                            else f"{pkg}{version_str}"
                                        )
                                    else:
                                        # pip uses '==' for exact version, or keeps operator if present
                                        pkg = (
                                            f"{pkg}=={version_str}"
                                            if not has_operator
                                            else f"{pkg}{version_str}"
                                        )

                                if item.source and item.source == "apt":
                                    apt_deps.add(pkg)
                                else:
                                    pip_deps.add(pkg)

        return {"pip": sorted(list(pip_deps)), "apt": sorted(list(apt_deps))}

    def generate_docker_files(self) -> None:
        """Generate Dockerfile, docker-compose.yml and install_deps.sh."""
        # Collect dependencies
        deps = self.get_dependencies()

        # Dockerfile
        template = self.env.get_template("Dockerfile.j2")
        context = {"apt_dependencies": deps["apt"]}
        self._write_template(template, context, self.output_dir / "Dockerfile")

        # requirements.txt
        template = self.env.get_template("requirements.txt.j2")
        context = {"dependencies": deps["pip"]}
        self._write_template(template, context, self.output_dir / "requirements.txt")

        # docker-compose.yml
        template = self.env.get_template("docker-compose.yml.j2")
        context = {"connections": self.get_connections()}
        self._write_template(template, context, self.output_dir / "docker-compose.yml")

        # install_deps.sh
        template = self.env.get_template("install_deps.sh.j2")
        context = {"apt_dependencies": deps["apt"]}
        self._write_template(template, context, self.output_dir / "install_deps.sh")
        # Make script executable
        os.chmod(self.output_dir / "install_deps.sh", 0o755)

    def _write_template(
        self, template: jinja2.Template, context: Dict[str, Any], output_path: Path
    ) -> None:
        """Render template and write to file.

        Args:
            template: Jinja2 template
            context: Template context
            output_path: Output file path
        """
        output = template.render(**context)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(output)

        logger.debug(f"Generated: {output_path}")


def m2t_rpi(model, output_dir="."):
    """Transform a DeMoL device model object to Raspberry Pi code.

    Args:
        model: Parsed textX device model
        output_dir: Output directory
    """
    output_path = Path(output_dir)
    if not output_path.exists():
        output_path.mkdir(parents=True, exist_ok=True)

    # Generate code using new architecture
    generator = RPiCodeGenerator(model, output_path)
    generator.generate()


def transform_device_model(
    device_model_path: str, output_dir: str, skip_semantics: bool = False
) -> None:
    """Transform a DeMoL device model to Raspberry Pi code.

    Args:
        device_model_path: Path to .dev model file (relative to examples/)
        output_dir: Output directory (relative to REPO_PATH)
        skip_semantics: Whether to skip semantic validation
    """
    # Build paths
    model_path = Path(device_model_path)

    logger.info(f"Transforming: {model_path}")

    # Parse device model
    device_model = build_model(str(model_path), skip_semantics=skip_semantics)

    m2t_rpi(device_model, output_dir)

    logger.info("Transformation complete!")


def main(dev_model: str, output_dir: str) -> None:
    """Main entry point for the transformation.

    Args:
        dev_model: Path to device model file
        output_dir: Output directory for generated code
    """
    transform_device_model(dev_model, output_dir)
