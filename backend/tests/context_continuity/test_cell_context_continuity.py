"""
Test Suite: Cell Context Continuity - DataFrame Columns and No Truncation

Tests that LLM receives FULL context without truncation:
1. DataFrame columns are included
2. All columns shown (no truncation to 8)
3. Previous cell code not truncated
4. Previous cell prompts not truncated
5. Context building works correctly

Date: 2025-12-04
"""

import pytest
import pandas as pd
import numpy as np
import sys
from pathlib import Path

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.execution_service import ExecutionService
from app.models.notebook import Notebook, Cell, CellType


class TestDataFrameColumnsInContext:
    """Test that DataFrame columns are included in get_variable_info()"""

    def test_dataframe_columns_included(self):
        """CRITICAL: Verify DataFrame columns are included in variable info"""
        service = ExecutionService()
        notebook_id = "test-notebook-1"

        # Create DataFrame with 15 columns (realistic clinical data)
        columns = ['USUBJID', 'ARM', 'AGE', 'SEX', 'RACE', 'DIAGDT', 'TUMOR_SIZE',
                   'STAGE', 'GRADE', 'BRCA_MUTATION', 'LYMPH_NODE', 'METASTASIS',
                   'RESPONSE', 'SURVIVAL_MONTHS', 'EVENT']

        df = pd.DataFrame(
            np.random.randn(50, 15),
            columns=columns
        )

        # Store DataFrame in notebook's globals
        globals_dict = service._get_notebook_globals(notebook_id)
        globals_dict['sdtm_dataset'] = df

        # Get variable info
        var_info = service.get_variable_info(notebook_id)

        # ASSERT: columns key exists
        assert 'dataframes' in var_info
        assert 'sdtm_dataset' in var_info['dataframes']

        df_info = var_info['dataframes']['sdtm_dataset']
        assert 'columns' in df_info, "CRITICAL BUG: columns not included in DataFrame info"

        # ASSERT: all columns present
        assert df_info['columns'] == columns, "Not all columns included"
        assert len(df_info['columns']) == 15, "Column count mismatch"

        print("✅ PASS: DataFrame columns correctly included in variable info")

    def test_dataframe_with_many_columns(self):
        """Test DataFrame with 20+ columns (all should be included)"""
        service = ExecutionService()
        notebook_id = "test-notebook-2"

        # Create DataFrame with 25 columns
        columns = [f'COL_{i}' for i in range(25)]
        df = pd.DataFrame(np.random.randn(100, 25), columns=columns)

        globals_dict = service._get_notebook_globals(notebook_id)
        globals_dict['wide_df'] = df

        var_info = service.get_variable_info(notebook_id)
        df_info = var_info['dataframes']['wide_df']

        # ASSERT: ALL 25 columns included (no truncation)
        assert 'columns' in df_info
        assert len(df_info['columns']) == 25, "Columns truncated!"
        assert df_info['columns'] == columns

        print("✅ PASS: All 25 columns included (no truncation)")

    def test_multiple_dataframes_all_columns_included(self):
        """Test multiple DataFrames, all columns included"""
        service = ExecutionService()
        notebook_id = "test-notebook-3"

        # Create 3 DataFrames with different column counts
        df1 = pd.DataFrame({'A': [1, 2], 'B': [3, 4], 'C': [5, 6]})
        df2 = pd.DataFrame({'X': [1], 'Y': [2], 'Z': [3], 'W': [4], 'V': [5]})
        df3 = pd.DataFrame({f'F{i}': [i] for i in range(10)})  # 10 columns

        globals_dict = service._get_notebook_globals(notebook_id)
        globals_dict['df1'] = df1
        globals_dict['df2'] = df2
        globals_dict['df3'] = df3

        var_info = service.get_variable_info(notebook_id)

        # ASSERT: all DataFrames present with all columns
        assert len(var_info['dataframes']) == 3
        assert var_info['dataframes']['df1']['columns'] == ['A', 'B', 'C']
        assert var_info['dataframes']['df2']['columns'] == ['X', 'Y', 'Z', 'W', 'V']
        assert len(var_info['dataframes']['df3']['columns']) == 10

        print("✅ PASS: Multiple DataFrames all have complete column lists")


class TestNoCodeTruncation:
    """Test that previous cell code is NOT truncated"""

    def test_long_code_not_truncated(self):
        """Verify code longer than 500 chars is NOT truncated"""
        from app.services.notebook_service import NotebookService
        from app.services.llm_service import LLMService

        # Create mock services
        notebook_service = NotebookService()

        # Create notebook with long code (800+ chars)
        long_code = """
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Create comprehensive clinical trial dataset
patient_id = [f"P{str(i+1).zfill(3)}" for i in range(50)]
arm = np.random.choice(['Control', 'Treatment'], size=50, p=[0.5, 0.5])
age = np.random.normal(48, 12, 50).astype(int)
sex = np.random.choice(['F', 'M'], size=50, p=[0.95, 0.05])
race = np.random.choice(['White', 'Black or African American', 'Asian', 'Other'], size=50, p=[0.7, 0.15, 0.1, 0.05])
diag_date = [datetime.now() - timedelta(days=np.random.randint(0, 730)) for _ in range(50)]
tumor_size = np.random.normal(4.2, 1.8, 50)
stage = np.random.choice(['I', 'II', 'III', 'IV'], size=50, p=[0.2, 0.3, 0.3, 0.2])

df = pd.DataFrame({
    'USUBJID': patient_id,
    'ARM': arm,
    'AGE': age,
    'SEX': sex,
    'RACE': race
})
"""

        # Build context with this code
        notebook = Notebook(title="Test")
        cell1 = Cell(cell_type=CellType.CODE, prompt="Create dataset", code=long_code)
        cell2 = Cell(cell_type=CellType.CODE, prompt="Analyze", code="")
        notebook.cells = [cell1, cell2]

        # Build context for cell 2
        context = notebook_service._build_execution_context(notebook, cell2)

        # ASSERT: code is NOT truncated
        assert 'previous_cells' in context
        assert len(context['previous_cells']) == 1

        prev_cell_code = context['previous_cells'][0]['code']
        assert len(prev_cell_code) > 500, "Code should not be truncated"
        # Compare without leading/trailing whitespace
        assert prev_cell_code.strip() == long_code.strip(), "Code was modified/truncated"

        print(f"✅ PASS: Long code ({len(long_code)} chars) NOT truncated")


class TestNoPromptTruncation:
    """Test that previous cell prompts are NOT truncated"""

    def test_long_prompt_not_truncated(self):
        """Verify prompts longer than 200 chars are NOT truncated"""
        from app.services.notebook_service import NotebookService

        notebook_service = NotebookService()

        # Create long prompt (300+ chars)
        long_prompt = """
Create a comprehensive SDTM dataset for 50 triple-negative breast cancer patients
enrolled in a Phase 2 clinical trial. Include demographics (age, sex, race),
disease characteristics (tumor size, stage, grade, BRCA mutation status, lymph node
involvement, metastasis), treatment arms (Control, Treatment), and outcomes
(response status, survival months, event indicator). Use realistic distributions.
"""

        notebook = Notebook(title="Test")
        cell1 = Cell(cell_type=CellType.PROMPT, prompt=long_prompt, code="# code here")
        cell2 = Cell(cell_type=CellType.PROMPT, prompt="Analyze", code="")
        notebook.cells = [cell1, cell2]

        context = notebook_service._build_execution_context(notebook, cell2)

        # ASSERT: prompt is NOT truncated
        prev_cell_prompt = context['previous_cells'][0]['prompt']
        assert len(prev_cell_prompt) > 200, "Prompt should not be truncated"
        assert prev_cell_prompt == long_prompt, "Prompt was modified/truncated"

        print(f"✅ PASS: Long prompt ({len(long_prompt)} chars) NOT truncated")


class TestColumnDisplayNoTruncation:
    """Test that LLM sees ALL columns when displayed"""

    def test_llm_service_shows_all_columns(self):
        """Verify get_variable_info includes all DataFrame columns without truncation"""
        from app.services.execution_service import ExecutionService

        exec_service = ExecutionService()
        notebook_id = "test-columns-display"

        # Create real DataFrame with 15 columns
        columns = ['USUBJID', 'ARM', 'AGE', 'SEX', 'RACE', 'DIAGDT', 'TUMOR_SIZE',
                   'STAGE', 'GRADE', 'BRCA_MUTATION', 'LYMPH_NODE', 'METASTASIS',
                   'RESPONSE', 'SURVIVAL_MONTHS', 'EVENT']

        df = pd.DataFrame(np.random.randn(50, 15), columns=columns)

        # Store in execution service
        globals_dict = exec_service._get_notebook_globals(notebook_id)
        globals_dict['sdtm_dataset'] = df

        # Get variable info (should now include columns)
        var_info = exec_service.get_variable_info(notebook_id)

        # CRITICAL ASSERT: Columns are included in variable info
        assert 'dataframes' in var_info
        assert 'sdtm_dataset' in var_info['dataframes']
        df_info = var_info['dataframes']['sdtm_dataset']
        assert 'columns' in df_info, "CRITICAL: columns not included!"

        # ASSERT: ALL 15 columns present (no truncation)
        assert len(df_info['columns']) == 15, f"Expected 15 columns, got {len(df_info['columns'])}"
        assert df_info['columns'] == columns, "Columns don't match"

        # ASSERT: No truncation in the column list itself
        for col in columns:
            assert col in df_info['columns'], f"Column {col} missing"

        print("✅ PASS: All 15 columns included in variable info (no truncation)")


class TestFullContextIntegration:
    """Integration test: End-to-end context building"""

    def test_full_context_no_truncation(self):
        """Integration: Verify complete context from execution to LLM"""
        from app.services.execution_service import ExecutionService
        from app.services.notebook_service import NotebookService
        from app.services.llm_service import LLMService

        exec_service = ExecutionService()
        notebook_service = NotebookService()
        llm_service = LLMService()

        notebook_id = "integration-test"

        # Step 1: Execute code that creates DataFrame
        code = """
import pandas as pd
df = pd.DataFrame({
    'A': [1, 2, 3],
    'B': [4, 5, 6],
    'C': [7, 8, 9],
    'D': [10, 11, 12]
})
"""
        result = exec_service.execute_code(code, "cell-1", notebook_id)
        assert result.status.value == 'success'

        # Step 2: Get variable info
        var_info = exec_service.get_variable_info(notebook_id)
        assert 'dataframes' in var_info
        assert 'df' in var_info['dataframes']
        assert var_info['dataframes']['df']['columns'] == ['A', 'B', 'C', 'D']

        # Step 3: Build context for next cell
        notebook = Notebook(title="Test")
        cell1 = Cell(cell_type=CellType.CODE, prompt="Create DF", code=code)
        cell2 = Cell(cell_type=CellType.PROMPT, prompt="Use df", code="")
        notebook.cells = [cell1, cell2]

        context = notebook_service._build_execution_context(notebook, cell2)

        # Step 4: Build LLM prompt
        user_prompt = llm_service._build_user_prompt("Use the DataFrame", context)

        # ASSERT: All columns visible in final prompt
        assert 'A, B, C, D' in user_prompt or ('A' in user_prompt and 'B' in user_prompt and 'C' in user_prompt and 'D' in user_prompt)
        assert 'DataFrame' in user_prompt

        print("✅ PASS: Full integration - columns propagate to LLM prompt")


if __name__ == "__main__":
    print("=" * 80)
    print("COMPREHENSIVE TEST SUITE: Cell Context Continuity")
    print("Testing: DataFrame columns + No truncation")
    print("=" * 80)

    # Run all tests
    pytest.main([__file__, "-v", "--tb=short"])
