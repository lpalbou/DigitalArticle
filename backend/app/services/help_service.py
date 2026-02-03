"""
Help / Documentation service.

Provides:
- A searchable index of user-facing documentation (`user_docs/`).
- Optional access to the product overview PDF (`untracked/digital-article.pdf`) when present.
- A contact email address exposed from an environment variable.

Design goals:
- Safe path handling (no path traversal).
- Deterministic, general-purpose search (no hardcoded doc names).
- Minimal dependencies (pure stdlib).
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional


DEFAULT_CONTACT_EMAIL = "lpalbou@gmail.com"
CONTACT_EMAIL_ENV_VAR = "DA_CONTACT_EMAIL"


@dataclass(frozen=True)
class HelpDocIndexEntry:
    """A single internal documentation entry."""

    doc_id: str  # path relative to docs root (e.g., "overview.md", "dive_ins/llm_service.md")
    title: str


@dataclass(frozen=True)
class HelpSearchHit:
    """A search match within one document."""

    doc_id: str
    title: str
    snippet: str


class HelpService:
    """
    Load and serve internal documentation for the in-app Help modal.

    Notes:
    - In Docker builds, we intentionally copy `user_docs/` into the runtime image (see `.dockerignore`).
    - The product overview PDF is expected at `untracked/digital-article.pdf` when available.
    """

    def __init__(self, project_root: Optional[Path] = None) -> None:
        if project_root is None:
            # `backend/app/services/help_service.py` -> parents[3] = repo root (/app in containers)
            project_root = Path(__file__).resolve().parents[3]
        self._project_root = project_root
        self._docs_root = self._project_root / "user_docs"
        self._pdf_path = self._project_root / "untracked" / "digital-article.pdf"

    def get_contact_email(self) -> str:
        """
        Contact email exposed to the UI.

        Uses env var `DA_CONTACT_EMAIL`, defaults to `lpalbou@gmail.com`.
        """
        return os.getenv(CONTACT_EMAIL_ENV_VAR, DEFAULT_CONTACT_EMAIL).strip() or DEFAULT_CONTACT_EMAIL

    def pdf_available(self) -> bool:
        return self._pdf_path.exists() and self._pdf_path.is_file()

    def get_pdf_path(self) -> Path:
        """Return the canonical PDF path (may not exist)."""
        return self._pdf_path

    def iter_docs(self) -> Iterable[Path]:
        """Iterate markdown files under docs root."""
        if not self._docs_root.exists():
            return []
        return (p for p in self._docs_root.rglob("*.md") if p.is_file())

    def get_docs_index(self) -> List[HelpDocIndexEntry]:
        """
        Return a deterministic, sorted documentation index.
        """
        entries: List[HelpDocIndexEntry] = []
        for path in self.iter_docs():
            rel = path.relative_to(self._docs_root).as_posix()
            title = self._infer_title(path)
            entries.append(HelpDocIndexEntry(doc_id=rel, title=title))
        entries.sort(key=lambda e: (e.title.lower(), e.doc_id.lower()))
        return entries

    def read_doc(self, doc_id: str) -> str:
        """
        Read one doc by id (relative to docs root).

        Security:
        - Reject absolute paths.
        - Reject path traversal (resolved path must stay under docs root).
        """
        if not doc_id or doc_id.startswith(("/", "\\")):
            raise ValueError("Invalid doc_id")

        raw = (self._docs_root / doc_id)
        resolved = raw.resolve()

        docs_root_resolved = self._docs_root.resolve()
        # Python 3.12 Path.is_relative_to exists; use it for clarity.
        if not resolved.is_relative_to(docs_root_resolved):
            raise ValueError("Access denied: doc_id escapes docs root")

        if not resolved.exists() or not resolved.is_file():
            raise FileNotFoundError(doc_id)

        return resolved.read_text(encoding="utf-8", errors="replace")

    def search(self, query: str, limit: int = 20) -> List[HelpSearchHit]:
        """
        Naive but robust full-text search across docs.

        - Case-insensitive substring search.
        - Returns short snippets around the first match per doc.
        """
        q = (query or "").strip()
        if not q:
            return []

        q_lower = q.lower()
        hits: List[HelpSearchHit] = []

        for entry in self.get_docs_index():
            try:
                content = self.read_doc(entry.doc_id)
            except Exception:
                continue

            idx = content.lower().find(q_lower)
            if idx < 0:
                continue

            snippet = self._make_snippet(content, idx, len(q))
            hits.append(HelpSearchHit(doc_id=entry.doc_id, title=entry.title, snippet=snippet))

            if len(hits) >= max(1, limit):
                break

        return hits

    @staticmethod
    def _infer_title(path: Path) -> str:
        """
        Try to infer a human-friendly title:
        - Prefer the first markdown heading.
        - Fallback to filename stem.
        """
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return path.stem

        # First markdown heading like "# Title"
        for line in text.splitlines()[:80]:
            m = re.match(r"^\s{0,3}#{1,6}\s+(?P<t>.+?)\s*$", line)
            if m:
                return m.group("t").strip()
        return path.stem.replace("_", " ").strip()

    @staticmethod
    def _make_snippet(text: str, match_idx: int, match_len: int, window: int = 140) -> str:
        start = max(0, match_idx - window)
        end = min(len(text), match_idx + match_len + window)
        snippet = text[start:end].replace("\n", " ").strip()
        if start > 0:
            snippet = "… " + snippet
        if end < len(text):
            snippet = snippet + " …"
        # Collapse whitespace
        snippet = re.sub(r"\s+", " ", snippet)
        return snippet

