"""Alert trigger validators.

This module validates ALERT trigger declarations:
- Alert names must be unique
- Source must be a sensor (not an actuator or board)
- ACTIVATE targets must be actuators
- VIA references must resolve to declared brokers
- Cooldown must be positive
- Condition properties are syntactically valid identifiers
- Per-OS multi-broker support is respected (see PER_OS_CAPABILITIES)

The per-OS capability table governs which runtime warnings are emitted. The
default is permissive: unknown OSes are assumed to support multi-broker
routing. RIOT is the only currently-flagged exception because its firmware
ships a single global MQTTClient, so non-default VIA references are
downgraded by the codegen. The `[Safety-Alert-RiotMultiBroker]` rule name is
preserved for backward compatibility.
"""

from ..core import raise_validation_error, raise_validation_warning
from .base import BaseValidator

# Per-OS capability table.
# Add a new target OS here (or extend an existing entry) when:
#   - the codegen for that OS starts/stops supporting non-default VIA routing,
#   - or any other OS-specific alert behavior diverges from the default.
#
# Default for unknown OSes: multi_broker is assumed supported, so adding a
# new target can never silently downgrade multi-broker routing.
PER_OS_CAPABILITIES = {
    "raspbian": {"multi_broker": True},
    "riotos": {"multi_broker": False},
    "zephyr": {"multi_broker": True},
    "arduino": {"multi_broker": True},
    "esp-idf": {"multi_broker": True},
    "esp-idf-rtos": {"multi_broker": True},
}


def _supports_multi_broker(target_os: str) -> bool:
    """Return True if the target OS supports routing to a non-default VIA broker.

    Looks up ``target_os`` in ``PER_OS_CAPABILITIES``; unknown OSes default to
    ``True`` so that adding a new target cannot silently strip the
    multi-broker routing path.
    """
    return PER_OS_CAPABILITIES.get(target_os, {}).get("multi_broker", True)


class AlertValidator(BaseValidator):
    """Validates ALERT trigger declarations."""

    @staticmethod
    def get_name() -> str:
        return "Alert Trigger Validation"

    @staticmethod
    def get_description() -> str:
        return "Validates ALERT trigger well-formedness and cross-references"

    @staticmethod
    def validate(model, **kwargs):
        """
        Validate all ALERT triggers in the model.

        Rules:
        - [Safety-Alert-UniqueNames] Alert names must be unique
        - [Safety-Alert-SensorSource] Source must be a sensor
        - [Safety-Alert-ActuatorTarget] ACTIVATE targets must be actuators
        - [Safety-Alert-ViaResolve] VIA references must resolve to brokers
        - [Safety-Alert-Cooldown] Cooldown must be positive if specified
        - [Safety-Alert-NoSelfActivate] Cannot ACTIVATE the source sensor
        """
        alerts = getattr(model, "alerts", [])
        if not alerts:
            return

        # Collect peripheral info for validation
        board = getattr(model.components, "board", None)
        peripherals = getattr(model.components, "peripherals", [])
        broker_map = getattr(model, "_broker_map", {})

        # Detect target OS capabilities. The multi-broker warning is only
        # emitted for OSes whose runtime does NOT support non-default VIA
        # routing. The capability table defaults to "supported" for unknown
        # OSes, so adding a new target can never silently strip this feature.
        metadata = getattr(model, "metadata", None)
        target_os = (getattr(metadata, "os", "") or "").lower() if metadata else ""
        multi_broker_supported = _supports_multi_broker(target_os)
        default_broker_name = None
        brokers_list = getattr(model, "brokers", None) or []
        if brokers_list:
            default_broker_name = getattr(brokers_list[0], "name", None)
        elif getattr(model, "broker", None):
            default_broker_name = getattr(model.broker, "name", None)

        # Build lookup: instance name -> component instance
        peripheral_map = {}
        sensor_names = set()
        actuator_names = set()
        for p in peripherals:
            inst_name = getattr(p, "name", None)
            if inst_name:
                peripheral_map[inst_name] = p
                ref = getattr(p, "ref", None)
                if ref:
                    ref_class = ref.__class__.__name__
                    if "Sensor" in ref_class:
                        sensor_names.add(inst_name)
                    elif "Actuator" in ref_class:
                        actuator_names.add(inst_name)

        # [Safety-Alert-UniqueNames] Check unique alert names
        seen_names = {}
        for alert in alerts:
            name = alert.name
            if name in seen_names:
                raise_validation_error(
                    alert,
                    f"[Safety-Alert-UniqueNames] Duplicate alert name '{name}'. "
                    f"Each ALERT must have a unique name.",
                    "AlertUniqueNameError",
                )
            else:
                seen_names[name] = alert

        for alert in alerts:
            source = alert.source
            source_name = getattr(source, "name", None)

            # [Safety-Alert-SensorSource] Source must be a sensor
            if source_name and source_name not in sensor_names:
                if source_name in actuator_names:
                    raise_validation_error(
                        alert,
                        f"[Safety-Alert-SensorSource] ALERT '{alert.name}' "
                        f"source '{source_name}' is an actuator, not a sensor. "
                        f"ALERTs can only monitor sensor readings.",
                        "AlertSourceError",
                    )
                elif board and source_name == board.name:
                    raise_validation_error(
                        alert,
                        f"[Safety-Alert-SensorSource] ALERT '{alert.name}' "
                        f"source '{source_name}' is the board. "
                        f"ALERTs can only monitor sensor readings.",
                        "AlertSourceError",
                    )

            # Validate actions
            for action in alert.actions:
                cls_name = action.__class__.__name__

                if cls_name == "AlertPublish":
                    # [Safety-Alert-ViaResolve] VIA must resolve
                    via = getattr(action, "via", None)
                    if via and via not in broker_map:
                        raise_validation_error(
                            alert,
                            f"[Safety-Alert-ViaResolve] ALERT '{alert.name}' "
                            f"action PUBLISH references broker '{via}' via VIA, "
                            f"but no broker with that name is declared. "
                            f"Available brokers: "
                            f"{', '.join(broker_map.keys()) if broker_map else 'none'}",
                            "AlertViaResolveError",
                        )

                    # [Safety-Alert-RiotMultiBroker] Per PER_OS_CAPABILITIES,
                    # only target OSes that do NOT support multi-broker routing
                    # get this warning. RIOT is the currently-flagged target:
                    # its firmware ships a single global MQTTClient, so
                    # m2t_riot.py downgrades non-default VIA to the default
                    # broker. Rule name is preserved for backward compat.
                    if (
                        not multi_broker_supported
                        and via
                        and via in broker_map
                        and default_broker_name
                        and via != default_broker_name
                    ):
                        raise_validation_warning(
                            alert,
                            f"[Safety-Alert-RiotMultiBroker] ALERT '{alert.name}' "
                            f"PUBLISH ... VIA '{via}' will be routed to the "
                            f"default broker '{default_broker_name}' on RIOT "
                            f"because the firmware uses a single MQTT client.",
                            "AlertRiotMultiBrokerWarning",
                        )

                    # Validate topic is non-empty
                    topic = getattr(action, "topic", "")
                    if not topic or not topic.strip():
                        raise_validation_error(
                            alert,
                            f"[Safety-Alert-EmptyTopic] ALERT '{alert.name}' " f"PUBLISH action has an empty topic.",
                            "AlertEmptyTopicError",
                        )

                elif cls_name == "AlertActivate":
                    target = action.target
                    target_name = getattr(target, "name", None)

                    # [Safety-Alert-ActuatorTarget] Target must be actuator
                    if target_name and target_name not in actuator_names:
                        if target_name in sensor_names:
                            raise_validation_error(
                                alert,
                                f"[Safety-Alert-ActuatorTarget] ALERT "
                                f"'{alert.name}' ACTIVATE target "
                                f"'{target_name}' is a sensor. "
                                f"ACTIVATE can only target actuators.",
                                "AlertActivateTargetError",
                            )
                        else:
                            raise_validation_error(
                                alert,
                                f"[Safety-Alert-ActuatorTarget] ALERT "
                                f"'{alert.name}' ACTIVATE target "
                                f"'{target_name}' is not a declared actuator.",
                                "AlertActivateTargetError",
                            )

                    # [Safety-Alert-NoSelfActivate] Can't activate source
                    if target_name and target_name == source_name:
                        raise_validation_error(
                            alert,
                            f"[Safety-Alert-NoSelfActivate] ALERT "
                            f"'{alert.name}' cannot ACTIVATE its own source "
                            f"'{source_name}'.",
                            "AlertSelfActivateError",
                        )

            # [Safety-Alert-Cooldown] Cooldown must be positive
            cooldown = getattr(alert, "cooldown", 0)
            if cooldown and cooldown < 0:
                raise_validation_error(
                    alert,
                    f"[Safety-Alert-Cooldown] ALERT '{alert.name}' " f"cooldown must be positive, got {cooldown}.",
                    "AlertCooldownError",
                )

            # Validate condition tree
            _validate_condition(alert, alert.condition)


def _validate_condition(alert, cond):
    """Recursively validate an AlertConditionExpr tree."""
    if cond is None:
        return

    cls_name = cond.__class__.__name__

    if cls_name == "AlertComparison":
        # Leaf node — validate property name is a valid identifier
        prop = getattr(cond, "property", None)
        if prop and not prop.isidentifier():
            raise_validation_error(
                alert,
                f"[Safety-Alert-InvalidProperty] ALERT '{alert.name}' "
                f"condition property '{prop}' is not a valid identifier.",
                "AlertPropertyError",
            )
    elif cls_name == "AlertConditionExpr":
        left = getattr(cond, "left", None)
        right = getattr(cond, "right", None)
        _validate_condition(alert, left)
        if right:
            _validate_condition(alert, right)


def validate_alerts(model, **kwargs):
    """Convenience function for backward compatibility."""
    AlertValidator.validate(model, **kwargs)


__all__ = [
    "AlertValidator",
    "validate_alerts",
]
