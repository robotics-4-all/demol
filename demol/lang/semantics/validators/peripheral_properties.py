"""Peripheral PROPERTIES validator.

PROPERTIES blocks on Sensor/Actuator definitions map DSL-visible property names
to platform-specific runtime expressions (used by ALERT codegen, particularly
RIOT). Each property may be tagged with `FOR <platform>` so the same DSL name
can resolve to different expressions per target.

Rules
-----
- [Properties-Empty-Expr]:        the right-hand-side `expr` string must be non-empty.
- [Properties-Scale-Positive]:    if SCALE is given it must be > 0.
- [Properties-Duplicate-Per-Target]:
        within a peripheral, two PROPERTIES entries cannot share the same name
        AND the same target tag (a default-target entry plus a `FOR riotos`
        entry for the same name is allowed and intended).
- [Properties-Conflicting-Default]:
        if a property has BOTH an untagged (default) entry and one or more
        target-tagged entries, that's a warning - the default would silently
        be shadowed on the tagged platforms which is rarely the author's
        intent. Authors should tag every entry explicitly.

The validator walks `model.peripherals` (USE-resolved peripheral instances) so
it runs on the device-side metamodel like every other validator. Properties
that don't exist on a peripheral (older `.hwd` files) are simply skipped.
"""

import logging
from collections import defaultdict

from ..core import raise_validation_error, raise_validation_warning, report_passed_rule
from .base import BaseValidator

logger = logging.getLogger(__name__)


class PeripheralPropertyValidator(BaseValidator):
    @staticmethod
    def get_name() -> str:
        return "Peripheral Properties"

    @staticmethod
    def get_description() -> str:
        return "Validates PROPERTIES blocks on peripherals (well-formedness, " "duplicates, scale plausibility)"

    @staticmethod
    def validate(model, **kwargs):
        any_failed = False
        # Each `connection.peripheral.ref` resolves to the Sensor/Actuator
        # definition that carries PROPERTIES. Different ComponentInstances may
        # reference the same definition; dedup by id(ref) so we don't report
        # the same peripheral type N times.
        seen_components = set()
        for conn in getattr(model, "connections", []) or []:
            instance = getattr(conn, "peripheral", None)
            if instance is None:
                continue
            periph = getattr(instance, "ref", None)
            if periph is None:
                continue
            key = id(periph)
            if key in seen_components:
                continue
            seen_components.add(key)

            properties = getattr(periph, "properties", None)
            if not properties:
                continue

            by_key = defaultdict(list)
            by_name = defaultdict(list)
            for prop in properties:
                target = getattr(prop, "target", None) or ""
                by_key[(prop.name, target)].append(prop)
                by_name[prop.name].append(prop)

                if not (prop.expr or "").strip():
                    raise_validation_error(
                        prop,
                        f"PROPERTIES entry '{prop.name}' on '{periph.name}' has an empty expression",
                        "[Properties-Empty-Expr]",
                    )
                    any_failed = True

                # Scale positivity check (scale=0 is the textX default for
                # an unset INT, so only flag explicit negatives).
                scale = getattr(prop, "scale", 0) or 0
                if scale < 0:
                    raise_validation_error(
                        prop,
                        f"PROPERTIES entry '{prop.name}' on '{periph.name}' has non-positive SCALE {scale}",
                        "[Properties-Scale-Positive]",
                    )
                    any_failed = True

            for (name, target), entries in by_key.items():
                if len(entries) > 1:
                    target_label = target or "<default>"
                    raise_validation_error(
                        entries[1],
                        (
                            f"PROPERTIES entry '{name}' on '{periph.name}' is declared "
                            f"{len(entries)} times for target '{target_label}'"
                        ),
                        "[Properties-Duplicate-Per-Target]",
                    )
                    any_failed = True

            for name, entries in by_name.items():
                targets = {(getattr(e, "target", None) or "") for e in entries}
                if "" in targets and len(targets) > 1:
                    raise_validation_warning(
                        entries[0],
                        (
                            f"PROPERTIES entry '{name}' on '{periph.name}' has both an "
                            "untagged default and one or more 'FOR <platform>' entries; "
                            "tag every entry explicitly to avoid silent platform shadowing"
                        ),
                        "[Properties-Conflicting-Default]",
                    )

        if not any_failed:
            report_passed_rule("Peripheral Properties")


def validate_peripheral_properties(model, **kwargs):
    PeripheralPropertyValidator.validate(model, **kwargs)
