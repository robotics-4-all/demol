"""Shared PeripheralTemplateMapper for code generators.

This module provides a single, OS-agnostic class for mapping peripheral types
to their corresponding Jinja2 templates across different platforms
(RPi/Raspbian, RiotOS, future Zephyr, etc.). Each peripheral's `.hwd` file
declares a `templates` map of `os=STRING template=STRING` entries; this mapper
looks up the entry matching the requested OS and returns the raw template
string.

Callers are responsible for any post-processing they need — for example, the
RiotOS generator strips `.c.j2` / `.j2` and an optional `_riot` suffix from
the returned string to derive a peripheral base name used for the
`sensor_<base>_N.c` filename construction.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class PeripheralTemplateMapper:
    """Maps peripheral types to their corresponding Jinja2 templates.

    Single-method mapper that resolves the raw template filename declared
    in a peripheral's `templates` map for a given target OS. Designed to be
    platform-agnostic — the caller decides how to interpret the result
    (load it directly via Jinja2, strip the suffix to derive a base name,
    etc.).
    """

    @classmethod
    def get_template(cls, peripheral_ref, os_name: str) -> Optional[str]:
        """Get the raw template string for a peripheral on the given OS.

        Args:
            peripheral_ref: Reference to the peripheral object. Must expose
                ``.templates`` (a list of ``TemplateMapping`` objects with
                ``.os`` and ``.template`` fields) and ``.name``.
            os_name: Target OS identifier (e.g. ``"raspbian"``, ``"riotos"``,
                ``"zephyr"``). Compared against ``TemplateMapping.os`` via
                ``str(...)`` to tolerate both enum and string forms.

        Returns:
            The raw template string declared for ``os_name`` (e.g.
            ``"bme680.c.j2"`` or ``"bme680.py.j2"``), or ``None`` if no
            matching entry exists.
        """
        if hasattr(peripheral_ref, "templates") and peripheral_ref.templates:
            for tmpl_mapping in peripheral_ref.templates:
                if str(tmpl_mapping.os) == os_name:
                    return str(tmpl_mapping.template)

        logger.warning(
            f"No '{os_name}' template found for peripheral "
            f"'{getattr(peripheral_ref, 'name', '?')}'. "
            f"Declare a `templates {os_name}=\"...\"` entry in the peripheral .hwd."
        )
        return None
