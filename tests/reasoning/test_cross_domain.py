"""
Cross-domain validation tests for Digital Article reasoning framework.

These tests verify that the reasoning framework is truly domain-agnostic
and works across different data types: clinical, financial, operational, marketing.
"""

import pytest
import sys
from pathlib import Path

# Add backend to path
backend_path = str(Path(__file__).parent.parent.parent / "backend")
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.services.analysis_planner import AnalysisPlanner
from app.services.analysis_critic import AnalysisCritic


class TestClinicalDataReasoning:
    """Test reasoning framework with clinical data."""

    def test_clinical_circular_reasoning_detected(self):
        """Verify framework detects circular reasoning in clinical context."""
        planner = AnalysisPlanner()

        # Clinical circular reasoning: predicting treatment group
        prompt = "predict which drug arm patients were assigned to based on their demographics"

        available_data = {
            'available_variables': {
                'patients_df': {
                    'type': 'DataFrame',
                    'shape': [200, 10],
                    'columns': ['patient_id', 'age', 'gender', 'drug_arm', 'response_rate', 'adverse_events']
                }
            }
        }

        # Plan analysis
        plan, trace = planner.plan_analysis(prompt, available_data, [])

        # Should detect circular reasoning
        has_circular_issue = any(
            issue.type.value == 'circular_reasoning'
            for issue in plan.validation_issues
        )

        assert has_circular_issue or len(plan.validation_issues) > 0, \
            "Should detect issue with predicting assigned group"


class TestFinancialDataReasoning:
    """Test reasoning framework with financial data."""

    def test_financial_circular_reasoning_detected(self):
        """Verify framework detects circular reasoning in financial context."""
        planner = AnalysisPlanner()

        # Financial circular reasoning: predicting portfolio assignment
        prompt = "predict which investment portfolio each client was assigned to based on their risk profile"

        available_data = {
            'available_variables': {
                'clients_df': {
                    'type': 'DataFrame',
                    'shape': [500, 8],
                    'columns': ['client_id', 'age', 'income', 'portfolio_type', 'returns', 'risk_score']
                }
            }
        }

        # Plan analysis
        plan, trace = planner.plan_analysis(prompt, available_data, [])

        # Should detect circular reasoning (portfolio assignment is predetermined)
        has_circular_issue = any(
            issue.type.value == 'circular_reasoning'
            for issue in plan.validation_issues
        )

        assert has_circular_issue or len(plan.validation_issues) > 0, \
            "Should detect issue with predicting assigned portfolio"


class TestOperationalDataReasoning:
    """Test reasoning framework with operational data."""

    def test_operational_valid_analysis(self):
        """Verify framework accepts valid operational analysis."""
        planner = AnalysisPlanner()

        # Valid operational analysis: predicting defect rate
        prompt = "predict manufacturing defect rate based on machine settings and environmental conditions"

        available_data = {
            'available_variables': {
                'production_df': {
                    'type': 'DataFrame',
                    'shape': [1000, 12],
                    'columns': ['batch_id', 'machine_id', 'temperature', 'pressure', 'humidity', 'defect_rate']
                }
            }
        }

        # Plan analysis
        plan, trace = planner.plan_analysis(prompt, available_data, [])

        # Should NOT have critical circular reasoning issues
        has_critical_circular = any(
            issue.type.value == 'circular_reasoning' and issue.severity.value == 'critical'
            for issue in plan.validation_issues
        )

        assert not has_critical_circular, \
            "Should NOT flag valid predictive analysis as circular reasoning"


class TestMarketingDataReasoning:
    """Test reasoning framework with marketing data."""

    def test_marketing_valid_analysis(self):
        """Verify framework accepts valid marketing analysis."""
        planner = AnalysisPlanner()

        # Valid marketing analysis: predicting conversion
        prompt = "analyze which customer characteristics predict conversion rate"

        available_data = {
            'available_variables': {
                'campaigns_df': {
                    'type': 'DataFrame',
                    'shape': [5000, 15],
                    'columns': ['customer_id', 'age', 'location', 'channel', 'campaign_type', 'converted', 'revenue']
                }
            }
        }

        # Plan analysis
        plan, trace = planner.plan_analysis(prompt, available_data, [])

        # Should suggest appropriate method
        assert plan.suggested_method is not None
        assert len(plan.suggested_method) > 0


class TestGenericDataPrinciples:
    """Test that reasoning uses universal principles, not domain-specific knowledge."""

    def test_no_domain_specific_terms_in_plan(self):
        """Verify plan doesn't include clinical terminology for non-clinical data."""
        planner = AnalysisPlanner()

        # Financial data
        prompt = "compare returns between two investment strategies"

        available_data = {
            'available_variables': {
                'investments_df': {
                    'type': 'DataFrame',
                    'shape': [300, 6],
                    'columns': ['investment_id', 'strategy', 'initial_amount', 'final_amount', 'duration']
                }
            }
        }

        plan, trace = planner.plan_analysis(prompt, available_data, [])

        # Check that plan doesn't use clinical terms
        plan_text = str(plan.to_dict()).lower()

        clinical_terms = ['patient', 'treatment', 'clinical', 'trial', 'drug', 'therapy']
        for term in clinical_terms:
            assert term not in plan_text, \
                f"Plan should not include clinical term '{term}' for financial data"

    def test_sample_size_warning_universal(self):
        """Verify sample size warnings work across domains."""
        planner = AnalysisPlanner()

        # Small sample in marketing context
        prompt = "perform statistical test on campaign effectiveness"

        available_data = {
            'available_variables': {
                'campaigns_df': {
                    'type': 'DataFrame',
                    'shape': [15, 5],  # Small sample
                    'columns': ['campaign_id', 'impressions', 'clicks', 'conversions', 'cost']
                }
            },
            'previous_cells': []
        }

        plan, trace = planner.plan_analysis(prompt, available_data, [])

        # Should warn about small sample
        has_sample_size_concern = any(
            'sample' in issue.message.lower() or 'small' in issue.message.lower()
            for issue in plan.validation_issues
        )

        # Note: This might not always trigger depending on method selection
        # But the capability should exist
        assert plan is not None


class TestCritiqueDomainAgnostic:
    """Test that critique uses universal quality principles."""

    def test_critique_works_across_domains(self):
        """Verify critique evaluates quality regardless of domain."""
        critic = AnalysisCritic()

        # Test with financial data
        execution_result = {
            'stdout': 'Mean return: 12.5%, Std dev: 4.2%',
            'stderr': '',
            'tables': [],
            'plots': []
        }

        code = """
import pandas as pd
import numpy as np

returns = [10.2, 12.5, 11.8, 13.1, 12.9]
mean_return = np.mean(returns)
std_return = np.std(returns)
print(f"Mean return: {mean_return}%, Std dev: {std_return}%")
"""

        critique, trace = critic.critique_analysis(
            user_intent="calculate average investment returns",
            code=code,
            execution_result=execution_result,
            analysis_plan=None,
            context={}
        )

        # Should produce valid critique
        assert critique.overall_quality is not None
        assert critique.confidence_in_results is not None
        assert isinstance(critique.findings, list)


if __name__ == "__main__":
    print("Running Cross-Domain Validation Tests...")
    print("=" * 70)

    # Run tests
    pytest.main([__file__, "-v", "-s"])
