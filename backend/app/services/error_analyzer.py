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
    Analyzes Python execution errors and provides enhanced context for LLM auto-retry.

    This service implements a plugin-style architecture where each error analyzer
    is a specialized method that detects and enhances specific error patterns.
    """

    def __init__(self):
        """Initialize the error analyzer with registered analyzers."""
        # Ordered list of analyzer methods to try
        self.analyzers = [
            self._analyze_matplotlib_subplot_error,
            self._analyze_matplotlib_figure_error,
            self._analyze_file_not_found_error,
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
        code: str
    ) -> ErrorContext:
        """
        Analyze an execution error and provide enhanced context.

        Args:
            error_message: The original error message
            error_type: The exception type (e.g., "ValueError")
            traceback: Full Python traceback
            code: The code that caused the error

        Returns:
            ErrorContext with enhanced guidance for LLM
        """
        logger.info(f"Analyzing {error_type}: {error_message[:100]}...")

        # Try each analyzer in order
        for analyzer in self.analyzers:
            try:
                context = analyzer(error_message, error_type, traceback, code)
                if context:
                    logger.info(f"Enhanced error with {analyzer.__name__}")
                    return context
            except Exception as e:
                logger.warning(f"Analyzer {analyzer.__name__} failed: {e}")
                continue

        # No specific analyzer matched, return generic enhanced context
        return self._create_generic_context(error_message, error_type, traceback, code)

    # ============================================================================
    # MATPLOTLIB ERROR ANALYZERS
    # ============================================================================

    def _analyze_matplotlib_subplot_error(
        self,
        error_message: str,
        error_type: str,
        traceback: str,
        code: str
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
        code: str
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
        code: str
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

    def _analyze_pandas_key_error(
        self,
        error_message: str,
        error_type: str,
        traceback: str,
        code: str
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
        ]

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
        code: str
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

    def _analyze_numpy_shape_error(
        self,
        error_message: str,
        error_type: str,
        traceback: str,
        code: str
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
        code: str
    ) -> Optional[ErrorContext]:
        """Analyze import errors."""
        if error_type not in ("ImportError", "ModuleNotFoundError"):
            return None

        # Extract module name
        module_pattern = r"No module named ['\"]([^'\"]+)['\"]"
        match = re.search(module_pattern, error_message)
        module = match.group(1) if match else "unknown"

        suggestions = [
            f"IMPORT ERROR - Module '{module}' not available",
            "",
            "Available libraries in execution environment:",
            "  - pandas (pd)",
            "  - numpy (np)",
            "  - matplotlib.pyplot (plt)",
            "  - plotly.express (px)",
            "  - plotly.graph_objects (go)",
            "  - seaborn (sns)",
            "  - scipy.stats (stats)",
            "  - sklearn (scikit-learn)",
            "",
            "Solutions:",
            f"1. If '{module}' is a typo, fix the import",
            f"2. Use alternative library from available list",
            f"3. If essential, inform user that library is not available",
            "",
            "Common alternatives:",
            "  - Use pandas instead of openpyxl for Excel",
            "  - Use scipy.stats instead of statsmodels",
            "  - Use sklearn instead of tensorflow/pytorch",
        ]

        return ErrorContext(
            original_error=error_message,
            error_type=error_type,
            enhanced_message=f"Module '{module}' not available in execution environment",
            suggestions=suggestions
        )

    # ============================================================================
    # GENERIC ERROR ANALYZERS
    # ============================================================================

    def _analyze_type_error(
        self,
        error_message: str,
        error_type: str,
        traceback: str,
        code: str
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
        code: str
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
        code: str
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

    def format_for_llm(self, context: ErrorContext) -> str:
        """
        Format error context for LLM consumption.

        Returns a formatted string that provides maximum helpful context
        for the LLM to fix the error during auto-retry.
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

        if context.relevant_docs:
            formatted += f"\n\nRELEVANT DOCUMENTATION:\n{context.relevant_docs}"

        return formatted
