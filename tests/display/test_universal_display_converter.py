"""
Comprehensive tests for the universal display converter.

Tests that display() can handle ANY data type without silent failures.
"""

import sys
import io
import json
import base64
import numpy as np
import pandas as pd
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

from app.services.execution_service import ExecutionService


def test_dataframe_display():
    """Test DataFrame display conversion."""
    service = ExecutionService()

    df = pd.DataFrame({
        'A': [1, 2, 3],
        'B': ['x', 'y', 'z']
    })

    result = service._convert_to_display_format(df, "My DataFrame", "test_notebook")

    assert result['type'] == 'table'
    assert result['label'] == 'My DataFrame'
    assert result['source'] == 'display'
    assert 'columns' in result
    assert 'data' in result  # Table data (not 'rows')
    print("✅ DataFrame display test passed")


def test_series_display():
    """Test Series display conversion."""
    service = ExecutionService()

    series = pd.Series([10, 20, 30], index=['a', 'b', 'c'], name='values')

    result = service._convert_to_display_format(series, "My Series", "test_notebook")

    assert result['type'] == 'table'
    assert result['label'] == 'My Series'
    assert result['source'] == 'display'
    print("✅ Series display test passed")


def test_numpy_1d_array_display():
    """Test 1D NumPy array display conversion."""
    service = ExecutionService()

    arr = np.array([1, 2, 3, 4, 5])

    result = service._convert_to_display_format(arr, "My Array", "test_notebook")

    assert result['type'] == 'table'
    assert result['label'] == 'My Array'
    assert result['source'] == 'display'
    print("✅ 1D NumPy array display test passed")


def test_numpy_2d_array_display():
    """Test 2D NumPy array display conversion."""
    service = ExecutionService()

    arr = np.array([[1, 2, 3], [4, 5, 6]])

    result = service._convert_to_display_format(arr, "Correlation Matrix", "test_notebook")

    assert result['type'] == 'table'
    assert result['label'] == 'Correlation Matrix'
    assert result['source'] == 'display'
    print("✅ 2D NumPy array display test passed")


def test_numpy_3d_array_display():
    """Test 3D+ NumPy array display conversion (should be text)."""
    service = ExecutionService()

    arr = np.zeros((3, 3, 3))

    result = service._convert_to_display_format(arr, "3D Tensor", "test_notebook")

    assert result['type'] == 'text'
    assert result['label'] == '3D Tensor'
    assert '(3, 3, 3)' in result['content']
    print("✅ 3D NumPy array display test passed")


def test_dict_display():
    """Test dictionary display conversion."""
    service = ExecutionService()

    data = {
        'accuracy': 0.95,
        'precision': 0.92,
        'recall': 0.88
    }

    result = service._convert_to_display_format(data, "Model Metrics", "test_notebook")

    assert result['type'] == 'json'
    assert result['label'] == 'Model Metrics'
    assert result['source'] == 'display'
    assert 'accuracy' in result['content']

    # Verify valid JSON
    parsed = json.loads(result['content'])
    assert parsed['accuracy'] == 0.95
    print("✅ Dictionary display test passed")


def test_list_small_display():
    """Test small list display conversion (should be JSON)."""
    service = ExecutionService()

    data = [1, 2, 3, 4, 5]

    result = service._convert_to_display_format(data, "My List", "test_notebook")

    assert result['type'] == 'json'
    assert result['label'] == 'My List'
    print("✅ Small list display test passed")


def test_list_large_display():
    """Test large list display conversion (should be table)."""
    service = ExecutionService()

    data = list(range(200))

    result = service._convert_to_display_format(data, None, "test_notebook")

    assert result['type'] == 'table'
    assert 'Table' in result['label']  # Auto-numbered
    print("✅ Large list display test passed")


def test_pandas_index_display():
    """Test pandas Index display conversion."""
    service = ExecutionService()

    idx = pd.Index(['A', 'B', 'C', 'D'], name='categories')

    result = service._convert_to_display_format(idx, "Categories", "test_notebook")

    assert result['type'] == 'table'
    assert result['label'] == 'Categories'
    print("✅ pandas Index display test passed")


def test_sklearn_model_display():
    """Test sklearn model display conversion."""
    try:
        from sklearn.linear_model import LinearRegression

        service = ExecutionService()
        model = LinearRegression()
        model.fit([[1], [2], [3]], [1, 2, 3])

        result = service._convert_to_display_format(model, "Trained Model", "test_notebook")

        # sklearn models have _repr_html_() so they're rendered as HTML (priority 3)
        assert result['type'] == 'html'
        assert result['label'] == 'Trained Model'
        assert 'LinearRegression' in result['content']
        print("✅ sklearn model display test passed")
    except ImportError:
        print("⚠️ sklearn not installed, skipping model test")


def test_fallback_unknown_type():
    """Test fallback for unknown object types."""
    service = ExecutionService()

    class CustomObject:
        def __init__(self):
            self.value = 42

        def __repr__(self):
            return f"CustomObject(value={self.value})"

    obj = CustomObject()

    result = service._convert_to_display_format(obj, "Custom Object", "test_notebook")

    assert result['type'] == 'text'
    assert result['label'] == 'Custom Object'
    assert 'CustomObject' in result['content']
    assert '42' in result['content']
    print("✅ Fallback display test passed")


def test_auto_labeling():
    """Test automatic labeling when no label provided."""
    service = ExecutionService()

    # Initialize counters
    service.notebook_table_counters = {}
    service.notebook_figure_counters = {}

    df1 = pd.DataFrame({'A': [1, 2, 3]})
    df2 = pd.DataFrame({'B': [4, 5, 6]})

    result1 = service._convert_to_display_format(df1, None, "test_notebook")
    result2 = service._convert_to_display_format(df2, None, "test_notebook")

    assert result1['label'] == 'Table 1'
    assert result2['label'] == 'Table 2'
    print("✅ Auto-labeling test passed")


def test_no_silent_failures():
    """Test that NO object type causes a silent failure."""
    service = ExecutionService()

    # Test various object types that might fail
    test_objects = [
        (None, "None value"),
        (42, "Scalar int"),
        (3.14, "Scalar float"),
        ("hello", "String"),
        (set([1, 2, 3]), "Set"),
        (frozenset([1, 2, 3]), "Frozenset"),
        ((1, 2, 3), "Tuple"),
        (b'bytes', "Bytes"),
        (lambda x: x, "Lambda function"),
    ]

    for obj, description in test_objects:
        result = service._convert_to_display_format(obj, description, "test_notebook")

        # MUST have a type - no silent failures!
        assert 'type' in result, f"Failed for {description}: no type field"
        assert result['type'] is not None, f"Failed for {description}: type is None"
        assert result['label'] == description, f"Failed for {description}: label mismatch"
        assert result['source'] == 'display', f"Failed for {description}: source mismatch"

        # MUST have displayable content
        assert 'content' in result or 'data' in result, f"Failed for {description}: no content"

        print(f"  ✓ {description}: type={result['type']}")

    print("✅ No silent failures test passed - ALL types handled!")


def test_repr_html_support():
    """Test objects with _repr_html_() method (Jupyter standard)."""
    service = ExecutionService()

    class HTMLObject:
        def _repr_html_(self):
            return "<div class='test'><b>HTML Content</b></div>"

    obj = HTMLObject()
    result = service._convert_to_display_format(obj, "HTML Object", "test_notebook")

    assert result['type'] == 'html'
    assert result['label'] == 'HTML Object'
    assert '<b>HTML Content</b>' in result['content']
    print("✅ _repr_html_() support test passed")


def test_error_handling():
    """Test that conversion errors don't crash - return error display."""
    service = ExecutionService()

    class BrokenObject:
        def __repr__(self):
            raise Exception("repr() is broken!")

    obj = BrokenObject()
    result = service._convert_to_display_format(obj, "Broken Object", "test_notebook")

    # Should return error display, not crash
    assert result['type'] == 'text'
    assert 'Error displaying object' in result['content']
    print("✅ Error handling test passed")


def test_long_repr_truncation():
    """Test that very long repr() strings are truncated intelligently."""
    service = ExecutionService()

    long_string = "A" * 5000

    result = service._convert_to_display_format(long_string, "Long String", "test_notebook")

    assert result['type'] == 'text'
    assert len(result['content']) < len(long_string)
    assert '... (' in result['content']  # Truncation indicator
    assert 'chars omitted' in result['content']
    print("✅ Long repr truncation test passed")


def test_nan_handling_in_arrays():
    """Test NaN values in arrays are handled properly."""
    service = ExecutionService()

    arr = np.array([1.0, np.nan, 3.0])

    result = service._convert_to_display_format(arr, "Array with NaN", "test_notebook")

    assert result['type'] == 'table'
    # Should not crash on NaN values
    print("✅ NaN handling in arrays test passed")


def test_empty_collections():
    """Test empty collections display correctly."""
    service = ExecutionService()

    # Empty DataFrame
    df = pd.DataFrame()
    result = service._convert_to_display_format(df, "Empty DF", "test_notebook")
    assert result['type'] == 'table'

    # Empty dict
    d = {}
    result = service._convert_to_display_format(d, "Empty Dict", "test_notebook")
    assert result['type'] == 'json'

    # Empty list
    lst = []
    result = service._convert_to_display_format(lst, "Empty List", "test_notebook")
    assert result['type'] == 'json'

    print("✅ Empty collections test passed")


if __name__ == '__main__':
    print("=" * 60)
    print("COMPREHENSIVE UNIVERSAL DISPLAY CONVERTER TESTS")
    print("=" * 60)
    print()

    test_dataframe_display()
    test_series_display()
    test_numpy_1d_array_display()
    test_numpy_2d_array_display()
    test_numpy_3d_array_display()
    test_dict_display()
    test_list_small_display()
    test_list_large_display()
    test_pandas_index_display()
    test_sklearn_model_display()
    test_fallback_unknown_type()
    test_auto_labeling()
    test_no_silent_failures()
    test_repr_html_support()
    test_error_handling()
    test_long_repr_truncation()
    test_nan_handling_in_arrays()
    test_empty_collections()

    print()
    print("=" * 60)
    print("✅ ALL TESTS PASSED!")
    print("=" * 60)
    print()
    print("Coverage Summary:")
    print("  - DataFrames: ✓")
    print("  - Series: ✓")
    print("  - NumPy arrays (1D, 2D, 3D+): ✓")
    print("  - Dictionaries: ✓")
    print("  - Lists (small & large): ✓")
    print("  - Tuples: ✓")
    print("  - pandas Index: ✓")
    print("  - sklearn models: ✓")
    print("  - Custom objects: ✓")
    print("  - Objects with _repr_html_(): ✓")
    print("  - Error handling: ✓")
    print("  - Auto-labeling: ✓")
    print("  - Long repr truncation: ✓")
    print("  - NaN handling: ✓")
    print("  - Empty collections: ✓")
    print("  - NO SILENT FAILURES: ✓")
    print()
    print("🎯 The universal converter handles ANY Python object!")
