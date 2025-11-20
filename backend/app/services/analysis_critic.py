"""
Analysis Critic Service - Post-Execution Critical Evaluation

This service implements domain-agnostic critical evaluation of completed analyses.
After code executes successfully, it critiques:
- Whether results are plausible
- Whether method assumptions were checked
- Whether interpretation is appropriate
- What limitations should be acknowledged
- How the analysis could be improved

Leverages AbstractCore's LLM-as-a-judge and session assessment capabilities.
"""

import logging
import json
import re
from typing import Dict, Any, List, Optional, Tuple
from abstractcore import BasicSession, create_llm
from abstractcore.processing import BasicJudge

from ..models.analysis_critique import (
    AnalysisCritique,
    CritiqueFinding,
    CritiqueSeverity,
    CritiqueCategory,
    PlausibilityCheck,
    AssumptionCheck,
    CritiqueTrace
)
from ..models.analysis_plan import AnalysisPlan

logger = logging.getLogger(__name__)


class AnalysisCritic:
    """
    Critiques completed data analysis using domain-agnostic reasoning.

    Uses LLM-as-a-judge to evaluate:
    1. Logical coherence of results
    2. Plausibility of findings
    3. Assumption validity
    4. Interpretation quality
    5. Completeness and limitations
    """

    def __init__(self, llm_provider: str = "anthropic", llm_model: str = "claude-haiku-4-5"):
        """
        Initialize critic with LLM for evaluation.

        Args:
            llm_provider: LLM provider (anthropic, openai, etc.)
            llm_model: Specific model to use for critique
        """
        self.llm_provider = llm_provider
        self.llm_model = llm_model
        self.llm = create_llm(llm_provider, model=llm_model)
        self.judge = BasicJudge()

    def critique_analysis(
        self,
        user_intent: str,
        code: str,
        execution_result: Dict[str, Any],
        analysis_plan: Optional[AnalysisPlan] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[AnalysisCritique, CritiqueTrace]:
        """
        Critically evaluate a completed analysis.

        Args:
            user_intent: Original user request
            code: Executed Python code
            execution_result: Results from execution (stdout, tables, plots, etc.)
            analysis_plan: The original analysis plan (if planning was used)
            context: Additional context (available variables, etc.)

        Returns:
            Tuple of (AnalysisCritique, CritiqueTrace)
        """
        logger.info(f"🔍 Critiquing analysis for: {user_intent[:100]}...")

        import time
        start_time = time.time()

        try:
            # Build critique context
            critique_context = self._build_critique_context(
                user_intent,
                code,
                execution_result,
                analysis_plan,
                context
            )

            # Use AbstractCore's BasicSession for multi-criteria assessment
            session = BasicSession(
                self.llm,
                system_prompt=self._build_critique_system_prompt()
            )

            # Get structured assessment using session.generate_assessment()
            assessment_raw = session.generate_assessment(
                criteria=[
                    "logical_coherence",
                    "result_plausibility",
                    "assumption_validity",
                    "interpretation_quality",
                    "completeness"
                ],
                include_score=True
            )

            # Also use BasicJudge for additional evaluation
            judge_assessment = self.judge.evaluate(
                text=critique_context,
                context="data analysis quality assessment",
                focus="result plausibility, assumption checking, interpretation accuracy"
            )

            # Parse assessments and build critique
            critique = self._build_critique_from_assessments(
                assessment_raw,
                judge_assessment,
                user_intent,
                code,
                execution_result,
                analysis_plan
            )

            # Perform specific plausibility checks
            plausibility_checks = self._check_result_plausibility(execution_result, code)
            critique.plausibility_checks = plausibility_checks

            # Perform assumption checks
            assumption_checks = self._check_assumptions(code, execution_result, analysis_plan)
            critique.assumption_checks = assumption_checks

            # Add findings for failed checks
            for check in plausibility_checks:
                if not check.passed:
                    critique.findings.append(CritiqueFinding(
                        severity=CritiqueSeverity.MAJOR,
                        category=CritiqueCategory.RESULT_PLAUSIBILITY,
                        title=f"Implausible result: {check.check_name}",
                        description=check.details,
                        impact="Results may be incorrect or indicate coding error",
                        suggestion="Review code and data for errors"
                    ))

            for check in assumption_checks:
                if check.checked and not check.met:
                    critique.findings.append(CritiqueFinding(
                        severity=CritiqueSeverity.MAJOR,
                        category=CritiqueCategory.ASSUMPTION_VIOLATION,
                        title=f"Assumption violated: {check.assumption}",
                        description=check.evidence,
                        impact=check.consequences,
                        suggestion="Use alternative method or note limitation"
                    ))

            # Create trace
            critique_time_ms = (time.time() - start_time) * 1000
            trace = CritiqueTrace(
                critique=critique,
                llm_provider=self.llm_provider,
                llm_model=self.llm_model,
                critique_time_ms=critique_time_ms,
                assessment_raw=str(assessment_raw)
            )

            logger.info(
                f"✅ Critique complete ({critique_time_ms:.0f}ms): "
                f"{critique.overall_quality} | "
                f"{len(critique.findings)} findings"
            )

            return critique, trace

        except Exception as e:
            logger.error(f"❌ Critique failed: {e}")
            # Return minimal critique on failure
            fallback_critique = AnalysisCritique(
                overall_quality="uncertain",
                confidence_in_results="medium",
                summary=f"Critique process failed: {str(e)}. Review analysis manually.",
                critique_method="failed"
            )
            trace = CritiqueTrace(
                critique=fallback_critique,
                llm_provider=self.llm_provider,
                llm_model=self.llm_model,
                critique_time_ms=(time.time() - start_time) * 1000
            )
            return fallback_critique, trace

    def _build_critique_system_prompt(self) -> str:
        """Build system prompt for critique reasoning."""
        return """You are a critical analysis evaluator that assesses the quality and validity of data analyses.

Your role is to provide constructive but rigorous critique of completed analyses, checking for:
- Logical coherence and consistency
- Result plausibility (no impossible values)
- Assumption validity (were requirements met?)
- Interpretation quality (appropriate conclusions?)
- Completeness (what's missing?)

EVALUATION FRAMEWORK:

1. LOGICAL COHERENCE
   - Do results make sense given the analysis?
   - Are conclusions supported by evidence?
   - Any internal contradictions?

2. RESULT PLAUSIBILITY
   - Are values within possible/reasonable ranges?
   - No negative variances, rates >100%, etc.?
   - Do patterns make intuitive sense?

3. ASSUMPTION VALIDITY
   - Were method assumptions checked?
   - If violated, was it acknowledged?
   - Are alternative methods needed?

4. INTERPRETATION QUALITY
   - Are results properly interpreted?
   - Correlation vs causation clear?
   - Statistical vs practical significance noted?
   - Limitations acknowledged?

5. COMPLETENESS
   - What's missing?
   - Robustness checks needed?
   - Alternative explanations considered?

You provide structured, actionable feedback that helps improve analysis quality."""

    def _build_critique_context(
        self,
        user_intent: str,
        code: str,
        execution_result: Dict[str, Any],
        analysis_plan: Optional[AnalysisPlan],
        context: Optional[Dict[str, Any]]
    ) -> str:
        """Build context string for critique."""

        context_parts = [
            "=== ANALYSIS TO CRITIQUE ===\n",
            f"USER INTENT: {user_intent}\n"
        ]

        if analysis_plan:
            context_parts.append(f"\nORIGINAL PLAN:\n{analysis_plan.get_summary()}\n")

        context_parts.append(f"\nCODE EXECUTED:\n```python\n{code}\n```\n")

        # Add execution results
        context_parts.append("\nEXECUTION RESULTS:\n")

        if execution_result.get('stdout'):
            context_parts.append(f"STDOUT:\n{execution_result['stdout'][:2000]}\n")  # Limit length

        if execution_result.get('stderr'):
            context_parts.append(f"STDERR:\n{execution_result['stderr'][:1000]}\n")

        if execution_result.get('tables'):
            context_parts.append(f"\nTABLES GENERATED: {len(execution_result['tables'])}\n")

        if execution_result.get('plots'):
            context_parts.append(f"PLOTS GENERATED: {len(execution_result['plots'])}\n")

        context_parts.append("\n=== END ANALYSIS ===")

        return "".join(context_parts)

    def _build_critique_from_assessments(
        self,
        assessment_raw: Any,
        judge_assessment: str,
        user_intent: str,
        code: str,
        execution_result: Dict[str, Any],
        analysis_plan: Optional[AnalysisPlan]
    ) -> AnalysisCritique:
        """Parse LLM assessments into structured critique."""

        # Extract overall quality from assessments
        overall_quality = self._extract_quality_rating(str(assessment_raw), judge_assessment)

        # Extract findings from judge assessment
        findings = self._extract_findings_from_judge(judge_assessment)

        # Infer confidence
        confidence = self._infer_confidence(overall_quality, findings)

        # Generate summary
        summary = self._generate_critique_summary(overall_quality, findings, judge_assessment)

        # Extract recommendations
        recommendations = self._extract_recommendations(judge_assessment)

        # Identify limitations
        limitations = self._identify_limitations(code, execution_result, analysis_plan, findings)

        critique = AnalysisCritique(
            overall_quality=overall_quality,
            confidence_in_results=confidence,
            summary=summary,
            findings=findings,
            recommended_improvements=recommendations,
            identified_limitations=limitations,
            critique_method="llm_judge",
            llm_assessment_score=self._extract_score(str(assessment_raw))
        )

        return critique

    def _check_result_plausibility(
        self,
        execution_result: Dict[str, Any],
        code: str
    ) -> List[PlausibilityCheck]:
        """Check if results are plausible using rule-based checks."""

        checks = []

        stdout = execution_result.get('stdout', '')

        # Check 1: No negative variances/std
        variance_pattern = r'(variance|std|standard\s+deviation)'
        if re.search(variance_pattern, stdout, re.IGNORECASE):
            has_negative = re.search(r'(variance|std|standard\s+deviation)[:\s=]+([-][\d.]+)', stdout, re.IGNORECASE)
            checks.append(PlausibilityCheck(
                check_name="No negative variance/std",
                passed=not bool(has_negative),
                details="Checked for negative variance or standard deviation values",
                expected_range="≥ 0",
                actual_value=has_negative.group(2) if has_negative else "OK"
            ))

        # Check 2: Percentages in valid range
        percentage_matches = re.findall(r'(\d+\.?\d*)\s*%', stdout)
        invalid_percentages = [p for p in percentage_matches if float(p) > 100 or float(p) < 0]
        if percentage_matches:
            checks.append(PlausibilityCheck(
                check_name="Percentages in valid range (0-100%)",
                passed=len(invalid_percentages) == 0,
                details=f"Found {len(percentage_matches)} percentage values",
                expected_range="0-100%",
                actual_value=f"Invalid: {invalid_percentages}" if invalid_percentages else "OK"
            ))

        # Check 3: P-values in valid range
        pvalue_matches = re.findall(r'p[-\s]*value[:\s=]+([\d.e-]+)', stdout, re.IGNORECASE)
        invalid_pvalues = [p for p in pvalue_matches if float(p) > 1.0]
        if pvalue_matches:
            checks.append(PlausibilityCheck(
                check_name="P-values in valid range (0-1)",
                passed=len(invalid_pvalues) == 0,
                details=f"Found {len(pvalue_matches)} p-values",
                expected_range="0-1",
                actual_value=f"Invalid: {invalid_pvalues}" if invalid_pvalues else "OK"
            ))

        # Check 4: Sample sizes are positive integers
        if 'n=' in stdout.lower() or 'n =' in stdout.lower():
            n_matches = re.findall(r'n\s*=\s*(\d+)', stdout, re.IGNORECASE)
            zero_n = [n for n in n_matches if int(n) == 0]
            checks.append(PlausibilityCheck(
                check_name="Sample sizes > 0",
                passed=len(zero_n) == 0,
                details=f"Found {len(n_matches)} sample size values",
                expected_range="> 0",
                actual_value="OK" if len(zero_n) == 0 else f"Found n=0"
            ))

        return checks

    def _check_assumptions(
        self,
        code: str,
        execution_result: Dict[str, Any],
        analysis_plan: Optional[AnalysisPlan]
    ) -> List[AssumptionCheck]:
        """Check whether method assumptions were validated."""

        checks = []

        # Common statistical tests and their assumptions
        code_lower = code.lower()
        stdout = execution_result.get('stdout', '')

        # T-test assumptions
        if 'ttest' in code_lower or 't_test' in code_lower:
            checks.append(AssumptionCheck(
                assumption="Normality of data (for t-test)",
                checked='shapiro' in code_lower or 'normaltest' in code_lower or 'qqplot' in code_lower,
                met=None,  # Can't determine without seeing results
                evidence="Normality test not found in code" if 'shapiro' not in code_lower else "Shapiro test detected",
                consequences="T-test may be invalid if data not normally distributed; consider Mann-Whitney U test"
            ))

            checks.append(AssumptionCheck(
                assumption="Equal variances (for independent t-test)",
                checked='levene' in code_lower or 'bartlett' in code_lower,
                met=None,
                evidence="Variance equality test not found" if 'levene' not in code_lower else "Levene test detected",
                consequences="Use Welch's t-test if variances unequal"
            ))

        # Linear regression assumptions
        if 'linearregression' in code_lower or 'ols' in code_lower:
            checks.append(AssumptionCheck(
                assumption="Linearity of relationship",
                checked='scatter' in code_lower or 'plot' in code_lower,
                met=None,
                evidence="Scatter plot check detected" if 'scatter' in code_lower else "No visualization of linearity",
                consequences="Linear regression inappropriate if relationship non-linear"
            ))

            checks.append(AssumptionCheck(
                assumption="Residual normality",
                checked='residual' in code_lower and ('hist' in code_lower or 'qqplot' in code_lower),
                met=None,
                evidence="Residual analysis detected" if 'residual' in code_lower else "Residuals not checked",
                consequences="Inference (p-values, confidence intervals) may be unreliable"
            ))

        # Chi-square test assumptions
        if 'chi2' in code_lower or 'chisquare' in code_lower:
            # Expected frequencies should be ≥ 5
            checks.append(AssumptionCheck(
                assumption="Expected frequencies ≥ 5 (for chi-square test)",
                checked='expected' in stdout.lower(),
                met=None,
                evidence="Expected frequencies not reported" if 'expected' not in stdout.lower() else "Expected frequencies shown",
                consequences="Fisher's exact test more appropriate if expected frequencies < 5"
            ))

        # Add plan assumptions if available
        if analysis_plan and analysis_plan.assumptions:
            for assumption in analysis_plan.assumptions:
                checks.append(AssumptionCheck(
                    assumption=assumption,
                    checked=False,  # Not verified
                    met=None,
                    evidence="Assumption from plan but not explicitly checked in code",
                    consequences="Results interpretation should note this limitation"
                ))

        return checks

    def _extract_quality_rating(self, assessment_str: str, judge_str: str) -> str:
        """Extract overall quality rating from assessments."""
        combined = (assessment_str + " " + judge_str).lower()

        if any(word in combined for word in ['excellent', 'outstanding', 'exceptional']):
            return "excellent"
        elif any(word in combined for word in ['poor', 'invalid', 'flawed', 'incorrect']):
            return "poor"
        elif any(word in combined for word in ['good', 'solid', 'appropriate']):
            return "good"
        elif any(word in combined for word in ['fair', 'adequate', 'acceptable']):
            return "fair"
        else:
            return "fair"

    def _extract_findings_from_judge(self, judge_assessment: str) -> List[CritiqueFinding]:
        """Extract structured findings from judge assessment text."""
        findings = []

        # Simple heuristic: look for negative keywords
        lines = judge_assessment.split('\n')
        for line in lines:
            line_lower = line.lower()

            # Critical issues
            if any(word in line_lower for word in ['critical', 'invalid', 'incorrect', 'wrong', 'error']):
                findings.append(CritiqueFinding(
                    severity=CritiqueSeverity.CRITICAL,
                    category=CritiqueCategory.METHODOLOGICAL_ISSUE,
                    title="Critical issue identified",
                    description=line.strip(),
                    impact="Results may be invalid",
                    suggestion="Review and correct the identified issue"
                ))

            # Major concerns
            elif any(word in line_lower for word in ['concern', 'problem', 'issue', 'limitation']):
                findings.append(CritiqueFinding(
                    severity=CritiqueSeverity.MAJOR,
                    category=CritiqueCategory.METHODOLOGICAL_ISSUE,
                    title="Concern identified",
                    description=line.strip(),
                    impact="May affect interpretation",
                    suggestion="Consider addressing this limitation"
                ))

        return findings

    def _infer_confidence(self, quality: str, findings: List[CritiqueFinding]) -> str:
        """Infer confidence in results based on quality and findings."""
        critical_count = sum(1 for f in findings if f.severity == CritiqueSeverity.CRITICAL)
        major_count = sum(1 for f in findings if f.severity == CritiqueSeverity.MAJOR)

        if critical_count > 0:
            return "none"
        elif major_count >= 2:
            return "low"
        elif quality in ["poor", "fair"]:
            return "medium"
        elif quality in ["good", "excellent"]:
            return "high"
        else:
            return "medium"

    def _generate_critique_summary(
        self,
        quality: str,
        findings: List[CritiqueFinding],
        judge_assessment: str
    ) -> str:
        """Generate human-readable summary."""
        summary = f"Analysis quality: {quality}. "

        if findings:
            critical = sum(1 for f in findings if f.severity == CritiqueSeverity.CRITICAL)
            major = sum(1 for f in findings if f.severity == CritiqueSeverity.MAJOR)

            if critical:
                summary += f"{critical} critical issue(s) found. "
            if major:
                summary += f"{major} major concern(s) identified. "

        # Extract key point from judge assessment
        first_line = judge_assessment.split('\n')[0] if judge_assessment else ""
        if first_line and len(first_line) < 200:
            summary += first_line

        return summary

    def _extract_recommendations(self, judge_assessment: str) -> List[str]:
        """Extract recommendations from judge assessment."""
        recommendations = []
        lines = judge_assessment.split('\n')

        in_recommendations = False
        for line in lines:
            if any(word in line.lower() for word in ['recommend', 'suggest', 'should', 'consider']):
                in_recommendations = True
                recommendations.append(line.strip())
            elif in_recommendations and line.strip().startswith('-'):
                recommendations.append(line.strip()[1:].strip())

        return recommendations[:5]  # Top 5

    def _identify_limitations(
        self,
        code: str,
        execution_result: Dict[str, Any],
        analysis_plan: Optional[AnalysisPlan],
        findings: List[CritiqueFinding]
    ) -> List[str]:
        """Identify analysis limitations."""
        limitations = []

        # From plan
        if analysis_plan and analysis_plan.limitations:
            limitations.extend(analysis_plan.limitations)

        # From findings
        for finding in findings:
            if finding.severity in [CritiqueSeverity.CRITICAL, CritiqueSeverity.MAJOR]:
                limitations.append(finding.description)

        # Generic limitations
        if 'cross_val' not in code.lower() and 'train_test_split' not in code.lower():
            if 'model' in code.lower() or 'predict' in code.lower():
                limitations.append("No train/test split or cross-validation performed")

        return list(set(limitations))  # Remove duplicates

    def _extract_score(self, assessment_str: str) -> Optional[float]:
        """Extract numerical score from assessment if present."""
        # Try multiple score patterns for robustness
        score_patterns = [
            r'score[:\s=]+([0-9.]+)',
            r'assessment[:\s=]+([0-9.]+)',
            r'rating[:\s=]+([0-9.]+)',
            r'\b([0-9.]+)\s*/\s*(?:1\.0|1|10)',  # "0.8/1" or "8/10"
            r'quality[:\s=]+([0-9.]+)',
        ]

        for pattern in score_patterns:
            match = re.search(pattern, assessment_str, re.IGNORECASE)
            if match:
                try:
                    score = float(match.group(1))
                    # Normalize if out of 10 scale (e.g., "8/10" → 0.8)
                    if score > 1.0 and score <= 10.0:
                        score = score / 10.0
                    # Validate range
                    if 0.0 <= score <= 1.0:
                        return score
                except (ValueError, IndexError):
                    continue

        return None
