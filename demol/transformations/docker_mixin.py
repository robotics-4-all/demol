"""Shared Docker file generation mixin for code generators.

This module provides :class:`DockerBuildMixin`, a reusable mixin that
consolidates the Docker-related code generation currently duplicated in the
RPi (``m2t_rpi.py``) and RIOT (``m2t_riot.py``) generators. It is designed
to be extended by future backends (e.g. Zephyr, Wokwi, Renode in Wave 2)
without each having to reimplement Dockerfile / compose / install-deps
plumbing.

The mixin assumes the host class exposes:

* ``self.env`` — a :class:`jinja2.Environment` already configured with the
  platform's template directory (RPi: ``TEMPLATES_RPI``, RIOT: ``TEMPLATES``).
* ``self.output_dir`` — a :class:`pathlib.Path` for the output directory.
* ``self.OS`` — a class-level string identifying the target OS
  (``"raspbian"`` or ``"riotos"``); used to look up the correct
  Dockerfile template.
* ``self.os_name()`` — an instance method returning the same value as
  ``self.OS``; the abstract base generator defines this.
* ``self._write_template(template, context, output_path)`` — the rendering
  helper inherited from :class:`BaseCodeGenerator`.

Per-OS Docker context construction is delegated to ``self._build_docker_context()``
so each generator can supply exactly the keys its templates need. The default
implementation raises :class:`NotImplementedError`; RPi and RIOT each override
it to return the dict their templates expect.
"""

import os
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    import jinja2


__all__ = ["DockerBuildMixin"]


class DockerBuildMixin:
    """Reusable mixin for Docker artifact generation.

    The mixin owns the small dispatch table mapping each supported ``OS`` to
    its primary Dockerfile template. It exposes both a high-level entry
    point (:meth:`generate_docker_files`) and the per-file renderers
    (:meth:`_render_dockerfile`, :meth:`_render_compose`,
    :meth:`_render_install_deps`, :meth:`_render_riot_dockerfile`,
    :meth:`_render_riot_build_script`) so subclasses and tests can drive any
    single artifact in isolation.

    Subclasses must:

    * inherit from :class:`BaseCodeGenerator` (or otherwise provide
      ``_write_template`` and ``env``);
    * set the ``OS`` class attribute;
    * implement :meth:`_build_docker_context` returning the Jinja context
      dictionary expected by their templates.
    """

    if TYPE_CHECKING:
        output_dir: Path
        env: "jinja2.Environment"
        OS: str

        def _write_template(
            self,
            template: "jinja2.Template",
            context: Dict[str, Any],
            output_path: Path,
        ) -> None: ...

    #: Map from ``OS`` identifier to the primary Dockerfile template name.
    #: Subclasses may extend this to register new backends.
    DOCKER_TEMPLATES: Dict[str, str] = {
        "raspbian": "Dockerfile.j2",
        "riotos": "Dockerfile.riotbuild.j2",
    }

    def generate_docker_files(self, output_dir: Optional[Path] = None) -> None:
        """Render all Docker-related files for the current OS.

        Dispatches to the OS-specific :meth:`_render_docker_files` entry
        point. When ``output_dir`` is ``None``, the generator's own
        ``self.output_dir`` is used. The ``OS`` string controls which
        template set is selected; unknown values are treated as "no Docker
        support" and silently return (future backends register their own
        template and override the renderer).
        """
        os_name = self.OS
        if os_name not in self.DOCKER_TEMPLATES and not self._has_docker_for_os(os_name):
            return
        self._render_docker_files(output_dir)

    def _has_docker_for_os(self, os_name: str) -> bool:
        """Return True if this mixin knows how to render Docker files for ``os_name``.

        Subclasses can override to add new backends without touching
        :attr:`DOCKER_TEMPLATES` (e.g. for OSes that share the raspbian
        template set but live under a different identifier).
        """
        return False

    def _render_docker_files(self, output_dir: Optional[Path] = None) -> None:
        """OS-aware dispatcher for the multi-file Docker rendering.

        Falls back to the primary Dockerfile template for any OS the mixin
        doesn't recognise explicitly — this keeps the contract simple for
        future backends that follow the raspbian-style "single Dockerfile"
        shape.
        """
        if self.OS == "riotos":
            self._render_riot_dockerfile(output_dir)
            self._render_riot_build_script(output_dir)
            return
        self._render_dockerfile(output_dir)
        self._render_requirements(output_dir)
        self._render_compose(output_dir)
        self._render_install_deps(output_dir)

    def _build_docker_context(self) -> Dict[str, Any]:
        """Return the Jinja context dict used by the Docker templates.

        The default implementation raises — each subclass must override
        this to return the keys its templates expect (e.g. RPi needs
        ``apt_dependencies`` and ``dependencies`` / ``connections``; RIOT
        needs the full global context with ``riot_version`` /
        ``riot_repo`` / ``board_name``).
        """
        raise NotImplementedError(
            f"{type(self).__name__} must implement _build_docker_context() " "to use DockerBuildMixin"
        )

    def _render_dockerfile(self, output_dir: Optional[Path] = None) -> None:
        """Render the primary ``Dockerfile`` for the current OS."""
        out = Path(output_dir) if output_dir else self.output_dir
        template_name = self.DOCKER_TEMPLATES[self.OS]
        template = self.env.get_template(template_name)
        context = self._build_docker_context()
        self._write_template(template, context, out / "Dockerfile")

    def _render_requirements(self, output_dir: Optional[Path] = None) -> None:
        """Render ``requirements.txt`` (RPi path)."""
        out = Path(output_dir) if output_dir else self.output_dir
        template = self.env.get_template("requirements.txt.j2")
        context = self._build_docker_context()
        self._write_template(template, context, out / "requirements.txt")

    def _render_compose(self, output_dir: Optional[Path] = None) -> None:
        """Render ``docker-compose.yml`` (RPi path)."""
        out = Path(output_dir) if output_dir else self.output_dir
        template = self.env.get_template("docker-compose.yml.j2")
        context = self._build_docker_context()
        self._write_template(template, context, out / "docker-compose.yml")

    def _render_install_deps(
        self,
        output_dir: Optional[Path] = None,
        os_specific_packages: Optional[List[str]] = None,
    ) -> None:
        """Render ``install_deps.sh`` and mark it executable (RPi path).

        Args:
            output_dir: Optional override for the output directory.
            os_specific_packages: Optional list of extra package names to
                inject into the install script's context (the
                ``os_specific_packages`` key is added to the template
                context under the same name). RPi templates do not
                currently use this key, but it is forwarded so future
                raspbian-style backends can extend the script.
        """
        out = Path(output_dir) if output_dir else self.output_dir
        template = self.env.get_template("install_deps.sh.j2")
        context = self._build_docker_context()
        if os_specific_packages is not None:
            context["os_specific_packages"] = list(os_specific_packages)
        script_path = out / "install_deps.sh"
        self._write_template(template, context, script_path)
        os.chmod(script_path, 0o755)

    def _render_riot_dockerfile(self, output_dir: Optional[Path] = None) -> None:
        """Render ``Dockerfile.riotbuild`` (RIOT path)."""
        out = Path(output_dir) if output_dir else self.output_dir
        template = self.env.get_template("Dockerfile.riotbuild.j2")
        context = self._build_docker_context()
        self._write_template(template, context, out / "Dockerfile.riotbuild")

    def _render_riot_build_script(self, output_dir: Optional[Path] = None) -> None:
        """Render ``build_docker.sh`` and mark it executable (RIOT path)."""
        out = Path(output_dir) if output_dir else self.output_dir
        template = self.env.get_template("build_docker.sh.j2")
        context = self._build_docker_context()
        script_path = out / "build_docker.sh"
        self._write_template(template, context, script_path)
        os.chmod(script_path, 0o755)
