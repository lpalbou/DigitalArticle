"""
Notebook Asset Numbering Service
--------------------------------
Centralizes **figure/table numbering** so it is:

- Deterministic (depends only on notebook content + cell order)
- Execution-order independent (re-running an upstream cell will renumber downstream assets)
- Robust to legacy formats (plots may be base64 strings or dicts)
- Robust to LLM-provided labels that incorrectly restart at 1 per cell

This service deliberately treats numbering as *derived data* computed from the
notebook structure, rather than state tracked during execution.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from ..models.notebook import Notebook

logger = logging.getLogger(__name__)


class NotebookAssetNumberingService:
    """
    Renumber figures and tables across a whole notebook.

    Design notes:
    - We **override** any user/LLM-provided "Table 1"/"Figure 1" prefixes to enforce
      uniqueness and correct ordering across the entire notebook.
    - We preserve descriptions after the prefix (e.g., "Table 1: Demographics" →
      "Table 7: Demographics").
    - We normalize plot entries to dicts so labels can be attached consistently.
    """

    def renumber_in_place(self, notebook: Notebook) -> None:
        table_counter = 0
        figure_counter = 0

        for cell_index, cell in enumerate(notebook.cells):
            result = cell.last_result
            if not result:
                continue

            # 1) Normalize + de-duplicate plots (so we can safely label them)
            try:
                result.plots = self._normalize_and_dedupe_plots(result.plots)
            except Exception as e:
                logger.warning(f"Failed to normalize plots for cell[{cell_index}]: {e}")

            try:
                result.interactive_plots = self._dedupe_interactive_plots(result.interactive_plots)
            except Exception as e:
                logger.warning(f"Failed to dedupe interactive plots for cell[{cell_index}]: {e}")

            # 2) Extract per-cell Plotly HTML "orphan labels" (legacy label carrier)
            # These are HTML items containing Plotly that we intentionally don't render as tables.
            orphan_plotly_descriptions = self._extract_plotly_orphan_descriptions(result.tables)

            # 3) Renumber display tables in notebook order
            for table in result.tables or []:
                if not self._should_number_as_table(table):
                    continue

                table_counter += 1
                description = self._extract_description(table.get("label"), kind="Table")
                table["label"] = self._format_label("Table", table_counter, description)

            # 4) Renumber static plots (matplotlib PNGs) in notebook order
            for plot in result.plots or []:
                if not isinstance(plot, dict):
                    # By construction we normalize to dicts, but stay defensive.
                    continue

                figure_counter += 1
                description = self._extract_description(plot.get("label"), kind="Figure")
                plot["label"] = self._format_label("Figure", figure_counter, description)

            # 5) Renumber interactive plots (Plotly) after static plots (matches frontend order)
            for idx, plot in enumerate(result.interactive_plots or []):
                if not isinstance(plot, dict):
                    continue

                figure_counter += 1
                description = self._extract_description(plot.get("label"), kind="Figure")

                # If Plotly plot lacks a useful description, fall back to the legacy orphan label
                # extracted from HTML captures in the same cell (order-aligned).
                if not description and idx < len(orphan_plotly_descriptions):
                    description = orphan_plotly_descriptions[idx]

                plot["label"] = self._format_label("Figure", figure_counter, description)

    # ---------------------------
    # Helpers (normalization)
    # ---------------------------

    def _normalize_and_dedupe_plots(self, plots: List[Any]) -> List[Dict[str, Any]]:
        """
        Normalize plots into dicts and remove obvious duplicates (same base64 payload).

        Legacy formats:
        - str: base64 PNG
        - dict: {data: base64 PNG, label?: str, source?: str, ...}
        """
        normalized: List[Dict[str, Any]] = []
        seen_payloads: set[str] = set()

        for plot in plots or []:
            if isinstance(plot, str):
                payload = plot
                plot_dict: Dict[str, Any] = {"type": "image", "data": payload, "source": "auto-captured"}
            elif isinstance(plot, dict):
                payload = (plot.get("data") or "").strip() if isinstance(plot.get("data"), str) else ""
                plot_dict = plot
                # Ensure a consistent key for the base64 payload if possible.
                if payload and "data" not in plot_dict:
                    plot_dict["data"] = payload
            else:
                # Unknown/unsupported plot format; keep as an unlabeled placeholder.
                continue

            if payload:
                if payload in seen_payloads:
                    continue
                seen_payloads.add(payload)

            normalized.append(plot_dict)

        return normalized

    def _dedupe_interactive_plots(self, plots: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate Plotly plots within a cell using the JSON payload as key when available."""
        deduped: List[Dict[str, Any]] = []
        seen: set[str] = set()

        for plot in plots or []:
            if not isinstance(plot, dict):
                continue

            key = plot.get("json")
            if not isinstance(key, str) or not key.strip():
                # Fallback: hash the figure dict (best-effort; may be large but per-cell is small).
                try:
                    key = json.dumps(plot.get("figure", {}), sort_keys=True, default=str)
                except Exception:
                    key = None

            if isinstance(key, str) and key:
                if key in seen:
                    continue
                seen.add(key)

            deduped.append(plot)

        return deduped

    # ---------------------------
    # Helpers (classification)
    # ---------------------------

    def _extract_plotly_orphan_descriptions(self, tables: List[Dict[str, Any]]) -> List[str]:
        """
        Plotly figures can be captured as HTML (via _repr_html_) and stored under `tables`.
        The frontend historically used these as a *label carrier* (orphanedLabels) for the
        real Plotly JSON stored in `interactive_plots`.

        We keep that behavior, but move it server-side so numbering is authoritative.
        """
        descriptions: List[str] = []

        for t in tables or []:
            try:
                if t.get("type") != "html":
                    continue

                content = t.get("content")
                if not isinstance(content, str) or "plotly" not in content.lower():
                    continue

                label = t.get("label")
                desc = self._extract_description(label, kind="Figure")
                if desc:
                    descriptions.append(desc)
            except Exception:
                continue

        return descriptions

    def _should_number_as_table(self, table: Dict[str, Any]) -> bool:
        """
        Decide whether an entry in `ExecutionResult.tables` should consume a Table number.

        We only number explicit display() outputs that are truly table-like:
        - source == "display"
        - type in {"table", "html"} (excluding Plotly HTML and empty/broken HTML captures)
        """
        if not isinstance(table, dict):
            return False

        if table.get("source") != "display":
            return False

        table_type = table.get("type")
        if table_type not in ("table", "html"):
            return False

        if table_type == "html":
            content = table.get("content")
            if not isinstance(content, str) or not content.strip():
                # Broken/empty HTML capture: do not number (and do not render).
                return False
            if "plotly" in content.lower():
                # Plotly HTML is a legacy representation of interactive plots. Not a table.
                return False

        return True

    # ---------------------------
    # Helpers (label parsing/format)
    # ---------------------------

    def _extract_description(self, label: Optional[str], kind: str) -> Optional[str]:
        """
        Extract description from labels like:
        - "Table 1: Demographics" -> "Demographics"
        - "Figure 2 - Kaplan-Meier" -> "Kaplan-Meier"
        - "Demographics" -> "Demographics" (treated as a description)
        - None / "Table 3" -> None
        """
        if not isinstance(label, str):
            return None

        s = label.strip()
        if not s:
            return None

        kind_lower = kind.lower()
        if not s.lower().startswith(kind_lower):
            # Treat arbitrary labels as descriptions
            return s

        # Strip the kind prefix ("Table"/"Figure")
        rest = s[len(kind) :].strip()

        # Strip leading number (if present)
        i = 0
        while i < len(rest) and rest[i].isdigit():
            i += 1
        rest = rest[i:].strip()

        # Strip punctuation separators
        rest = rest.lstrip(" :.-–—\t")

        return rest if rest else None

    def _format_label(self, kind: str, number: int, description: Optional[str]) -> str:
        if description:
            return f"{kind} {number}: {description}"
        return f"{kind} {number}"

