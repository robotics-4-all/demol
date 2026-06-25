"""Meta-OS validator — rejects reserved OS values that are not backed by a
code generator.

This validator checks that the device model's declared OS is one of the
supported targets (``raspbian``, ``riotos``, ``zephyr``).  The values
``arduino``, ``esp-idf``, and ``esp-idf-rtos`` are preserved in the grammar
for backward compatibility but are **not** backed by a code generator and are
therefore flagged as unsupported.
"""

from ..core import raise_validation_error
from .base import BaseValidator

# Reserved OS values that exist in the grammar but are not codegen targets.
_RESERVED_OS = {"arduino", "esp-idf", "esp-idf-rtos"}


class MetaOsNotSupportedValidator(BaseValidator):
    """Validates that the device OS is a supported codegen target."""

    @staticmethod
    def get_name() -> str:
        return "[Meta-OS-NotSupported]"

    @staticmethod
    def get_description() -> str:
        return (
            "Rejects reserved OS values (arduino, esp-idf, esp-idf-rtos) "
            "that have no codegen backend"
        )

    @staticmethod
    def validate(model, **kwargs):
        """Check ``model.metadata.os`` against the reserved set.

        If the declared OS is one of the reserved values (arduino, esp-idf,
        esp-idf-rtos), a validation error is raised.
        """
        metadata = getattr(model, "metadata", None)
        if metadata is None:
            return

        os_value = getattr(metadata, "os", None)
        if os_value is None:
            return

        os_str = os_value.lower() if isinstance(os_value, str) else str(os_value).lower()

        if os_str in _RESERVED_OS:
            raise_validation_error(
                metadata,
                f"[Meta-OS-NotSupported] OS '{os_str}' is reserved and not "
                f"supported by any code generator. "
                f"Valid targets: raspbian, riotos, zephyr.",
                "MetaOsNotSupported",
            )


def validate_meta_os(model, **kwargs):
    """Convenience function for backward compatibility.

    Calls :meth:`MetaOsNotSupportedValidator.validate`.
    """
    MetaOsNotSupportedValidator.validate(model, **kwargs)


__all__ = [
    "MetaOsNotSupportedValidator",
    "validate_meta_os",
]
