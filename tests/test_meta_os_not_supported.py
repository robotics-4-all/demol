"""Tests for the [Meta-OS-NotSupported] validator.

Verifies that reserved OS values (arduino, esp-idf, esp-idf-rtos) are rejected
by the MetaOsNotSupportedValidator with an appropriate error message.
"""

import pytest
from textx import TextXSemanticError
from demol.lang.semantics.validators.meta_os import (
    MetaOsNotSupportedValidator,
    validate_meta_os,
    _RESERVED_OS,
)

# Minimal valid model preamble — the OS is the only variable part.
PREAMBLE = """
DEVICE TestDevice WITH description="test", author="test", os={os};
USE RaspberryPi_5_8GB;
"""


class TestMetaOsNotSupportedValidator:
    """MetaOsNotSupportedValidator: unit-level tests."""

    def test_get_name(self):
        assert MetaOsNotSupportedValidator.get_name() == "[Meta-OS-NotSupported]"

    def test_get_description(self):
        desc = MetaOsNotSupportedValidator.get_description()
        assert "arduino" in desc
        assert "esp-idf" in desc
        assert "esp-idf-rtos" in desc

    def test_reserved_os_set(self):
        assert "arduino" in _RESERVED_OS
        assert "esp-idf" in _RESERVED_OS
        assert "esp-idf-rtos" in _RESERVED_OS
        assert len(_RESERVED_OS) == 3


class TestMetaOsNotSupportedValidation:
    """Integration: reserved OS models raise validation errors."""

    @pytest.mark.parametrize(
        "os_key",
        ["arduino", "esp-idf", "esp-idf-rtos"],
        ids=["arduino-rejected", "esp-idf-rejected", "esp-idf-rtos-rejected"],
    )
    def test_reserved_os_rejected(self, device_mm, os_key):
        model_str = PREAMBLE.format(os=os_key)
        with pytest.raises(TextXSemanticError, match=r"\[Meta-OS-NotSupported\]"):
            device_mm.model_from_str(model_str)

    def test_valid_os_not_rejected(self, device_mm):
        """A supported OS (raspbian) must pass without [Meta-OS-NotSupported] errors."""
        model_str = PREAMBLE.format(os="raspbian")
        # Should not raise TextXSemanticError for [Meta-OS-NotSupported]
        try:
            device_mm.model_from_str(model_str)
        except TextXSemanticError as e:
            if "[Meta-OS-NotSupported]" in str(e):
                pytest.fail(f"raspbian should not trigger [Meta-OS-NotSupported]: {e}")


class TestValidateMetaOsFunction:
    """validate_meta_os convenience function."""

    def test_function_exists(self):
        assert callable(validate_meta_os)
