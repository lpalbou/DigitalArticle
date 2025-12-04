"""
Test that LLM sees complete variable information (not "unknown")

This test verifies the fix for the bug where variables showed as "unknown"
in the user prompt, causing the LLM to recreate DataFrames instead of reusing them.
"""

import pytest
import pandas as pd
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.execution_service import ExecutionService
from app.services.llm_service import LLMService
from app.services.notebook_service import NotebookService


def test_variables_not_shown_as_unknown():
    """CRITICAL: Verify variables are NOT shown as 'unknown' in user prompt"""

    exec_service = ExecutionService()
    llm_service = LLMService()
    notebook_id = "test-variable-display"

    # Create DataFrame with real data
    df = pd.DataFrame({
        'USUBJID': ['P001', 'P002', 'P003'],
        'AGE': [45, 52, 38],
        'SEX': ['F', 'F', 'M'],
        'ARM': ['Treatment', 'Control', 'Treatment']
    })

    # Store DataFrame in execution service
    globals_dict = exec_service._get_notebook_globals(notebook_id)
    globals_dict['sdtm_df'] = df
    globals_dict['patient_count'] = 50
    globals_dict['ages'] = np.array([45, 52, 38])

    # Get variable info (categorized structure)
    var_info = exec_service.get_variable_info(notebook_id)

    # Create context
    context = {
        'available_variables': var_info
    }

    # Build user prompt
    user_prompt = llm_service._build_user_prompt("Analyze data", context)

    # CRITICAL ASSERTIONS: Variables should NOT be shown as "unknown"
    assert "'dataframes': unknown" not in user_prompt, "BUG: DataFrames shown as 'unknown'!"
    assert "'arrays': unknown" not in user_prompt, "BUG: Arrays shown as 'unknown'!"
    assert "'numbers': unknown" not in user_prompt, "BUG: Numbers shown as 'unknown'!"

    # ASSERT: DataFrame details are visible
    assert "sdtm_df" in user_prompt, "DataFrame name missing"
    assert "USUBJID" in user_prompt, "Column names missing"
    assert "AGE" in user_prompt, "Column names missing"
    assert "DataFrame" in user_prompt, "DataFrame type missing"

    # ASSERT: Array info is visible
    assert "ages" in user_prompt, "Array name missing"
    assert "ndarray" in user_prompt or "array" in user_prompt.lower(), "Array type missing"

    # ASSERT: Number info is visible
    assert "patient_count" in user_prompt, "Number variable missing"
    assert "50" in user_prompt or "int" in user_prompt, "Number value/type missing"

    print("✅ PASS: Variables displayed correctly (not 'unknown')")
    print(f"\nUser prompt preview:\n{user_prompt[:500]}...")


def test_dataframe_shown_first_with_columns():
    """Verify DataFrames are shown FIRST with full column details"""

    exec_service = ExecutionService()
    llm_service = LLMService()
    notebook_id = "test-df-priority"

    # Create multiple variable types
    df = pd.DataFrame({
        'COL1': [1, 2, 3],
        'COL2': [4, 5, 6],
        'COL3': [7, 8, 9]
    })

    globals_dict = exec_service._get_notebook_globals(notebook_id)
    globals_dict['my_df'] = df
    globals_dict['my_array'] = np.array([1, 2, 3])
    globals_dict['my_num'] = 42

    var_info = exec_service.get_variable_info(notebook_id)
    context = {'available_variables': var_info}
    user_prompt = llm_service._build_user_prompt("Test", context)

    # ASSERT: DataFrame section appears BEFORE other sections
    df_index = user_prompt.find('DATAFRAMES AVAILABLE')
    arrays_index = user_prompt.find('ARRAYS AVAILABLE')

    assert df_index >= 0, "DataFrames section missing"
    assert df_index < arrays_index, "DataFrames should appear BEFORE arrays"

    # ASSERT: All columns visible
    assert 'COL1' in user_prompt
    assert 'COL2' in user_prompt
    assert 'COL3' in user_prompt

    # ASSERT: DataFrame has proper usage instructions
    assert "USE THIS: my_df" in user_prompt, "Usage instructions missing"

    print("✅ PASS: DataFrames shown first with complete details")


def test_integration_with_notebook_service():
    """Integration test: Verify context from NotebookService shows variables correctly"""
    from app.models.notebook import Notebook, Cell, CellType
    import uuid

    notebook_service = NotebookService()
    exec_service = notebook_service.execution_service
    llm_service = notebook_service.llm_service

    notebook_id = str(uuid.uuid4())  # Use actual UUID

    # Simulate Cell 1 creating DataFrame
    globals_dict = exec_service._get_notebook_globals(notebook_id)
    globals_dict['sdtm_df'] = pd.DataFrame({
        'PATIENT_ID': ['P001', 'P002'],
        'RESPONSE': ['CR', 'PR']
    })

    # Build context for Cell 2
    notebook = Notebook(title="Test", id=notebook_id)
    cell1 = Cell(cell_type=CellType.CODE, prompt="Create data", code="# cell 1 code")
    cell2 = Cell(cell_type=CellType.CODE, prompt="Analyze", code="")
    notebook.cells = [cell1, cell2]

    context = notebook_service._build_execution_context(notebook, cell2)

    # Build user prompt
    user_prompt = llm_service._build_user_prompt("Analyze data", context)

    # ASSERT: DataFrame visible with columns
    assert "sdtm_df" in user_prompt
    assert "PATIENT_ID" in user_prompt
    assert "RESPONSE" in user_prompt
    assert "'dataframes': unknown" not in user_prompt

    print("✅ PASS: Integration test - variables visible in notebook context")


if __name__ == "__main__":
    print("=" * 80)
    print("TEST SUITE: Variable Display Fix")
    print("Verifying: Variables NOT shown as 'unknown'")
    print("=" * 80)

    pytest.main([__file__, "-v", "--tb=short"])
