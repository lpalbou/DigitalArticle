"""
Version for Digital Article backend.
Source of truth: digitalarticle/_version.py
"""

from __future__ import annotations

from dataclasses import dataclass
import importlib.metadata
from pathlib import Path
import re


@dataclass(frozen=True)
class VersionInfo:
    """
    Lightweight version carrier.

    This module is imported both at runtime (API `/api/system/version`) and at
    packaging time (backend `pyproject.toml` dynamic version). Keep it dependency-free.
    """

    version: str
    release_date: str


class VersionInfoResolver:
    """
    Resolve version/release-date with a robust preference order:

    1) If `digitalarticle` is importable, use `digitalarticle._version` directly.
       - This is the canonical source of truth in this repository.
    2) If running from a repo-style checkout or Docker context, locate and parse
       `digitalarticle/_version.py` as a file (no import required).
    3) Fallback to installed package metadata (version only).
    """

    _VERSION_RE = re.compile(r'^\s*__version__\s*=\s*[\'"]([^\'"]+)[\'"]\s*$', re.MULTILINE)
    _RELEASE_DATE_RE = re.compile(
        r'^\s*__release_date__\s*=\s*[\'"]([^\'"]+)[\'"]\s*$', re.MULTILINE
    )

    def resolve(self) -> VersionInfo:
        # 1) Canonical import path (preferred when available)
        try:
            from digitalarticle._version import (  # type: ignore
                __version__ as da_version,
                __release_date__ as da_release_date,
            )

            return VersionInfo(version=da_version, release_date=da_release_date)
        except Exception:
            pass

        # 2) Repo/Docker context: parse the canonical file without importing it.
        version_file = self._find_digitalarticle_version_file(start_dir=Path(__file__).resolve().parent)
        if version_file is not None:
            return self._parse_version_file(version_file)

        # 3) Installed metadata fallback (version only).
        version = self._get_installed_backend_version() or "0.0.0"
        return VersionInfo(version=version, release_date="")

    def _get_installed_backend_version(self) -> str | None:
        try:
            return importlib.metadata.version("digital-article-backend")
        except Exception:
            return None

    def _find_digitalarticle_version_file(self, start_dir: Path) -> Path | None:
        for parent in [start_dir] + list(start_dir.parents):
            candidate = parent / "digitalarticle" / "_version.py"
            if candidate.is_file():
                return candidate
        return None

    def _parse_version_file(self, path: Path) -> VersionInfo:
        text = path.read_text(encoding="utf-8")

        version_match = self._VERSION_RE.search(text)
        if version_match is None:
            raise ValueError(f"Could not find __version__ in {path}")

        release_date_match = self._RELEASE_DATE_RE.search(text)
        release_date = release_date_match.group(1) if release_date_match else ""

        return VersionInfo(version=version_match.group(1), release_date=release_date)


_version_info = VersionInfoResolver().resolve()

__version__ = _version_info.version
__release_date__ = _version_info.release_date

