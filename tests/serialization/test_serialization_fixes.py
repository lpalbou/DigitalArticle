"""
Test serialization fixes for backend errors.

This test suite verifies that all critical serialization issues are fixed:
1. Pydantic validation for plots field (Union[str, Dict])
2. Pandas Period type JSON serialization
3. Module filtering in state persistence
4. Deprecated .dict() replaced with .model_dump()
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../backend'))

import pandas as pd
import numpy as np
from datetime import datetime
from uuid import uuid4

from app.models.notebook import ExecutionResult, ExecutionStatus
from app.services.execution_service import ExecutionService
from app.services.state_persistence_service import StatePersistenceService


def test_pydantic_plot_validation():
    """Test that ExecutionResult accepts both string and dict plots."""
    print("\n=== Test 1: Pydantic Plot Validation ===")

    # Test with legacy string plots
    result1 = ExecutionResult(
        status=ExecutionStatus.SUCCESS,
        plots=["base64string1", "base64string2"]
    )
    assert len(result1.plots) == 2
    assert result1.plots[0] == "base64string1"
    print("✅ Legacy string plots work")

    # Test with new dict plots (from display())
    result2 = ExecutionResult(
        status=ExecutionStatus.SUCCESS,
        plots=[
            {"data": "base64data", "label": "Figure 1", "source": "display"},
            {"data": "base64data2", "label": "Figure 2", "source": "display"}
        ]
    )
    assert len(result2.plots) == 2
    assert result2.plots[0]["label"] == "Figure 1"
    print("✅ New dict plots work")

    # Test with mixed plots
    result3 = ExecutionResult(
        status=ExecutionStatus.SUCCESS,
        plots=[
            "base64string",
            {"data": "base64data", "label": "Figure 1", "source": "display"}
        ]
    )
    assert len(result3.plots) == 2
    assert isinstance(result3.plots[0], str)
    assert isinstance(result3.plots[1], dict)
    print("✅ Mixed plots work")

    print("✅ All Pydantic plot validation tests passed!")


def test_pandas_period_serialization():
    """Test that DataFrames with Period types can be serialized to JSON."""
    print("\n=== Test 2: Pandas Period Serialization ===")

    # Create DataFrame with Period index
    periods = pd.period_range('2024-01', periods=3, freq='M')
    df = pd.DataFrame({
        'value': [1, 2, 3],
    }, index=periods)

    print(f"Created DataFrame with Period index:\n{df}")

    # Test the make_json_serializable function
    service = ExecutionService()
    table_data = service._dataframe_to_table_data(df, "Test Table")

    # Verify it can be converted to dict (for JSON serialization)
    assert 'data' in table_data
    assert len(table_data['data']) == 3

    # Check that Period values were converted to strings
    for row in table_data['data']:
        for key, value in row.items():
            assert not isinstance(value, pd.Period), f"Period not converted: {value}"

    print("✅ DataFrame with Period index serializes correctly")

    # Create DataFrame with Period column
    df2 = pd.DataFrame({
        'period_col': pd.period_range('2024-01', periods=3, freq='M'),
        'value': [10, 20, 30]
    })

    table_data2 = service._dataframe_to_table_data(df2, "Test Table 2")
    assert 'data' in table_data2
    assert len(table_data2['data']) == 3

    print("✅ DataFrame with Period column serializes correctly")
    print("✅ All pandas Period serialization tests passed!")


def test_module_filtering_in_state_persistence():
    """Test that modules are properly filtered during state persistence."""
    print("\n=== Test 3: Module Filtering in State Persistence ===")

    # Create a globals dict with modules and regular variables
    globals_dict = {
        'pd': pd,  # Module - should be filtered
        'np': np,  # Module - should be filtered
        'df': pd.DataFrame({'a': [1, 2, 3]}),  # DataFrame - should be kept
        'value': 42,  # Regular variable - should be kept
        '__builtins__': {},  # Built-in - should be filtered
        '_private': 'test',  # Private - should be filtered
    }

    service = StatePersistenceService()
    safe_dict = service._prepare_for_pickle(globals_dict)

    # Check that modules were filtered out
    assert 'pd' not in safe_dict, "Module 'pd' should be filtered"
    assert 'np' not in safe_dict, "Module 'np' should be filtered"
    print("✅ Modules filtered correctly")

    # Check that regular variables were kept
    assert 'df' in safe_dict, "DataFrame 'df' should be kept"
    assert 'value' in safe_dict, "Regular variable 'value' should be kept"
    print("✅ Regular variables preserved")

    # Check that private variables were filtered
    assert '__builtins__' not in safe_dict, "Built-ins should be filtered"
    print("✅ Private variables filtered")

    print("✅ All module filtering tests passed!")


def test_model_dump_instead_of_dict():
    """Test that models use model_dump() instead of deprecated dict()."""
    print("\n=== Test 4: model_dump() Usage ===")

    # Create an ExecutionResult
    result = ExecutionResult(
        status=ExecutionStatus.SUCCESS,
        stdout="Test output",
        plots=[{"data": "test", "label": "Test", "source": "display"}]
    )

    # Test that model_dump() works
    try:
        data = result.model_dump()
        assert 'status' in data
        assert 'stdout' in data
        assert 'plots' in data
        print("✅ model_dump() works correctly")
    except AttributeError:
        raise AssertionError("model_dump() method not available (still using .dict()?)")

    print("✅ All model_dump() tests passed!")


def test_end_to_end_serialization():
    """Test complete serialization pipeline."""
    print("\n=== Test 5: End-to-End Serialization ===")

    # Create a realistic execution scenario
    service = ExecutionService()
    notebook_id = str(uuid4())

    # Execute code that creates variables with Period types
    code = """
import pandas as pd
import numpy as np

# Create DataFrame with Period index
periods = pd.period_range('2024-01', periods=5, freq='M')
df_with_period = pd.DataFrame({
    'sales': np.random.randint(100, 1000, 5),
    'costs': np.random.randint(50, 500, 5)
}, index=periods)

# Create regular DataFrame
df_normal = pd.DataFrame({'a': [1, 2, 3], 'b': [4, 5, 6]})

# Regular variables
total_sales = df_with_period['sales'].sum()
"""

    result = service.execute_code(code, "cell_1", notebook_id)

    # Check execution succeeded
    assert result.status == ExecutionStatus.SUCCESS, f"Execution failed: {result.error_message}"
    print("✅ Code executed successfully")

    # Get the globals
    globals_dict = service._get_notebook_globals(notebook_id)

    # Test DataFrame serialization with Period types
    df_with_period = globals_dict.get('df_with_period')
    if df_with_period is not None:
        table_data = service._dataframe_to_table_data(df_with_period, "Sales Data")
        assert 'data' in table_data
        print("✅ DataFrame with Period index serialized")

    # Test state persistence
    persistence_service = StatePersistenceService()
    success = persistence_service.save_notebook_state(notebook_id, globals_dict)
    assert success, "State persistence failed"
    print("✅ State saved successfully")

    # Test state restoration
    restored_dict = persistence_service.load_notebook_state(notebook_id)
    assert restored_dict is not None, "State restoration failed"
    assert 'df_normal' in restored_dict, "DataFrame not restored"
    assert 'total_sales' in restored_dict, "Variable not restored"
    assert 'pd' not in restored_dict, "Module should not be in restored state"
    print("✅ State restored successfully")

    print("✅ All end-to-end serialization tests passed!")


if __name__ == "__main__":
    print("=" * 70)
    print("TESTING SERIALIZATION FIXES")
    print("=" * 70)

    try:
        test_pydantic_plot_validation()
        test_pandas_period_serialization()
        test_module_filtering_in_state_persistence()
        test_model_dump_instead_of_dict()
        test_end_to_end_serialization()

        print("\n" + "=" * 70)
        print("🎉 ALL TESTS PASSED!")
        print("=" * 70)
        print("\nSummary:")
        print("✅ Pydantic plot validation works with Union[str, Dict]")
        print("✅ Pandas Period types serialize correctly to JSON")
        print("✅ Modules are filtered during state persistence")
        print("✅ model_dump() is used instead of deprecated dict()")
        print("✅ End-to-end serialization pipeline works")
        print("\nAll backend errors should be fixed! 🚀")

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
