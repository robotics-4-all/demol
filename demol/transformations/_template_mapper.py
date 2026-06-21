"""Shared PeripheralTemplateMapper for code generators.

This module provides a unified class for mapping peripheral types to their
corresponding Jinja2 templates across different platforms (RPi/Raspbian and
RiotOS).

Methods:
    get_template(peripheral_ref) — RPi behavior: returns full template filename
        (e.g., "bme680.py.tmpl") for the "raspbian" OS.
    get_template_base(peripheral_ref) — RiotOS behavior: returns stripped base
        name (e.g., "bme680") for the "riotos" OS, with `.c.j2`/`.j2` and
        optional `_riot` suffix removed.
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class PeripheralTemplateMapper:
    """Maps peripheral types to their corresponding Jinja2 templates.

    Unified class supporting both RPi (`get_template`) and RiotOS
    (`get_template_base`) template resolution.
    """

    @classmethod
    def get_template(cls, peripheral_ref) -> Optional[str]:
        """Get template name for a peripheral from its templates section.

        Args:
            peripheral_ref: Reference to the peripheral object (has .name and .templates)

        Returns:
            Template filename for raspbian OS, or None if not found
        """
        # Check peripheral's templates section for raspbian
        if hasattr(peripheral_ref, "templates") and peripheral_ref.templates:
            for template_mapping in peripheral_ref.templates:
                if template_mapping.os == "raspbian":
                    return str(template_mapping.template)

        # No template found
        logger.warning(
            f"No raspbian template found for peripheral '{peripheral_ref.name}'. "
            f"Please add a templates section with raspbian mapping to the peripheral model."
        )
        return None

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

        # No RIOT template declared in .hwd — skip cleanly. The generate loop
        # will treat None as "this peripheral has no RIOT support" and move on.
        # The fail-fast TemplateNotFound check only triggers when riotos= IS
        # declared but the matching template file is missing (true misconfig).
        return None
