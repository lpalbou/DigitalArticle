"""
Comprehensive tests for pandas DataFrame parsing from stdout.

Tests the new backend table parser that extracts pandas DataFrames
from console output and converts them to interactive TableData format.
"""

import pytest
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from app.services.execution_service import ExecutionService


class TestPandasStdoutParser:
    """Test suite for parsing pandas DataFrames from stdout."""

    @pytest.fixture
    def execution_service(self):
        """Create execution service instance."""
        return ExecutionService()

    def test_simple_dataframe_parsing(self, execution_service):
        """Test parsing a simple pandas DataFrame from print() output."""
        code = """
import pandas as pd
import numpy as np

df = pd.DataFrame({
    'STUDYID': ['TNBC_2023'] * 3,
    'ARM': ['TREATMENT', 'CONTROL', 'TREATMENT'],
    'AGE': [45, 52, 38]
})

print(df)
"""
        result = execution_service.execute_code(code, "test_cell_1", "test_notebook")

        # Should have stdout
        assert result.stdout, "Should have stdout output"

        # Should have parsed tables
        assert len(result.tables) > 0, "Should have parsed at least one table"

        # Check table structure
        parsed_tables = [t for t in result.tables if t.get('source') == 'stdout']
        assert len(parsed_tables) >= 1, "Should have at least one stdout table"

        table = parsed_tables[0]
        assert table['columns'], "Should have columns"
        assert table['data'], "Should have data rows"
        assert table['shape'], "Should have shape"

        print(f"✅ Parsed {len(parsed_tables)} table(s) from stdout")
        print(f"   Columns: {table['columns']}")
        print(f"   Shape: {table['shape']}")

    def test_dataframe_head_parsing(self, execution_service):
        """Test parsing df.head() output."""
        code = """
import pandas as pd

df = pd.DataFrame({
    'COL_A': list(range(20)),
    'COL_B': list(range(20, 40)),
    'COL_C': ['value_' + str(i) for i in range(20)]
})

print(df.head())
"""
        result = execution_service.execute_code(code, "test_cell_2", "test_notebook")

        parsed_tables = [t for t in result.tables if t.get('source') == 'stdout']
        assert len(parsed_tables) >= 1, "Should parse df.head() output"

        table = parsed_tables[0]
        assert 'COL_A' in table['columns'], "Should have COL_A column"
        assert 'COL_B' in table['columns'], "Should have COL_B column"
        assert 'COL_C' in table['columns'], "Should have COL_C column"

        print(f"✅ Parsed df.head() - {len(table['data'])} rows")

    def test_wide_dataframe_with_ellipsis(self, execution_service):
        """Test parsing wide DataFrames with ... truncation."""
        code = """
import pandas as pd
import numpy as np

# Create wide DataFrame (many columns)
df = pd.DataFrame({
    f'COL_{i}': np.random.randint(0, 100, 3) for i in range(20)
})

print(df)  # Will show ... for truncated columns
"""
        result = execution_service.execute_code(code, "test_cell_3", "test_notebook")

        parsed_tables = [t for t in result.tables if t.get('source') == 'stdout']
        assert len(parsed_tables) >= 1, "Should parse wide DataFrame"

        table = parsed_tables[0]
        print(f"✅ Parsed wide DataFrame - {len(table['columns'])} columns visible")

    def test_dataframe_to_string(self, execution_service):
        """Test parsing df.to_string() output (no truncation)."""
        code = """
import pandas as pd

df = pd.DataFrame({
    'NAME': ['Alice', 'Bob', 'Charlie'],
    'AGE': [25, 30, 35],
    'CITY': ['NYC', 'LA', 'Chicago']
})

print(df.to_string())
"""
        result = execution_service.execute_code(code, "test_cell_4", "test_notebook")

        parsed_tables = [t for t in result.tables if t.get('source') == 'stdout']
        assert len(parsed_tables) >= 1, "Should parse to_string() output"

        table = parsed_tables[0]
        assert len(table['data']) == 3, "Should have 3 rows"
        assert 'NAME' in table['columns'], "Should have NAME column"

        print(f"✅ Parsed df.to_string() - complete table without truncation")

    def test_multiple_dataframes_in_stdout(self, execution_service):
        """Test parsing multiple DataFrames from same stdout."""
        code = """
import pandas as pd

df1 = pd.DataFrame({
    'A': [1, 2, 3],
    'B': [4, 5, 6]
})

df2 = pd.DataFrame({
    'X': [10, 20, 30],
    'Y': [40, 50, 60]
})

print("First DataFrame:")
print(df1)

print("\\nSecond DataFrame:")
print(df2)
"""
        result = execution_service.execute_code(code, "test_cell_5", "test_notebook")

        parsed_tables = [t for t in result.tables if t.get('source') == 'stdout']

        # Should parse both tables
        assert len(parsed_tables) >= 2, f"Should parse both DataFrames, got {len(parsed_tables)}"

        print(f"✅ Parsed {len(parsed_tables)} DataFrames from single stdout")

    def test_mixed_stdout_with_text_and_dataframe(self, execution_service):
        """Test parsing when stdout contains both text and DataFrames."""
        code = """
import pandas as pd

print("Analysis starting...")
print("Loading data...")

df = pd.DataFrame({
    'METRIC': ['Mean', 'Median', 'Std'],
    'VALUE': [15.3, 14.5, 2.1]
})

print("\\nResults:")
print(df)

print("\\nAnalysis complete!")
"""
        result = execution_service.execute_code(code, "test_cell_6", "test_notebook")

        # Should have full stdout
        assert "Analysis starting" in result.stdout
        assert "Analysis complete" in result.stdout

        # Should also have parsed table
        parsed_tables = [t for t in result.tables if t.get('source') == 'stdout']
        assert len(parsed_tables) >= 1, "Should parse DataFrame even with surrounding text"

        table = parsed_tables[0]
        assert 'METRIC' in table['columns']
        assert 'VALUE' in table['columns']

        print(f"✅ Successfully parsed DataFrame from mixed stdout")

    def test_dataframe_with_float_values(self, execution_service):
        """Test parsing DataFrames with floating point numbers."""
        code = """
import pandas as pd

df = pd.DataFrame({
    'MEASUREMENT': ['Height', 'Weight', 'BMI'],
    'VALUE': [175.5, 70.3, 22.9],
    'UNIT': ['cm', 'kg', '']
})

print(df)
"""
        result = execution_service.execute_code(code, "test_cell_7", "test_notebook")

        parsed_tables = [t for t in result.tables if t.get('source') == 'stdout']
        assert len(parsed_tables) >= 1, "Should parse DataFrame with floats"

        table = parsed_tables[0]
        # Check that numeric values were preserved
        assert table['data'], "Should have data"

        print(f"✅ Parsed DataFrame with float values")

    def test_source_attribution(self, execution_service):
        """Test that tables are correctly marked with source='stdout' vs source='variable'."""
        code = """
import pandas as pd

# This DataFrame is assigned to a variable - should be source='variable'
df_variable = pd.DataFrame({
    'VAR_COL': [1, 2, 3]
})

# This DataFrame is printed - should be source='stdout'
print(pd.DataFrame({
    'STDOUT_COL': [4, 5, 6]
}))
"""
        result = execution_service.execute_code(code, "test_cell_8", "test_notebook")

        # Should have both types of tables
        variable_tables = [t for t in result.tables if t.get('source') == 'variable']
        stdout_tables = [t for t in result.tables if t.get('source') == 'stdout']

        assert len(variable_tables) >= 1, "Should have variable table"
        assert len(stdout_tables) >= 1, "Should have stdout table"

        print(f"✅ Source attribution correct:")
        print(f"   Variable tables: {len(variable_tables)}")
        print(f"   Stdout tables: {len(stdout_tables)}")

    def test_no_false_positives(self, execution_service):
        """Test that non-tabular stdout is not parsed as tables."""
        code = """
print("This is just regular text")
print("No tables here")
print("Just some output with UPPERCASE and numbers 123")
"""
        result = execution_service.execute_code(code, "test_cell_9", "test_notebook")

        # Should have stdout but no parsed tables
        assert result.stdout, "Should have stdout"

        parsed_tables = [t for t in result.tables if t.get('source') == 'stdout']
        assert len(parsed_tables) == 0, "Should not parse regular text as tables"

        print(f"✅ No false positives - regular text not parsed as table")


def run_tests():
    """Run all tests and report results."""
    pytest.main([__file__, '-v', '--tb=short', '-s'])


if __name__ == '__main__':
    run_tests()
