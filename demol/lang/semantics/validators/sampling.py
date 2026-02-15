"""Sampling configuration validator.

Rules:
- [Sampling-Positive-Rate]: rate must be > 0
- [Sampling-Duplicate]: each peripheral may have at most one SAMPLING block
- [Sampling-OnChange-Threshold]: on_change mode requires threshold > 0
- [Sampling-Batch-Buffer]: batch mode requires buffer > 0
- [Sampling-Board-Target]: SAMPLING target must be a peripheral, not a board
"""

import logging
from ..core import raise_validation_error, raise_validation_warning
from .base import BaseValidator

logger = logging.getLogger(__name__)

_FREQ_UNIT_TO_HZ = {
    "ghz": 1e9,
    "mhz": 1e6,
    "khz": 1e3,
    "hz": 1.0,
}


def _rate_to_hz(rate, unit):
    if rate is None or unit is None:
        return None
    factor = _FREQ_UNIT_TO_HZ.get(str(unit).lower(), 1.0)
    return float(rate) * factor


class SamplingValidator(BaseValidator):
    @staticmethod
    def get_name() -> str:
        return "Sampling Configuration"

    @staticmethod
    def get_description() -> str:
        return "Validates SAMPLING block constraints (rate, mode, duplicates)"

    @staticmethod
    def validate(model, **kwargs):
        samplings = getattr(model, "samplings", [])
        if not samplings:
            return

        seen_targets = {}

        for s in samplings:
            target = s.target
            target_name = getattr(target, "name", "unknown")

            if target_name in seen_targets:
                raise_validation_error(
                    s,
                    f"Duplicate SAMPLING for '{target_name}'. " f"Each peripheral may have at most one SAMPLING block.",
                    "Sampling-Duplicate",
                )
                continue
            seen_targets[target_name] = s

            ref = target.ref if hasattr(target, "ref") else target
            ref_class = type(ref).__name__
            if "Board" in ref_class:
                raise_validation_error(
                    s,
                    f"SAMPLING target '{target_name}' is a board, not a peripheral. "
                    f"SAMPLING can only be applied to sensors and actuators.",
                    "Sampling-Board-Target",
                )
                continue

            rate_hz = _rate_to_hz(s.rate, s.rate_unit)
            if rate_hz is not None and rate_hz <= 0:
                raise_validation_error(
                    s,
                    f"SAMPLING rate for '{target_name}' must be positive, " f"got {s.rate} {s.rate_unit}.",
                    "Sampling-Positive-Rate",
                )

            ref_op = getattr(ref, "operational", None)
            if ref_op and rate_hz:
                freq_max = getattr(ref_op, "freq_max", None)
                if freq_max:
                    max_val = getattr(freq_max, "value", None)
                    max_unit = getattr(freq_max, "unit", None)
                    if max_val and max_unit:
                        max_hz = _rate_to_hz(max_val, max_unit)
                        if max_hz and rate_hz > max_hz:
                            raise_validation_warning(
                                s,
                                f"SAMPLING rate for '{target_name}' "
                                f"({s.rate} {s.rate_unit} = {rate_hz:.0f} Hz) "
                                f"exceeds peripheral max frequency "
                                f"({max_val} {max_unit} = {max_hz:.0f} Hz).",
                                "SamplingRateWarning",
                            )

            mode = getattr(s, "mode", None)
            threshold = getattr(s, "threshold", 0.0)
            buffer_size = getattr(s, "buffer", 0)

            if mode == "on_change" and (threshold is None or threshold <= 0):
                raise_validation_error(
                    s,
                    f"SAMPLING mode 'on_change' for '{target_name}' requires " f"threshold > 0.",
                    "Sampling-OnChange-Threshold",
                )

            if mode == "batch" and (buffer_size is None or buffer_size <= 0):
                raise_validation_error(
                    s,
                    f"SAMPLING mode 'batch' for '{target_name}' requires buffer > 0.",
                    "Sampling-Batch-Buffer",
                )


def validate_sampling(model):
    SamplingValidator.validate(model)


__all__ = [
    "SamplingValidator",
    "validate_sampling",
]
