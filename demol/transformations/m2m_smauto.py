from pathlib import Path
from typing import Any, Dict, List

import jinja2

from demol.definitions import SMAUTO_TEMPLATES
from .base_generator import BaseCodeGenerator


class SmautoGenerator(BaseCodeGenerator):
    """Generates a SmartAuto model from a DeMoL device model."""

    OS = ""

    def __init__(self, device_model, output_dir="."):
        self.output_dir = Path(output_dir)
        super().__init__(device_model, self.output_dir)
        self.env = self.setup_template_environment()
        self.broker_data: Dict[str, Any] = {}
        self.peripherals_data: List[Dict[str, Any]] = []

    def setup_template_environment(self) -> jinja2.Environment:
        fsloader = jinja2.FileSystemLoader(SMAUTO_TEMPLATES)
        return jinja2.Environment(loader=fsloader)

    def _get_broker_info(self) -> None:
        device_model = self.device_model
        broker_type = device_model.broker.__class__.__name__
        self.broker_data["broker_type"] = broker_type.replace("Broker", "")
        self.broker_data["broker_host"] = device_model.broker.host
        self.broker_data["broker_port"] = device_model.broker.port
        self.broker_data["broker_name"] = device_model.broker.name
        if hasattr(device_model.broker, "auth_username") and device_model.broker.auth_username:
            self.broker_data["broker_username"] = device_model.broker.auth_username
            self.broker_data["broker_password"] = getattr(device_model.broker, "auth_password", None)
        elif hasattr(device_model.broker, "auth") and str(device_model.broker.auth.__class__.__name__) == "AuthPlain":
            self.broker_data["broker_username"] = device_model.broker.auth.username
            self.broker_data["broker_password"] = device_model.broker.auth.password
        else:
            self.broker_data["broker_username"] = None
            self.broker_data["broker_password"] = None

        if self.broker_data["broker_type"] == "AMQP" and hasattr(device_model.broker, "vhost"):
            self.broker_data["broker_vhost"] = device_model.broker.vhost
        if self.broker_data["broker_type"] == "AMQP" and hasattr(device_model.broker, "topicE"):
            self.broker_data["broker_topicExchange"] = device_model.broker.topicE

        if (
            self.broker_data["broker_type"] == "Redis"
            and hasattr(device_model.broker, "db")
            and device_model.broker.db is not None
        ):
            self.broker_data["broker_db"] = device_model.broker.db

    def _get_peripherals_info(self) -> None:
        for i, conn in enumerate(self.device_model.connections):
            peripheral_data: Dict[str, Any] = {}
            per_frequency = 0

            if not hasattr(conn, "peripheral") or not conn.peripheral:
                continue

            per_dev_name = conn.peripheral.name
            per_real_name = conn.peripheral.ref.name
            per_type = type(conn.peripheral.ref).__name__
            per_topic = conn.remote if conn.remote else f"device/{per_dev_name}"
            per_broker = self.broker_data["broker_name"]
            per_msg_type = conn.peripheral.ref.type
            peripheral_data = {
                "per_name": per_dev_name,
                "per_real_name": per_real_name,
                "per_type": per_type,
                "per_topic": per_topic,
                "per_broker": per_broker,
                "per_msg_type": per_msg_type,
            }

            freq_found = False
            if hasattr(conn.peripheral, "attributes"):
                for attribute in conn.peripheral.attributes:
                    if attribute.name == "frequency":
                        per_frequency = attribute.value
                        peripheral_data = peripheral_data | {"per_frequency": per_frequency}
                        freq_found = True
                        break

            if not freq_found:
                for attribute in conn.peripheral.ref.attributes:
                    if attribute.name == "frequency":
                        per_frequency = attribute.default
                        peripheral_data = peripheral_data | {"per_frequency": per_frequency}

            self.peripherals_data.append(peripheral_data)

    def generate(self) -> None:
        self._get_broker_info()
        self._get_peripherals_info()

        if str(self.output_dir) != "." and not self.output_dir.exists():
            self.output_dir.mkdir(parents=True, exist_ok=True)

        template = self.env.get_template("BrokerAndEntity.j2")
        filepath = self.output_dir / f"{self.device_model.metadata.name}SmAutoModel.auto"
        self._write_template(template, {**self.broker_data, "peripherals": self.peripherals_data}, filepath)


def demol2smauto(model, output_dir="."):
    generator = SmautoGenerator(model, Path(output_dir))
    generator.generate()
