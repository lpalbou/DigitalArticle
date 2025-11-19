"""
Test Execution Insights Extractor

Tests the extraction of rich insights from execution results for methodology generation.
"""

import pytest
import pandas as pd
import numpy as np
from backend.app.services.execution_insights_extractor import ExecutionInsightsExtractor


def test_extract_table_insights():
    """Test extraction of table insights with statistics."""
    # Create sample table data
    table_data = {
        'label': 'Table 1: Patient Demographics',
        'source': 'display',
        'shape': [50, 4],
        'columns': ['AGE', 'SEX', 'TUMOR_SIZE', 'ARM'],
        'data': [
            {'AGE': 52, 'SEX': 'F', 'TUMOR_SIZE': 4.2, 'ARM': 1},
            {'AGE': 48, 'SEX': 'F', 'TUMOR_SIZE': 3.8, 'ARM': 0},
            {'AGE': 61, 'SEX': 'M', 'TUMOR_SIZE': 5.1, 'ARM': 1},
        ]
    }

    tables = [table_data]
    insights = ExecutionInsightsExtractor._extract_table_insights(tables)

    assert len(insights) == 1
    assert insights[0]['label'] == 'Table 1: Patient Demographics'
    assert insights[0]['shape'] == [50, 4]
    assert 'AGE' in insights[0]['columns']
    assert 'statistics' in insights[0]
    # Should have calculated statistics for numeric columns
    if insights[0]['statistics']:
        assert 'AGE' in insights[0]['statistics'] or 'TUMOR_SIZE' in insights[0]['statistics']


def test_extract_plot_metadata():
    """Test extraction of plot metadata from plots list."""
    plots = [
        {'label': 'Figure 1: Age Distribution', 'source': 'display', 'data': 'base64data'},
        {'label': 'Figure 2: Treatment Response', 'source': 'display', 'data': 'base64data'},
    ]

    metadata = ExecutionInsightsExtractor._extract_plot_metadata(plots)

    assert len(metadata) == 2
    assert metadata[0]['label'] == 'Figure 1: Age Distribution'
    assert metadata[1]['label'] == 'Figure 2: Treatment Response'
    assert metadata[0]['source'] == 'display'


def test_extract_statistical_findings():
    """Test extraction of statistical findings from stdout."""
    stdout = """
    Analysis Results:
    Mean age: 52.3 years
    Standard deviation: 8.7
    p-value: 0.002
    correlation: 0.45
    accuracy: 0.89
    """

    findings = ExecutionInsightsExtractor._extract_statistical_findings(stdout)

    # Should find some statistical values
    assert len(findings) > 0
    stat_types = [f['type'] for f in findings]
    assert 'mean' in stat_types or 'p_value' in stat_types


def test_extract_code_insights():
    """Test extraction of insights from Python code using AST."""
    code = """
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy import stats

df = pd.read_csv('data.csv')
mean_val = df['AGE'].mean()
result = stats.ttest_ind(group1, group2)
plt.hist(df['AGE'])
"""

    insights = ExecutionInsightsExtractor._extract_code_insights(code)

    assert 'pandas' in insights['libraries_imported'] or 'pd' in str(insights)
    assert 'numpy' in insights['libraries_imported'] or 'np' in str(insights)
    # Should detect common methods
    methods = insights['methods_called']
    assert len(methods) > 0


def test_format_for_methodology_prompt():
    """Test formatting of insights for methodology prompt."""
    insights = {
        'tables': [
            {
                'label': 'Table 1: Patient Data',
                'shape': [50, 4],
                'columns': ['AGE', 'SEX', 'TUMOR_SIZE', 'ARM'],
                'statistics': {
                    'AGE': {'mean': 52.3, 'std': 8.7}
                }
            }
        ],
        'plots': [
            {'label': 'Figure 1: Age Distribution', 'source': 'display'}
        ],
        'statistical_findings': [
            {'type': 'p_value', 'value': '0.002'}
        ],
        'code_insights': {
            'libraries_imported': ['pandas', 'numpy'],
            'methods_called': ['mean', 'hist']
        }
    }

    formatted = ExecutionInsightsExtractor.format_for_methodology_prompt(insights)

    # Should contain structured sections
    assert '## TABLES GENERATED:' in formatted
    assert 'Table 1: Patient Data' in formatted
    assert '50 rows' in formatted
    assert '## FIGURES GENERATED:' in formatted
    assert 'Figure 1: Age Distribution' in formatted
    assert '## STATISTICAL FINDINGS:' in formatted


def test_extract_insights_integration():
    """Test full insights extraction pipeline."""
    # Create mock execution result
    class MockResult:
        def __init__(self):
            self.tables = [{
                'label': 'Table 1: Test Data',
                'source': 'display',
                'shape': [10, 3],
                'columns': ['A', 'B', 'C'],
                'data': [{'A': 1, 'B': 2, 'C': 3}]
            }]
            self.plots = [
                {'label': 'Figure 1: Test Plot', 'source': 'display'}
            ]
            self.stdout = "Mean value: 15.3\np-value: 0.001"

    code = """
import pandas as pd
df = pd.read_csv('test.csv')
mean_val = df['A'].mean()
"""

    result = MockResult()
    insights = ExecutionInsightsExtractor.extract_insights(result, code, None)

    # Should have extracted all types of insights
    assert 'tables' in insights
    assert 'plots' in insights
    assert 'statistical_findings' in insights
    assert 'code_insights' in insights
    assert 'summary' in insights

    # Tables should have insights
    assert len(insights['tables']) > 0
    assert insights['tables'][0]['label'] == 'Table 1: Test Data'

    # Plots should have metadata
    assert len(insights['plots']) > 0
    assert insights['plots'][0]['label'] == 'Figure 1: Test Plot'

    # Should have found statistical findings in stdout
    assert len(insights['statistical_findings']) > 0


def test_extract_insights_handles_empty_results():
    """Test that extractor handles empty execution results gracefully."""
    class EmptyResult:
        def __init__(self):
            self.tables = []
            self.plots = []
            self.stdout = ""

    result = EmptyResult()
    insights = ExecutionInsightsExtractor.extract_insights(result, "", None)

    # Should return valid structure even with no data
    assert 'tables' in insights
    assert 'plots' in insights
    assert 'statistical_findings' in insights
    assert insights['tables'] == []
    assert insights['plots'] == []


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
