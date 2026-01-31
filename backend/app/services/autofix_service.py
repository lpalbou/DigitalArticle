"""
Safe autofix engine (deterministic, offline).

This is intentionally conservative:
- Only allowlisted transformations are applied.
- Transformations are line-based (preserve formatting/comments as much as possible).
- Every rewrite produces an explicit diff and change list for transparency.
"""

from __future__ import annotations

import ast
import difflib
import re
import types
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple

from ..models.autofix import AutofixChange, AutofixReport
from ..models.linting import LintReport


@dataclass(frozen=True)
class _LineEdit:
    line_no: int  # 1-based
    new_line: str


class AutofixService:
    """Apply a strictly limited subset of safe code transformations."""

    _CALLABLE_ASSIGNMENT_RE = re.compile(
        r"^(?P<indent>\s*)(?P<lhs>(?P<alias>[A-Za-z_]\w*)\.(?P<attr>[A-Za-z_]\w*))\s*=\s*(?P<rhs>.+?)(?P<comment>\s+#.*)?$"
    )
    _BRACKET_CALL_RE = re.compile(
        r"^(?P<indent>\s*)(?P<lhs>(?P<alias>[A-Za-z_]\w*)\.(?P<attr>[A-Za-z_]\w*))\[(?P<arg>.+)\](?P<comment>\s+#.*)?$"
    )
    _BUILTIN_CALL_RE = re.compile(
        r"^(?P<indent>\s*)(?P<builtin>int|float|str|list|dict|tuple)\[(?P<arg>.+)\](?P<comment>\s+#.*)?$"
    )

    def apply_pre_validation_fixes(self, code: str, globals_dict: Optional[Dict[str, Any]] = None) -> Tuple[str, List[AutofixChange]]:
        """
        Fix clearly-wrong mechanical patterns before syntax validation / execution.

        These fixes are intentionally limited to transformations that are overwhelmingly
        likely to be mistakes and can be validated using the current execution globals.
        """
        globals_dict = globals_dict or {}
        changes: List[AutofixChange] = []

        edits: List[_LineEdit] = []
        lines = code.splitlines()
        for idx, line in enumerate(lines, start=1):
            # Preserve exact line including indentation; edits are applied by line number.
            m_assign = self._CALLABLE_ASSIGNMENT_RE.match(line)
            if m_assign:
                alias = m_assign.group("alias")
                attr = m_assign.group("attr")
                rhs = m_assign.group("rhs").rstrip()
                comment = m_assign.group("comment") or ""

                # Only fix when the alias is a module and the attribute is callable.
                alias_val = globals_dict.get(alias)
                if isinstance(alias_val, types.ModuleType):
                    attr_val = getattr(alias_val, attr, None)
                    if callable(attr_val):
                        new_line = f"{m_assign.group('indent')}{alias}.{attr}({rhs}){comment}"
                        edits.append(_LineEdit(line_no=idx, new_line=new_line))
                        changes.append(
                            AutofixChange(
                                rule_id="DA2001",
                                message=f"Replaced accidental assignment with function call: {alias}.{attr}(...)",
                                line=idx,
                            )
                        )

            m_bracket = self._BRACKET_CALL_RE.match(line)
            if m_bracket:
                alias = m_bracket.group("alias")
                attr = m_bracket.group("attr")
                arg = m_bracket.group("arg").rstrip()
                comment = m_bracket.group("comment") or ""

                alias_val = globals_dict.get(alias)
                if isinstance(alias_val, types.ModuleType):
                    attr_val = getattr(alias_val, attr, None)
                    if callable(attr_val):
                        new_line = f"{m_bracket.group('indent')}{alias}.{attr}({arg}){comment}"
                        edits.append(_LineEdit(line_no=idx, new_line=new_line))
                        changes.append(
                            AutofixChange(
                                rule_id="DA2002",
                                message=f"Replaced bracket call with function call: {alias}.{attr}(...)",
                                line=idx,
                            )
                        )

            # Fix `int[value]`-style calls only when it's clearly not a type annotation.
            # Heuristic: only apply when the line contains `=` and does not look like an annotation (`:` before `=`).
            if "=" in line:
                before_eq = line.split("=", 1)[0]
                if ":" not in before_eq:
                    m_builtin = self._BUILTIN_CALL_RE.match(line.strip())
                    if m_builtin:
                        builtin = m_builtin.group("builtin")
                        arg = m_builtin.group("arg").rstrip()
                        comment = m_builtin.group("comment") or ""
                        indent = re.match(r"^\s*", line).group(0)
                        new_line = f"{indent}{builtin}({arg}){comment}"
                        edits.append(_LineEdit(line_no=idx, new_line=new_line))
                        changes.append(
                            AutofixChange(
                                rule_id="DA2003",
                                message=f"Replaced bracket call with builtin call: {builtin}(...)",
                                line=idx,
                            )
                        )

        if not edits:
            return code, []

        edited = lines[:]
        for e in edits:
            if 1 <= e.line_no <= len(edited):
                edited[e.line_no - 1] = e.new_line

        fixed = "\n".join(edited)
        if code.endswith("\n"):
            fixed += "\n"
        return fixed, changes

    def apply_safe_autofix(
        self,
        code: str,
        lint_before: LintReport,
        globals_dict: Optional[Dict[str, Any]] = None,
    ) -> AutofixReport:
        """
        Apply allowlisted, provably-safe lint-based rewrites.

        In notebook context, we only rewrite imports when they are **redundant**:
        removing them must not change the current globals binding.
        """
        report = AutofixReport(enabled=True, applied=False, original_code=code, lint_before=lint_before)

        # Allowlist: only remove provably redundant single-import statements
        # (identified by the builtin linter as DA1101).
        redundant_import_lines = {
            issue.line
            for issue in (lint_before.issues or [])
            if issue.rule_id == "DA1101" and issue.fixable and issue.line
        }
        if not redundant_import_lines:
            return report

        fixed_code, changes = self._remove_redundant_single_import_lines(code, redundant_import_lines, globals_dict or {})
        if fixed_code == code:
            return report

        diff = "\n".join(
            difflib.unified_diff(
                code.splitlines(),
                fixed_code.splitlines(),
                fromfile="before.py",
                tofile="after.py",
                lineterm="",
            )
        )

        report.applied = True
        report.fixed_code = fixed_code
        report.diff = diff
        report.changes = changes
        return report

    def _remove_redundant_single_import_lines(
        self,
        code: str,
        redundant_import_lines: Set[int],
        globals_dict: Dict[str, Any],
    ) -> Tuple[str, List[AutofixChange]]:
        """
        Remove entire import statements that are safe to drop.

        Safety rules:
        - Only remove imports that are single-line and contain exactly ONE imported name.
        - Only remove top-level imports (module body), not imports nested in blocks.
        - Do not rewrite multi-import statements (e.g., `import a, b`) or multi-line imports.
        - Only remove if the current globals binding already matches what the import would bind.
        """
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return code, []

        # Map of removable line ranges (1-based inclusive)
        removable_lines: Set[int] = set()
        changes: List[AutofixChange] = []

        for node in getattr(tree, "body", []):
            if not getattr(node, "lineno", None):
                continue
            lineno = int(node.lineno)
            end_lineno = int(getattr(node, "end_lineno", lineno))

            # Only consider nodes that are explicitly marked redundant by the linter (by line)
            if lineno not in redundant_import_lines:
                continue

            # Only remove single-line imports
            if end_lineno != lineno:
                continue

            # `import x` (single alias only)
            if isinstance(node, ast.Import) and len(node.names) == 1:
                imported = node.names[0].name
                exposed = node.names[0].asname or imported.split(".")[0]

                existing = globals_dict.get(exposed)
                if not isinstance(existing, types.ModuleType):
                    continue
                # Ensure binding matches (module name)
                if getattr(existing, "__name__", None) != imported:
                    continue

                removable_lines.add(lineno)
                changes.append(
                    AutofixChange(rule_id="DA1101", message=f"Removed redundant import: {imported}", line=lineno)
                )
                continue

            # `from x import y` (single alias only, no star)
            if isinstance(node, ast.ImportFrom) and len(node.names) == 1 and node.names[0].name != "*":
                mod = node.module or ""
                name = node.names[0].name
                exposed = node.names[0].asname or name
                imported = f"{mod}.{name}" if mod else name

                existing = globals_dict.get(exposed)
                if existing is None:
                    continue

                # Best-effort match: object originates from same module and has same name.
                if getattr(existing, "__name__", None) != name:
                    continue
                if getattr(existing, "__module__", None) != mod:
                    continue

                removable_lines.add(lineno)
                changes.append(
                    AutofixChange(rule_id="DA1101", message=f"Removed redundant import: {imported}", line=lineno)
                )
                continue

        if not removable_lines:
            return code, []

        lines = code.splitlines()
        new_lines: List[str] = []
        for idx, line in enumerate(lines, start=1):
            if idx in removable_lines:
                continue
            new_lines.append(line)

        # Lightweight cleanup: collapse excessive blank lines created by deletions
        cleaned: List[str] = []
        blank_run = 0
        for line in new_lines:
            if line.strip() == "":
                blank_run += 1
                if blank_run <= 2:
                    cleaned.append(line)
            else:
                blank_run = 0
                cleaned.append(line)

        # Preserve trailing newline if the original had one
        fixed_code = "\n".join(cleaned)
        if code.endswith("\n"):
            fixed_code += "\n"

        return fixed_code, changes

