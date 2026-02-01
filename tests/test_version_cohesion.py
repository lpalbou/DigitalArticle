from __future__ import annotations

import json
from pathlib import Path

import tomllib


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_version_is_single_source_of_truth_across_repo() -> None:
    """
    Prevent "trust drift" in public-facing version surfaces.

    Canonical source of truth: `digitalarticle/_version.py`.
    """
    from digitalarticle._version import __version__ as canonical_version

    # Frontend package metadata (keep in sync for releases)
    package_json = json.loads((PROJECT_ROOT / "frontend" / "package.json").read_text(encoding="utf-8"))
    assert package_json["version"] == canonical_version

    # Backend runtime surface (`/api/system/version`) should match canonical
    from backend.app._version import __version__ as backend_version

    assert backend_version == canonical_version

    # Backend packaging must derive version dynamically (no manual duplication)
    backend_pyproject = tomllib.loads((PROJECT_ROOT / "backend" / "pyproject.toml").read_text(encoding="utf-8"))
    assert backend_pyproject["project"]["dynamic"] == ["version"]
    assert backend_pyproject["tool"]["setuptools"]["dynamic"]["version"]["attr"] == "app._version.__version__"

    # README "Current Status" should match canonical (communication cohesion)
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    assert f"**Version**: {canonical_version}" in readme

