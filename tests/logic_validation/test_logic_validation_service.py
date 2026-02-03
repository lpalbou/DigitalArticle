"""
Tests for Logic Validation Service (ADR 0004).

Tests the hybrid validation approach:
1. Heuristic checks for obvious issues
2. LLM-as-judge for semantic validation
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from backend.app.services.logic_validation_service import (
    LogicValidationService,
    LogicValidationResult,
    LogicValidationReport,
    IssueSeverity,
)
from backend.app.models.notebook import ExecutionResult, ExecutionStatus


class TestHeuristicChecks:
    """Test deterministic heuristic checks."""
    
    @pytest.fixture
    def mock_llm_service(self):
        """Create a mock LLM service."""
        service = MagicMock()
        service.llm = MagicMock()
        return service
    
    @pytest.fixture
    def validator(self, mock_llm_service):
        """Create a LogicValidationService with mocked LLM."""
        return LogicValidationService(mock_llm_service)
    
    def test_no_output_for_plot_request(self, validator):
        """Detect when plot is requested but not generated."""
        prompt = "Create a bar chart showing sales by region"
        code = "import pandas as pd\ndf = pd.read_csv('data.csv')"
        result = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            stdout="",
            plots=[],
            tables=[],
        )
        
        report = validator._run_heuristic_checks(prompt, code, result)
        
        assert report.result == LogicValidationResult.FAIL
        assert any("plot" in issue.lower() or "visualization" in issue.lower() 
                   for issue in report.issues)
        assert report.categorized_issues, "Heuristic FAIL should categorize issues"
        assert report.categorized_issues[0].severity.value == "high"
    
    def test_no_output_for_table_request(self, validator):
        """Detect when table display is requested but not generated."""
        prompt = "Show me the first 10 rows of the data"
        code = "df = pd.read_csv('data.csv')\nprint(df.head())"
        result = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            stdout="Some output",
            plots=[],
            tables=[],
        )
        
        # Heuristics should not FAIL on debatable presentation choices (print vs display),
        # but may still surface it as a non-blocking note.
        report = validator._run_heuristic_checks(prompt, code, result)
        
        # print() without display() should be flagged
        assert report.result == LogicValidationResult.PASS
        assert any("print" in issue.lower() or "display" in issue.lower() 
                   for issue in report.issues)
        assert report.categorized_issues, "Heuristic notes should categorize issues"
    
    def test_statistical_test_without_pvalue(self, validator):
        """Detect statistical test without p-value in output."""
        prompt = "Perform a t-test to compare group A and group B"
        code = "from scipy import stats\nstats.ttest_ind(a, b)"
        result = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            stdout="Ttest_indResult(statistic=1.23, pvalue=0.05)",  # Has p-value
            plots=[],
            tables=[],
        )
        
        # This should pass - p-value is in output
        report = validator._run_heuristic_checks(prompt, code, result)
        # Heuristics may pass or flag print() issue
        # Key: p-value check should NOT trigger since it's present
    
    def test_successful_plot_generation(self, validator):
        """Pass when plot is requested and generated."""
        prompt = "Create a scatter plot of x vs y"
        code = "import matplotlib.pyplot as plt\nplt.scatter(x, y)\ndisplay(plt.gcf())"
        result = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            stdout="",
            plots=[{"type": "image", "data": "base64..."}],
            tables=[],
        )
        
        report = validator._run_heuristic_checks(prompt, code, result)
        
        # Should pass - plot was generated
        assert report.result == LogicValidationResult.PASS
    
    def test_successful_table_display(self, validator):
        """Pass when table is requested and displayed."""
        prompt = "Display the dataframe"
        code = "display(df, 'Table 1: Data')"
        result = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            stdout="",
            plots=[],
            tables=[{"data": [["a", "b"]], "headers": ["col1", "col2"]}],
        )
        
        report = validator._run_heuristic_checks(prompt, code, result)
        
        assert report.result == LogicValidationResult.PASS


class TestLLMValidation:
    """Test LLM-as-judge validation."""
    
    @pytest.fixture
    def mock_llm_service(self):
        """Create a mock LLM service with async generate."""
        service = MagicMock()
        service.llm = MagicMock()
        return service
    
    @pytest.fixture
    def validator(self, mock_llm_service):
        """Create a LogicValidationService with mocked LLM."""
        return LogicValidationService(mock_llm_service)
    
    def test_parse_pass_response(self, validator):
        """Parse a PASS response from LLM."""
        response = """RESULT: PASS
ISSUES: None
SUGGESTIONS: None
CONFIDENCE: 0.95"""
        
        report = validator._parse_validation_response(response)
        
        assert report.result == LogicValidationResult.PASS
        assert len(report.issues) == 0
        assert report.confidence == 0.95
    
    def test_parse_non_blocking_issues_do_not_fail(self, validator):
        """
        Non-blocking issues (MEDIUM/LOW) should not produce a FAIL.

        Rationale: Logic Validation should focus on plain wrong answers and explicit prompt violations.
        """
        response = """RESULT: FAIL
ISSUES:
- [MEDIUM] Missing Shapiro-Wilk normality test | evidence_code: `stats.ttest_ind(a, b)` | evidence_output: `Ttest_indResult`
- [LOW] Improve variable naming | evidence_code: `mean_value` | evidence_output: `NONE`
SUGGESTIONS:
- Add normality check before t-test
- Rename variables for clarity
CONFIDENCE: 0.85"""

        report = validator._parse_validation_response(
            response,
            code="from scipy import stats\nstats.ttest_ind(a, b)\nmean_value = 1",
            stdout="Ttest_indResult(statistic=1.0, pvalue=0.5)",
        )

        assert report.result == LogicValidationResult.PASS
        assert len(report.issues) == 2
        assert len(report.suggestions) == 2
        assert report.confidence == 0.85
        assert report.categorized_issues, "Parsed issues should include categorized issues"
    
    def test_parse_uncertain_response(self, validator):
        """Parse an ambiguous response as UNCERTAIN."""
        response = """The analysis appears to be correct but I'm not sure about 
the sample size requirements for this test."""
        
        report = validator._parse_validation_response(response)
        
        assert report.result == LogicValidationResult.UNCERTAIN

    def test_parse_severity_tags(self, validator):
        """Parse severity tags [HIGH]/[MEDIUM]/[LOW] into categorized issues."""
        response = """RESULT: FAIL
ISSUES:
- [HIGH] Wrong statistical test used | evidence_code: `stats.ttest_ind(a, b)` | evidence_output: `Ttest_indResult`
- [MEDIUM] Missing normality check | evidence_code: `stats.ttest_ind(a, b)` | evidence_output: `NONE`
- [LOW] Improve variable naming | evidence_code: `mean_value` | evidence_output: `NONE`
SUGGESTIONS:
- Use Mann-Whitney U test instead of t-test
- Add Shapiro-Wilk test before parametric tests
- Rename variables for clarity
CONFIDENCE: 0.80"""

        report = validator._parse_validation_response(
            response,
            code="from scipy import stats\nstats.ttest_ind(a, b)\nmean_value = 1",
            stdout="Ttest_indResult(statistic=1.0, pvalue=0.5)",
        )
        assert report.result == LogicValidationResult.FAIL
        assert len(report.categorized_issues) == 3
        assert report.categorized_issues[0].severity.value == "high"
        assert report.categorized_issues[1].severity.value == "medium"
        assert report.categorized_issues[2].severity.value == "low"
        assert report.categorized_issues[0].suggestion == "Use Mann-Whitney U test instead of t-test"
        # Evidence is preserved for grounding logic correction.
        assert report.categorized_issues[0].evidence_code == "stats.ttest_ind(a, b)"
        assert report.categorized_issues[0].evidence_output == "Ttest_indResult"

    def test_parse_critical_prefix_as_high(self, validator):
        """Treat 'Critical:' as HIGH severity for backward compatibility."""
        response = """RESULT: FAIL
ISSUES:
- **Critical: Group mismatch** - groups do not align with time_to_event assignment | evidence_code: `groups =` | evidence_output: `NONE`
SUGGESTIONS:
- Align group labels with event time generation
CONFIDENCE: 0.70"""

        report = validator._parse_validation_response(response, code="groups = ['A','B']", stdout="")
        assert report.result == LogicValidationResult.FAIL
        assert len(report.categorized_issues) == 1
        assert report.categorized_issues[0].severity.value == "high"

    def test_drops_self_retracted_issue_blocks(self, validator):
        """
        If the validator retracts an issue inside the same block (\"this is NOT an issue\" / \"actually correct\"),
        we must not treat it as a blocker.

        This is a general-purpose robustness guard against incoherent LLM outputs.
        """
        response = """RESULT: FAIL
ISSUES:
- [HIGH] Group assignment is reversed | evidence_code: `groups = ['A']` | evidence_output: `NONE`
  Actually, upon re-examination, the assignment is ACTUALLY CORRECT. This is NOT an issue.
- [LOW] Minor formatting suggestion | evidence_code: `print('ok')` | evidence_output: `NONE`
SUGGESTIONS:
- (retracted)
- (optional)
CONFIDENCE: 0.80"""

        report = validator._parse_validation_response(
            response,
            code="groups = ['A']\nprint('ok')\n",
            stdout="",
        )

        # Self-retracted HIGH should be dropped; remaining LOW should not fail.
        assert report.result == LogicValidationResult.PASS
        assert len(report.categorized_issues) == 1
        assert report.categorized_issues[0].severity.value == "low"

    def test_suggestion_based_retraction_downgrades_high(self, validator):
        """Retractions expressed in SUGGESTIONS should prevent an issue from being a blocker."""
        response = """RESULT: FAIL
ISSUES:
- [HIGH] Wrong mapping | evidence_code: `x = 1` | evidence_output: `NONE`
SUGGESTIONS:
- Upon re-examination, this is NOT an issue. Remove the [HIGH] flag.
CONFIDENCE: 0.80"""

        report = validator._parse_validation_response(response, code="x = 1", stdout="")
        assert report.result == LogicValidationResult.PASS
        assert len(report.categorized_issues) == 1
        assert report.categorized_issues[0].severity.value == "low"

    def test_q_gate_marks_inconsistent_as_uncertain(self, validator):
        """
        If Q1–Q4 say NO blockers but the model also emits a HIGH issue, treat as UNCERTAIN.
        This prevents inconsistent LLM outputs from poisoning correction loops.
        """
        response = """RESULT: FAIL
Q1_FAILED_TO_ANSWER_USER_INTENT: NO | prompt_clause: \"NONE\" | evidence_code: `NONE` | evidence_output: `NONE`
Q2_MISREPRESENTED_USER_INTENT: NO | prompt_clause: \"NONE\" | evidence_code: `NONE` | evidence_output: `NONE`
Q3_STATISTICALLY_INACCURATE: NO | prompt_clause: \"NONE\" | evidence_code: `NONE` | evidence_output: `NONE`
Q4_RULE_VIOLATION: NO | prompt_clause: \"NONE\" | evidence_code: `NONE` | evidence_output: `NONE`
ISSUES:
- [HIGH] Something wrong | evidence_code: `x = 1` | evidence_output: `NONE`
SUGGESTIONS:
- (n/a)
CONFIDENCE: 0.5"""
        report = validator._parse_validation_response(response, code="x = 1", stdout="")
        assert report.result == LogicValidationResult.UNCERTAIN

    def test_comment_only_evidence_code_is_not_sufficient_for_high(self, validator):
        """
        A comment-only evidence_code (starts with '#') should not count as verifiable code evidence.
        If there's no verifiable output evidence either, HIGH must be downgraded (prevents false FAILs).
        """
        response = """RESULT: FAIL
ISSUES:
- [HIGH] Missing hazard ratio verification | evidence_code: `# This implies a Hazard Ratio of 0.5` | evidence_output: `NONE`
SUGGESTIONS:
- (optional)
CONFIDENCE: 0.90"""

        report = validator._parse_validation_response(
            response,
            code="# This implies a Hazard Ratio of 0.5\nx = 1\n",
            stdout="",
        )

        assert report.result == LogicValidationResult.PASS
        assert len(report.categorized_issues) == 1
        assert report.categorized_issues[0].severity.value == "medium"

    def test_evidence_snippet_with_escaped_newlines_is_verified(self, validator):
        """
        Evidence snippets sometimes contain literal "\\n" sequences (escaped newlines) instead of real newlines.
        We normalize these so evidence verification doesn't accidentally downgrade real blockers.
        """
        response = """RESULT: FAIL
Q1_FAILED_TO_ANSWER_USER_INTENT: YES | prompt_clause: "X" | evidence_code: `NONE` | evidence_output: `NONE`
Q2_MISREPRESENTED_USER_INTENT: NO | prompt_clause: N/A | evidence_code: `NONE` | evidence_output: `NONE`
Q3_STATISTICALLY_INACCURATE: NO | prompt_clause: N/A | evidence_code: `NONE` | evidence_output: `NONE`
Q4_RULE_VIOLATION: NO | prompt_clause: N/A | evidence_code: `NONE` | evidence_output: `NONE`
ISSUES:
- [HIGH] Missing required deliverable | prompt_clause: "X" | evidence_code: `a = 1\\nb = 2` | evidence_output: `line1\\nline2`
SUGGESTIONS:
- Add the deliverable
CONFIDENCE: 0.90"""

        report = validator._parse_validation_response(
            response,
            code="a = 1\nb = 2\nprint('ok')\n",
            stdout="line1\nline2\n",
        )

        assert any(ci.severity == IssueSeverity.HIGH for ci in report.categorized_issues)
        assert report.result == LogicValidationResult.FAIL
    
    @pytest.mark.asyncio
    async def test_full_validation_with_mock_llm(self, mock_llm_service):
        """Test full validation flow with mocked LLM."""
        # Mock LLM response
        mock_response = MagicMock()
        mock_response.content = """RESULT: PASS
ISSUES: None
SUGGESTIONS: None
CONFIDENCE: 0.90"""
        
        mock_llm_service.llm.agenerate = AsyncMock(return_value=mock_response)
        
        validator = LogicValidationService(mock_llm_service)
        
        prompt = "Calculate the mean of the data"
        code = "mean_value = df['value'].mean()\ndisplay(mean_value, 'Mean Value')"
        result = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            stdout="",
            plots=[],
            tables=[{"data": [[42.5]], "headers": ["Mean Value"]}],
        )
        
        report = await validator.validate(prompt, code, result)
        
        # Should pass both heuristics and LLM validation
        assert report.result == LogicValidationResult.PASS

    def test_validation_user_prompt_includes_table_summary(self, validator):
        """
        The validator must receive schema-first table evidence, otherwise it over-indexes on truncated stdout
        (pandas '...') and hallucinates missing columns/values.
        """
        result = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            stdout="Table 2: Summary Statistics by Group:\n     Group  Age_mean  ...  Event_Observed_sum\n",  # truncated repr
            plots=[],
            tables=[
                {
                    "name": "Table 2: Summary Statistics by Group",
                    "shape": [2, 3],
                    "columns": ["Group", "Time_to_Event_median", "Event_Observed_mean"],
                    "data": [
                        {"Group": "Chemo", "Time_to_Event_median": 7.0, "Event_Observed_mean": 0.8},
                        {"Group": "ImmunoX", "Time_to_Event_median": 14.0, "Event_Observed_mean": 0.8},
                    ],
                    "source": "display",
                }
            ],
        )
        user_prompt = validator._build_validation_user_prompt(
            prompt="Generate a dataset",
            code="df = ...",
            result=result,
            context={},
        )
        assert "TABLES SUMMARY (schema-first" in user_prompt
        assert "Time_to_Event_median" in user_prompt


class TestValidationReport:
    """Test LogicValidationReport structure."""
    
    def test_report_structure(self):
        """Report contains all expected fields."""
        report = LogicValidationReport(
            result=LogicValidationResult.FAIL,
            issues=["Issue 1", "Issue 2"],
            suggestions=["Fix 1"],
            confidence=0.8,
            validation_type="llm",
        )
        
        assert report.result == LogicValidationResult.FAIL
        assert len(report.issues) == 2
        assert len(report.suggestions) == 1
        assert report.confidence == 0.8
        assert report.validation_type == "llm"
        assert report.code_fix is None  # Optional field
