"""
Analysis Planning Service - Universal Reasoning Framework

This service implements domain-agnostic critical thinking for data analysis.
Before generating code, it reasons about:
- What the user is trying to learn
- What variables are appropriate
- Whether the analysis makes logical sense
- What assumptions are being made
- What potential issues exist

Key principle: All reasoning is based on universal logical principles,
not domain-specific knowledge. Works for clinical, financial, operational,
marketing, or any other type of data analysis.
"""

import logging
import json
import re
from typing import Dict, Any, List, Optional, Tuple
from abstractcore import BasicSession, create_llm

from ..models.analysis_plan import (
    AnalysisPlan,
    LogicalIssue,
    IssueSeverity,
    IssueType,
    ReasoningStep,
    ReasoningTrace
)

logger = logging.getLogger(__name__)


class AnalysisPlanner:
    """
    Plans data analysis using domain-agnostic reasoning.

    Uses multi-turn LLM reasoning to:
    1. Clarify user intent
    2. Identify appropriate variables
    3. Validate logical coherence
    4. Select appropriate methods
    5. Flag potential issues
    """

    def __init__(self, llm_provider: str = "anthropic", llm_model: str = "claude-haiku-4-5"):
        """
        Initialize planner with LLM for reasoning.

        Args:
            llm_provider: LLM provider (anthropic, openai, etc.)
            llm_model: Specific model to use for reasoning
        """
        self.llm_provider = llm_provider
        self.llm_model = llm_model
        self.llm = create_llm(llm_provider, model=llm_model)

    def plan_analysis(
        self,
        user_prompt: str,
        available_data: Dict[str, Any],
        previous_cells: Optional[List[Dict[str, Any]]] = None
    ) -> Tuple[AnalysisPlan, ReasoningTrace]:
        """
        Create analysis plan using multi-turn reasoning.

        Args:
            user_prompt: User's natural language request
            available_data: Dictionary of available variables with their info
            previous_cells: Context from previous cells in notebook

        Returns:
            Tuple of (AnalysisPlan, ReasoningTrace)
        """
        logger.info(f"📋 Planning analysis for prompt: {user_prompt[:100]}...")

        # Create reasoning session for multi-turn coherence
        session = BasicSession(
            self.llm,
            system_prompt=self._build_planning_system_prompt()
        )

        reasoning_trace = ReasoningTrace(
            steps=[],
            final_plan=None,  # Will be set later
            total_reasoning_time_ms=0,
            llm_provider=self.llm_provider,
            llm_model=self.llm_model
        )

        import time
        start_time = time.time()

        try:
            # Step 1: Clarify intent
            intent_step = self._clarify_intent(session, user_prompt, previous_cells)
            reasoning_trace.add_step(intent_step)

            # Step 2: Identify variables
            variables_step = self._identify_variables(
                session,
                user_prompt,
                available_data,
                intent_step
            )
            reasoning_trace.add_step(variables_step)

            # Step 3: Validate logical coherence
            validation_step = self._validate_logical_coherence(
                session,
                user_prompt,
                available_data,
                variables_step
            )
            reasoning_trace.add_step(validation_step)

            # Step 4: Select method
            method_step = self._select_method(
                session,
                intent_step,
                variables_step,
                available_data
            )
            reasoning_trace.add_step(method_step)

            # Step 5: Synthesize into analysis plan
            plan = self._synthesize_plan(
                user_prompt,
                intent_step,
                variables_step,
                validation_step,
                method_step,
                available_data
            )

            reasoning_trace.final_plan = plan
            reasoning_trace.total_reasoning_time_ms = (time.time() - start_time) * 1000

            logger.info(
                f"✅ Planning complete ({reasoning_trace.total_reasoning_time_ms:.0f}ms): "
                f"{plan.suggested_method} | "
                f"{len(plan.validation_issues)} issues found"
            )

            return plan, reasoning_trace

        except Exception as e:
            logger.error(f"❌ Planning failed: {e}")
            # Return a minimal plan that allows execution to proceed
            fallback_plan = AnalysisPlan(
                user_intent=user_prompt,
                research_question=user_prompt,
                analysis_type="exploratory",
                suggested_method="proceed with caution",
                method_rationale="Planning failed, proceeding with direct code generation",
                validation_issues=[
                    LogicalIssue(
                        severity=IssueSeverity.WARNING,
                        type=IssueType.MISSING_ASSUMPTIONS,
                        message="Planning phase failed",
                        explanation=f"Analysis planning encountered an error: {str(e)}",
                        suggestion="Review generated code carefully"
                    )
                ]
            )
            reasoning_trace.final_plan = fallback_plan
            return fallback_plan, reasoning_trace

    def _build_planning_system_prompt(self) -> str:
        """Build system prompt for analysis planning reasoning."""
        return """You are an analytical reasoning assistant that helps plan data analysis using critical thinking and logical validation.

Your role is to reason about analysis requests BEFORE any code is written, using domain-agnostic logical principles that work for any type of data (clinical, financial, operational, marketing, etc.).

CORE REASONING FRAMEWORK:

1. CLARIFY INTENT
   - What question is the user trying to answer?
   - What is the goal: explore, predict, compare, test, quantify?
   - What would constitute a successful answer?

2. IDENTIFY VARIABLES
   - What is the TARGET/OUTCOME (what we're trying to explain/understand)?
   - What are PREDICTORS/INPUTS (what might influence the outcome)?
   - What DERIVED variables might be needed?

3. VALIDATE LOGICAL COHERENCE
   - Does this analysis make logical sense?
   - Are there circular reasoning issues?
   - Do the requested variables exist?
   - Is there temporal logic (cause before effect)?

4. SELECT METHOD
   - What analytical approach fits this question and data type?
   - What assumptions does this method make?
   - What are alternatives?

CRITICAL THINKING PRINCIPLES:

✓ QUESTION ASSUMPTIONS: Don't accept the request at face value
✓ CHECK COHERENCE: Does the analysis logic make sense?
✓ IDENTIFY CIRCULARITY: Watch for predicting X from X
✓ VALIDATE DATA: Do variables exist? Are they appropriate?
✓ NOTE LIMITATIONS: What could go wrong?
✓ SUGGEST IMPROVEMENTS: How could this be better?

You respond with structured JSON following the requested format."""

    def _clarify_intent(
        self,
        session: BasicSession,
        user_prompt: str,
        previous_cells: Optional[List[Dict]] = None
    ) -> ReasoningStep:
        """Step 1: Clarify what the user is trying to learn."""

        context = ""
        if previous_cells:
            context = "\n\nPREVIOUS ANALYSIS CONTEXT:\n"
            for i, cell in enumerate(previous_cells, 1):  # All previous cells - no truncation
                context += f"Step {i}: {cell.get('prompt', 'N/A')}\n"  # Full prompt - no truncation

        prompt = f"""Analyze this data analysis request and clarify the user's intent:

USER REQUEST: {user_prompt}{context}

Respond with JSON:
{{
    "intent": "What the user is trying to learn/discover",
    "research_question": "The specific question being answered",
    "analysis_type": "exploration|prediction|comparison|hypothesis_test|quantification",
    "success_criteria": "What would make this analysis successful",
    "reasoning": "Your reasoning about the intent"
}}

Focus on WHAT they want to learn, not HOW to code it."""

        response = session.generate(prompt)

        try:
            parsed = json.loads(response.content)
        except:
            # Fallback parsing
            parsed = {
                "intent": user_prompt,
                "research_question": user_prompt,
                "analysis_type": "exploratory",
                "success_criteria": "Generate relevant insights",
                "reasoning": "Could not parse structured response"
            }

        return ReasoningStep(
            step_number=1,
            step_type="intent_clarification",
            prompt=prompt,
            response=response.content,
            reasoning=parsed.get("reasoning", "Intent clarified")
        )

    def _identify_variables(
        self,
        session: BasicSession,
        user_prompt: str,
        available_data: Dict[str, Any],
        intent_step: ReasoningStep
    ) -> ReasoningStep:
        """Step 2: Identify target and predictor variables."""

        # Format available data for LLM
        data_summary = self._format_available_data(available_data)

        prompt = f"""Based on the user's intent, identify the appropriate variables for analysis:

USER REQUEST: {user_prompt}

CLARIFIED INTENT: {intent_step.response}

AVAILABLE DATA:
{data_summary}

CRITICAL: Identify variables that ACTUALLY EXIST in the data above.

Respond with JSON:
{{
    "target_variable": "The outcome/dependent variable (what we're trying to explain/predict) - must be specific column/variable name or null",
    "predictor_variables": ["List of input/independent variables - must be actual column names"],
    "derived_variables": ["Variables that need to be created (e.g., 'age_group from AGE', 'category from STATUS', 'rate from COUNT and TIME')"],
    "rationale": "Why these variables are appropriate for the intent",
    "warnings": ["Any concerns about variable selection"]
}}

IMPORTANT CHECKS:
1. Does the target variable make sense for this question?
2. Are predictors available BEFORE the target would be known?
3. If variables don't exist, how can they be derived?"""

        response = session.generate(prompt)

        try:
            parsed = json.loads(response.content)
        except:
            parsed = {
                "target_variable": None,
                "predictor_variables": [],
                "derived_variables": [],
                "rationale": "Could not parse response",
                "warnings": []
            }

        return ReasoningStep(
            step_number=2,
            step_type="variable_identification",
            prompt=prompt,
            response=response.content,
            reasoning=parsed.get("rationale", "Variables identified")
        )

    def _validate_logical_coherence(
        self,
        session: BasicSession,
        user_prompt: str,
        available_data: Dict[str, Any],
        variables_step: ReasoningStep
    ) -> ReasoningStep:
        """Step 3: Validate logical coherence of the proposed analysis."""

        prompt = f"""Critically evaluate the logical coherence of this analysis plan:

USER REQUEST: {user_prompt}

PROPOSED VARIABLES: {variables_step.response}

AVAILABLE DATA: {self._format_available_data(available_data)}

Perform CRITICAL THINKING checks:

1. CIRCULAR REASONING CHECK:
   - Is the target variable something that should be PREDICTABLE from the predictors?
   - Red flag: Predicting group assignment, experimental condition, or other externally-assigned labels
   - Red flag: Predicting cause from effect

2. DATA EXISTENCE CHECK:
   - Do all proposed variables actually exist in available data?
   - If not, can they be reasonably derived?

3. TEMPORAL LOGIC CHECK:
   - Are we predicting future from past (OK) or past from future (BAD)?
   - Do predictors come before outcome?

4. RELATIONSHIP PLAUSIBILITY CHECK:
   - Does it make logical sense to analyze this relationship?
   - Are we analyzing something trivial or tautological?

Respond with JSON:
{{
    "coherence_score": "high|medium|low",
    "logical_issues": [
        {{
            "issue_type": "circular_reasoning|data_mismatch|temporal_logic|implausible_relationship",
            "severity": "critical|warning|info",
            "description": "What the issue is",
            "affected_variables": ["variables involved"],
            "suggestion": "How to fix"
        }}
    ],
    "coherence_assessment": "Overall assessment of logical coherence"
}}

Be a CRITICAL THINKER - flag issues even if request seems straightforward."""

        response = session.generate(prompt)

        try:
            parsed = json.loads(response.content)
        except:
            parsed = {
                "coherence_score": "medium",
                "logical_issues": [],
                "coherence_assessment": "Could not parse validation response"
            }

        return ReasoningStep(
            step_number=3,
            step_type="logical_validation",
            prompt=prompt,
            response=response.content,
            reasoning=parsed.get("coherence_assessment", "Validation complete")
        )

    def _select_method(
        self,
        session: BasicSession,
        intent_step: ReasoningStep,
        variables_step: ReasoningStep,
        available_data: Dict[str, Any]
    ) -> ReasoningStep:
        """Step 4: Select appropriate analytical method."""

        # Determine data characteristics
        data_info = self._analyze_data_characteristics(available_data)

        prompt = f"""Select the appropriate analytical method for this analysis:

INTENT: {intent_step.response}

VARIABLES: {variables_step.response}

DATA CHARACTERISTICS:
{json.dumps(data_info, indent=2)}

Select method based on:
- Analysis type (exploration, prediction, comparison, etc.)
- Data types (continuous, categorical, mixed)
- Sample size
- Number of variables

Respond with JSON:
{{
    "suggested_method": "Specific method name (e.g., 'logistic regression', 't-test', 'random forest')",
    "method_rationale": "Why this method is appropriate",
    "assumptions": ["Key assumptions this method makes"],
    "alternatives": ["Other valid methods"],
    "sample_size_adequate": true|false,
    "data_requirements": ["What the data needs (e.g., 'normality', 'independence')"]
}}

Be practical - consider sample size and complexity."""

        response = session.generate(prompt)

        try:
            parsed = json.loads(response.content)
        except:
            parsed = {
                "suggested_method": "exploratory analysis",
                "method_rationale": "Could not parse method selection",
                "assumptions": [],
                "alternatives": [],
                "sample_size_adequate": True,
                "data_requirements": []
            }

        return ReasoningStep(
            step_number=4,
            step_type="method_selection",
            prompt=prompt,
            response=response.content,
            reasoning=parsed.get("method_rationale", "Method selected")
        )

    def _synthesize_plan(
        self,
        user_prompt: str,
        intent_step: ReasoningStep,
        variables_step: ReasoningStep,
        validation_step: ReasoningStep,
        method_step: ReasoningStep,
        available_data: Dict[str, Any]
    ) -> AnalysisPlan:
        """Synthesize reasoning steps into structured analysis plan."""

        # Parse reasoning step responses
        try:
            intent_data = json.loads(intent_step.response)
            variables_data = json.loads(variables_step.response)
            validation_data = json.loads(validation_step.response)
            method_data = json.loads(method_step.response)
        except:
            # Fallback if parsing fails
            logger.warning("Failed to parse reasoning steps, using fallback plan")
            intent_data = {"intent": user_prompt, "research_question": user_prompt, "analysis_type": "exploratory"}
            variables_data = {"target_variable": None, "predictor_variables": [], "derived_variables": []}
            validation_data = {"logical_issues": []}
            method_data = {"suggested_method": "exploratory", "method_rationale": "Fallback method", "assumptions": []}

        # Convert logical issues to LogicalIssue models
        validation_issues = []
        for issue_data in validation_data.get("logical_issues", []):
            try:
                issue = LogicalIssue(
                    severity=IssueSeverity(issue_data.get("severity", "warning")),
                    type=self._map_issue_type(issue_data.get("issue_type", "missing_assumptions")),
                    message=issue_data.get("description", "Unknown issue"),
                    explanation=issue_data.get("description", ""),
                    suggestion=issue_data.get("suggestion", "Review analysis approach"),
                    affected_variables=issue_data.get("affected_variables", [])
                )
                validation_issues.append(issue)
            except Exception as e:
                logger.warning(f"Failed to parse issue: {e}")

        # Determine if user review required
        requires_review = any(
            issue.severity == IssueSeverity.CRITICAL
            for issue in validation_issues
        )

        # Build plan
        plan = AnalysisPlan(
            user_intent=intent_data.get("intent", user_prompt),
            research_question=intent_data.get("research_question", user_prompt),
            analysis_type=intent_data.get("analysis_type", "exploratory"),
            target_variable=variables_data.get("target_variable"),
            predictor_variables=variables_data.get("predictor_variables", []),
            derived_variables=variables_data.get("derived_variables", []),
            suggested_method=method_data.get("suggested_method", "exploratory analysis"),
            method_rationale=method_data.get("method_rationale", ""),
            alternative_methods=method_data.get("alternatives", []),
            assumptions=method_data.get("assumptions", []),
            limitations=self._infer_limitations(validation_data, method_data, available_data),
            confounders=[],  # Could be enhanced in future
            data_requirements=method_data.get("data_requirements", []),
            data_quality_checks=["check for missing values", "check for outliers"],
            validation_issues=validation_issues,
            confidence_level=self._assess_confidence(validation_data, method_data),
            requires_user_review=requires_review
        )

        return plan

    def _format_available_data(self, available_data: Dict[str, Any]) -> str:
        """Format available data for LLM consumption."""
        if not available_data or 'available_variables' not in available_data:
            return "No data available"

        formatted = []
        for var_name, var_info in available_data['available_variables'].items():
            formatted.append(f"  • {var_name}: {var_info}")

        return "\n".join(formatted)

    def _analyze_data_characteristics(self, available_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze data characteristics for method selection."""

        # Extract sample size - try multiple patterns for robustness
        sample_size = None
        for var_info in available_data.get('available_variables', {}).values():
            info_str = str(var_info)
            # Try multiple patterns: "50 rows", "n=100", "observations: 200", etc.
            patterns = [
                r'(\d+)\s+(rows|observations|samples|records|instances)',
                r'n\s*=\s*(\d+)',
                r'size[:\s]+(\d+)',
                r'\((\d+)\s+rows'
            ]
            for pattern in patterns:
                match = re.search(pattern, info_str, re.IGNORECASE)
                if match:
                    # Extract number from first or second group depending on pattern
                    sample_size = int(match.group(1))
                    break
            if sample_size:
                break

        return {
            "sample_size": sample_size,
            "num_variables": len(available_data.get('available_variables', {})),
            "has_dataframes": any('DataFrame' in str(v) for v in available_data.get('available_variables', {}).values())
        }

    def _map_issue_type(self, issue_type_str: str) -> IssueType:
        """Map string to IssueType enum."""
        mapping = {
            "circular_reasoning": IssueType.CIRCULAR_REASONING,
            "data_mismatch": IssueType.DATA_MISMATCH,
            "temporal_logic": IssueType.TEMPORAL_LOGIC,
            "implausible_relationship": IssueType.METHOD_MISMATCH,
            "sample_size": IssueType.SAMPLE_SIZE
        }
        return mapping.get(issue_type_str, IssueType.MISSING_ASSUMPTIONS)

    def _infer_limitations(
        self,
        validation_data: Dict,
        method_data: Dict,
        available_data: Dict
    ) -> List[str]:
        """Infer analysis limitations from reasoning."""
        limitations = []

        # Sample size limitations
        data_chars = self._analyze_data_characteristics(available_data)
        if data_chars['sample_size'] and data_chars['sample_size'] < 30:
            limitations.append(f"Small sample size (n={data_chars['sample_size']}) limits statistical power")

        # Method-specific limitations
        if not method_data.get("sample_size_adequate", True):
            limitations.append("Sample size may be inadequate for chosen method")

        # Logical issues as limitations
        for issue in validation_data.get("logical_issues", []):
            if issue.get("severity") in ["critical", "warning"]:
                limitations.append(f"{issue.get('description')}")

        return limitations

    def _assess_confidence(self, validation_data: Dict, method_data: Dict) -> str:
        """Assess overall confidence in analysis plan."""
        coherence = validation_data.get("coherence_score", "medium")
        has_critical = any(
            issue.get("severity") == "critical"
            for issue in validation_data.get("logical_issues", [])
        )

        if has_critical:
            return "low"
        elif coherence == "high" and method_data.get("sample_size_adequate", True):
            return "high"
        else:
            return "medium"
