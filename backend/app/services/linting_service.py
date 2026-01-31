"""
Built-in linting service (minimal, deterministic, offline).

Design intent:
- Provide a structured lint report to improve debuggability and enable future
  improvement loops (LLM-assisted or deterministic autofix).
- Keep the initial implementation conservative to avoid false positives and noise.
"""

from __future__ import annotations

import ast
import builtins
from dataclasses import dataclass
import types
from typing import Any, Dict, Iterable, Optional, Set, Tuple

from ..models.linting import LintIssue, LintReport, LintSeverity


@dataclass(frozen=True)
class _ImportedName:
    exposed_name: str
    module: str  # module path (for Import) or base module (for ImportFrom)
    symbol: Optional[str]  # imported name for ImportFrom, else None
    line: Optional[int]
    column: Optional[int]


class LintingService:
    """Minimal offline linter for notebook cell code."""

    def lint(self, code: str, available_globals: Optional[Dict[str, Any]] = None) -> LintReport:
        """
        Lint a code cell.

        Args:
            code: Python code to lint
            available_globals: variables already available from the notebook execution context (globals)

        Returns:
            LintReport with 0+ issues (errors/warnings/info).
        """
        available_globals = available_globals or {}
        available_names = set(available_globals.keys())
        report = LintReport(engine="builtin", issues=[])

        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            report.issues.append(
                LintIssue(
                    severity=LintSeverity.ERROR,
                    rule_id="DA0001",
                    message=f"SyntaxError: {e.msg}",
                    line=e.lineno,
                    column=e.offset,
                    suggestion="Fix syntax error before execution.",
                    fixable=False,
                )
            )
            return report

        used_names = self._collect_used_names(tree)
        assigned_names = self._collect_assigned_names(tree)
        imported_names = self._collect_imported_names(tree)

        # Unused imports (warning). In a notebook context, an import may be "unused in this cell"
        # but still intentionally establishes context for future cells. We only mark imports
        # as auto-fixable when they are provably redundant given the current globals.
        for imp in imported_names:
            if imp.exposed_name not in used_names:
                existing = available_globals.get(imp.exposed_name)

                # "Redundant" means: removing this import does NOT change notebook semantics because
                # the import would not change the current binding.
                is_redundant = False
                if existing is not None:
                    if imp.symbol is None:
                        # import module as alias
                        if isinstance(existing, types.ModuleType) and getattr(existing, "__name__", None) == imp.module:
                            is_redundant = True
                    else:
                        # from module import symbol as alias
                        if getattr(existing, "__name__", None) == imp.symbol and getattr(existing, "__module__", None) == imp.module:
                            is_redundant = True

                imported_label = f"{imp.module}.{imp.symbol}" if imp.symbol else imp.module
                report.issues.append(
                    LintIssue(
                        severity=LintSeverity.WARNING,
                        rule_id="DA1101" if is_redundant else "DA1001",
                        message=(
                            f"Redundant import: '{imp.exposed_name}' from {imported_label} "
                            f"(name already exists in notebook globals)"
                            if is_redundant
                            else f"Unused import: '{imp.exposed_name}' from {imported_label}"
                        ),
                        line=imp.line,
                        column=imp.column,
                        suggestion=(
                            "Remove the redundant import to reduce noise and avoid confusion."
                            if is_redundant
                            else "Consider removing the unused import if it is not meant to establish notebook context for future cells."
                        ),
                        fixable=is_redundant,
                    )
                )

        # Undefined names (warning; conservative)
        builtins_set = set(dir(builtins))
        known_names = assigned_names | builtins_set | available_names

        for name, (line, col) in self._collect_loaded_names_with_locations(tree):
            if name in known_names:
                continue
            # Avoid flagging dunder names (often used intentionally)
            if name.startswith("__") and name.endswith("__"):
                continue
            report.issues.append(
                LintIssue(
                    severity=LintSeverity.WARNING,
                    rule_id="DA1002",
                    message=f"Possibly undefined name: '{name}'",
                    line=line,
                    column=col,
                    suggestion="If this name should come from a previous cell, make sure it exists; otherwise define/import it in this cell.",
                    fixable=False,
                )
            )

        return report

    @staticmethod
    def _collect_used_names(tree: ast.AST) -> Set[str]:
        used: Set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                used.add(node.id)
        return used

    @staticmethod
    def _collect_loaded_names_with_locations(tree: ast.AST) -> Iterable[Tuple[str, Tuple[Optional[int], Optional[int]]]]:
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                yield node.id, (getattr(node, "lineno", None), getattr(node, "col_offset", None))

    @staticmethod
    def _collect_assigned_names(tree: ast.AST) -> Set[str]:
        assigned: Set[str] = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)):
                assigned.add(node.id)

            # Function/class definitions define names in the module scope
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                assigned.add(node.name)
                # Function parameters
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    for arg in node.args.args + node.args.kwonlyargs:
                        assigned.add(arg.arg)
                    if node.args.vararg:
                        assigned.add(node.args.vararg.arg)
                    if node.args.kwarg:
                        assigned.add(node.args.kwarg.arg)

            # Exception handler `except Exception as e:`
            if isinstance(node, ast.ExceptHandler) and node.name:
                assigned.add(node.name)

        # Imports also define names
        for imp in LintingService._collect_imported_names(tree):
            assigned.add(imp.exposed_name)

        return assigned

    @staticmethod
    def _collect_imported_names(tree: ast.AST) -> Set[_ImportedName]:
        imported: Set[_ImportedName] = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    exposed = alias.asname or alias.name.split(".")[0]
                    imported.add(
                        _ImportedName(
                            exposed_name=exposed,
                            module=alias.name,
                            symbol=None,
                            line=getattr(node, "lineno", None),
                            column=getattr(node, "col_offset", None),
                        )
                    )
            elif isinstance(node, ast.ImportFrom):
                # Skip star imports (we cannot reason about names safely)
                if any(a.name == "*" for a in node.names):
                    continue
                mod = node.module or ""
                for alias in node.names:
                    exposed = alias.asname or alias.name
                    imported.add(
                        _ImportedName(
                            exposed_name=exposed,
                            module=mod,
                            symbol=alias.name,
                            line=getattr(node, "lineno", None),
                            column=getattr(node, "col_offset", None),
                        )
                    )

        return imported

