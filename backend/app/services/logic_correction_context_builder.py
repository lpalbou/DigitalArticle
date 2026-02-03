"""
Logic correction context builder.

Why this exists
---------------
Logic correction (ADR 0004) is a semantic self-correction loop: code executes, but the answer may
not satisfy the user's intent. For reliable correction, the LLM needs:
- the issues to fix (with evidence)
- a compact summary of the execution artifacts (stdout/tables/plots counts)
- domain best-practice guidance (personas; optional bibliography)
- article-level context (notebook title/description) to stay aligned with the global narrative

This module builds a **compact, explicit** delta request that can be injected as `rerun_comment`
into the existing `LLMService.asuggest_improvements(...)` pathway.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence

from ..models.notebook import ExecutionResult
from ..models.persona import PersonaCombination, PersonaScope
from .persona_service import PersonaService
from .logic_validation_service import CategorizedIssue


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LogicCorrectionInputs:
    notebook_title: str
    notebook_description: str
    user_prompt: str
    previous_cells_brief: str
    issues_to_fix: Sequence[CategorizedIssue]
    severity_label: str
    attempt_number: int
    execution_result: ExecutionResult
    persona_combination: Optional[PersonaCombination] = None
    bibliography: Optional[Any] = None  # string | list[str] | dict (user-provided; we keep it flexible)


class LogicCorrectionContextBuilder:
    """
    Builds a robust, compact "delta request" for logic correction.

    Notes on compaction (ADR 0003):
    - We explicitly compact long artifacts and include `#COMPACTION_NOTICE:`.
    - We log at INFO when compaction occurs (grep-auditable).
    """

    MAX_STDOUT_CHARS = 3000
    MAX_TABLE_SAMPLE_ROWS = 2
    MAX_TABLE_COLS = 20
    MAX_BIBLIOGRAPHY_CHARS = 2500

    def build_rerun_comment(self, inputs: LogicCorrectionInputs) -> str:
        parts: List[str] = []

        parts.append("LOGIC VALIDATION FAILED.\n")
        parts.append(
            "You are correcting code that EXECUTED but did not satisfy the user's intent.\n"
            "Make the minimal necessary changes (prefer minimal diffs) while preserving the global notebook logic.\n"
            "DO NOT add extra analyses/plots/models unless explicitly requested.\n"
            "Return the FULL corrected code.\n"
        )

        # Article alignment context (cheap, high-signal)
        if inputs.notebook_title or inputs.notebook_description:
            parts.append("\nARTICLE CONTEXT:\n")
            if inputs.notebook_title:
                parts.append(f"- Title: {inputs.notebook_title}\n")
            if inputs.notebook_description:
                parts.append(f"- Description: {inputs.notebook_description}\n")

        if inputs.previous_cells_brief.strip():
            parts.append("\nUPSTREAM NOTEBOOK CONTEXT (recent cells):\n")
            parts.append(inputs.previous_cells_brief.strip() + "\n")

        # Domain best practices from personas (use REVIEW scope for correction)
        persona_guidance = self._persona_review_guidance(inputs.persona_combination)
        if persona_guidance:
            parts.append("\nDOMAIN BEST PRACTICES (from personas):\n")
            parts.append(persona_guidance.strip() + "\n")

        # Optional bibliography/references (user-provided)
        bib = self._format_bibliography(inputs.bibliography)
        if bib:
            parts.append("\nOPTIONAL REFERENCE MATERIAL (bibliography):\n")
            parts.append(bib + "\n")

        # Issues + evidence
        parts.append("\nISSUES TO FIX (with evidence):\n")
        for ci in inputs.issues_to_fix:
            sev = getattr(ci.severity, "value", str(ci.severity))
            parts.append(f"- [{sev.upper()}] {ci.issue}\n")
            if ci.suggestion:
                parts.append(f"  suggestion: {ci.suggestion}\n")
            # Evidence fields are verbatim substrings or "NONE"
            ev_code = ci.evidence_code or "NONE"
            ev_out = ci.evidence_output or "NONE"
            parts.append(f"  evidence_code: `{self._truncate_evidence(ev_code)}`\n")
            parts.append(f"  evidence_output: `{self._truncate_evidence(ev_out)}`\n")

        # Execution artifact summary (ground the correction)
        parts.append("\nEXECUTION ARTIFACTS (from last successful run):\n")
        parts.append(self._format_execution_summary(inputs.execution_result))

        return "".join(parts).strip()

    def _persona_review_guidance(self, persona_combination: Optional[PersonaCombination]) -> str:
        if not persona_combination:
            return ""
        try:
            persona_service = PersonaService()
            return persona_service.build_system_prompt_addition(persona_combination, PersonaScope.REVIEW) or ""
        except Exception as e:
            logger.warning(f"Could not build persona REVIEW guidance for logic correction: {e}")
            return ""

    def _format_bibliography(self, bibliography: Any) -> str:
        if not bibliography:
            return ""

        try:
            if isinstance(bibliography, str):
                text = bibliography.strip()
            elif isinstance(bibliography, list):
                # List[str] or list[dict]; serialize robustly
                lines = []
                for item in bibliography[:50]:
                    if isinstance(item, str):
                        lines.append(f"- {item.strip()}")
                    else:
                        lines.append(f"- {json.dumps(item, ensure_ascii=False, default=str)}")
                text = "\n".join(lines)
            elif isinstance(bibliography, dict):
                text = json.dumps(bibliography, indent=2, ensure_ascii=False, default=str)
            else:
                text = str(bibliography)

            if len(text) <= self.MAX_BIBLIOGRAPHY_CHARS:
                return text

            head = text[: self.MAX_BIBLIOGRAPHY_CHARS // 2]
            tail = text[-(self.MAX_BIBLIOGRAPHY_CHARS // 2) :]
            notice = (
                f"#COMPACTION_NOTICE: bibliography compacted for LLM context "
                f"(original_len={len(text)} chars; shown=head+tail).\n"
            )
            logger.info(notice.strip())
            return head + "\n\n" + notice + tail
        except Exception as e:
            logger.warning(f"Could not format bibliography for logic correction: {e}")
            return ""

    def _truncate_evidence(self, ev: str, *, max_chars: int = 200) -> str:
        ev = (ev or "").strip()
        if not ev:
            return "NONE"
        if len(ev) <= max_chars:
            return ev
        return ev[: max_chars - 3] + "..."

    def _compact(self, text: str, *, max_chars: int, label: str) -> str:
        if text is None:
            return ""
        if len(text) <= max_chars:
            return text
        head_len = max_chars // 2
        tail_len = max_chars - head_len
        head = text[:head_len]
        tail = text[-tail_len:] if tail_len > 0 else ""
        notice = (
            f"#COMPACTION_NOTICE: {label} compacted for logic correction (original_len={len(text)} chars, "
            f"shown=head+tail={len(head) + len(tail)} chars; middle omitted).\n"
        )
        logger.info(notice.strip())
        return head + "\n\n" + notice + "\n" + tail

    def _format_execution_summary(self, result: ExecutionResult) -> str:
        lines: List[str] = []

        # Counts (cheap and robust)
        lines.append(f"- STDOUT chars: {len(result.stdout or '')}\n")
        lines.append(f"- TABLES generated: {len(result.tables or [])}\n")
        lines.append(f"- STATIC PLOTS generated: {len(result.plots or [])}\n")
        lines.append(f"- INTERACTIVE PLOTS generated: {len(result.interactive_plots or [])}\n")
        lines.append(f"- IMAGES generated: {len(result.images or [])}\n")

        # Compact stdout (most useful grounding for many issues)
        if result.stdout:
            stdout_compact = self._compact(result.stdout, max_chars=self.MAX_STDOUT_CHARS, label="STDOUT")
            lines.append("\nSTDOUT (compacted if needed):\n")
            lines.append(stdout_compact + "\n")

        # Tables summary: prefer display outputs
        if result.tables:
            display_tables = [t for t in (result.tables or []) if isinstance(t, dict) and t.get("source") == "display"]
            tables = display_tables if display_tables else [t for t in (result.tables or []) if isinstance(t, dict)]
            lines.append("\nTABLES SUMMARY:\n")
            for idx, t in enumerate(tables[:10], start=1):
                label = t.get("label", f"Table {idx}")
                shape = t.get("shape")
                columns = t.get("columns", [])
                columns_short = columns[: self.MAX_TABLE_COLS] if isinstance(columns, list) else []
                lines.append(f"- {label}: shape={shape}, columns={columns_short}\n")

                sample = t.get("data") if isinstance(t.get("data"), list) else []
                if sample:
                    for row in sample[: self.MAX_TABLE_SAMPLE_ROWS]:
                        try:
                            row_json = json.dumps(row, ensure_ascii=False, default=str)
                        except Exception:
                            row_json = str(row)
                        if len(row_json) > 400:
                            row_json = row_json[:397] + "..."
                        lines.append(f"  sample_row: {row_json}\n")

        return "".join(lines)

