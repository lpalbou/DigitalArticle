"""
Logic Validation Service for Digital Article (ADR 0004).

Validates that successfully executed code actually satisfies the user's intent
and follows domain best practices from personas.

This is distinct from the execution retry loop:
- Execution retry: fixes runtime errors (code doesn't run)
- Logic validation: fixes semantic errors (code runs but answer is wrong)
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from ..models.notebook import Cell, ExecutionResult, ExecutionStatus
from ..models.persona import PersonaCombination, PersonaScope
from .llm_service import LLMService
from .persona_service import PersonaService

logger = logging.getLogger(__name__)


class LogicValidationResult(str, Enum):
    """Result of logic validation check."""
    PASS = "pass"           # Code satisfies intent and best practices
    FAIL = "fail"           # Code has semantic issues that need fixing
    UNCERTAIN = "uncertain" # Validator cannot determine (edge case)


class IssueSeverity(str, Enum):
    """Severity level for logic validation issues."""
    HIGH = "high"       # MUST be fixed - breaks correctness
    MEDIUM = "medium"   # SHOULD be fixed - impacts quality
    LOW = "low"         # NICE to fix - minor improvements


@dataclass
class CategorizedIssue:
    """Issue with severity categorization."""
    issue: str
    severity: IssueSeverity
    suggestion: Optional[str] = None
    # Evidence snippets (verbatim substrings) used to justify the issue.
    # These are critical for:
    # - epistemic honesty (no hallucinated claims)
    # - grounding logic correction prompts in real artifacts (code/stdout)
    evidence_code: Optional[str] = None
    evidence_output: Optional[str] = None


@dataclass
class LogicValidationReport:
    """Report from logic validation check."""
    result: LogicValidationResult
    issues: List[str]                              # What's wrong (if FAIL) - legacy flat list
    suggestions: List[str]                         # How to fix it - legacy flat list
    categorized_issues: List[CategorizedIssue] = None  # Issues with severity (preferred)
    code_fix: Optional[str] = None                 # Proposed fixed code (if available)
    confidence: float = 0.0                        # 0-1 confidence in the assessment
    validation_type: str = "llm"                   # "heuristic" or "llm"
    raw_response: Optional[str] = None             # LLM response for debugging
    duration_ms: float = 0.0                       # How long validation took
    llm_prompt: Optional[str] = None               # For tracing (combined)
    llm_system_prompt: Optional[str] = None        # For UI/debugging
    llm_user_prompt: Optional[str] = None          # For UI/debugging
    llm_response: Optional[str] = None             # For tracing
    llm_usage: Optional[Dict[str, Any]] = None     # Token usage if available
    llm_parameters: Optional[Dict[str, Any]] = None  # Parameters used (temp, max_tokens, etc.)
    
    def __post_init__(self):
        if self.categorized_issues is None:
            self.categorized_issues = []
    
    def has_high_severity_issues(self) -> bool:
        """Check if there are any HIGH severity issues that must be fixed."""
        return any(ci.severity == IssueSeverity.HIGH for ci in self.categorized_issues)
    
    def get_issues_by_severity(self, severity: IssueSeverity) -> List[CategorizedIssue]:
        """Get issues filtered by severity."""
        return [ci for ci in self.categorized_issues if ci.severity == severity]


class LogicValidationService:
    """
    Service for validating that execution results satisfy user intent.
    
    Uses a hybrid approach (per ADR 0004):
    1. Deterministic heuristics for obvious issues (cheap, fast)
    2. LLM-as-judge for semantic validation (expensive, thorough)
    """
    
    # Prompt compaction limits (ADR 0003: explicit compaction only; never silent).
    # Note: these are character budgets (not tokens). We compact via head+tail.
    MAX_CODE_CHARS = 4000
    MAX_STDOUT_CHARS = 3000
    MAX_EVIDENCE_SNIPPET_CHARS = 200
    
    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service
        self.persona_service = PersonaService()
    
    async def validate(
        self,
        prompt: str,
        code: str,
        result: ExecutionResult,
        persona_combination: Optional[PersonaCombination] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> LogicValidationReport:
        """
        Validate that execution result satisfies user intent.
        
        Args:
            prompt: Original user prompt
            code: Generated/executed code
            result: Execution result (stdout, plots, tables, etc.)
            persona_combination: Active personas for domain-specific checks
            context: Additional context (available variables, etc.)
            
        Returns:
            LogicValidationReport with pass/fail and suggestions
        """
        import time
        start_time = time.time()
        
        # Stage 1: Fast deterministic heuristics
        heuristic_report = self._run_heuristic_checks(prompt, code, result)
        if heuristic_report.result == LogicValidationResult.FAIL:
            heuristic_report.duration_ms = (time.time() - start_time) * 1000
            logger.info(f"🔍 Logic validation FAILED on heuristics: {heuristic_report.issues}")
            return heuristic_report
        
        # Stage 2: LLM-as-judge for semantic validation
        llm_report = await self._run_llm_validation(
            prompt, code, result, persona_combination, context
        )
        llm_report.duration_ms = (time.time() - start_time) * 1000
        
        return llm_report
    
    def _run_heuristic_checks(
        self,
        prompt: str,
        code: str,
        result: ExecutionResult,
    ) -> LogicValidationReport:
        """
        Fast deterministic checks for obvious issues.
        
        These are cheap and catch common problems without LLM calls.
        """
        issues: List[str] = []
        suggestions: List[str] = []
        categorized: List[CategorizedIssue] = []
        
        # Check 1: No output at all
        if not result.stdout and not result.plots and not result.tables and not result.interactive_plots:
            if any(kw in prompt.lower() for kw in ['plot', 'chart', 'graph', 'figure', 'visualize', 'show']):
                issue = "Prompt requests visualization but no plot was generated"
                suggestion = "Add code to create and display a plot using matplotlib/seaborn/plotly"
                issues.append(issue)
                suggestions.append(suggestion)
                categorized.append(
                    CategorizedIssue(
                        issue=issue,
                        severity=IssueSeverity.HIGH,
                        suggestion=suggestion,
                        evidence_code="display(" if "display(" in code else None,
                        evidence_output="(no stdout)" if not result.stdout else result.stdout[: self.MAX_EVIDENCE_SNIPPET_CHARS],
                    )
                )
            elif any(kw in prompt.lower() for kw in ['table', 'dataframe', 'show data', 'display']):
                issue = "Prompt requests data display but no table was generated"
                suggestion = "Add display(df, 'Table: Description') to show the data"
                issues.append(issue)
                suggestions.append(suggestion)
                categorized.append(
                    CategorizedIssue(
                        issue=issue,
                        severity=IssueSeverity.HIGH,
                        suggestion=suggestion,
                        evidence_code="display(" if "display(" in code else None,
                        evidence_output="(no stdout)" if not result.stdout else result.stdout[: self.MAX_EVIDENCE_SNIPPET_CHARS],
                    )
                )
        
        # Check 2: Print statements but no display() calls
        if 'print(' in code and 'display(' not in code:
            if result.stdout and not result.plots and not result.tables:
                issue = "Code uses print() instead of display() for results"
                suggestion = "Replace print() with display(result, 'Label') for proper rendering"
                issues.append(issue)
                suggestions.append(suggestion)
                categorized.append(
                    CategorizedIssue(
                        issue=issue,
                        # This is a presentation quality recommendation, not a correctness blocker.
                        severity=IssueSeverity.LOW,
                        suggestion=suggestion,
                        evidence_code="print(",
                        evidence_output=result.stdout[: self.MAX_EVIDENCE_SNIPPET_CHARS] if result.stdout else None,
                    )
                )
        
        # Check 3: Statistical test without reporting key metrics
        statistical_keywords = ['t-test', 'ttest', 'anova', 'chi-square', 'correlation', 'regression', 'p-value', 'hypothesis']
        if any(kw in prompt.lower() for kw in statistical_keywords):
            if result.stdout:
                stdout_lower = result.stdout.lower()
                if 'p' not in stdout_lower and 'statistic' not in stdout_lower and 'coefficient' not in stdout_lower:
                    issue = "Statistical analysis requested but p-value/test statistic not visible in output"
                    suggestion = "Display the test statistic, p-value, and effect size"
                    issues.append(issue)
                    suggestions.append(suggestion)
                    categorized.append(
                        CategorizedIssue(
                            issue=issue,
                            severity=IssueSeverity.MEDIUM,
                            suggestion=suggestion,
                            evidence_code=None,
                            evidence_output=result.stdout[: self.MAX_EVIDENCE_SNIPPET_CHARS] if result.stdout else None,
                        )
                    )
        
        # Check 4: Column name mismatch (common error)
        if 'KeyError' in (result.stderr or '') or 'not in index' in (result.stderr or ''):
            issue = "Code references column that doesn't exist in the data"
            suggestion = "Check available columns with df.columns and use correct column names"
            issues.append(issue)
            suggestions.append(suggestion)
            categorized.append(
                CategorizedIssue(
                    issue=issue,
                    severity=IssueSeverity.HIGH,
                    suggestion=suggestion,
                    evidence_code="df[" if "df[" in code else None,
                    evidence_output=(result.stderr or "")[: self.MAX_EVIDENCE_SNIPPET_CHARS],
                )
            )
        
        if issues:
            # Heuristic checks should only FAIL on objective correctness blockers (HIGH severity).
            # Non-blocking notes are allowed, but should not force a correction loop.
            has_blocker = any(ci.severity == IssueSeverity.HIGH for ci in categorized)
            return LogicValidationReport(
                result=LogicValidationResult.FAIL if has_blocker else LogicValidationResult.PASS,
                issues=issues,
                suggestions=suggestions,
                categorized_issues=categorized,
                validation_type="heuristic",
                confidence=0.9 if has_blocker else 0.6,
            )
        
        return LogicValidationReport(
            result=LogicValidationResult.PASS,
            issues=[],
            suggestions=[],
            categorized_issues=[],
            validation_type="heuristic",
            confidence=0.5,  # Passing heuristics doesn't mean it's correct
        )
    
    async def _run_llm_validation(
        self,
        prompt: str,
        code: str,
        result: ExecutionResult,
        persona_combination: Optional[PersonaCombination] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> LogicValidationReport:
        """
        Use LLM to validate semantic correctness.
        
        This catches issues heuristics miss, like:
        - Wrong statistical test for the data type
        - Assumption violations
        - Missing data preprocessing steps
        - Incorrect interpretation of results
        """
        # Build validation prompt
        system_prompt = self._build_validation_system_prompt(persona_combination)
        user_prompt = self._build_validation_user_prompt(prompt, code, result, context)
        full_prompt = f"[System]\n{system_prompt}\n\n[User]\n{user_prompt}"
        
        try:
            # Use the LLM to validate
            temperature = 0.1
            max_tokens = 1000
            response = await self.llm_service.llm.agenerate(
                user_prompt,
                system_prompt=system_prompt,
                temperature=temperature,  # Low temperature for consistent judgment
                max_tokens=max_tokens,
            )
            
            # Parse the response and include prompt/response for tracing
            # Evidence verification should consider BOTH real stdout and the explicit output summary lines
            # included in the validator prompt (plots/tables counts).
            output_summary = (
                f"STATIC_PLOTS GENERATED: {len(result.plots or [])}\n"
                f"INTERACTIVE_PLOTS GENERATED: {len(result.interactive_plots or [])}\n"
                f"IMAGES GENERATED: {len(result.images or [])}\n"
                f"TABLES GENERATED: {len(result.tables or [])}\n"
            )
            report = self._parse_validation_response(
                response.content,
                code=code,
                stdout=(result.stdout or "") + "\n" + output_summary,
            )
            report.llm_prompt = full_prompt
            report.llm_system_prompt = system_prompt
            report.llm_user_prompt = user_prompt
            report.llm_response = response.content
            report.llm_usage = getattr(response, 'usage', None)
            report.llm_parameters = {
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            return report
            
        except Exception as e:
            logger.error(f"LLM validation failed: {e}")
            return LogicValidationReport(
                result=LogicValidationResult.UNCERTAIN,
                issues=[f"Validation check failed: {str(e)}"],
                suggestions=[],
                validation_type="llm",
                confidence=0.0,
                llm_prompt=full_prompt,
                llm_system_prompt=system_prompt,
                llm_user_prompt=user_prompt,
                llm_parameters={
                    "temperature": 0.1,
                    "max_tokens": 1000,
                },
            )
    
    def _build_validation_system_prompt(
        self,
        persona_combination: Optional[PersonaCombination] = None,
    ) -> str:
        """Build system prompt for validation LLM call."""
        base_prompt = """You are a senior scientific code reviewer validating that generated code
correctly answers the user's request. Think carefully about the evidences and the prompt.

Your goal is epistemic honesty: say NOTHING when it is correct/adequate.

You MUST answer four directed questions (YES/NO). This is a correctness check, not an open-ended review.

HONESTY / SCOPE RULES (critical):
- Do NOT FAIL based on what "might break" in another environment. Only use empirical evidence from the provided code/output.
- Do NOT invent requirements. If the prompt says "about" or describes randomness, allow statistical variation.
- Do NOT treat harmless extra steps (e.g., printing extra summary lines, optional file export) as "misrepresentation" unless they contradict the user's explicit requirements.
- If the prompt asks to "save as a DataFrame", it is satisfied by creating the DataFrame object in code (e.g., `df = pd.DataFrame(...)`) and/or displaying it.
  Do NOT require file I/O unless the user explicitly asked to write a file.
- Group/row ordering is not a requirement unless the user explicitly requests an ordering. Validate semantic mapping (labels ↔ parameters ↔ outputs), not array order.

Q1_FAILED_TO_ANSWER_USER_INTENT:
- YES only if the code/output is missing a required deliverable explicitly asked in the user prompt
  (e.g., user asked to save a file, create a plot/table, compute/report a specific result) and it is absent.

Q2_MISREPRESENTED_USER_INTENT:
- YES only if the produced artifact contradicts an explicit requirement
  (wrong columns, wrong grouping, wrong metric, wrong label/value semantics).

Q3_STATISTICALLY_INACCURATE:
- YES only if there is a contradiction between claims and evidence in code/output
  (e.g., a reported p-value/HR/median that doesn't match any shown output or computed value).
- Do NOT answer YES for "didn't check assumptions" or "didn't add extra validation" unless the user explicitly asked for it.

Q4_RULE_VIOLATION (persona/domain hard constraints only):
- YES only if a MUST/NEVER constraint is violated (from persona guidance or domain rules),
  and that constraint is relevant to the user prompt's correctness.
- Do NOT treat soft best-practice guidance as a blocker.

PROOF OBLIGATION (required for any YES):
- Quote the exact prompt clause you believe is violated: prompt_clause: "..."
- Provide empirical evidence copied verbatim from the provided code/output:
  evidence_code: `<substring from code>` OR `NONE`
  evidence_output: `<substring from output>` OR `NONE`

RESPOND IN THIS EXACT FORMAT:
RESULT: PASS or FAIL
Q1_FAILED_TO_ANSWER_USER_INTENT: YES/NO | prompt_clause: "..." | evidence_code: `...` | evidence_output: `...`
Q2_MISREPRESENTED_USER_INTENT: YES/NO | prompt_clause: "..." | evidence_code: `...` | evidence_output: `...`
Q3_STATISTICALLY_INACCURATE: YES/NO | prompt_clause: "..." | evidence_code: `...` | evidence_output: `...`
Q4_RULE_VIOLATION: YES/NO | prompt_clause: "..." | evidence_code: `...` | evidence_output: `...`
ISSUES: (only if any Q is YES; otherwise write 'None')
- [HIGH] Issue (must map to a YES above) | prompt_clause: "..." | evidence_code: `...` | evidence_output: `...`
SUGGESTIONS: (only if ISSUES is not None; otherwise write 'None')
- Suggestion 1 (minimal diff, scope-tight)
CONFIDENCE: (0.0 to 1.0)

IMPORTANT RULES:
- RESULT must be PASS if all Q1–Q4 are NO (and then ISSUES/SUGGESTIONS must be None).
- RESULT must be FAIL only if at least one Q is YES and at least one [HIGH] issue is listed with evidence.
- Never include a self-contradictory issue; if it is correct, do NOT list it.
- Do NOT infer missing columns/values from pandas '...' truncation; use TABLES SUMMARY if provided.
"""
        
        # Add persona-specific validation guidance
        if persona_combination:
            try:
                # Check if LOGIC_VALIDATION scope exists, otherwise use REVIEW
                guidance = persona_combination.effective_guidance.get(
                    PersonaScope.REVIEW,
                    None
                )
                if guidance and guidance.system_prompt_addition:
                    base_prompt += (
                        "\n\nDOMAIN-SPECIFIC VALIDATION RULES (apply ONLY when they change correctness of the user's request):\n"
                        f"{guidance.system_prompt_addition}"
                    )
            except Exception as e:
                logger.warning(f"Could not add persona guidance to validation: {e}")
        
        return base_prompt
    
    def _build_validation_user_prompt(
        self,
        prompt: str,
        code: str,
        result: ExecutionResult,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Build user prompt for validation LLM call."""
        # ADR 0003: explicit compaction only (never silent). We compact via head+tail and mark it.
        def _compact(text: str, *, max_chars: int, label: str) -> tuple[str, bool]:
            if text is None:
                return "", False
            if len(text) <= max_chars:
                return text, False
            head_len = max_chars // 2
            tail_len = max_chars - head_len
            head = text[:head_len]
            tail = text[-tail_len:] if tail_len > 0 else ""
            notice = (
                f"#COMPACTION_NOTICE: {label} compacted for LLM context (original_len={len(text)} chars, "
                f"shown=head+tail={len(head) + len(tail)} chars; middle omitted).\n"
            )
            compacted = head + "\n\n" + notice + "\n" + tail
            logger.info(notice.strip())
            return compacted, True

        compacted_code, code_compacted = _compact(code, max_chars=self.MAX_CODE_CHARS, label="CODE")
        compacted_stdout, stdout_compacted = _compact(result.stdout or "", max_chars=self.MAX_STDOUT_CHARS, label="STDOUT")
        
        user_prompt = f"""VALIDATE THIS ANALYSIS:

USER PROMPT:
{prompt}

GENERATED CODE:
```python
{compacted_code}
```

EXECUTION OUTPUT:
{compacted_stdout if compacted_stdout else "(no stdout)"}

# Output summary (IMPORTANT): Plotly figures are counted as INTERACTIVE_PLOTS.
STATIC_PLOTS GENERATED: {len(result.plots or [])}
INTERACTIVE_PLOTS GENERATED: {len(result.interactive_plots or [])}
IMAGES GENERATED: {len(result.images or [])}
TABLES GENERATED: {len(result.tables or [])}
"""

        # Add compact table summaries so the validator isn't forced to rely on truncated stdout reprs.
        # This is schema-first evidence: label, shape, columns, and a couple of sample rows.
        try:
            tables = result.tables or []
            display_tables = [t for t in tables if (t.get("source") == "display" or t.get("source") is None)]
            if display_tables:
                user_prompt += "\n\nTABLES SUMMARY (schema-first; do NOT infer missing columns from pandas '...'):\n"
                for t in display_tables[:3]:
                    name = t.get("name") or t.get("label") or "Unlabeled Table"
                    cols = t.get("columns") or t.get("headers") or []
                    shape = t.get("shape")
                    user_prompt += f"- {name}: shape={shape}, columns={cols}\n"

                    # Try to include up to 2 representative rows if available
                    data = t.get("data")
                    if isinstance(data, list) and data:
                        sample_rows = data[:2]
                        for r in sample_rows:
                            if isinstance(r, dict):
                                user_prompt += f"  sample_row: {r}\n"
                            elif isinstance(r, list) and cols and len(cols) == len(r):
                                user_prompt += f"  sample_row: {dict(zip(cols, r))}\n"
                            else:
                                user_prompt += f"  sample_row: {str(r)[:200]}\n"
        except Exception as e:
            # Never let prompt formatting failures break validation.
            logger.warning(f"Could not build TABLES SUMMARY for validation: {e}")
        
        user_prompt += (
            "\n\nAnswer Q1–Q4 as directed in the system prompt.\n"
            "- Be strict about proof obligations: quote prompt_clause and provide evidence_code/evidence_output.\n"
            "- If all Q are NO, be silent: RESULT=PASS, ISSUES=None.\n"
        )
        
        return user_prompt
    
    def _parse_validation_response(
        self,
        response: str,
        *,
        code: Optional[str] = None,
        stdout: Optional[str] = None,
    ) -> LogicValidationReport:
        """
        Parse LLM response into structured report with severity categorization.

        Also applies a minimal, robust sanity filter:
        - If the validator labels an issue as HIGH but provides no verifiable evidence snippet present in the
          provided code/stdout, we downgrade severity (HIGH→MEDIUM, MEDIUM→LOW).
        """
        import re
        response_upper = response.upper()
        
        # Determine result from the model's header (we may override later based on parsed blockers).
        if 'RESULT: PASS' in response_upper or 'RESULT:PASS' in response_upper:
            result = LogicValidationResult.PASS
        elif 'RESULT: FAIL' in response_upper or 'RESULT:FAIL' in response_upper:
            result = LogicValidationResult.FAIL
        else:
            result = LogicValidationResult.UNCERTAIN

        # Directed-question self-consistency gate:
        # If Q1–Q4 are present, we treat inconsistencies as UNCERTAIN (do not trigger correction loops).
        def _parse_yes_no(line: str) -> Optional[bool]:
            lu = line.upper()
            if "YES" in lu:
                return True
            if "NO" in lu:
                return False
            return None

        q_lines = {}
        for qkey in (
            "Q1_FAILED_TO_ANSWER_USER_INTENT",
            "Q2_MISREPRESENTED_USER_INTENT",
            "Q3_STATISTICALLY_INACCURATE",
            "Q4_RULE_VIOLATION",
        ):
            m = re.search(rf"^{qkey}\s*:\s*(.+)$", response, flags=re.IGNORECASE | re.MULTILINE)
            if m:
                q_lines[qkey] = m.group(0)

        q_blockers = None
        if q_lines:
            parsed = []
            for qkey, full_line in q_lines.items():
                yn = _parse_yes_no(full_line)
                if yn is not None:
                    parsed.append(yn)
            if parsed:
                q_blockers = any(parsed)
        
        # Extract issues with severity (+ evidence parsing).
        #
        # Robust parsing: issues often span multiple lines, e.g.
        # - [HIGH] Something...
        #   evidence_code: `...`
        #   evidence_output: `...`
        issues: List[str] = []
        categorized_issues: List[CategorizedIssue] = []
        if 'ISSUES:' in response.upper():
            issues_section = (
                response.split('ISSUES:')[1].split('SUGGESTIONS:')[0]
                if 'SUGGESTIONS:' in response.upper()
                else response.split('ISSUES:')[1]
            )

            raw_lines = issues_section.splitlines()
            blocks: List[List[str]] = []
            current: Optional[List[str]] = None

            # A new issue should start only when the bullet line contains an explicit severity marker.
            # This avoids treating continuation bullets (common in messy LLM output) as separate issues.
            sev_re = re.compile(r"\b(HIGH|MEDIUM|LOW|CRITICAL)\b", flags=re.IGNORECASE)

            for raw in raw_lines:
                if not raw.strip():
                    continue
                is_bullet = raw.lstrip().startswith(('-', '•'))
                has_sev = bool(sev_re.search(raw))

                if is_bullet and has_sev:
                    # Start a new issue block
                    if current:
                        blocks.append(current)
                    current = [raw]
                elif is_bullet and not has_sev:
                    # Continuation bullet (or malformed): attach to current if possible
                    if current:
                        current.append(raw)
                    else:
                        # No current block yet: treat as a new (untyped) block anyway
                        current = [raw]
                else:
                    if current:
                        current.append(raw)
            if current:
                blocks.append(current)

            for block_lines in blocks:
                first_line = block_lines[0].lstrip().lstrip('-•').strip()
                block_text = "\n".join(block_lines)

                if first_line.lower() in ['none', 'n/a', '']:
                    continue

                # Parse severity from the first line
                severity = IssueSeverity.MEDIUM  # Default
                clean_issue = first_line

                if '[HIGH]' in first_line.upper() or '**HIGH' in first_line.upper():
                    severity = IssueSeverity.HIGH
                    clean_issue = re.sub(r'\[?HIGH\]?:?\s*|\*\*HIGH\*\*:?\s*', '', clean_issue, flags=re.IGNORECASE).strip()
                elif '[MEDIUM]' in first_line.upper() or '**MEDIUM' in first_line.upper():
                    severity = IssueSeverity.MEDIUM
                    clean_issue = re.sub(r'\[?MEDIUM\]?:?\s*|\*\*MEDIUM\*\*:?\s*', '', clean_issue, flags=re.IGNORECASE).strip()
                elif '[LOW]' in first_line.upper() or '**LOW' in first_line.upper():
                    severity = IssueSeverity.LOW
                    clean_issue = re.sub(r'\[?LOW\]?:?\s*|\*\*LOW\*\*:?\s*', '', clean_issue, flags=re.IGNORECASE).strip()
                elif 'CRITICAL:' in first_line.upper() or '**CRITICAL' in first_line.upper():
                    severity = IssueSeverity.HIGH
                    clean_issue = re.sub(r'\*?\*?CRITICAL:?\*?\*?\s*', '', clean_issue, flags=re.IGNORECASE).strip()

                # Extract evidence snippets if present (accept inline or subsequent lines).
                # NOTE: Evidence snippets must be from CODE/STDOUT. Comment-only "evidence_code" is not sufficient
                # to justify a correctness FAIL.
                def _extract_evidence(key: str) -> Optional[str]:
                    m = re.search(rf"{key}:\s*`([^`]+)`", block_text, flags=re.IGNORECASE)
                    if m:
                        return m.group(1)[: self.MAX_EVIDENCE_SNIPPET_CHARS]
                    m2 = re.search(rf"{key}:\s*(.+)", block_text, flags=re.IGNORECASE)
                    if m2:
                        return m2.group(1).strip()[: self.MAX_EVIDENCE_SNIPPET_CHARS]
                    return None

                evidence_code = _extract_evidence("evidence_code")
                evidence_output = _extract_evidence("evidence_output")

                # Sanitize evidence: comment-only "evidence_code" is not a meaningful code evidence snippet.
                if evidence_code and evidence_code.strip().startswith("#"):
                    evidence_code = None

                # Normalize common escaped sequences so evidence can be verified against real artifacts.
                # Some models paste snippets with literal "\\n" instead of actual newlines.
                def _normalize_evidence(ev: Optional[str]) -> Optional[str]:
                    if not ev:
                        return None
                    # Keep this intentionally minimal to avoid surprising transformations.
                    return (
                        ev.replace("\\r\\n", "\n")
                        .replace("\\n", "\n")
                        .replace("\\t", "\t")
                        .replace("\\r", "\r")
                    )

                evidence_code = _normalize_evidence(evidence_code)
                evidence_output = _normalize_evidence(evidence_output)

                # Drop self-retracted issues (intellectual honesty guard):
                # If the validator itself states the issue is NOT an issue / actually correct, we cannot treat it
                # as a blocker. This prevents incoherent LLM outputs from triggering correction loops.
                #
                # IMPORTANT: We only drop on explicit retraction language (not mere "re-examining" phrasing),
                # to avoid hiding legitimate issues where the model re-checks and still concludes "wrong".
                block_upper = block_text.upper()
                explicit_retraction_markers = (
                    "THIS IS NOT AN ISSUE",
                    "NOT AN ISSUE",
                    "ACTUALLY CORRECT",
                    "THIS IS CORRECT",
                    "THE CODE IS CORRECT",
                    "ASSIGNMENT IS CORRECT",
                )
                if any(m in block_upper for m in explicit_retraction_markers):
                    logger.info("Dropping self-retracted validator issue block to preserve epistemic honesty.")
                    continue

                # Sanity check: downgrade severity if evidence can't be verified against artifacts.
                # We accept verification if EITHER code evidence matches OR output evidence matches.
                def _evidence_verified() -> bool:
                    code_ev = evidence_code if (evidence_code and evidence_code.upper() != "NONE") else None
                    out_ev = evidence_output if (evidence_output and evidence_output.upper() != "NONE") else None

                    if not code_ev and not out_ev:
                        return False

                    code_ok = bool(code_ev and code and code_ev in code)
                    out_ok = bool(out_ev and stdout and out_ev in stdout)
                    return code_ok or out_ok

                if (severity == IssueSeverity.HIGH or severity == IssueSeverity.MEDIUM) and not _evidence_verified():
                    if severity == IssueSeverity.HIGH:
                        severity = IssueSeverity.MEDIUM
                    else:
                        severity = IssueSeverity.LOW

                # Remove inline evidence markers if present in the first line
                clean_issue = re.sub(r"evidence_code:\s*`[^`]*`", "", clean_issue, flags=re.IGNORECASE).strip()
                clean_issue = re.sub(r"evidence_output:\s*`[^`]*`", "", clean_issue, flags=re.IGNORECASE).strip()
                clean_issue = re.sub(r"\s*\|\s*\|\s*", " | ", clean_issue).strip(" |")

                issues.append(clean_issue)
                categorized_issues.append(
                    CategorizedIssue(
                        issue=clean_issue,
                        severity=severity,
                        evidence_code=evidence_code,
                        evidence_output=evidence_output,
                    )
                )

        # Extract suggestions and pair with issues
        suggestions = []
        if 'SUGGESTIONS:' in response.upper():
            suggestions_section = response.split('SUGGESTIONS:')[1].split('CONFIDENCE:')[0] if 'CONFIDENCE:' in response.upper() else response.split('SUGGESTIONS:')[1]
            suggestion_idx = 0
            for line in suggestions_section.strip().split('\n'):
                line = line.strip()
                if line.startswith('-') or line.startswith('•'):
                    suggestion = line.lstrip('-•').strip()
                    if suggestion.lower() not in ['none', 'n/a', '']:
                        suggestions.append(suggestion)
                        # Pair with categorized issue if available
                        if suggestion_idx < len(categorized_issues):
                            categorized_issues[suggestion_idx].suggestion = suggestion
                        suggestion_idx += 1

        # Suggestion-based self-retraction guard:
        # Some models place the retraction in the suggestion rather than in the issue block itself
        # (e.g., "Upon re-examination, this is NOT an issue; remove the HIGH flag.").
        # In that case, the issue cannot be treated as a correctness blocker.
        retraction_markers = (
            "THIS IS NOT AN ISSUE",
            "NOT AN ISSUE",
            "REMOVE THE [HIGH] FLAG",
            "REMOVE THE HIGH FLAG",
            "ACTUALLY CORRECT",
            "THE CODE IS CORRECT",
            "ASSIGNMENT IS CORRECT",
        )
        for ci in categorized_issues:
            if not ci.suggestion:
                continue
            sug_upper = ci.suggestion.upper()
            if any(m in sug_upper for m in retraction_markers):
                # Downgrade to LOW so it never triggers FAIL/correction, but keep it visible in metadata.
                ci.severity = IssueSeverity.LOW

        # Final correctness gate (intellectual honesty / product intent):
        # - Only HIGH severity issues are considered blockers that should drive FAIL.
        # - MEDIUM/LOW issues should not block correctness in ambiguous cases.
        #
        # This also prevents cases where the model returns RESULT: FAIL for minor suggestions.
        has_blocker = any(ci.severity == IssueSeverity.HIGH for ci in categorized_issues)

        # If Q1–Q4 were present, enforce consistency:
        # - Q says "no blockers" but we have HIGH -> UNCERTAIN
        # - Q says "blocker exists" but we have no HIGH -> UNCERTAIN
        if q_blockers is not None and q_blockers != has_blocker:
            logger.info(
                "Validator response is self-inconsistent (Q1–Q4 vs issues severities). Marking UNCERTAIN to avoid poisoning correction."
            )
            result = LogicValidationResult.UNCERTAIN
        elif has_blocker:
            result = LogicValidationResult.FAIL
        else:
            # Preserve UNCERTAIN when the response isn't parseable/structured enough to be trusted.
            # Otherwise, treat non-blocking issues as PASS.
            if result == LogicValidationResult.UNCERTAIN:
                result = LogicValidationResult.UNCERTAIN
            elif result == LogicValidationResult.FAIL and not categorized_issues:
                result = LogicValidationResult.UNCERTAIN
            else:
                result = LogicValidationResult.PASS
        
        # Extract confidence
        confidence = 0.7  # Default
        if 'CONFIDENCE:' in response.upper():
            try:
                conf_section = response.upper().split('CONFIDENCE:')[1][:20]
                conf_match = re.search(r'(\d+\.?\d*)', conf_section)
                if conf_match:
                    confidence = float(conf_match.group(1))
                    if confidence > 1:
                        confidence = confidence / 100  # Handle percentage format
            except:
                pass
        
        return LogicValidationReport(
            result=result,
            issues=issues,
            suggestions=suggestions,
            categorized_issues=categorized_issues,
            validation_type="llm",
            confidence=confidence,
            raw_response=response,
        )


def get_logic_validation_service(llm_service: LLMService) -> LogicValidationService:
    """Factory function for LogicValidationService."""
    return LogicValidationService(llm_service)
