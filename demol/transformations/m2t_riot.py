"""Model-to-Text transformation for RiotOS devices.

This module provides functionality to transform DeMoL device models into
C code for RiotOS, including sensor/actuator drivers and MQTT
communication.
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

import jinja2

from demol.definitions import TEMPLATES
from .base_generator import BaseCodeGenerator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PeripheralTemplateMapper:
    """Maps peripheral types to their corresponding Jinja2 templates for RiotOS."""

    @classmethod
    def get_template_base(cls, peripheral_ref) -> Optional[str]:
        """Get template base name for a peripheral.

        Example: if riotos="bme680.c.j2", returns "bme680".
        """
        if hasattr(peripheral_ref, "templates") and peripheral_ref.templates:
            for template_mapping in peripheral_ref.templates:
                if template_mapping.os == "riotos":
                    tmpl: str = str(template_mapping.template)
                    # Strip .c.j2 or .j2
                    base = tmpl
                    if tmpl.endswith(".c.j2"):
                        base = tmpl[:-5]
                    elif tmpl.endswith(".j2"):
                        base = tmpl[:-3]

                    # Strip _riot suffix if present
                    if base.endswith("_riot"):
                        base = base[:-5]
                    return base

        # Fallback based on type
        peripheral_type = type(peripheral_ref).__name__
        if peripheral_type == "Sensor":
            return "unsupported_sensor"
        elif peripheral_type == "Actuator":
            return "unsupported_actuator"

        return None


class RiotCodeGenerator(BaseCodeGenerator):
    """Generates RiotOS C code from device model."""

    def __init__(self, device_model, output_dir: Path):
        """Initialize code generator with device model.

        Args:
            device_model: Parsed textX device model
            output_dir: Output directory for generated code
        """
        super().__init__(device_model, output_dir)
        self.env = self.setup_template_environment()

    def setup_template_environment(self) -> jinja2.Environment:
        """Setup Jinja2 environment with RiotOS-specific templates.

        Returns:
            Configured Jinja2 Environment
        """
        fsloader = jinja2.FileSystemLoader(TEMPLATES)
        return jinja2.Environment(loader=fsloader)

    def build_global_context(self) -> Dict[str, Any]:
        """Build global context for main.c and Makefile."""
        connections = self.get_connections()
        board = self.get_board()
        broker_config = self.get_broker_config()

        peripheral_names = {}
        peripheral_types = {}
        frequencies = []
        topics = []
        ids = []
        modules = {}
        conns_info = []
        attributes_list = []
        op_list = []
        sampling_list = []

        for i, conn in enumerate(connections):
            pref = conn.peripheral.ref
            base_name = PeripheralTemplateMapper.get_template_base(pref)
            if not base_name:
                continue

            peripheral_names[i] = base_name
            peripheral_types[base_name] = type(pref).__name__.lower()

            attrs = self.get_peripheral_attributes(conn.peripheral)
            attributes_list.append(attrs)
            op_list.append(self.get_operational_attributes(pref))

            sampling = self.get_sampling_config(conn.peripheral.name)
            sampling_list.append(sampling)

            if sampling:
                frequencies.append(sampling["rate_hz"])
            elif "frequency" in attrs:
                frequencies.append(attrs["frequency"])
            elif "poll_period" in attrs and attrs["poll_period"] > 0:
                frequencies.append(1.0 / attrs["poll_period"])
            else:
                frequencies.append(1.0)

            topics.append(conn.remote if conn.remote else f"device/{conn.peripheral.name}")
            ids.append(i)
            modules[i] = base_name

            # Build structured connection info
            pins = self.get_pin_mappings(conn, board)
            conn_info = self._build_conn_info(pins, board)
            if "i2c" in conn_info and "slave_address" in conn_info["i2c"]:
                addr = conn_info["i2c"]["slave_address"]
                if isinstance(addr, int):
                    conn_info["i2c"]["slave_address"] = f"{addr:02x}"
            conns_info.append(conn_info)

        network = self.device_model.network
        wifi_ssid = getattr(network, "ssid", "")
        wifi_passwd = getattr(network, "passwd", "")

        # Board name mapping for RiotOS
        board_name = board.name.lower()
        platform_attrs = self.get_platform_attributes(board, "riotos")
        if "board" in platform_attrs:
            board_name = platform_attrs["board"]
        elif board_name == "esp32wroom32":
            board_name = "esp32-wroom-32"
        # Add more mappings as needed or use a more generic approach
        # For now, let's try to be smart about common patterns
        elif "_" in board_name:
            board_name = board_name.replace("_", "-")

        context = {
            "peripheral_name": peripheral_names,
            "peripheral_type": peripheral_types,
            "frequency": frequencies,
            "topic": topics,
            "id": ids,
            "conns": conns_info,
            "attributes_list": attributes_list,
            "op_list": op_list,
            "sampling_list": sampling_list,
            "num_of_peripherals": len(peripheral_names),
            "broker": broker_config,
            "port": broker_config.get("port", 1883),
            "address": broker_config.get("host", "::1"),
            "board_name": board_name,
            "connection_conf": self.device_model.metadata.name.lower(),
            "wifi_ssid": wifi_ssid,
            "wifi_passwd": wifi_passwd,
            "module": modules,
            "dependencies": self.get_dependencies(),
            "peripheral_counts": self.get_peripheral_counts(),
            "riot_version": os.environ.get("DEMOL_RIOT_VERSION", "2024.10"),
            "riot_repo": os.environ.get("DEMOL_RIOT_REPO", "https://github.com/RIOT-OS/RIOT.git"),
        }
        return context

    def get_peripheral_counts(self) -> Dict[str, int]:
        """Count occurrences of each peripheral type.

        Returns:
            Dictionary mapping peripheral base name to count.
        """
        counts: dict = {}
        for connection in self.get_connections():
            pref = connection.peripheral.ref
            base_name = PeripheralTemplateMapper.get_template_base(pref)
            if base_name:
                counts[base_name] = counts.get(base_name, 0) + 1
        return counts

    def get_dependencies(self) -> List[str]:
        """Collect RIOT dependencies from all used peripherals.

        Returns:
            List of RIOT module names.
        """
        riot_deps = set()
        for connection in self.get_connections():
            peripheral_ref = connection.peripheral.ref
            if hasattr(peripheral_ref, "dependencies"):
                for dep_mapping in peripheral_ref.dependencies:
                    if dep_mapping.target == "riotos":
                        for item in dep_mapping.items:
                            if isinstance(item, str):
                                riot_deps.add(item)
                            else:
                                # Structured dependency
                                riot_deps.add(item.name)
        return sorted(list(riot_deps))

    def generate(self) -> None:
        """Generate all RiotOS code."""
        logger.info("Generating RiotOS code...")
        global_context = self.build_global_context()

        # Generate main.c
        template = self.env.get_template("main.c.j2")
        self._write_template(template, global_context, self.output_dir / "main.c")

        # Generate Makefile
        template = self.env.get_template("Makefile.j2")
        self._write_template(template, global_context, self.output_dir / "Makefile")

        # Generate MQTT broker files
        template = self.env.get_template("mqtt_broker.c.j2")
        self._write_template(template, global_context, self.output_dir / "mqtt_broker.c")
        template = self.env.get_template("mqtt_broker.h.j2")
        self._write_template(template, global_context, self.output_dir / "mqtt_broker.h")

        # Generate JSON handler files
        template = self.env.get_template("json_handler.c.j2")
        self._write_template(template, global_context, self.output_dir / "json_handler.c")
        template = self.env.get_template("json_handler.h.j2")
        self._write_template(template, global_context, self.output_dir / "json_handler.h")

        # Generate build script
        template = self.env.get_template("build_docker.sh.j2")
        script_path = self.output_dir / "build_docker.sh"
        self._write_template(template, global_context, script_path)
        # Make script executable
        os.chmod(script_path, 0o755)

        # Generate Dockerfile for the self-contained RIOT build environment
        template = self.env.get_template("Dockerfile.riotbuild.j2")
        self._write_template(template, global_context, self.output_dir / "Dockerfile.riotbuild")

        # Generate peripheral drivers
        for i, conn in enumerate(self.get_connections()):
            pref = conn.peripheral.ref
            base_name = PeripheralTemplateMapper.get_template_base(pref)
            if not base_name:
                continue

            # Build context for this specific peripheral
            context = global_context.copy()
            context.update(
                {
                    "name": base_name,
                    "instance": conn.peripheral.name,
                    "index": i,
                    "freq": int(1000 / global_context["frequency"][i]),
                    "topic_name": global_context["topic"][i],
                    "conn": global_context["conns"][i],
                    "attributes": global_context["attributes_list"][i],
                    "op": global_context["op_list"][i],
                    "sampling": global_context["sampling_list"][i],
                }
            )

            p_type = type(pref).__name__.lower()
            try:
                c_template = self.env.get_template(f"{p_type}_{base_name}.c.j2")
                h_template = self.env.get_template(f"{p_type}_{base_name}.h.j2")
                self._write_template(c_template, context, self.output_dir / f"{p_type}_{base_name}_{i}.c")
                self._write_template(h_template, context, self.output_dir / f"{p_type}_{base_name}_{i}.h")
            except jinja2.TemplateNotFound as exc:
                hwd_name = type(pref).__name__ + "[" + getattr(pref, "name", "?") + "]"
                msg = (
                    f"RIOT driver template missing for peripheral '{hwd_name}': "
                    f"expected '{p_type}_{base_name}.c.j2' and '{p_type}_{base_name}.h.j2' "
                    f"in demol/templates/riot/. The .hwd file declares riotos= but the "
                    f"matching templates do not exist (jinja2: {exc})."
                )
                if os.environ.get("DEMOL_RIOT_SKIP_MISSING") == "1":
                    logger.warning(msg + " Skipping (DEMOL_RIOT_SKIP_MISSING=1).")
                    continue
                raise FileNotFoundError(msg) from exc

        logger.info("RiotOS code generation complete!")

    def _write_template(self, template, context, output_path):
        output = template.render(**context)
        with open(output_path, "w") as f:
            f.write(output)
        logger.info(f"Generated: {output_path}")


def m2t_riot(model, output_dir="."):
    """Transform a DeMoL device model object to RiotOS code."""
    output_path = Path(output_dir)
    if not output_path.exists():
        output_path.mkdir(parents=True, exist_ok=True)
    generator = RiotCodeGenerator(model, output_path)
    generator.generate()
