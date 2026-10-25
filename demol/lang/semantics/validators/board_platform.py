"""Board-Platform compatibility validator.

Warns when a device model's board does not declare support for the
model's target operating system via its ``PLATFORMS`` block.

This validator catches the problem early (at ``demol validate`` time)
instead of failing opaquely at codegen build time when
:class:`~demol.transformations.board_registry.BoardNameRegistry` falls
back to the lowercased DeMoL board name.

Rule: ``[Board-Platform]`` — Severity: warning
"""

from __future__ import annotations

from ..core import raise_validation_warning, report_passed_rule
from .base import BaseValidator

# The set of OS values that have a working code generator.
_CODEGEN_OSES = {"raspbian", "riotos", "zephyr", "wokwi", "renode"}

# Known OS values in the grammar that have NO codegen backend.
_RESERVED_OS = {"arduino", "esp-idf", "esp-idf-rtos"}


class BoardPlatformValidator(BaseValidator):
    """Validates that the device's board declares support for the target OS."""

    @staticmethod
    def get_name() -> str:
        return "[Board-Platform]"

    @staticmethod
    def get_description() -> str:
        return "Warns when the board's PLATFORMS block does not include " "the model's declared OS"

    @staticmethod
    def validate(model, **kwargs):
        """Check board-platform compatibility.

        For each board referenced in the model, checks whether its
        ``PLATFORMS`` block (in the ``.hwd`` file) includes an entry for
        the operating system declared in ``model.metadata.os``.

        If the model does not declare an ``os``, the validator skips
        (no target OS to validate against).
        """
        metadata = getattr(model, "metadata", None)
        if metadata is None:
            return

        os_value = getattr(metadata, "os", None)
        if os_value is None:
            return

        model_os = str(os_value).lower()

        # Skip reserved OS values — those are caught by MetaOsNotSupportedValidator.
        if model_os in _RESERVED_OS:
            return

        # Skip if the OS is not a codegen target (future-proofing).
        if model_os not in _CODEGEN_OSES:
            return

        board = getattr(model, "components", None)
        if board is None:
            return
        board = getattr(board, "board", None)
        if board is None:
            return

        board_name = getattr(board, "name", "unknown")

        platforms = getattr(board, "platforms", None)

        if not platforms:
            # Board has no PLATFORMS block at all — board support status unknown.
            raise_validation_warning(
                board,
                f"[Board-Platform] Board '{board_name}' has no PLATFORMS block. "
                f"Code generation for OS '{model_os}' may fail at build time. "
                f"Add a PLATFORMS section to the board's .hwd file to declare "
                f"supported targets.",
                "BoardPlatformWarning",
            )
            return

        # Collect all OS names declared in the board's PLATFORMS block.
        declared_oses = {p.os for p in platforms if hasattr(p, "os")}

        if model_os not in declared_oses:
            declared_list = ", ".join(sorted(declared_oses)) if declared_oses else "none"
            raise_validation_warning(
                board,
                f"[Board-Platform] Board '{board_name}' declares PLATFORMS for "
                f"OS ({declared_list}) but does not include '{model_os}'. "
                f"Code generation for OS '{model_os}' may fail at build time.",
                "BoardPlatformWarning",
            )
            return

        report_passed_rule("[Board-Platform]")


def validate_board_platform(model, **kwargs):
    """Convenience function for backward compatibility.

    Calls :meth:`BoardPlatformValidator.validate`.
    """
    BoardPlatformValidator.validate(model, **kwargs)


__all__ = [
    "BoardPlatformValidator",
    "validate_board_platform",
]
