"""Board name registry for cross-OS target resolution.

Maps DeMoL board names (.hwd `BOARD` declarations) to target-OS-specific
board identifiers used by downstream build systems. The registry is
extensible via :meth:`BoardNameRegistry.register` and is consulted by
per-OS generators (``m2t_zephyr``, ``m2t_riot``) to translate between
the neutral DeMoL board namespace and vendor/toolchain-specific names.

Examples:

* ``RaspberryPi_4_Model_B``  → ``rpi_4b``       (Zephyr)
* ``RaspberryPi_4B_4GB``     → ``rpi_4b``       (Zephyr, alias)
* ``RaspberryPi_4B_8GB``     → ``rpi_4b``       (Zephyr, alias)
* ``esp32wroom32``           → ``esp32_devkitc`` (Zephyr)
* ``ESP32Wroom32``           → ``esp32_devkitc`` (Zephyr, case-insensitive)
* ``esp32wroom32``           → ``esp32-wroom-32`` (RIOT OS)
* ``raspberrypi_5_8gb``      → ``rpi_5``         (Zephyr)

Lookups are case-insensitive — ``resolve("ESP32Wroom32", "zephyr")`` and
``resolve("esp32wroom32", "zephyr")`` both yield the Zephyr target name.
Unknown boards fall back to the lowercased DeMoL name so generators never
silently drop a board reference.
"""

from typing import Dict, Optional

__all__ = ["BoardNameRegistry"]


class BoardNameRegistry:
    """Registry of DeMoL board name → target-OS board name mappings.

    The default constructor seeds a small but pragmatic mapping for the
    boards present in :mod:`demol.builtin_models.boards` plus the legacy
    ``RaspberryPi_4_Model_B`` alias used in early DeMoL documentation and
    test fixtures. New mappings can be added with :meth:`register`; the
    default seeds may be overridden by passing ``overwrite=True``.
    """

    # Keys are lowercased DeMoL board names; values are per-OS target names.
    _DEFAULT_MAPPINGS: Dict[str, Dict[str, str]] = {
        "raspberrypi_4b_4gb": {"zephyr": "rpi_4b", "riotos": "rpi_4b"},
        "raspberrypi_4b_8gb": {"zephyr": "rpi_4b", "riotos": "rpi_4b"},
        "raspberrypi_4_model_b": {"zephyr": "rpi_4b", "riotos": "rpi_4b"},
        "raspberrypi_5_8gb": {"zephyr": "rpi_5", "riotos": "rpi_5"},
        "raspberrypi_3a_plus": {"zephyr": "rpi_3a_plus", "riotos": "rpi_3a_plus"},
        "raspberrypi_3b": {"zephyr": "rpi_3b", "riotos": "rpi_3b"},
        "raspberrypi_3b_plus": {"zephyr": "rpi_3b_plus", "riotos": "rpi_3b_plus"},
        "raspberrypi_pico": {"zephyr": "rpi_pico", "riotos": "rpi_pico"},
        "esp32wroom32": {"zephyr": "esp32_devkitc", "riotos": "esp32-wroom-32"},
        "nodemcu_esp8266": {"zephyr": "esp8266", "riotos": "esp8266"},
        "wemos_d1_mini": {"zephyr": "esp8266", "riotos": "esp8266"},
        "wemos_d1_r32": {"zephyr": "esp32_devkitc", "riotos": "esp32-wroom-32"},
        "arduino_uno": {"zephyr": "arduino_uno", "riotos": "arduino-uno"},
    }

    def __init__(self) -> None:
        """Initialize the registry with the default board name mappings."""
        # Deep copy the default mapping so instance mutations are isolated.
        # Keys are normalized via _normalize() so that e.g. ``wemos_d1_r32``
        # (from the .hwd filename) matches ``WemosD1R32`` (from USE in a
        # .dev model) — both resolve to ``wemosd1r32``.
        self._mappings: Dict[str, Dict[str, str]] = {
            self._normalize(board): dict(os_map)
            for board, os_map in self._DEFAULT_MAPPINGS.items()
        }

    @staticmethod
    def _normalize(board_name: str) -> str:
        """Normalize a board name to the registry's canonical key form.

        Strips underscores and lowercases so that ``WemosD1R32``,
        ``wemos_d1_r32`` (from .hwd filenames), and ``WemosD1R32``
        all resolve to the same key ``wemosd1r32``.
        """
        return board_name.replace("_", "").lower() if board_name else ""

    def register(
        self,
        board_name: str,
        os_name: str,
        target: str,
        overwrite: bool = False,
    ) -> None:
        """Register or extend a board name → OS → target mapping.

        Args:
            board_name: DeMoL board name (case-insensitive).
            os_name: Target OS identifier (e.g. ``"zephyr"``, ``"riotos"``).
            target: OS-specific target board name.
            overwrite: If ``True``, allow replacing an existing mapping for
                the same ``(board_name, os_name)`` pair. Defaults to
                ``False`` to surface accidental double registrations.
        """
        key = self._normalize(board_name)
        os_key = os_name.lower()
        if key not in self._mappings:
            self._mappings[key] = {}
        if not overwrite and os_key in self._mappings[key]:
            raise ValueError(
                f"BoardNameRegistry: duplicate mapping for "
                f"({board_name!r}, {os_name!r}); pass overwrite=True to replace."
            )
        self._mappings[key][os_key] = target

    def resolve(self, board_name: str, os_name: str) -> str:
        """Resolve a DeMoL board name to the target-OS-specific name.

        Lookup is case-insensitive. If no explicit mapping exists, the
        normalized DeMoL name is returned so generators never silently
        drop a board reference — the result is always a non-empty string.

        Args:
            board_name: DeMoL board name (e.g. ``"RaspberryPi_4B_4GB"``).
            os_name: Target OS identifier (e.g. ``"zephyr"``, ``"riotos"``).

        Returns:
            Target-OS-specific board name. Falls back to the lowercased
            DeMoL name when no mapping is registered.
        """
        key = self._normalize(board_name)
        os_key = os_name.lower() if os_name else ""
        os_map = self._mappings.get(key)
        if os_map and os_key in os_map:
            return os_map[os_key]
        # Fall back to the normalized DeMoL name. This keeps generators
        # functional on boards not yet registered, while making the
        # un-mapped case observable (lowercased + separator-preserving).
        return key

    def get(self, board_name: str, os_name: str) -> Optional[str]:
        """Return the mapped target name or ``None`` if no mapping exists.

        Unlike :meth:`resolve`, this method does not fall back to the
        normalized DeMoL name; it returns ``None`` for unmapped pairs.

        Args:
            board_name: DeMoL board name (case-insensitive).
            os_name: Target OS identifier (e.g. ``"zephyr"``).

        Returns:
            The target name if mapped, otherwise ``None``.
        """
        key = self._normalize(board_name)
        os_key = os_name.lower() if os_name else ""
        os_map = self._mappings.get(key)
        if os_map and os_key in os_map:
            return os_map[os_key]
        return None

    def known_boards(self) -> list:
        """Return the list of registered DeMoL board names (lowercased)."""
        return sorted(self._mappings.keys())

    def __contains__(self, board_name: str) -> bool:
        return self._normalize(board_name) in self._mappings
