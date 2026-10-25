"""Device-level validators.

This module contains validators for device-level configuration:
- Broker requirements
- Network requirements
- Broker security
- Topic format validation (MQTT, AMQP, Redis)
"""

import re
from typing import Tuple, Optional
from ..core import raise_validation_error
from .base import BaseValidator


class BrokerRequirementsValidator(BaseValidator):
    """Validates that a broker is configured."""

    @staticmethod
    def get_name() -> str:
        return "Broker Requirements"

    @staticmethod
    def get_description() -> str:
        return "Ensures a broker is defined in the model"

    @staticmethod
    def validate(model):
        brokers = getattr(model, "brokers", [])
        if not brokers:
            if not hasattr(model, "broker") or model.broker is None:
                raise_validation_error(
                    model,
                    "[WF-Broker-Requirements] Broker configuration required: "
                    "At least one broker must be defined in the model.",
                    "MissingBrokerError",
                )


class NetworkRequirementsValidator(BaseValidator):
    """Validates that a network is configured."""

    @staticmethod
    def get_name() -> str:
        return "Network Requirements"

    @staticmethod
    def get_description() -> str:
        return "Ensures a network configuration is present"

    @staticmethod
    def validate(model):
        """
        Validate WF-Network-Requirements.

        Ensures that a network configuration is present.

        Network is now mandatory for all models.
        """
        if not hasattr(model, "network") or model.network is None:
            raise_validation_error(
                model,
                "[WF-Network-Requirements] Network configuration required: A network must be configured in the model.",
                "MissingNetworkError",
            )


class BrokerSecurityValidator(BaseValidator):
    """Validates broker security configuration."""

    @staticmethod
    def get_name() -> str:
        return "Broker Security"

    @staticmethod
    def get_description() -> str:
        return "Ensures remote brokers have authentication configured"

    @staticmethod
    def validate(model):
        brokers = getattr(model, "brokers", [])
        if not brokers:
            broker = getattr(model, "broker", None)
            brokers = [broker] if broker else []

        for broker in brokers:
            host = getattr(broker, "host", "localhost")

            has_auth = False
            if hasattr(broker, "auth") and broker.auth:
                username = getattr(broker.auth, "username", "")
                password = getattr(broker.auth, "password", "")
                key = getattr(broker.auth, "key", "")

                if (username and password) or key:
                    has_auth = True

            if host != "localhost" and not has_auth:
                raise_validation_error(
                    broker,
                    f"Remote broker '{broker.name}' ({host}) is used without authentication. "
                    "This is not secure. Please add 'auth.username' and 'auth.password' "
                    "(or 'auth.key') to your broker configuration.",
                    "SecurityError",
                )


class TopicFormatValidator(BaseValidator):
    """Validates topic format based on broker type."""

    @staticmethod
    def get_name() -> str:
        return "Topic Format Validation"

    @staticmethod
    def get_description() -> str:
        return "Ensures connection topics match the broker type format"

    @staticmethod
    def validate_mqtt_topic(topic: str) -> Tuple[bool, Optional[str]]:
        """
        Validate MQTT topic format.

        Rules:
        - Use forward slashes (/) as level separators
        - Cannot be empty
        - Cannot start with $ (reserved for system topics)
        - Wildcards: + (single level), # (multi-level, must be last)
        - No null characters
        - Max level depth (typically 128, but we'll be lenient)

        Returns:
            (is_valid, error_message)
        """
        if not topic:
            return False, "MQTT topic cannot be empty"

        # Check for null characters
        if "\x00" in topic:
            return False, "MQTT topic cannot contain null characters"

        # Check length (MQTT spec allows up to 65535 bytes, but keep reasonable)
        if len(topic) > 1000:
            return (
                False,
                f"MQTT topic too long ({len(topic)} chars), should be under 1000",
            )

        # System topics start with $, which is reserved
        if topic.startswith("$"):
            return (
                False,
                "MQTT topic cannot start with '$' (reserved for system topics)",
            )

        # Check each level
        levels = topic.split("/")

        for i, level in enumerate(levels):
            # Single-level wildcard
            if level == "+":
                continue

            # Multi-level wildcard (must be last and alone)
            if "#" in level:
                if i != len(levels) - 1:
                    return False, "MQTT wildcard '#' must be the last level"
                if level != "#":
                    return False, "MQTT wildcard '#' must be alone in its level"
                continue

            # Regular level - check for invalid wildcard usage
            if "+" in level:
                if level != "+":
                    return False, "MQTT wildcard '+' must be alone in its level"

        return True, None

    @staticmethod
    def validate_amqp_topic(topic: str) -> Tuple[bool, Optional[str]]:
        """
        Validate AMQP routing key / topic format.

        Rules:
        - Use dots (.) as separators
        - Can use wildcards: * (single word), # (zero or more words)
        - Alphanumeric and underscore, hyphen, dot
        - Cannot be empty

        Returns:
            (is_valid, error_message)
        """
        if not topic:
            return False, "AMQP routing key cannot be empty"

        # Check length
        if len(topic) > 255:
            return (
                False,
                f"AMQP routing key too long ({len(topic)} chars), should be under 255",
            )

        # Split by dots
        parts = topic.split(".")

        for part in parts:
            if not part:
                return (
                    False,
                    "AMQP routing key cannot have empty segments (double dots)",
                )

            # Allow wildcards
            if part in ("*", "#"):
                continue

            # Check valid characters: alphanumeric, underscore, hyphen
            if not re.match(r"^[a-zA-Z0-9_-]+$", part):
                return (
                    False,
                    f"AMQP routing key segment '{part}' contains invalid characters. Use alphanumeric, underscore, or hyphen only",
                )

        return True, None

    @staticmethod
    def validate_redis_topic(topic: str) -> Tuple[bool, Optional[str]]:
        """
        Validate Redis pub/sub channel pattern.

        Rules:
        - Can use pattern matching with * and ?
        - Typically uses : or . as separators by convention
        - Cannot be empty
        - No special restrictions like MQTT

        Returns:
            (is_valid, error_message)
        """
        if not topic:
            return False, "Redis channel cannot be empty"

        # Check length
        if len(topic) > 512:
            return (
                False,
                f"Redis channel too long ({len(topic)} chars), should be under 512",
            )

        # Redis is quite flexible, just check it's not empty and reasonable length
        # Pattern matching with glob-style patterns is allowed

        return True, None

    @staticmethod
    def _get_broker_validator(broker):
        broker_type = broker.__class__.__name__
        if "MQTT" in broker_type.upper():
            return TopicFormatValidator.validate_mqtt_topic, "MQTT"
        elif "AMQP" in broker_type.upper():
            return TopicFormatValidator.validate_amqp_topic, "AMQP"
        elif "REDIS" in broker_type.upper():
            return TopicFormatValidator.validate_redis_topic, "Redis"
        return None, None

    @staticmethod
    def validate(model):
        default_broker = getattr(model, "broker", None)
        broker_map = getattr(model, "_broker_map", {})

        if not default_broker and not broker_map:
            return

        for connection in model.connections:
            if not hasattr(connection, "remote") or not connection.remote:
                continue

            resolved = getattr(connection, "_resolved_broker", default_broker)
            if not resolved:
                continue

            validator, broker_name = TopicFormatValidator._get_broker_validator(resolved)
            if not validator:
                continue

            topic = connection.remote.strip('"').strip("'")
            is_valid, error_msg = validator(topic)

            if not is_valid:
                try:
                    from demol.lang.semantics.core import get_location as get_loc

                    location = get_loc(connection)
                    location_str = f"{location.get('filename', 'unknown')}:{location.get('line', '?')}"
                except Exception:
                    location_str = "unknown location"

                warning_msg = (
                    f"[Topic-Validation] Invalid {broker_name} topic at "
                    f"{location_str}: "
                    f"Connection has topic '{topic}'. "
                    f"{error_msg}"
                )
                raise_validation_error(connection, warning_msg, "TopicValidationError")


# Convenience function exports (for backward compatibility)
def validate_broker_requirements(model):
    """Validate broker requirements."""
    BrokerRequirementsValidator.validate(model)


def validate_network_requirements(model):
    """Validate network requirements."""
    NetworkRequirementsValidator.validate(model)


def validate_broker_security(model):
    """Validate broker security."""
    BrokerSecurityValidator.validate(model)


def validate_topic_format(model):
    """Validate topic format."""
    TopicFormatValidator.validate(model)


__all__ = [
    "BrokerRequirementsValidator",
    "NetworkRequirementsValidator",
    "BrokerSecurityValidator",
    "TopicFormatValidator",
    "validate_broker_requirements",
    "validate_network_requirements",
    "validate_broker_security",
    "validate_topic_format",
]
