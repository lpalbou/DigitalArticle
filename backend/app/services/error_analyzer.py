"""
Error Analyzer Service for enhancing error context during auto-retry.

This service analyzes Python execution errors and provides domain-specific
guidance to help the LLM fix errors more effectively during auto-retry cycles.

Design Philosophy:
- General-purpose: Extensible analyzer system for various error types
- Non-invasive: Enhances error messages, doesn't modify execution
- Domain-aware: Provides library-specific guidance (matplotlib, pandas, file I/O)
- No artificial constraints: Never restricts valid code, only adds helpful context
"""

import re
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ErrorContext:
    """Enhanced error context with domain-specific guidance."""

    original_error: str
    error_type: str
    enhanced_message: str
    suggestions: List[str]
    relevant_docs: Optional[str] = None


class ErrorAnalyzer:
    """
    AUTHORITATIVE ERROR HANDLING SYSTEM - Single source of truth for all error analysis.

    This service implements a plugin-style architecture where each error analyzer
    is a specialized method that detects and enhances specific error patterns.
    
    🚨 CRITICAL: ALL error handling in Digital Article MUST go through this system.
    
    Architecture:
    - Primary path: ErrorAnalyzer -> LLMService.suggest_improvements() -> LLM
    - Fallback only: Basic fixes when LLM service completely fails
    - Forbidden: Direct LLM calls for error fixing (bypasses domain expertise)
    
    To add new error types:
    1. Add analyzer method: _analyze_new_error_type()
    2. Add to self.analyzers list in __init__()
    3. Test integration through suggest_improvements()
    
    See docs/error-handling.md for complete guidelines.
    """

    def __init__(self):
        """Initialize the error analyzer with registered analyzers."""
        # Ordered list of analyzer methods to try
        self.analyzers = [
            self._analyze_matplotlib_color_error,  # NEW: Handle color mapping errors
            self._analyze_matplotlib_subplot_error,
            self._analyze_matplotlib_figure_error,
            self._analyze_numpy_timedelta_error,
            self._analyze_numpy_type_conversion_error,
            self._analyze_file_not_found_error,
            self._analyze_pandas_length_mismatch_error,  # NEW: Handle pandas length mismatch
            self._analyze_pandas_key_error,
            self._analyze_pandas_merge_error,
            self._analyze_numpy_shape_error,
            self._analyze_import_error,
            self._analyze_type_error,
            self._analyze_index_error,
            self._analyze_value_error,
        ]

    def analyze_error(
        self,
        error_message: str,
        error_type: str,
        traceback: str,
        code: str,
        context: Optional[Dict[str, Any]] = None
    ) -> ErrorContext:
        """
        Analyze an execution error and provide enhanced context.

        Args:
            error_message: The original error message
            error_type: The exception type (e.g., "ValueError")
            traceback: Full Python traceback
            code: The code that caused the error
            context: Optional execution context with available variables

        Returns:
            ErrorContext with enhanced guidance for LLM
        """
        logger.info(f"Analyzing {error_type}: {error_message[:100]}...")

        # Try each analyzer in order
        for analyzer in self.analyzers:
            try:
                error_context = analyzer(error_message, error_type, traceback, code, context)
                if error_context:
                    logger.info(f"Enhanced error with {analyzer.__name__}")
                    return error_context
            except Exception as e:
                logger.warning(f"Analyzer {analyzer.__name__} failed: {e}")
                continue

        # No specific analyzer matched, return generic enhanced context
        return self._create_generic_context(error_message, error_type, traceback, code)

    # ============================================================================
    # MATPLOTLIB ERROR ANALYZERS
    # ============================================================================

    def _analyze_matplotlib_color_error(
        self,
        error_message: str,
        error_type: str,
        traceback: str,
        code: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[ErrorContext]:
        """Analyze matplotlib color mapping errors."""
        if error_type != "ValueError":
            return None
        
        # Check for color-related errors
        color_patterns = [
            r"'c' argument must be a color",
            r"Invalid RGBA argument",
            r"to_rgba_array",
            r"_parse_scatter_color_args"
        ]
        
        if not any(re.search(pattern, error_message) or re.search(pattern, traceback) for pattern in color_patterns):
            return None
        
        # Extract the problematic data from error message
        data_match = re.search(r"not (.+?)(?:\n|$)", error_message)
        problematic_data = data_match.group(1) if data_match else "categorical data"
        
        suggestions = [
            "MATPLOTLIB COLOR ERROR - Categorical data used as colors",
            "",
            "🎨 PROBLEM: You're passing categorical/text data to the 'c' parameter",
            "   Matplotlib expects colors or numeric values, not text labels like 'SD', 'PR', 'CR'",
            "",
            "🔧 SOLUTIONS:",
            "",
            "1. MAP CATEGORIES TO COLORS:",
            "   # Create a color mapping",
            "   color_map = {'SD': 'blue', 'PR': 'green', 'CR': 'red', 'PD': 'orange'}",
            "   colors = df['RESPONSE'].map(color_map)",
            "   plt.scatter(x, y, c=colors)",
            "",
            "2. USE NUMERIC ENCODING:",
            "   # Convert categories to numbers",
            "   from sklearn.preprocessing import LabelEncoder",
            "   le = LabelEncoder()",
            "   numeric_colors = le.fit_transform(df['RESPONSE'])",
            "   plt.scatter(x, y, c=numeric_colors, cmap='viridis')",
            "",
            "3. USE SEABORN (HANDLES CATEGORIES AUTOMATICALLY):",
            "   import seaborn as sns",
            "   sns.scatterplot(data=df, x='x_col', y='y_col', hue='RESPONSE')",
            "",
            "4. PANDAS FACTORIZE (SIMPLE):",
            "   colors = pd.factorize(df['RESPONSE'])[0]",
            "   plt.scatter(x, y, c=colors, cmap='tab10')",
            "",
            "💡 RECOMMENDED: Use seaborn for automatic categorical color handling"
        ]

        return ErrorContext(
            original_error=error_message,
            error_type=error_type,
            enhanced_message="Categorical data passed to matplotlib color parameter - need color mapping",
            suggestions=suggestions
        )

    def _analyze_matplotlib_subplot_error(
        self,
        error_message: str,
        error_type: str,
        traceback: str,
        code: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[ErrorContext]:
        """
        Analyze matplotlib subplot grid constraint errors.

        Detects errors like:
        - "num must be an integer with 1 <= num <= 12, not 13"

        Root cause: plt.subplot(nrows, ncols, index) where index > nrows * ncols
        """
        if error_type != "ValueError":
            return None

        # Pattern: "num must be an integer with 1 <= num <= X, not Y"
        pattern = r"num must be an integer with 1 <= num <= (\d+), not (\d+)"
        match = re.search(pattern, error_message)

        if not match:
            return None

        max_valid = int(match.group(1))
        invalid_index = int(match.group(2))

        # Try to extract subplot parameters from code
        subplot_calls = self._extract_subplot_calls(code)

        suggestions = [
            f"MATHEMATICAL CONSTRAINT: You tried to create subplot position {invalid_index}, but the grid only has {max_valid} positions.",
            f"",
            f"When calling plt.subplot(nrows, ncols, index):",
            f"  - Total positions available = nrows × ncols",
            f"  - Valid index range = 1 to (nrows × ncols)",
            f"  - In your case: Maximum valid index = {max_valid}",
            f"",
            f"COMMON CAUSES:",
            f"1. Loop range error: for i in range(1, {invalid_index}) when grid is smaller",
            f"2. Incorrect grid size: Using {max_valid}-position grid for {invalid_index} subplots",
            f"3. Off-by-one error: Zero-indexing vs 1-indexing confusion",
            f"",
            f"FIX OPTIONS:",
            f"1. Reduce number of subplots to {max_valid} (match grid size)",
            f"2. Increase grid size to accommodate {invalid_index} subplots:",
        ]

        # Suggest appropriate grid sizes
        grid_suggestions = self._suggest_grid_sizes(invalid_index)
        for grid in grid_suggestions:
            suggestions.append(f"   - plt.subplot({grid[0]}, {grid[1]}, ...) gives {grid[0] * grid[1]} positions")

        suggestions.extend([
            f"",
            f"3. Fix loop range if using iteration:",
            f"   - WRONG: for i in range(1, {invalid_index})",
            f"   - RIGHT: for i in range(1, {max_valid + 1})",
            f"",
            f"DETECTED SUBPLOT CALLS IN YOUR CODE:",
        ])

        if subplot_calls:
            for call in subplot_calls:
                suggestions.append(f"  - {call}")
        else:
            suggestions.append(f"  - (Could not parse subplot calls - check your code manually)")

        enhanced_message = f"""
MATPLOTLIB SUBPLOT GRID CONSTRAINT VIOLATED

Original Error: {error_message}

EXPLANATION:
Matplotlib subplot grids have a fundamental mathematical constraint:
  subplot_index must be ≤ (nrows × ncols)

You attempted to create subplot #{invalid_index} in a grid that only has {max_valid} positions.
This is like trying to access the 13th element of a 12-element array - mathematically impossible.

This is NOT a matplotlib limitation or bug - it's a logical constraint.
You cannot have position {invalid_index} in a {max_valid}-position grid.
""".strip()

        return ErrorContext(
            original_error=error_message,
            error_type=error_type,
            enhanced_message=enhanced_message,
            suggestions=suggestions,
            relevant_docs="https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.subplot.html"
        )

    def _analyze_matplotlib_figure_error(
        self,
        error_message: str,
        error_type: str,
        traceback: str,
        code: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[ErrorContext]:
        """Analyze matplotlib figure management errors."""
        if "figure" not in error_message.lower() and "Figure" not in traceback:
            return None

        suggestions = [
            "MATPLOTLIB FIGURE MANAGEMENT ISSUE",
            "",
            "Common causes:",
            "1. Calling plt.show() or fig.show() multiple times",
            "2. Trying to access closed figures",
            "3. Figure number conflicts",
            "",
            "Solutions:",
            "1. Create figure explicitly: fig = plt.figure(figsize=(10, 6))",
            "2. Use plt.clf() to clear current figure",
            "3. Use plt.close('all') to close all figures before creating new ones",
            "4. Assign subplots to variables: fig, ax = plt.subplots(2, 2)",
        ]

        return ErrorContext(
            original_error=error_message,
            error_type=error_type,
            enhanced_message=f"Matplotlib figure management error: {error_message}",
            suggestions=suggestions
        )

    # ============================================================================
    # FILE I/O ERROR ANALYZERS
    # ============================================================================

    def _analyze_file_not_found_error(
        self,
        error_message: str,
        error_type: str,
        traceback: str,
        code: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[ErrorContext]:
        """Analyze file not found errors with data/ directory context."""
        if error_type not in ("FileNotFoundError", "OSError"):
            return None

        if "No such file or directory" not in error_message and "FileNotFoundError" not in error_type:
            return None

        # Extract attempted filename from error
        file_pattern = r"['\"]([^'\"]+\.(csv|xlsx|json|txt|tsv|parquet))['\"]"
        matches = re.findall(file_pattern, error_message + code, re.IGNORECASE)

        attempted_files = [match[0] for match in matches] if matches else []

        suggestions = [
            "FILE NOT FOUND ERROR",
            "",
            "CRITICAL: All data files MUST be accessed via the 'data/' directory prefix.",
            "",
            "The execution environment requires:",
            "  - Working directory structure: workspace_{notebook_id}/data/",
            "  - All data files are located in: data/",
            "  - You MUST use: pd.read_csv('data/filename.csv')",
            "  - NOT: pd.read_csv('filename.csv')",
            "",
        ]

        if attempted_files:
            suggestions.append("Files you attempted to access:")
            for f in attempted_files:
                suggestions.append(f"  - '{f}'")
                if not f.startswith('data/'):
                    suggestions.append(f"    FIX: Change to 'data/{f}'")
            suggestions.append("")

        suggestions.extend([
            "CORRECT PATTERNS:",
            "  ✓ df = pd.read_csv('data/gene_expression.csv')",
            "  ✓ data = pd.read_excel('data/patient_data.xlsx')",
            "  ✓ with open('data/config.json') as f: ...",
            "",
            "INCORRECT PATTERNS:",
            "  ✗ df = pd.read_csv('gene_expression.csv')  # Missing data/ prefix",
            "  ✗ df = pd.read_csv('/data/file.csv')  # Don't use absolute paths",
            "  ✗ df = pd.read_csv('../data/file.csv')  # Don't use relative paths",
            "",
            "If file truly doesn't exist:",
            "1. Check available files in the data directory",
            "2. Verify filename spelling (case-sensitive)",
            "3. Ask user to upload the file if missing",
        ])

        enhanced_message = f"""
FILE ACCESS ERROR - DATA DIRECTORY REQUIRED

Original Error: {error_message}

EXPLANATION:
All data files in Digital Article must be accessed through the 'data/' directory.
The execution environment works in isolated notebook workspaces with this structure:

  workspace_{{notebook_id}}/
    data/           ← All data files are here
      *.csv
      *.xlsx
      ...

SOLUTION:
Prefix all file paths with 'data/', for example:
  - WRONG: pd.read_csv('myfile.csv')
  - RIGHT: pd.read_csv('data/myfile.csv')
""".strip()

        return ErrorContext(
            original_error=error_message,
            error_type=error_type,
            enhanced_message=enhanced_message,
            suggestions=suggestions
        )

    # ============================================================================
    # PANDAS ERROR ANALYZERS
    # ============================================================================

    def _analyze_pandas_length_mismatch_error(
        self,
        error_message: str,
        error_type: str,
        traceback: str,
        code: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[ErrorContext]:
        """
        Analyze pandas length mismatch errors.
        
        Detects: ValueError: Length of values (X) does not match length of index (Y)
        """
        if error_type != "ValueError":
            return None
        
        # Check for the specific pandas length mismatch pattern
        length_pattern = r"Length of values \((\d+)\) does not match length of index \((\d+)\)"
        match = re.search(length_pattern, error_message)
        
        if not match:
            return None
        
        values_length = int(match.group(1))
        index_length = int(match.group(2))
        
        # Check if this is pandas-related
        is_pandas_related = (
            "pandas" in traceback.lower() or
            "DataFrame" in traceback or
            "pd." in code or
            "df[" in code or
            "_sanitize_column" in traceback or
            "_set_item" in traceback
        )
        
        if not is_pandas_related:
            return None
        
        # Analyze the mismatch
        ratio = values_length / index_length if index_length > 0 else 0
        
        suggestions = [
            f"PANDAS LENGTH MISMATCH - Values ({values_length}) ≠ Index ({index_length})",
            "",
            "🔍 PROBLEM ANALYSIS:",
            f"   • You're trying to assign {values_length} values to a DataFrame with {index_length} rows",
            f"   • Mismatch ratio: {ratio:.2f}x ({'too many' if ratio > 1 else 'too few'} values)",
            "",
            "🚨 COMMON CAUSES:",
        ]
        
        # Add specific guidance based on the ratio
        if ratio == 0.2:  # 1/5 ratio - common sampling issue
            suggestions.extend([
                "   • SAMPLING MISMATCH: Using sample() then assigning to full DataFrame",
                "   • You likely sampled data but forgot to update the assignment target",
            ])
        elif ratio == 0.1:  # 1/10 ratio
            suggestions.extend([
                "   • SUBSET OPERATION: Working with 10% sample but assigning to full data",
                "   • Check if you used .head(), .sample(), or filtering before assignment",
            ])
        elif values_length < index_length:
            suggestions.extend([
                "   • FILTERED DATA: You filtered/sampled values but kept original DataFrame",
                "   • AGGREGATION: You grouped/summarized data (fewer results than input)",
                "   • MISSING DATA: Some values were dropped during processing",
            ])
        else:  # values_length > index_length
            suggestions.extend([
                "   • EXPANSION: You created more values than original rows (e.g., explode, repeat)",
                "   • WRONG TARGET: Assigning to wrong DataFrame or subset",
                "   • CONCATENATION: You combined data but target wasn't updated",
            ])
        
        suggestions.extend([
            "",
            "🔧 ROBUST SOLUTIONS:",
            "",
            "1. ALIGN THE ASSIGNMENT TARGET:",
            "   # Instead of assigning to original DataFrame:",
            "   # df['new_col'] = processed_values  # ❌ Length mismatch",
            "   ",
            "   # Create new DataFrame or update the right subset:",
            "   df_subset = df[some_condition]  # This has the right length",
            "   df_subset['new_col'] = processed_values  # ✅ Lengths match",
            "",
            "2. USE .loc[] FOR CONDITIONAL ASSIGNMENT:",
            "   # If values are for a subset, assign to that subset:",
            "   mask = df['condition'] == True",
            "   df.loc[mask, 'new_col'] = processed_values  # ✅ Safe assignment",
            "",
            "3. RESET INDEX AFTER FILTERING:",
            "   # If you filtered data, reset the index:",
            "   df_filtered = df[df['col'] > threshold].reset_index(drop=True)",
            "   df_filtered['new_col'] = processed_values  # ✅ Clean index",
            "",
            "4. CREATE NEW DATAFRAME WHEN LENGTHS DIFFER:",
            "   # Don't force assignment - create new structure:",
            "   new_df = pd.DataFrame({",
            "       'original_col': source_data,",
            "       'new_col': processed_values",
            "   })  # ✅ Lengths naturally match",
            "",
            "5. USE PANDAS MERGE/JOIN FOR DIFFERENT LENGTHS:",
            "   # If data should be combined but has different lengths:",
            "   result_df = pd.merge(df, processed_df, on='key_column', how='left')",
            "",
            "🔍 DEBUGGING STEPS:",
            f"1. Check your data shapes:",
            f"   print('DataFrame shape:', df.shape)  # Should be (?, {index_length})",
            f"   print('Values shape:', len(processed_values))  # Currently {values_length}",
            "",
            "2. Trace the data flow:",
            "   print('Before processing:', original_data.shape)",
            "   print('After processing:', processed_values.shape)",
            "   print('Assignment target:', target_df.shape)",
            "",
            "3. Identify where the mismatch occurred:",
            "   # Add prints before the failing line to see data transformations",
            "",
            "💡 PREVENTION TIPS:",
            "• Always check shapes before assignment: assert len(values) == len(df)",
            "• Use .loc[] for conditional assignments instead of direct column assignment",
            "• When filtering data, work with the filtered DataFrame, not the original",
            "• Consider using merge/join operations for combining different-length data",
        ])
        
        enhanced_message = f"""
PANDAS LENGTH MISMATCH ERROR

Original Error: {error_message}

EXPLANATION:
You're trying to assign {values_length} values to a DataFrame column that has {index_length} rows.
This is a fundamental constraint in pandas - every column must have the same number of rows.

ROOT CAUSE:
The data you're assigning ({values_length} items) doesn't match the DataFrame structure ({index_length} rows).
This typically happens when you:
1. Filter/sample data but assign to the original DataFrame
2. Aggregate data (reducing rows) but assign to the full DataFrame  
3. Expand data (increasing rows) but assign to a smaller DataFrame

SOLUTION PATTERN:
Instead of forcing the assignment, align your data structures:
- If you filtered data: assign to the filtered DataFrame
- If you aggregated data: create a new DataFrame or use merge/join
- If you expanded data: ensure the target DataFrame has the right size

The key is to match the assignment target to your actual data, not force mismatched data together.
""".strip()
        
        return ErrorContext(
            original_error=error_message,
            error_type=error_type,
            enhanced_message=enhanced_message,
            suggestions=suggestions,
            relevant_docs="https://pandas.pydata.org/docs/user_guide/indexing.html#indexing-view-versus-copy"
        )

    def _analyze_pandas_key_error(
        self,
        error_message: str,
        error_type: str,
        traceback: str,
        code: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[ErrorContext]:
        """Analyze pandas KeyError (column not found)."""
        if error_type != "KeyError":
            return None

        # Check if this is a pandas DataFrame-related error
        is_pandas_related = (
            "DataFrame" in traceback or
            "pd." in code or
            "pandas" in traceback.lower() or
            "df[" in code or
            ".columns" in code
        )

        if not is_pandas_related:
            return None

        # Extract the missing key
        key_pattern = r"KeyError: ['\"]?([^'\"]+)['\"]?"
        match = re.search(key_pattern, error_message)
        missing_key = match.group(1) if match else "unknown"

        suggestions = [
            f"PANDAS KEYERROR - Column '{missing_key}' not found in DataFrame",
            "",
        ]

        # ENHANCEMENT: If context provides available variables, show actual DataFrame columns
        dataframe_found = False
        if context and 'available_variables' in context:
            for var_name, var_info in context['available_variables'].items():
                if 'DataFrame' in var_info:
                    dataframe_found = True
                    suggestions.append(f"ACTUAL AVAILABLE DATA:")
                    suggestions.append(f"  Variable '{var_name}': {var_info}")
                    suggestions.append("")
                    suggestions.append(f"CRITICAL FIX:")
                    suggestions.append(f"  1. The DataFrame '{var_name}' exists but doesn't have column '{missing_key}'")
                    suggestions.append(f"  2. Use ONLY the columns shown above in the DataFrame info")
                    suggestions.append(f"  3. Adapt your code to work with the ACTUAL available columns")
                    suggestions.append("")
                    break

        if not dataframe_found:
            # Fallback to generic guidance
            suggestions.extend([
                "Common causes:",
                "1. Typo in column name (pandas is case-sensitive)",
                "2. Column doesn't exist in the data",
                "3. Column name has extra spaces or special characters",
                "4. Using wrong DataFrame variable",
                "",
                "Solutions:",
                "1. Print column names first: print(df.columns.tolist())",
                "2. Check for exact spelling and case",
                "3. Strip whitespace: df.columns = df.columns.str.strip()",
                "4. Use df.get() for safe access: df.get('column', default_value)",
                "",
                f"DEBUGGING STEPS:",
                f"1. Add before the error line:",
                f"   print('Available columns:', df.columns.tolist())",
                f"2. Check if '{missing_key}' appears in the list",
                f"3. Look for similar column names with different case/spacing",
            ])

        return ErrorContext(
            original_error=error_message,
            error_type=error_type,
            enhanced_message=f"Pandas column '{missing_key}' not found in DataFrame",
            suggestions=suggestions
        )

    def _analyze_pandas_merge_error(
        self,
        error_message: str,
        error_type: str,
        traceback: str,
        code: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[ErrorContext]:
        """Analyze pandas merge/join errors."""
        if "merge" not in error_message.lower() and "join" not in error_message.lower():
            return None

        suggestions = [
            "PANDAS MERGE/JOIN ERROR",
            "",
            "Common causes:",
            "1. Merge key column doesn't exist in one/both DataFrames",
            "2. Key columns have different data types",
            "3. Missing 'on' parameter",
            "4. Duplicate column names",
            "",
            "Solutions:",
            "1. Verify key columns exist: print(df1.columns), print(df2.columns)",
            "2. Check data types: print(df1['key'].dtype), print(df2['key'].dtype)",
            "3. Use explicit 'on' parameter: pd.merge(df1, df2, on='id')",
            "4. Handle suffixes: pd.merge(df1, df2, suffixes=('_left', '_right'))",
        ]

        return ErrorContext(
            original_error=error_message,
            error_type=error_type,
            enhanced_message=f"Pandas merge/join error: {error_message}",
            suggestions=suggestions
        )

    # ============================================================================
    # NUMPY ERROR ANALYZERS
    # ============================================================================

    def _analyze_numpy_timedelta_error(
        self,
        error_message: str,
        error_type: str,
        traceback: str,
        code: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[ErrorContext]:
        """
        Analyze numpy type incompatibility with timedelta.

        Detects: TypeError: unsupported type for timedelta days component: numpy.int64
        """
        if error_type != "TypeError":
            return None

        if "timedelta" not in error_message.lower() and "timedelta" not in traceback:
            return None

        if "numpy" not in error_message and "numpy" not in traceback:
            return None

        # Extract the numpy type
        numpy_type_pattern = r"numpy\.(\w+)"
        match = re.search(numpy_type_pattern, error_message)
        numpy_type = match.group(1) if match else "numeric type"

        suggestions = [
            f"NUMPY TYPE INCOMPATIBILITY WITH TIMEDELTA",
            "",
            "PROBLEM:",
            f"Python's timedelta() function doesn't accept NumPy types (numpy.{numpy_type}).",
            "This happens when using pandas Series values or numpy arrays directly in timedelta.",
            "",
            "ROOT CAUSE:",
            "NumPy types (int64, float64, etc.) are not the same as Python native types.",
            "Many Python built-ins (timedelta, datetime, range, etc.) require native Python types.",
            "",
            "SOLUTION - Convert NumPy types to Python types:",
            "",
            "METHOD 1: Use .item() for scalar values",
            "  WRONG: timedelta(days=np_value)",
            "  RIGHT: timedelta(days=np_value.item())",
            "  RIGHT: timedelta(days=int(np_value))",
            "",
            "METHOD 2: Use pd.to_timedelta() for pandas operations",
            "  WRONG: df['days'].apply(lambda x: timedelta(days=x))",
            "  RIGHT: pd.to_timedelta(df['days'], unit='D')",
            "",
            "METHOD 3: Convert in bulk operations",
            "  WRONG: [timedelta(days=x) for x in df['days']]",
            "  RIGHT: pd.to_timedelta(df['days'], unit='D')",
            "  RIGHT: [timedelta(days=int(x)) for x in df['days']]",
            "",
            "COMMON SCENARIOS:",
            "1. Random integer generation:",
            "   days = np.random.randint(1, 30)  # Returns numpy.int64",
            "   FIX: days = int(np.random.randint(1, 30))",
            "",
            "2. DataFrame operations:",
            "   df['date'] = df['days'].apply(lambda x: timedelta(days=x))  # Fails",
            "   FIX: df['date'] = pd.to_timedelta(df['days'], unit='D')",
            "",
            "3. Arithmetic operations:",
            "   result = series.sum()  # Returns numpy type",
            "   FIX: result = int(series.sum())",
            "",
            "AUTOMATIC CONVERSION HELPER:",
            "Use the provided safe_timedelta() function:",
            "  safe_timedelta(days=np_value)  # Automatically converts",
        ]

        enhanced_message = f"""
NUMPY TYPE INCOMPATIBILITY ERROR

Original Error: {error_message}

EXPLANATION:
Python's timedelta() requires native Python int/float, not NumPy types.
When you use pandas/numpy operations, results are numpy.{numpy_type}, not Python int.

This is a type system boundary issue between NumPy and Python stdlib.

QUICK FIX:
  Before: timedelta(days=numpy_value)
  After:  timedelta(days=int(numpy_value))
  Better: pd.to_timedelta(numpy_value, unit='D')  # For pandas operations
""".strip()

        return ErrorContext(
            original_error=error_message,
            error_type=error_type,
            enhanced_message=enhanced_message,
            suggestions=suggestions,
            relevant_docs="https://pandas.pydata.org/docs/reference/api/pandas.to_timedelta.html"
        )

    def _analyze_numpy_type_conversion_error(
        self,
        error_message: str,
        error_type: str,
        traceback: str,
        code: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[ErrorContext]:
        """
        Analyze general numpy type conversion errors.

        Detects errors where numpy types are used in contexts expecting Python types.
        """
        if error_type != "TypeError":
            return None

        # Check if numpy types are mentioned
        if "numpy" not in error_message and "numpy" not in traceback:
            return None

        # Check for common type conversion issues
        type_conversion_keywords = [
            "unsupported type",
            "cannot convert",
            "expected",
            "requires",
            "invalid type"
        ]

        if not any(keyword in error_message.lower() for keyword in type_conversion_keywords):
            return None

        suggestions = [
            "NUMPY TYPE CONVERSION ERROR",
            "",
            "Common causes:",
            "1. NumPy types (int64, float64) used where Python types expected",
            "2. Passing numpy scalars to Python built-in functions",
            "3. Type mismatches in function arguments",
            "",
            "Solutions:",
            "1. Convert numpy scalars to Python types:",
            "   - Use .item(): numpy_value.item() → Python type",
            "   - Use int/float/str: int(numpy_value)",
            "",
            "2. For pandas Series/DataFrame operations:",
            "   - Use vectorized pandas methods instead of Python loops",
            "   - Use .values.tolist() to convert to Python list",
            "   - Use .astype() for type conversion within pandas",
            "",
            "3. Check function signatures:",
            "   - Some functions only accept Python native types",
            "   - Use type checking: type(value) to debug",
            "",
            "DETECTION PATTERN:",
            "print(f'Type: {type(value)}')  # Check if numpy type",
            "if isinstance(value, np.generic):",
            "    value = value.item()  # Convert to Python type",
        ]

        enhanced_message = f"""
NumPy Type Conversion Error: {error_message}

NumPy types (numpy.int64, numpy.float64, etc.) are not always compatible
with Python built-in functions that expect native Python types.

Quick fix: Convert numpy types to Python types using .item() or int()/float()
""".strip()

        return ErrorContext(
            original_error=error_message,
            error_type=error_type,
            enhanced_message=enhanced_message,
            suggestions=suggestions,
            relevant_docs="https://numpy.org/doc/stable/user/basics.types.html"
        )

    def _analyze_numpy_shape_error(
        self,
        error_message: str,
        error_type: str,
        traceback: str,
        code: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[ErrorContext]:
        """Analyze numpy shape mismatch errors."""
        if "shape" not in error_message.lower() and error_type != "ValueError":
            return None

        if "broadcast" in error_message.lower() or "dimension" in error_message.lower():
            suggestions = [
                "NUMPY SHAPE MISMATCH ERROR",
                "",
                "Common causes:",
                "1. Array dimensions don't align for operation",
                "2. Broadcasting rules violated",
                "3. Matrix multiplication dimension mismatch",
                "",
                "Solutions:",
                "1. Print shapes: print(arr1.shape, arr2.shape)",
                "2. Reshape if needed: arr.reshape(-1, 1) or arr.flatten()",
                "3. Use transpose: arr.T",
                "4. Check broadcasting rules: https://numpy.org/doc/stable/user/basics.broadcasting.html",
            ]

            return ErrorContext(
                original_error=error_message,
                error_type=error_type,
                enhanced_message=f"NumPy shape mismatch: {error_message}",
                suggestions=suggestions
            )

        return None

    # ============================================================================
    # IMPORT ERROR ANALYZERS
    # ============================================================================

    def _analyze_import_error(
        self,
        error_message: str,
        error_type: str,
        traceback: str,
        code: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[ErrorContext]:
        """Analyze import errors with simple, targeted suggestions."""
        if error_type not in ("ImportError", "ModuleNotFoundError"):
            return None

        # Extract module name
        module_pattern = r"No module named ['\"]([^'\"]+)['\"]"
        match = re.search(module_pattern, error_message)
        module = match.group(1) if match else "unknown"

        # Simple keyword-based suggestions
        quick_fixes = self._get_simple_import_suggestions(module, code)
        
        suggestions = [
            f"IMPORT ERROR - Module '{module}' not available",
            "",
        ]
        
        if quick_fixes:
            suggestions.extend(quick_fixes)
            suggestions.append("")
        
        suggestions.extend([
            "📚 AVAILABLE LIBRARIES:",
            "  - pandas (pd), numpy (np), matplotlib.pyplot (plt)",
            "  - plotly.express (px), seaborn (sns), scipy.stats (stats)",
            "  - sklearn (machine learning), scanpy (sc), umap",
            "  - PIL (images), requests (web), openpyxl (Excel)",
            "",
            "💡 SOLUTIONS:",
            f"1. Check spelling: '{module}'",
            f"2. Use available alternative from list above",
            f"3. If essential, inform user library needs installation",
        ])

        return ErrorContext(
            original_error=error_message,
            error_type=error_type,
            enhanced_message=f"Module '{module}' not available",
            suggestions=suggestions
        )
    
    def _get_simple_import_suggestions(self, module: str, code: str) -> List[str]:
        """Simple keyword matching for common import issues."""
        module_lower = module.lower()
        suggestions = []
        
        # Common substitutions
        if 'tensorflow' in module_lower or 'torch' in module_lower or 'keras' in module_lower:
            suggestions.extend([
                "🔄 DEEP LEARNING → Use sklearn instead:",
                "   from sklearn.neural_network import MLPClassifier",
                "   from sklearn.ensemble import RandomForestClassifier"
            ])
        elif 'cv2' in module_lower or 'opencv' in module_lower:
            suggestions.extend([
                "🖼️ COMPUTER VISION → Use PIL for basic image tasks:",
                "   from PIL import Image",
                "   img = Image.open('data/image.jpg')"
            ])
        elif 'pil' in module_lower and 'cannot import name' in code:
            suggestions.extend([
                "🖼️ PIL IMPORT → Try:",
                "   from PIL import Image  # (PIL is available)"
            ])
        elif 'umap' in code and 'sklearn.manifold' in code:
            suggestions.extend([
                "🎯 UMAP FIX → Use correct import:",
                "   from umap import UMAP  # (not from sklearn.manifold)"
            ])
        elif 'excel' in module_lower or 'xlsx' in module_lower:
            suggestions.extend([
                "📊 EXCEL FILES → Use pandas or openpyxl:",
                "   df = pd.read_excel('data/file.xlsx')",
                "   import openpyxl  # (available)"
            ])
        
        return suggestions

    # ============================================================================
    # GENERIC ERROR ANALYZERS
    # ============================================================================

    def _analyze_type_error(
        self,
        error_message: str,
        error_type: str,
        traceback: str,
        code: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[ErrorContext]:
        """Analyze TypeError."""
        if error_type != "TypeError":
            return None

        suggestions = [
            "TYPE ERROR",
            "",
            "Common causes:",
            "1. Calling method on wrong type (e.g., list.columns())",
            "2. Passing wrong argument type to function",
            "3. Trying to iterate over non-iterable",
            "4. None value where object expected",
            "",
            "Solutions:",
            "1. Print variable type: print(type(variable))",
            "2. Check for None: if variable is not None:",
            "3. Convert type: int(), float(), str(), list()",
            "4. Verify variable is what you expect before using",
        ]

        return ErrorContext(
            original_error=error_message,
            error_type=error_type,
            enhanced_message=f"Type error: {error_message}",
            suggestions=suggestions
        )

    def _analyze_index_error(
        self,
        error_message: str,
        error_type: str,
        traceback: str,
        code: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[ErrorContext]:
        """Analyze IndexError."""
        if error_type != "IndexError":
            return None

        suggestions = [
            "INDEX ERROR - Accessing index that doesn't exist",
            "",
            "Common causes:",
            "1. List/array is smaller than expected",
            "2. Off-by-one error (0-indexing vs 1-indexing)",
            "3. Empty list/array",
            "",
            "Solutions:",
            "1. Check length: print(len(my_list))",
            "2. Use safe indexing: if len(my_list) > index:",
            "3. Use .get() for dicts: my_dict.get(key, default)",
            "4. Check for empty: if my_list:",
        ]

        return ErrorContext(
            original_error=error_message,
            error_type=error_type,
            enhanced_message=f"Index error: {error_message}",
            suggestions=suggestions
        )

    def _analyze_value_error(
        self,
        error_message: str,
        error_type: str,
        traceback: str,
        code: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[ErrorContext]:
        """Analyze generic ValueError."""
        if error_type != "ValueError":
            return None

        # This is a catch-all for ValueErrors not handled by specific analyzers
        suggestions = [
            "VALUE ERROR",
            "",
            "Common causes:",
            "1. Invalid value passed to function",
            "2. Data type conversion failed",
            "3. Value doesn't meet function requirements",
            "",
            "Solutions:",
            "1. Check input value: print(the_value)",
            "2. Verify value is in expected range/format",
            "3. Handle conversion errors: try/except",
            "4. Read function documentation for valid inputs",
        ]

        return ErrorContext(
            original_error=error_message,
            error_type=error_type,
            enhanced_message=f"Value error: {error_message}",
            suggestions=suggestions
        )

    # ============================================================================
    # HELPER METHODS
    # ============================================================================

    def _create_generic_context(
        self,
        error_message: str,
        error_type: str,
        traceback: str,
        code: str
    ) -> ErrorContext:
        """Create generic error context when no specific analyzer matches."""
        suggestions = [
            f"{error_type.upper()} OCCURRED",
            "",
            "General debugging steps:",
            "1. Read the error message carefully",
            "2. Check the line number in traceback",
            "3. Print variable values before the error",
            "4. Simplify the code to isolate the issue",
            "5. Check data types and shapes",
            "",
            "If error persists:",
            "1. Break code into smaller steps",
            "2. Add print statements for debugging",
            "3. Try alternative approach",
        ]

        return ErrorContext(
            original_error=error_message,
            error_type=error_type,
            enhanced_message=error_message,
            suggestions=suggestions
        )

    def _extract_subplot_calls(self, code: str) -> List[str]:
        """Extract all plt.subplot() calls from code."""
        # Pattern: plt.subplot(args...)
        pattern = r'plt\.subplot\s*\([^)]+\)'
        matches = re.findall(pattern, code)
        return matches if matches else []

    def _suggest_grid_sizes(self, num_subplots: int) -> List[tuple]:
        """
        Suggest appropriate grid sizes for a given number of subplots.

        Returns list of (nrows, ncols) tuples that can fit num_subplots.
        """
        suggestions = []

        # Find factors and near-square grids
        for nrows in range(1, num_subplots + 1):
            for ncols in range(nrows, num_subplots + 1):
                if nrows * ncols >= num_subplots:
                    # Prefer more square-ish grids (aspect ratio close to 1)
                    aspect_ratio = max(nrows, ncols) / min(nrows, ncols)
                    if aspect_ratio <= 3:  # Not too elongated
                        suggestions.append((nrows, ncols))

                    # Only need first few that fit
                    if len(suggestions) >= 3:
                        return suggestions

        return suggestions if suggestions else [(1, num_subplots)]

    def format_for_llm(self, context: ErrorContext, traceback: str = "") -> str:
        """
        Format error context for LLM consumption.

        Returns a formatted string that provides maximum helpful context
        for the LLM to fix the error during auto-retry.
        
        Args:
            context: Enhanced error context from analyzer
            traceback: Full Python traceback
        """
        formatted = f"""
{'=' * 80}
ERROR ANALYSIS AND FIX GUIDANCE
{'=' * 80}

{context.enhanced_message}

{'=' * 80}
DETAILED GUIDANCE FOR FIXING THIS ERROR
{'=' * 80}

{chr(10).join(context.suggestions)}

{'=' * 80}
ORIGINAL ERROR MESSAGE
{'=' * 80}

{context.original_error}

""".strip()

        # Add full traceback if provided
        if traceback and traceback.strip():
            formatted += f"""

{'=' * 80}
FULL PYTHON STACK TRACE
{'=' * 80}

{traceback.strip()}
"""

        if context.relevant_docs:
            formatted += f"\n\nRELEVANT DOCUMENTATION:\n{context.relevant_docs}"

        return formatted
