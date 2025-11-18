"""
Test Import Shadowing Fix

Tests that the _prepare_imports() method correctly handles namespace shadowing
and ensures imports always succeed.
"""

import sys
sys.path.insert(0, '/Users/albou/projects/digital-article/backend')

from app.services.execution_service import ExecutionService


def test_basic_import_shadowing():
    """Test that imports override shadowing variables."""
    print("\n" + "="*80)
    print("TEST 1: Basic Import Shadowing")
    print("="*80)

    service = ExecutionService()

    # Set up shadowing variables
    globals_dict = {
        'stats': None,
        'sns': None,
        'pd': 'some_string'
    }
    print(f"Before: globals_dict has stats={globals_dict.get('stats')}, sns={globals_dict.get('sns')}, pd={globals_dict.get('pd')}")

    # Prepare code with imports
    code = """
from scipy import stats
import seaborn as sns
import pandas as pd
"""

    # Clean namespace
    service._prepare_imports(code, globals_dict)
    print(f"After _prepare_imports: 'stats' in globals_dict = {('stats' in globals_dict)}")
    print(f"After _prepare_imports: 'sns' in globals_dict = {('sns' in globals_dict)}")
    print(f"After _prepare_imports: 'pd' in globals_dict = {('pd' in globals_dict)}")

    # Verify shadowing variables were removed
    assert 'stats' not in globals_dict, "stats should have been removed"
    assert 'sns' not in globals_dict, "sns should have been removed"
    assert 'pd' not in globals_dict, "pd should have been removed"

    # Execute imports
    exec(code, globals_dict)

    # Verify modules imported correctly
    import scipy.stats
    import seaborn
    import pandas
    assert globals_dict['stats'] == scipy.stats, "stats should be scipy.stats module"
    assert globals_dict['sns'] == seaborn, "sns should be seaborn module"
    assert globals_dict['pd'] == pandas, "pd should be pandas module"

    print("✅ Test 1 PASSED: Shadowing variables removed, imports succeeded")


def test_import_with_alias():
    """Test import with alias (import X as Y)."""
    print("\n" + "="*80)
    print("TEST 2: Import with Alias")
    print("="*80)

    service = ExecutionService()

    # Shadow the alias, not the module name
    globals_dict = {
        'np_array': None
    }
    print(f"Before: globals_dict has np_array={globals_dict.get('np_array')}")

    code = "import numpy as np_array"

    service._prepare_imports(code, globals_dict)
    print(f"After _prepare_imports: 'np_array' in globals_dict = {('np_array' in globals_dict)}")

    # Verify shadowing variable was removed
    assert 'np_array' not in globals_dict, "np_array should have been removed"

    # Execute import
    exec(code, globals_dict)

    # Verify module imported correctly
    import numpy
    assert globals_dict['np_array'] == numpy, "np_array should be numpy module"

    print("✅ Test 2 PASSED: Import alias worked correctly")


def test_from_import_with_alias():
    """Test from import with alias (from X import Y as Z)."""
    print("\n" + "="*80)
    print("TEST 3: From Import with Alias")
    print("="*80)

    service = ExecutionService()

    # Shadow the alias
    globals_dict = {
        'ttest': None
    }
    print(f"Before: globals_dict has ttest={globals_dict.get('ttest')}")

    code = "from scipy.stats import ttest_ind as ttest"

    service._prepare_imports(code, globals_dict)
    print(f"After _prepare_imports: 'ttest' in globals_dict = {('ttest' in globals_dict)}")

    # Verify shadowing variable was removed
    assert 'ttest' not in globals_dict, "ttest should have been removed"

    # Execute import
    exec(code, globals_dict)

    # Verify function imported correctly
    from scipy.stats import ttest_ind
    assert globals_dict['ttest'] == ttest_ind, "ttest should be ttest_ind function"

    print("✅ Test 3 PASSED: From import with alias worked correctly")


def test_preserve_existing_module():
    """Test that existing modules are preserved, not deleted."""
    print("\n" + "="*80)
    print("TEST 4: Preserve Existing Module")
    print("="*80)

    service = ExecutionService()

    # Set up namespace with module already imported
    import numpy
    globals_dict = {
        'np': numpy  # Already a module
    }
    print(f"Before: globals_dict has np (type={type(globals_dict.get('np'))})")

    code = "import numpy as np"

    service._prepare_imports(code, globals_dict)
    print(f"After _prepare_imports: 'np' in globals_dict = {('np' in globals_dict)}")
    print(f"After _prepare_imports: np is still numpy = {globals_dict.get('np') == numpy}")

    # Verify module was NOT removed (because it's already a module)
    assert 'np' in globals_dict, "np should still be in globals_dict"
    assert globals_dict['np'] == numpy, "np should still be numpy module"

    print("✅ Test 4 PASSED: Existing module preserved")


def test_nested_module_import():
    """Test importing nested modules (from X.Y import Z)."""
    print("\n" + "="*80)
    print("TEST 5: Nested Module Import")
    print("="*80)

    service = ExecutionService()

    # Shadow nested module name
    globals_dict = {
        'pyplot': None
    }
    print(f"Before: globals_dict has pyplot={globals_dict.get('pyplot')}")

    code = "from matplotlib import pyplot"

    service._prepare_imports(code, globals_dict)
    print(f"After _prepare_imports: 'pyplot' in globals_dict = {('pyplot' in globals_dict)}")

    # Verify shadowing variable was removed
    assert 'pyplot' not in globals_dict, "pyplot should have been removed"

    # Execute import
    exec(code, globals_dict)

    # Verify module imported correctly
    from matplotlib import pyplot
    assert globals_dict['pyplot'] == pyplot, "pyplot should be matplotlib.pyplot module"

    print("✅ Test 5 PASSED: Nested module import worked correctly")


def test_multiple_imports_same_line():
    """Test multiple imports on same line (import X, Y, Z)."""
    print("\n" + "="*80)
    print("TEST 6: Multiple Imports Same Line")
    print("="*80)

    service = ExecutionService()

    # Shadow multiple modules
    globals_dict = {
        'os': None,
        'sys': None,
        'json': None
    }
    print(f"Before: globals_dict has os={globals_dict.get('os')}, sys={globals_dict.get('sys')}, json={globals_dict.get('json')}")

    code = "import os, sys, json"

    service._prepare_imports(code, globals_dict)
    print(f"After _prepare_imports: 'os' in globals_dict = {('os' in globals_dict)}")
    print(f"After _prepare_imports: 'sys' in globals_dict = {('sys' in globals_dict)}")
    print(f"After _prepare_imports: 'json' in globals_dict = {('json' in globals_dict)}")

    # Verify all shadowing variables were removed
    assert 'os' not in globals_dict, "os should have been removed"
    assert 'sys' not in globals_dict, "sys should have been removed"
    assert 'json' not in globals_dict, "json should have been removed"

    # Execute imports
    exec(code, globals_dict)

    # Verify all modules imported correctly
    import os as os_module
    import sys as sys_module
    import json as json_module
    assert globals_dict['os'] == os_module, "os should be os module"
    assert globals_dict['sys'] == sys_module, "sys should be sys module"
    assert globals_dict['json'] == json_module, "json should be json module"

    print("✅ Test 6 PASSED: Multiple imports worked correctly")


def test_real_world_scenario():
    """Test real-world scenario from failing notebook."""
    print("\n" + "="*80)
    print("TEST 7: Real-World Scenario (scipy.stats)")
    print("="*80)

    service = ExecutionService()

    # Simulate namespace from Cell 1 that set stats = None
    globals_dict = {
        'stats': None,
        'data': [1, 2, 3],
        'other_var': 'some_value'
    }
    print(f"Before: globals_dict has stats={globals_dict.get('stats')}")

    # Cell 2 code that tries to use scipy.stats
    code = """
from scipy import stats

# Perform t-test
treatment = [1, 2, 3, 4, 5]
control = [2, 3, 4, 5, 6]
t_stat, p_val = stats.ttest_ind(treatment, control)
result = (t_stat, p_val)
"""

    service._prepare_imports(code, globals_dict)
    print(f"After _prepare_imports: 'stats' in globals_dict = {('stats' in globals_dict)}")

    # Verify stats was removed
    assert 'stats' not in globals_dict, "stats should have been removed"

    # Execute code
    exec(code, globals_dict)

    # Verify import worked and t-test executed
    assert 'result' in globals_dict, "result should exist"
    t_stat, p_val = globals_dict['result']
    assert isinstance(t_stat, float), "t_stat should be float"
    assert isinstance(p_val, float), "p_val should be float"

    print(f"✅ Test 7 PASSED: Real-world scenario worked (t_stat={t_stat:.4f}, p_val={p_val:.4f})")


def test_no_imports_no_changes():
    """Test that code without imports doesn't modify namespace."""
    print("\n" + "="*80)
    print("TEST 8: No Imports - No Changes")
    print("="*80)

    service = ExecutionService()

    # Set up namespace with variables
    globals_dict = {
        'stats': None,
        'data': [1, 2, 3]
    }
    original_keys = set(globals_dict.keys())
    print(f"Before: globals_dict keys = {original_keys}")

    # Code without imports
    code = """
x = 10
y = 20
result = x + y
"""

    service._prepare_imports(code, globals_dict)
    print(f"After _prepare_imports: globals_dict keys = {set(globals_dict.keys())}")

    # Verify nothing was removed (no imports in code)
    assert set(globals_dict.keys()) == original_keys, "No variables should have been removed"
    assert globals_dict['stats'] is None, "stats should still be None"

    print("✅ Test 8 PASSED: No changes when no imports present")


if __name__ == "__main__":
    print("\n" + "="*80)
    print("IMPORT SHADOWING FIX - COMPREHENSIVE TEST SUITE")
    print("="*80)

    try:
        test_basic_import_shadowing()
        test_import_with_alias()
        test_from_import_with_alias()
        test_preserve_existing_module()
        test_nested_module_import()
        test_multiple_imports_same_line()
        test_real_world_scenario()
        test_no_imports_no_changes()

        print("\n" + "="*80)
        print("✅ ALL 8 TESTS PASSED!")
        print("="*80)
        print("\nImport shadowing fix is working correctly! 🎯")

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()

    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
