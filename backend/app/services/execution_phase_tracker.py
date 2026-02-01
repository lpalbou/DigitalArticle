"""
Execution Phase Tracker

Why this exists:
- Cell execution is a multi-step pipeline (context build, LLM generation, execution, retries, methodology, etc.).
- The frontend runs a long-lived /cells/execute request and can poll /cells/{id}/status concurrently.
- To show accurate, real-time UI status, we persist a lightweight "phase + message" into cell.metadata["execution"].

Design:
- Keep the schema stable and JSON-friendly (strings + small ints).
- Avoid changing the public Cell model unless necessary; metadata is the extension point.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from ..models.notebook import Cell, Notebook


class CellExecutionPhaseTracker:
    """
    A tiny helper responsible for updating execution phase metadata on a cell.

    Stored under: cell.metadata["execution"]
    Keys:
      - phase: str
      - message: str
      - updated_at: ISO timestamp str
      - (optional) max_retries, methodology_attempt, max_methodology_retries, ...
    """

    def __init__(self, notebook: Notebook, cell: Cell):
        self._notebook = notebook
        self._cell = cell

    def set_phase(self, phase: str, message: str, **extra: Any) -> None:
        execution_meta: Dict[str, Any] = self._cell.metadata.setdefault("execution", {})

        execution_meta["phase"] = phase
        execution_meta["message"] = message
        execution_meta["updated_at"] = datetime.now().isoformat()

        # Persist small additional fields when useful (attempt counters, max retries, etc.).
        for key, value in extra.items():
            execution_meta[key] = value

        # Keep timestamps consistent for UX and debugging.
        self._cell.updated_at = datetime.now()
        self._notebook.updated_at = datetime.now()

    def clear(self) -> None:
        """Clear user-facing phase/message while keeping other execution metadata (e.g. clean-rerun bookkeeping)."""
        execution_meta: Dict[str, Any] = self._cell.metadata.setdefault("execution", {})
        execution_meta.pop("phase", None)
        execution_meta.pop("message", None)
        execution_meta.pop("updated_at", None)

        self._cell.updated_at = datetime.now()
        self._notebook.updated_at = datetime.now()

    def get_phase(self) -> Optional[str]:
        execution_meta: Dict[str, Any] = self._cell.metadata.get("execution", {})
        return execution_meta.get("phase")

    def get_message(self) -> Optional[str]:
        execution_meta: Dict[str, Any] = self._cell.metadata.get("execution", {})
        return execution_meta.get("message")

