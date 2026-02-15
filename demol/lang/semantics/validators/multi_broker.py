"""Multi-broker validator.

Rules:
- [Broker-Unique-Names]: all declared brokers must have unique names
- [Broker-VIA-Resolve]: VIA references in connections must resolve to a declared broker
"""

import logging
from ..core import raise_validation_error
from .base import BaseValidator

logger = logging.getLogger(__name__)


class MultiBrokerValidator(BaseValidator):
    @staticmethod
    def get_name() -> str:
        return "Multi-Broker Validation"

    @staticmethod
    def get_description() -> str:
        return "Validates broker uniqueness and VIA routing references"

    @staticmethod
    def validate(model, **kwargs):
        brokers = getattr(model, "brokers", [])
        if not brokers:
            return

        seen_names = {}
        for b in brokers:
            name = getattr(b, "name", None)
            if not name:
                continue
            if name in seen_names:
                raise_validation_error(
                    b,
                    f"Duplicate broker name '{name}'. " f"Each BROKER must have a unique name.",
                    "Broker-Unique-Names",
                )
            else:
                seen_names[name] = b

        broker_names = set(seen_names.keys())

        for c in getattr(model, "connections", []):
            via = getattr(c, "via", None)
            if via and via not in broker_names:
                raise_validation_error(
                    c,
                    f"VIA '{via}' does not match any declared broker. "
                    f"Available brokers: {', '.join(sorted(broker_names))}.",
                    "Broker-VIA-Resolve",
                )

        for sc in getattr(model, "smartConnections", []):
            via = getattr(sc, "via", None)
            if via and via not in broker_names:
                raise_validation_error(
                    sc,
                    f"VIA '{via}' does not match any declared broker. "
                    f"Available brokers: {', '.join(sorted(broker_names))}.",
                    "Broker-VIA-Resolve",
                )


def validate_multi_broker(model):
    MultiBrokerValidator.validate(model)


__all__ = [
    "MultiBrokerValidator",
    "validate_multi_broker",
]
