"""
Execution Service for running Python code and capturing results.

This service handles the execution of Python code generated from prompts,
capturing outputs, plots, tables, and handling errors safely.
"""

import sys
import io
import traceback
import base64
import time
import logging
import warnings
import ast
import difflib
import re
import types
import json
from contextlib import redirect_stdout, redirect_stderr
from typing import Dict, Any, List, Optional, Tuple
import matplotlib
import matplotlib.pyplot as plt
import plotly
import pandas as pd
import numpy as np

from ..models.notebook import ExecutionResult, ExecutionStatus, sanitize_for_json
from ..models.linting import LintIssue, LintReport, LintSeverity
from .linting_service import LintingService
from .autofix_service import AutofixService

# Configure matplotlib for non-interactive backend
matplotlib.use('Agg')

# Suppress matplotlib non-interactive backend warnings
warnings.filterwarnings('ignore', message='.*non-interactive.*')
warnings.filterwarnings('ignore', category=UserWarning, module='matplotlib.*')

logger = logging.getLogger(__name__)


class ExecutionService:
    """Service for executing Python code and capturing rich outputs."""
    
    def __init__(self):
        """Initialize the execution service."""
        logger.info("🚀 INITIALIZING EXECUTION SERVICE")
        
        try:
            from .data_manager_clean import get_data_manager
            logger.info("✅ Imported data_manager_clean")
            
            # Get the data manager to set up workspace  
            self.data_manager = get_data_manager()
            logger.info(f"✅ Got data manager: {type(self.data_manager)}")
            
            # Set working directory to the notebook working directory
            import os
            working_dir = self.data_manager.get_working_directory()
            logger.info(f"📁 Setting working directory to: {working_dir}")
            os.chdir(str(working_dir))
            logger.info(f"✅ Changed to working directory: {os.getcwd()}")
            
            logger.info(f"📊 Execution service initialized:")
            logger.info(f"   Working directory: {os.getcwd()}")
            logger.info(f"   Data directory: {self.data_manager.data_dir}")
            logger.info(f"   Data dir exists: {os.path.exists(self.data_manager.data_dir)}")
            logger.info(f"   Available files: {len(self.data_manager.list_available_files())}")
            
            files = self.data_manager.list_available_files()
            for file in files:
                logger.info(f"     - {file['name']} at {file['path']}")
                
        except Exception as e:
            logger.error(f"💥 FAILED TO INITIALIZE EXECUTION SERVICE: {e}")
            logger.error(f"💥 Exception type: {type(e)}")
            import traceback
            logger.error(f"💥 Full traceback:\n{traceback.format_exc()}")
            raise
        
        # Per-notebook execution environments for complete isolation
        self.notebook_globals: Dict[str, Dict[str, Any]] = {}
        self.execution_count = 0

        # Execution environment seed management (separate from LLM seed)
        self.notebook_execution_seeds: Dict[str, Optional[int]] = {}  # Per-notebook seeds

        # Global figure/table counters per notebook for sequential numbering across entire article
        self.notebook_table_counters: Dict[str, int] = {}  # Table 1, 2, 3... per notebook
        self.notebook_figure_counters: Dict[str, int] = {}  # Figure 1, 2, 3... per notebook

        # State persistence service for automatic save/restore across backend restarts
        from .state_persistence_service import StatePersistenceService
        self.state_persistence = StatePersistenceService()
    
    def _initialize_globals(self) -> Dict[str, Any]:
        """Initialize the global namespace for code execution."""

        # Import datetime for helper functions
        from datetime import timedelta, datetime, date

        # Helper function: Safe timedelta that handles numpy types
        def safe_timedelta(**kwargs):
            """
            Create timedelta with automatic numpy type conversion.

            Usage:
                safe_timedelta(days=numpy_int64_value)
                safe_timedelta(hours=5, minutes=30)
            """
            converted_kwargs = {}
            for key, value in kwargs.items():
                # Convert numpy types to Python native types
                if hasattr(value, 'item'):  # numpy scalar
                    converted_kwargs[key] = value.item()
                elif isinstance(value, (np.integer, np.floating)):
                    converted_kwargs[key] = value.item()
                else:
                    converted_kwargs[key] = value
            return timedelta(**converted_kwargs)

        # Helper function: Convert numpy types to Python types
        def to_python_type(value):
            """
            Convert numpy types to Python native types.

            Usage:
                python_int = to_python_type(numpy_int64_value)
                python_list = to_python_type(numpy_array)
            """
            # Check array/series types first (they also have .item() but for single elements)
            if isinstance(value, np.ndarray):
                return value.tolist()
            elif isinstance(value, pd.Series):
                return value.tolist()
            elif isinstance(value, pd.DataFrame):
                return value.to_dict('records')
            elif hasattr(value, 'item') and not isinstance(value, (np.ndarray, pd.Series)):
                # numpy scalar has .item()
                return value.item()
            elif isinstance(value, (np.integer, np.floating, np.bool_)):
                return value.item()
            else:
                return value

        # Helper function: Safe int/float conversion
        def safe_int(value):
            """Convert value to int, handling numpy types."""
            if hasattr(value, 'item'):
                return int(value.item())
            return int(value)

        def safe_float(value):
            """Convert value to float, handling numpy types."""
            if hasattr(value, 'item'):
                return float(value.item())
            return float(value)

        # Display function: Explicitly mark results for article display
        def display(obj, label=None):
            """
            Mark an object for display in the article.

            This function explicitly registers results (tables, figures) to be shown
            in the article view with proper sequential numbering across the entire article.

            Args:
                obj: The object to display (DataFrame, matplotlib figure, plotly figure, etc.)
                label: Optional custom label (e.g., "Table 1: Patient Demographics")
                       If not provided, will be auto-numbered sequentially (Table 1, 2, 3... Figure 1, 2, 3...)

            Returns:
                The object (for chaining or further use)

            Examples:
                display(df)  # Auto-numbered: Table 1, Table 2, etc. (sequential across article)
                display(stats_df, "Table 1: Summary Statistics")  # Custom label
                display(fig, "Figure 1: Age Distribution")  # Custom label for figure
            """
            # Initialize results registry if it doesn't exist
            if not hasattr(display, 'results'):
                display.results = []

            # Register the result (numbering will be done during capture with global counters)
            display.results.append({
                'object': obj,
                'label': label,  # None means auto-number during capture
                'type': type(obj).__name__
            })

            # Print preview to console for immediate feedback
            # Note: Label might be None here if auto-numbering, will be assigned during capture
            if isinstance(obj, pd.DataFrame):
                preview_label = label if label else "[Will be auto-numbered]"
                print(f"\n{preview_label}:")
                print(obj)
            elif hasattr(obj, '__str__') and label:
                print(f"\n{label}:")
                print(obj)

            return obj

        # Override plt.show() to prevent warnings about non-interactive backend
        # Plots are captured automatically, so showing them is not needed
        def noop_show(*args, **kwargs):
            """No-op replacement for plt.show() to prevent non-interactive backend warnings."""
            pass

        # Replace plt.show with no-op version
        plt.show = noop_show

        globals_dict = {
            '__builtins__': __builtins__,
            'pd': pd,
            'np': np,
            'plt': plt,
            'px': None,  # Will import plotly.express lazily
            'go': None,  # Will import plotly.graph_objects lazily
            'sns': None,  # Will import seaborn lazily
            'stats': None,  # Will import scipy.stats lazily
            # Add datetime types
            'timedelta': timedelta,
            'datetime': datetime,
            'date': date,
            # Add helper functions for type safety
            'safe_timedelta': safe_timedelta,
            'to_python_type': to_python_type,
            'safe_int': safe_int,
            'safe_float': safe_float,
            # Add display function for explicit result registration
            'display': display,
        }

        # Lazy import function for heavy libraries
        def lazy_import(module_path: str, alias: str):
            if globals_dict[alias] is None:
                try:
                    # Import the full module path directly
                    parts = module_path.split('.')
                    if len(parts) == 1:
                        # Simple import like 'pandas'
                        module = __import__(module_path)
                    else:
                        # Complex import like 'plotly.express' or 'plotly.graph_objects'
                        module = __import__(module_path, fromlist=[parts[-1]])
                    globals_dict[alias] = module
                except ImportError as e:
                    logger.warning(f"Failed to import {module_path}: {e}")
                    globals_dict[alias] = None
            return globals_dict[alias]

        # Add lazy import helpers
        globals_dict['_lazy_import'] = lazy_import

        logger.info("✅ Initialized execution globals with type safety helpers")
        logger.info("   Available helpers: safe_timedelta, to_python_type, safe_int, safe_float")

        return globals_dict

    def _get_notebook_globals(self, notebook_id: str) -> Dict[str, Any]:
        """
        Get or create the globals dictionary for a specific notebook.

        This method attempts to restore previously saved state before creating
        a new execution environment, enabling seamless continuation of work
        across backend restarts.

        Args:
            notebook_id: Unique identifier for the notebook

        Returns:
            The globals dictionary for this notebook
        """
        if notebook_id not in self.notebook_globals:
            # Try to restore from saved state first
            saved_state = self.state_persistence.load_notebook_state(notebook_id)

            if saved_state:
                # State restored - merge with fresh globals for built-ins
                logger.info(f"✅ Restored execution state for notebook {notebook_id} "
                           f"({len(saved_state)} variables)")
                # Start with fresh globals (includes imports and helpers)
                fresh_globals = self._initialize_globals()
                # Merge saved state on top (user variables take precedence)
                fresh_globals.update(saved_state)
                self.notebook_globals[notebook_id] = fresh_globals
            else:
                # No saved state - create fresh environment
                logger.info(f"🆕 Creating new execution environment for notebook {notebook_id}")
                self.notebook_globals[notebook_id] = self._initialize_globals()

        return self.notebook_globals[notebook_id]

    # NOTE:
    # Figure/table numbering is now handled by `NotebookAssetNumberingService` at the
    # notebook level (execution-order independent). ExecutionService should only
    # capture raw outputs; numbering is applied deterministically before save/return.

    def set_notebook_execution_seed(self, notebook_id: str, seed: Optional[int] = None):
        """
        Set random seed for the execution environment (separate from LLM seed).

        This ensures that when generated code runs random operations like np.random.randn(),
        the results are consistent per notebook.

        Args:
            notebook_id: Notebook identifier
            seed: Random seed (if None, checks for custom seed then uses notebook_id hash)
        """
        if seed is None:
            # Check for custom seed first
            if hasattr(self, '_custom_seeds') and notebook_id in self._custom_seeds:
                seed = self._custom_seeds[notebook_id]
            else:
                # Generate consistent seed from notebook_id hash
                import hashlib
                seed = int(hashlib.md5(notebook_id.encode()).hexdigest()[:8], 16) % (2**31)

        # Store seed for this notebook
        self.notebook_execution_seeds[notebook_id] = seed

        # Set seeds in the execution environment
        import random
        import numpy as np

        random.seed(seed)
        np.random.seed(seed)

        # Also set in notebook-specific globals_dict so user code can access if needed
        globals_dict = self._get_notebook_globals(notebook_id)
        globals_dict['_notebook_execution_seed'] = seed

        logger.info(f"🎲 Set execution environment seed: {seed} for notebook {notebook_id}")

    def validate_code_syntax(self, code: str) -> Tuple[bool, Optional[str], Optional[List[str]]]:
        """
        Validate Python code for syntax errors and common anti-patterns.

        This catches errors BEFORE execution to provide immediate feedback to the LLM.

        Args:
            code: Python code to validate

        Returns:
            Tuple of (is_valid, error_message, suggestions)
        """
        suggestions = []

        # Phase 1: Check for basic Python syntax using AST
        try:
            ast.parse(code)
        except SyntaxError as e:
            error_msg = f"Syntax Error on line {e.lineno}: {e.msg}"

            # Provide helpful suggestions for common syntax errors
            if "invalid syntax" in str(e.msg).lower():
                # Check for common mistakes around the error line
                lines = code.split('\n')
                if 0 <= e.lineno - 1 < len(lines):
                    error_line = lines[e.lineno - 1]

                    # Detect function call written as assignment (e.g., random.choice=)
                    if re.search(r'\w+\.\w+\s*=\s*[^\s]', error_line):
                        suggestions.append("CRITICAL: You wrote an assignment (=) instead of a function call ()")
                        suggestions.append("Example: 'random.choice=' should be 'random.choice()'")
                        suggestions.append(f"Problem line: {error_line.strip()}")

                    # Detect missing parentheses for function calls
                    if re.search(r'(random|np|pd)\.\w+\s*=', error_line):
                        suggestions.append("You appear to be calling a function but used '=' instead of '()'")
                        suggestions.append("Functions must be called with parentheses: function_name()")

            return False, error_msg, suggestions
        except Exception as e:
            return False, f"Code parsing error: {str(e)}", ["Code could not be parsed - check for syntax errors"]

        # Phase 2: Check for anti-patterns and common mistakes
        lines = code.split('\n')
        line_num = 0

        for line in lines:
            line_num += 1
            stripped = line.strip()

            # Skip empty lines and comments
            if not stripped or stripped.startswith('#'):
                continue

            # Anti-pattern 1: Function call written as assignment
            # Example: random.choice= instead of random.choice()
            if re.search(r'(\w+\.\w+)\s*=(?!=)', stripped):
                # Check if it's actually trying to call a function (not a variable assignment)
                # CRITICAL: Use \b word boundary to avoid false positives like "summary_stats.columns"
                # matching "stats" as a module name
                match = re.search(r'\b(random|np|pd|plt|sns|stats)\.\w+\s*=', stripped)
                if match:
                    return (False,
                           f"Anti-pattern detected on line {line_num}: Function call written as assignment",
                           [
                               f"Line {line_num}: '{stripped}'",
                               "This looks like you're trying to call a function but used '=' instead of '()'",
                               "CORRECT: random.choice(['A', 'B'])",
                               "WRONG: random.choice=['A', 'B']",
                               "Functions from libraries (random, np, pd, etc.) must be called with parentheses"
                           ])

            # Anti-pattern 2: Missing parentheses for function calls in list comprehensions
            if re.search(r'random\.choice\[', stripped):
                return (False,
                       f"Anti-pattern detected on line {line_num}: Square brackets used instead of parentheses",
                       [
                           f"Line {line_num}: '{stripped}'",
                           "You used square brackets [] but functions need parentheses ()",
                           "CORRECT: random.choice(items)",
                           "WRONG: random.choice[items]"
                       ])

            # Anti-pattern 3: Trying to call built-in functions incorrectly
            if re.search(r'\b(int|float|str|list|dict|tuple)\[', stripped) and '=' in stripped:
                return (False,
                       f"Anti-pattern detected on line {line_num}: Type conversion with wrong syntax",
                       [
                           f"Line {line_num}: '{stripped}'",
                           "Type conversion functions need parentheses (), not brackets []",
                           "CORRECT: int(value), float(value), str(value)",
                           "WRONG: int[value], float[value], str[value]"
                       ])

        # Phase 3: Check for imports without usage
        # (This is informational, not an error)
        imported_modules = set()
        used_modules = set()

        for line in lines:
            stripped = line.strip()
            # Track imports
            if stripped.startswith('import ') or stripped.startswith('from '):
                # Extract module name
                if 'import' in stripped:
                    parts = stripped.split()
                    if 'as' in parts:
                        alias_idx = parts.index('as') + 1
                        if alias_idx < len(parts):
                            imported_modules.add(parts[alias_idx])
                    elif stripped.startswith('import '):
                        imported_modules.add(parts[1].split('.')[0])

            # Track usage (simple heuristic)
            for module in ['pd', 'np', 'plt', 'px', 'go', 'sns', 'stats']:
                if module + '.' in stripped or module + '(' in stripped:
                    used_modules.add(module)

        # All validation passed
        return True, None, None
    
    def execute_code(
        self,
        code: str,
        cell_id: str,
        notebook_id: Optional[str] = None,
        autofix: bool = True,
        capture_outputs: bool = True,
        persist_state: bool = True,
    ) -> ExecutionResult:
        """
        Execute Python code and capture all outputs.

        Args:
            code: Python code to execute
            cell_id: Unique identifier for the cell being executed

        Returns:
            ExecutionResult containing all outputs and metadata
        """
        result = ExecutionResult()
        start_time = time.time()
        original_code = code

        # Determine notebook context early (needed for safe pre-validation autofix).
        # Use notebook-specific data manager if provided
        if notebook_id:
            from .data_manager_clean import get_data_manager
            notebook_data_manager = get_data_manager(notebook_id)
            working_dir = notebook_data_manager.get_working_directory()

            # Set notebook-specific execution environment seed for consistency
            if notebook_id not in self.notebook_execution_seeds:
                self.set_notebook_execution_seed(notebook_id)
        else:
            # Fallback for backward compatibility (shouldn't happen in normal use)
            working_dir = self.data_manager.get_working_directory()
            notebook_id = "default"
            logger.warning("⚠️ No notebook_id provided - using default namespace")

        # Get or create notebook-specific globals (may restore saved state)
        globals_dict = self._get_notebook_globals(notebook_id)

        # PHASE 0: Default-on safe autofix BEFORE validation/first execution (no LLM involved)
        autofix_changes: List[Any] = []
        if autofix:
            try:
                autofix_service = AutofixService()
                fixed_code, pre_changes = autofix_service.apply_pre_validation_fixes(code, globals_dict=globals_dict)
                if pre_changes and fixed_code != code:
                    autofix_changes.extend(pre_changes)
                    code = fixed_code
            except Exception as autofix_err:
                logger.warning(f"Pre-validation autofix failed (non-fatal): {autofix_err}")

        # PHASE 1: Validate code syntax and anti-patterns BEFORE execution
        is_valid, error_msg, suggestions = self.validate_code_syntax(code)

        if not is_valid:
            logger.error(f"❌ CODE VALIDATION FAILED for cell {cell_id}")
            logger.error(f"   Error: {error_msg}")
            if suggestions:
                logger.error("   Suggestions:")
                for suggestion in suggestions:
                    logger.error(f"     - {suggestion}")

            # Return validation error immediately (don't waste execution attempt)
            result.status = ExecutionStatus.ERROR
            result.error_type = "ValidationError"
            result.error_message = error_msg

            # Attach structured lint report (so UI can surface the failure cleanly)
            lint_issues = [
                LintIssue(
                    severity=LintSeverity.ERROR,
                    rule_id="DA0002",
                    message=error_msg or "Code validation failed",
                    suggestion="Fix validation errors before execution.",
                    fixable=False,
                )
            ]
            if suggestions:
                for s in suggestions:
                    lint_issues.append(
                        LintIssue(
                            severity=LintSeverity.INFO,
                            rule_id="DA0002_SUGGESTION",
                            message=s,
                            fixable=False,
                        )
                    )
            result.lint_report = LintReport(engine="builtin", issues=lint_issues)

            # Format helpful error message with suggestions
            if suggestions:
                suggestion_text = "\n".join(f"  • {s}" for s in suggestions)
                result.stderr = f"CODE VALIDATION FAILED:\n{error_msg}\n\nSUGGESTIONS:\n{suggestion_text}"
                result.traceback = f"Validation failed - code did not pass syntax checks\n\n{error_msg}\n\nCommon fixes:\n{suggestion_text}"
            else:
                result.stderr = f"CODE VALIDATION FAILED:\n{error_msg}"
                result.traceback = f"Validation failed - code did not pass syntax checks\n\n{error_msg}"

            result.execution_time = time.time() - start_time
            logger.error(f"💥 Returning validation error result (no execution attempted)")
            return result

        logger.info(f"✅ Code validation passed for cell {cell_id}")

        # PHASE 2: Lint report (non-blocking warnings) using available notebook globals
        # This is intentionally deterministic and offline (no network calls).
        linter = LintingService()
        lint_before_for_report: Optional[LintReport] = None
        try:
            lint_before_for_report = linter.lint(original_code, available_globals=globals_dict)
        except Exception as lint_error:
            logger.warning(f"Linting failed (non-fatal): {lint_error}")

        try:
            lint_before_exec = linter.lint(code, available_globals=globals_dict)
        except Exception as lint_error:
            logger.warning(f"Linting failed (non-fatal): {lint_error}")
            lint_before_exec = None

        # PHASE 3: Default-on safe autofix (deterministic, allowlisted)
        if autofix and lint_before_exec is not None:
            try:
                autofix_service = AutofixService()
                lint_fix_report = autofix_service.apply_safe_autofix(
                    code,
                    lint_before=lint_before_exec,
                    globals_dict=globals_dict,
                )

                if lint_fix_report.applied and lint_fix_report.fixed_code:
                    # Safety: validate fixed code before executing it
                    fixed_is_valid, fixed_error, _fixed_suggestions = self.validate_code_syntax(lint_fix_report.fixed_code)
                    if fixed_is_valid:
                        code = lint_fix_report.fixed_code
                        autofix_changes.extend(lint_fix_report.changes)
                        # Recompute lint report for the code we will actually execute
                        result.lint_report = linter.lint(code, available_globals=globals_dict)
                    else:
                        logger.warning(f"Autofix produced invalid code; skipping. Error: {fixed_error}")
                        result.lint_report = lint_before_exec
                else:
                    result.lint_report = lint_before_exec
            except Exception as autofix_error:
                logger.warning(f"Autofix failed (non-fatal): {autofix_error}")
                result.lint_report = lint_before_exec
        else:
            result.lint_report = lint_before_exec

        # Attach autofix report only when something actually changed (keeps UI noise low).
        if autofix and autofix_changes and code != original_code:
            try:
                from ..models.autofix import AutofixReport

                result.autofix_report = AutofixReport(
                    enabled=True,
                    applied=True,
                    original_code=original_code,
                    fixed_code=code,
                    diff="\n".join(
                        difflib.unified_diff(
                            original_code.splitlines(),
                            code.splitlines(),
                            fromfile="before.py",
                            tofile="after.py",
                            lineterm="",
                        )
                    ),
                    changes=autofix_changes,
                    lint_before=lint_before_for_report,
                    lint_after=result.lint_report,
                )
            except Exception as report_error:
                logger.warning(f"Failed to build autofix report (non-fatal): {report_error}")

        # Ensure we're in the correct working directory for this notebook
        import os
        if str(working_dir) != os.getcwd():
            os.chdir(str(working_dir))

        # Prepare output capture
        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()

        try:
            # Configure warnings to be written to stderr
            warnings.simplefilter('always')  # Show all warnings
            # But suppress the specific non-interactive matplotlib warning
            warnings.filterwarnings('ignore', message='.*non-interactive.*')
            warnings.filterwarnings('ignore', message='.*FigureCanvasAgg.*')

            # Clear any existing plots
            plt.clf()
            plt.close('all')

            # Clear display() results from previous execution (each cell starts fresh)
            if 'display' in globals_dict and hasattr(globals_dict['display'], 'results'):
                globals_dict['display'].results = []
                logger.debug("🧹 Cleared previous display() results")

            # Track variables before execution to only capture new DataFrames
            pre_execution_vars = set(globals_dict.keys())
            pre_execution_dataframes = {
                name: obj for name, obj in globals_dict.items()
                if isinstance(obj, pd.DataFrame) and not name.startswith('_')
            }

            # Track Plotly figures before execution to only capture new ones
            # This prevents figures from previous cells from being re-captured
            # We track by object ID (memory address) to detect if a variable is reassigned to a new figure
            pre_execution_plotly_figures = {
                name: id(obj) for name, obj in globals_dict.items()
                if hasattr(obj, 'to_dict') and hasattr(obj, 'data') and hasattr(obj, 'layout')
                and not name.startswith('_')
            }

            # Add lazy imports to code if needed
            processed_code = self._preprocess_code(code)

            # Prepare namespace for imports (remove shadowing variables)
            # This ensures imports always succeed even if variables with the same name exist
            self._prepare_imports(processed_code, globals_dict)

            # Execute the code with output redirection in notebook-specific namespace
            with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
                exec(processed_code, globals_dict)
            
            # Capture outputs
            result.stdout = stdout_buffer.getvalue()
            result.stderr = stderr_buffer.getvalue()
            result.status = ExecutionStatus.SUCCESS

            if capture_outputs:
                # Capture visualizations and rich outputs
                # 1. First capture explicitly displayed results (highest priority)
                # Pass notebook_id for sequential numbering across entire article
                displayed_tables, displayed_plots, other_displays = self._capture_displayed_results(globals_dict, notebook_id)

                # CRITICAL: Sanitize all data to convert numpy types (including new numpy.dtypes.*)
                # to JSON-serializable Python types BEFORE storing in Pydantic models
                displayed_tables = sanitize_for_json(displayed_tables)
                displayed_plots = sanitize_for_json(displayed_plots)
                other_displays = sanitize_for_json(other_displays)

                result.tables = displayed_tables + other_displays  # Include HTML, JSON, text, model displays
                result.plots = displayed_plots  # Start with explicitly displayed plots
                logger.info(
                    f"✅ Captured {len(displayed_tables)} table(s), {len(displayed_plots)} plot(s), {len(other_displays)} other display(s)"
                )

                # 2. Then capture other outputs (auto-captured plots with sequential numbering)
                auto_plots = self._capture_plots(notebook_id)
                auto_plots = sanitize_for_json(auto_plots)  # Sanitize numpy types
                result.plots.extend(auto_plots)  # Add auto-captured plots after displayed ones
                logger.info(f"📊 Captured {len(auto_plots)} additional auto-captured plot(s)")

                interactive_plots = self._capture_interactive_plots(globals_dict, notebook_id, pre_execution_plotly_figures)
                result.interactive_plots = sanitize_for_json(interactive_plots)  # Sanitize numpy types

                # 3. Capture intermediary DataFrame variables (for debugging in Execution Details)
                variable_tables = self._capture_tables(globals_dict, pre_execution_vars, pre_execution_dataframes)
                variable_tables = sanitize_for_json(variable_tables)  # Sanitize numpy types
                result.tables.extend(variable_tables)

                # Stdout table parsing (compatibility + quality of life):
                # - `display(df)` remains the recommended way to explicitly include tables in the article view
                # - but we still parse `print(df)` output so users (and tests) get structured tables
                stdout_tables = self._parse_pandas_stdout(result.stdout)
                if stdout_tables:
                    logger.info(f"📊 Parsed {len(stdout_tables)} table(s) from stdout")
                    stdout_tables = sanitize_for_json(stdout_tables)  # Sanitize numpy types
                    for table in stdout_tables:
                        table['source'] = 'stdout'
                    result.tables.extend(stdout_tables)

                self.execution_count += 1
                logger.info(f"Successfully executed cell {cell_id}")

                # Check for statistical warnings in the output (stdout and tables)
                statistical_warnings = self._check_statistical_warnings(result.stdout, result.tables)
                if statistical_warnings:
                    result.warnings.extend(statistical_warnings)
                    logger.warning(f"⚠️ Statistical validation found {len(statistical_warnings)} warning(s):")
                    for warning in statistical_warnings:
                        logger.warning(f"   {warning}")
            else:
                # Context-rebuild mode: we only care about side effects in globals, not user-visible outputs.
                # Critically, we do NOT want to renumber/capture tables/figures during upstream replay.
                logger.debug("Context-only execution: skipping rich output capture")

            # Auto-save notebook state after successful execution
            if persist_state and notebook_id:
                try:
                    self.state_persistence.save_notebook_state(
                        notebook_id,
                        globals_dict
                    )
                except Exception as save_error:
                    # State save failure shouldn't break execution
                    logger.error(f"Failed to save state for notebook {notebook_id}: {save_error}")

        except Exception as e:
            logger.error(f"💥 EXECUTION EXCEPTION CAUGHT: {type(e).__name__}: {e}")
            
            # Capture COMPLETE error information
            full_traceback = traceback.format_exc()
            stderr_content = stderr_buffer.getvalue() if 'stderr_buffer' in locals() else ""
            
            result.status = ExecutionStatus.ERROR
            result.error_type = type(e).__name__
            # Provide actionable guidance for common environment errors.
            if isinstance(e, ModuleNotFoundError):
                missing = getattr(e, "name", None)
                if missing:
                    result.error_message = (
                        f"{str(e)}\n\n"
                        f"HINT: Missing Python package '{missing}'. Install it (e.g. `pip install {missing}`)\n"
                        f"or install backend dependencies (`pip install -e backend`)."
                    )
                else:
                    result.error_message = str(e)
            else:
                result.error_message = str(e)
            result.traceback = full_traceback
            result.stderr = stderr_content + "\n\nFULL PYTHON STACK TRACE:\n" + full_traceback
            
            logger.error(f"💥 PYTHON EXECUTION FAILED for cell {cell_id}")
            logger.error(f"💥 Exception type: {type(e).__name__}")
            logger.error(f"💥 Exception message: {str(e)}")
            logger.error(f"💥 Working directory: {os.getcwd()}")
            logger.error(f"💥 Code that failed:\n{code}")
            logger.error(f"💥 COMPLETE STACK TRACE:\n{full_traceback}")
            logger.error(f"💥 Stderr output: {stderr_content}")
            
            # Environment debugging
            logger.error(f"🔍 ENVIRONMENT DEBUG:")
            logger.error(f"   Current directory: {os.getcwd()}")
            logger.error(f"   Data directory exists: {os.path.exists('data')}")
            if os.path.exists('data'):
                logger.error(f"   Files in data: {os.listdir('data')}")
            else:
                logger.error(f"   NO DATA DIRECTORY FOUND!")
                logger.error(f"   Current directory contents: {os.listdir('.')}")
                
            # Check Python environment
            import sys
            logger.error(f"🐍 PYTHON ENVIRONMENT:")
            logger.error(f"   Python executable: {sys.executable}")
            logger.error(f"   Python path: {sys.path[:3]}...")  # First 3 entries
            
            # Don't re-raise - return the error result instead
            logger.error(f"💥 Returning error result instead of re-raising")
        
        finally:
            result.execution_time = time.time() - start_time

        return result

    def _check_statistical_warnings(self, stdout: str, tables: List[Dict[str, Any]] = None) -> List[str]:
        """Check for statistical red flags in execution results.

        Scans stdout and displayed tables for common issues that indicate methodological problems:
        - Parameters at optimizer bounds (unreliable estimates)
        - Impossible confidence intervals (negative clearance, etc.)
        - Poor parameter precision (%CV > 150%)

        Args:
            stdout: Standard output from code execution
            tables: Optional list of displayed tables to scan for statistical warnings

        Returns:
            List of warning messages
        """
        warnings_list = []

        # Check for parameters at optimizer bounds
        if re.search(r'(?:at|hit|reached|hitting)\s*(?:lower|upper)?\s*bound', stdout, re.I):
            warnings_list.append("⚠️ STATISTICAL: Parameter(s) may be at optimizer bounds - results unreliable. Consider different initial values or model structure.")

        # Check for impossible confidence intervals (negative values for positive-only parameters)
        ci_matches = re.findall(r'95%\s*CI[:\s]+\[?([-\d.]+)[,\s]+to[,\s]+([-\d.]+)', stdout, re.I)
        for lower_str, upper_str in ci_matches:
            try:
                lower = float(lower_str)
                # Check if CI includes negative values for parameters that must be positive
                if lower < 0:
                    # Common positive-only parameters in pharmacometrics
                    if re.search(r'\b(?:clearance|CL|Vd|volume|rate|constant|k)\b', stdout, re.I):
                        warnings_list.append(f"🚨 CRITICAL: Confidence interval [{lower_str}, {upper_str}] includes impossible negative values for a positive parameter. This indicates severe model misspecification or inappropriate methodology.")
                        break  # Only report once
            except ValueError:
                pass

        # Check for poor parameter precision (%CV > 150%)
        cv_matches = re.findall(r'%CV[:\s]+([\d.]+)', stdout, re.I)
        for cv_str in cv_matches:
            try:
                cv = float(cv_str)
                if cv > 150:
                    warnings_list.append(f"⚠️ STATISTICAL: %CV of {cv}% indicates very poor parameter precision (typically %CV < 50% is acceptable). Consider more data or simpler model.")
            except ValueError:
                pass

        # NEW: Also scan displayed tables for statistical red flags
        if tables:
            for table in tables:
                columns = table.get('columns', [])
                data = table.get('data', [])

                # Find %CV column (case-insensitive, look for %CV, CV, or coefficient of variation)
                cv_col = None
                for col in columns:
                    col_lower = str(col).lower()
                    if '%cv' in col_lower or col_lower == 'cv' or 'coefficient' in col_lower:
                        cv_col = col
                        break

                # Check %CV values in table
                if cv_col and data:
                    for row in data:
                        cv_value = row.get(cv_col)
                        if isinstance(cv_value, (int, float)) and cv_value > 100:
                            # Try to get parameter name from row
                            param_name = row.get('Parameter', row.get('parameter', row.get('param', 'Unknown')))
                            if cv_value > 1000:
                                warnings_list.append(f"🚨 CRITICAL: {param_name} has %CV = {cv_value:.1f}% - parameter is essentially unidentifiable. Model cannot be reliably estimated from this data.")
                            else:
                                warnings_list.append(f"⚠️ STATISTICAL: {param_name} has %CV = {cv_value:.1f}% (>100%) - poor parameter precision. Consider more data or simpler model.")

                # Check for parameters at common optimizer bounds
                # ONLY if this looks like a statistical modeling output table
                # (must have a Parameter/param column AND specific estimate column, not just any table with values)

                # First, find a parameter name column (required for modeling tables)
                param_col = None
                for col in columns:
                    col_lower = str(col).lower()
                    if col_lower in ['parameter', 'param', 'name', 'variable']:
                        param_col = col
                        break

                # Find estimate column (exclude generic columns that cause false positives)
                estimate_col = None
                generic_columns = {'value', 'count', 'total', 'n', 'frequency', 'metric', 'number', 'qty'}
                for col in columns:
                    col_lower = str(col).lower()
                    # Only match specific statistical estimate columns, not generic "value" columns
                    if col_lower in generic_columns:
                        continue  # Skip generic columns
                    if 'estimate' in col_lower or 'fitted' in col_lower or 'mle' in col_lower or 'coefficient' in col_lower:
                        estimate_col = col
                        break

                # Only proceed if we have BOTH a parameter column AND a proper estimate column
                # This ensures we only check actual statistical modeling output, not summary tables
                if param_col and estimate_col and data:
                    # Common optimizer bounds in PK/PD modeling
                    common_bounds = {0.1, 1.0, 10.0, 100.0, 0.01, 0.001, 1000.0, 0.0001, 10000.0}
                    for row in data:
                        est_value = row.get(estimate_col)
                        if isinstance(est_value, (int, float)):
                            # Get parameter name from the parameter column
                            param_name = row.get(param_col, 'Unknown')
                            # Check if value matches a common bound (within floating point tolerance)
                            for bound in common_bounds:
                                if abs(est_value - bound) < 1e-6:
                                    warnings_list.append(f"⚠️ STATISTICAL: {param_name} = {est_value} appears to be at optimizer bounds. Parameter estimates at bounds are unreliable - consider different initial values or bounds.")
                                    break

        return warnings_list

    def get_variable_info(self, notebook_id: str) -> Dict[str, Any]:
        """
        Get categorized information about variables in the notebook-specific execution context.

        Args:
            notebook_id: Unique identifier for the notebook

        Returns:
            Dict with categorized variables:
            {
                "dataframes": {name: {type, shape, display}},
                "modules": {name: {type, module_name, display}},
                "numbers": {name: {type, value, display}},
                "dicts": {name: {type, size, display}},
                "arrays": {name: {type, shape/size, display}},  # ndarray, Series, list
                "other": {name: {type, display}}  # matplotlib objects, etc.
            }
        """
        try:
            # Get notebook-specific globals
            globals_dict = self._get_notebook_globals(notebook_id)

            # Initialize categorized storage
            categorized = {
                "dataframes": {},
                "modules": {},
                "numbers": {},
                "dicts": {},
                "arrays": {},  # Arrays & Series (ndarray, Series)
                "other": {}
            }

            for name, value in globals_dict.items():
                # Skip private variables and callables
                if name.startswith('_') or callable(value):
                    continue

                try:
                    var_type = type(value).__name__

                    # FILTER OUT: NoneType variables (import shadowing artifacts)
                    if var_type == 'NoneType' or value is None:
                        logger.debug(f"🧹 Filtering out NoneType variable '{name}' (likely import shadowing artifact)")
                        continue

                    # CATEGORY 1: DataFrames
                    if hasattr(value, 'columns') and hasattr(value, 'shape'):
                        categorized["dataframes"][name] = {
                            "type": var_type,
                            "shape": list(value.shape),
                            "columns": value.columns.tolist(),  # CRITICAL: Include column names for LLM
                            "display": f"{var_type} {value.shape}"
                        }

                    # CATEGORY 2: Modules (library imports)
                    elif isinstance(value, types.ModuleType):
                        module_name = getattr(value, '__name__', var_type)
                        categorized["modules"][name] = {
                            "type": "module",
                            "module_name": module_name,
                            "display": module_name
                        }

                    # CATEGORY 3: Numbers (int, float, numpy numerics)
                    elif var_type in ['int', 'float', 'int32', 'int64', 'float32', 'float64', 'complex']:
                        # Format value for display
                        if var_type in ['float', 'float32', 'float64']:
                            display_value = f"{float(value):.2f}" if abs(value) < 1000 else f"{float(value):.2e}"
                        else:
                            display_value = str(value)

                        categorized["numbers"][name] = {
                            "type": var_type,
                            "value": float(value) if 'float' in var_type else int(value),
                            "display": display_value
                        }

                    # CATEGORY 4: Dicts & JSON
                    elif var_type == 'dict':
                        size = len(value)
                        categorized["dicts"][name] = {
                            "type": "dict",
                            "size": size,
                            "display": f"dict ({size} items)"
                        }

                    # CATEGORY 5: Arrays & Series (ndarray, Series, list)
                    elif var_type in ['ndarray', 'Series'] or (hasattr(value, 'shape') and hasattr(value, 'dtype')):
                        categorized["arrays"][name] = {
                            "type": var_type,
                            "shape": getattr(value, 'shape', 'N/A'),
                            "display": f"{var_type} {getattr(value, 'shape', '')}"
                        }
                    elif var_type == 'list':
                        # Lists are array-like, group with arrays
                        size = len(value)
                        categorized["arrays"][name] = {
                            "type": "list",
                            "size": size,
                            "display": f"list ({size} items)"
                        }

                    # CATEGORY 6: Other (matplotlib objects, strings, etc.)
                    else:
                        categorized["other"][name] = {
                            "type": var_type,
                            "display": var_type
                        }

                except Exception as e:
                    logger.debug(f"Error categorizing variable '{name}': {e}")
                    categorized["other"][name] = {
                        "type": "unknown",
                        "display": "unknown"
                    }

            # Sanitize all data to handle numpy types before returning
            return sanitize_for_json(categorized)

        except Exception as e:
            logger.warning(f"Failed to get variable info for notebook {notebook_id}: {e}")
            return {
                "dataframes": {},
                "modules": {},
                "numbers": {},
                "dicts": {},
                "arrays": {},
                "other": {}
            }

    def get_variable_content(self, notebook_id: str, variable_name: str) -> Dict[str, Any]:
        """
        Get the actual content/preview of a specific variable.

        Args:
            notebook_id: Unique identifier for the notebook
            variable_name: Name of the variable to retrieve

        Returns:
            Dict with variable content and metadata
        """
        try:
            # Get notebook-specific globals
            globals_dict = self._get_notebook_globals(notebook_id)

            if variable_name not in globals_dict:
                return {"error": f"Variable '{variable_name}' not found"}

            value = globals_dict[variable_name]
            var_type = type(value).__name__

            # Return different preview formats based on type
            if hasattr(value, 'columns') and hasattr(value, 'shape'):
                # Pandas DataFrame
                preview_rows = min(100, len(value))

                # Convert to dict and replace NaN with None for JSON compatibility
                preview_data = value.head(preview_rows).to_dict('records')
                # Replace NaN values with None (JSON null)
                import math
                for row in preview_data:
                    for key in row:
                        if isinstance(row[key], float) and math.isnan(row[key]):
                            row[key] = None

                result = {
                    "type": "DataFrame",
                    "shape": value.shape,
                    "columns": value.columns.tolist(),
                    "dtypes": {col: str(dtype) for col, dtype in value.dtypes.items()},
                    "preview": preview_data,
                    "preview_rows": preview_rows,
                    "total_rows": len(value)
                }
                return sanitize_for_json(result)
            elif var_type == 'Series':
                # Pandas Series - handle separately (doesn't have .flatten())
                import math
                preview_size = min(1000, len(value))

                # Convert to list and replace NaN with None for JSON compatibility
                preview_values = value.head(preview_size).tolist()
                for i in range(len(preview_values)):
                    if isinstance(preview_values[i], float) and math.isnan(preview_values[i]):
                        preview_values[i] = None

                result = {
                    "type": "Series",
                    "shape": value.shape,
                    "dtype": str(value.dtype),
                    "name": value.name if hasattr(value, 'name') else None,
                    "preview": preview_values,
                    "preview_size": preview_size,
                    "total_size": len(value)
                }
                return sanitize_for_json(result)
            elif hasattr(value, 'shape') and hasattr(value, 'dtype'):
                # NumPy array
                import numpy as np
                import math
                preview_size = min(1000, value.size)

                # NumPy arrays have .flatten() method
                flat_values = value.flatten()[:preview_size].tolist()

                # Replace NaN with None for JSON compatibility
                for i in range(len(flat_values)):
                    if isinstance(flat_values[i], float) and math.isnan(flat_values[i]):
                        flat_values[i] = None

                result = {
                    "type": var_type,
                    "shape": getattr(value, 'shape', None),
                    "dtype": str(getattr(value, 'dtype', 'unknown')),
                    "preview": flat_values,
                    "preview_size": preview_size,
                    "total_size": value.size
                }
                return sanitize_for_json(result)
            elif isinstance(value, (list, tuple)):
                # List or tuple
                preview_size = min(100, len(value))
                result = {
                    "type": var_type,
                    "preview": list(value[:preview_size]),
                    "preview_size": preview_size,
                    "total_size": len(value)
                }
                return sanitize_for_json(result)
            elif isinstance(value, dict):
                # Dictionary
                preview_size = min(100, len(value))
                items = list(value.items())[:preview_size]

                # Convert values to JSON-serializable format
                # (e.g., LabelEncoder objects need string representation)
                serializable_dict = {}
                for k, v in items:
                    try:
                        # Try to serialize directly
                        import json
                        json.dumps(v)
                        serializable_dict[k] = v
                    except (TypeError, ValueError):
                        # Not JSON-serializable - convert to string
                        serializable_dict[k] = str(v)

                result = {
                    "type": "dict",
                    "preview": serializable_dict,
                    "preview_size": preview_size,
                    "total_size": len(value)
                }
                return sanitize_for_json(result)
            elif isinstance(value, str):
                # String
                preview_size = min(1000, len(value))
                result = {
                    "type": "str",
                    "preview": value[:preview_size],
                    "preview_size": preview_size,
                    "total_size": len(value)
                }
                return sanitize_for_json(result)
            else:
                # Scalar or other types
                result = {
                    "type": var_type,
                    "value": str(value)
                }
                return sanitize_for_json(result)

        except Exception as e:
            logger.error(f"Failed to get variable content for '{variable_name}': {e}")
            return {"error": str(e)}

    def _prepare_imports(self, code: str, globals_dict: Dict[str, Any]) -> None:
        """
        Prepare namespace for imports by removing shadowing variables.

        This ensures that import statements always succeed by deleting
        any existing variables that would shadow module imports.

        For example, if a previous cell set `stats = None`, and the current
        cell tries `from scipy import stats`, this method will delete the
        existing `stats = None` variable so the import can succeed.

        Args:
            code: Python code that may contain imports
            globals_dict: The globals dictionary to clean
        """
        # Parse the code to find import statements
        try:
            tree = ast.parse(code)
        except:
            # If we can't parse the code, just proceed - exec() will handle syntax errors
            return

        # Find all import targets
        imports_to_clean = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                # import module1, module2
                # or: import module1 as alias1
                for alias in node.names:
                    # Use the alias if provided, otherwise the module name
                    name = alias.asname if alias.asname else alias.name.split('.')[0]
                    imports_to_clean.add(name)

            elif isinstance(node, ast.ImportFrom):
                # from module import name1, name2
                # or: from module import name1 as alias1
                for alias in node.names:
                    if alias.name != '*':  # Skip wildcard imports
                        # Use the alias if provided, otherwise the imported name
                        name = alias.asname if alias.asname else alias.name
                        imports_to_clean.add(name)

        # Delete any existing variables that would shadow imports
        # Only delete if the variable is NOT already a module (safe check)
        for name in imports_to_clean:
            if name in globals_dict:
                existing_value = globals_dict[name]
                # Check if it's not already a module
                # Use isinstance(value, types.ModuleType) to properly detect modules
                if not isinstance(existing_value, types.ModuleType):
                    logger.debug(f"🧹 Clearing shadowing variable '{name}' (was {type(existing_value).__name__}) to allow import")
                    del globals_dict[name]

    def _preprocess_code(self, code: str) -> str:
        """
        Preprocess code to handle lazy imports and add necessary setup.

        Args:
            code: Original Python code

        Returns:
            Processed code with lazy imports resolved
        """
        lines = code.split('\n')
        processed_lines = []
        
        # Add plotly configuration at the beginning if plotly is used
        has_plotly = any('plotly' in line for line in lines)
        if has_plotly:
            processed_lines.extend([
                "# Configure plotly for inline display",
                "import plotly.io as pio",
                "pio.renderers.default = 'json'  # Capture plots as JSON instead of showing in browser",
                ""
            ])
        
        for line in lines:
            # Handle common import patterns with lazy loading
            if 'import plotly.express as px' in line:
                processed_lines.append("px = _lazy_import('plotly.express', 'px')")
            elif 'import plotly.graph_objects as go' in line:
                processed_lines.append("go = _lazy_import('plotly.graph_objects', 'go')")
            elif 'from plotly.subplots import make_subplots' in line:
                processed_lines.append("from plotly.subplots import make_subplots")
            elif 'import seaborn as sns' in line:
                processed_lines.append("sns = _lazy_import('seaborn', 'sns')")
            elif 'import scipy.stats as stats' in line:
                processed_lines.append("stats = _lazy_import('scipy.stats', 'stats')")
            elif 'from sklearn' in line:
                # Handle sklearn imports
                processed_lines.append(line)
            elif '.show()' in line and ('fig' in line or 'plot' in line):
                # Replace .show() calls with variable assignment to capture the plot
                # This prevents plots from opening in new browser tabs
                if '=' not in line:  # Only if it's not already assigned
                    # Extract the figure variable name
                    fig_var = line.split('.show()')[0].strip()
                    processed_lines.append(f"# Capture plot for inline display instead of showing in browser")
                    processed_lines.append(f"_captured_plot = {fig_var}")
                else:
                    processed_lines.append(line)
            else:
                processed_lines.append(line)
        
        return '\n'.join(processed_lines)
    
    def _capture_plots(self, notebook_id: str) -> List[Dict[str, Any]]:
        """
        Capture matplotlib plots as base64-encoded PNG images.
        
        Args:
            notebook_id: Notebook ID (kept for backward compatibility; numbering is applied later)
        
        Returns:
            List of plot dictionaries with image data (labels are assigned later)
        """
        plots = []
        
        try:
            # Get all figure numbers
            fig_nums = plt.get_fignums()
            
            for fig_num in fig_nums:
                fig = plt.figure(fig_num)
                
                # Save figure to bytes buffer
                buffer = io.BytesIO()
                fig.savefig(buffer, format='png', bbox_inches='tight', dpi=150)
                buffer.seek(0)
                
                # Encode as base64
                plot_data = base64.b64encode(buffer.getvalue()).decode('utf-8')

                plots.append({
                    'type': 'image',
                    'data': plot_data,
                    'source': 'auto-captured'
                })
                
                buffer.close()
            
            # Clear figures after capturing
            plt.close('all')
            
        except Exception as e:
            logger.warning(f"Failed to capture plots: {e}")

        return plots

    def _convert_to_display_format(self, obj: Any, label: Optional[str], notebook_id: str) -> Dict[str, Any]:
        """
        Universal converter that handles ANY object type for display.

        Uses a priority-based conversion pipeline that:
        1. Leverages Python/Jupyter standard representations (_repr_html_)
        2. Handles known scientific types optimally (DataFrame, numpy, etc.)
        3. Falls back gracefully for unknown types
        4. Never silently fails - always returns something displayable

        Args:
            obj: The object to convert
            label: Optional label for the display
            notebook_id: Notebook ID for counter management

        Returns:
            Dict with display information including type, content, and label
        """
        # Ensure counters exist (should have been initialized by _initialize_counters_from_notebook)
        # If not initialized yet, default to 0 (will be fixed on next execution)
        if notebook_id not in self.notebook_table_counters:
            self.notebook_table_counters[notebook_id] = 0
        if notebook_id not in self.notebook_figure_counters:
            self.notebook_figure_counters[notebook_id] = 0

        try:
            # Priority 1: DataFrames (check before _repr_html_ to use our custom TableDisplay)
            if isinstance(obj, pd.DataFrame):
                # Preserve explicit labels; only auto-label when no label is provided.
                # Notebook-wide numbering is applied later by NotebookAssetNumberingService.
                if label is None:
                    self.notebook_table_counters[notebook_id] += 1
                    label = f"Table {self.notebook_table_counters[notebook_id]}"

                table_data = self._dataframe_to_table_data(obj, "displayed_result")
                table_data['source'] = 'display'
                table_data['label'] = label
                table_data['type'] = 'table'
                return table_data

            # Priority 2: pandas Series (keep existing optimized handling)
            if isinstance(obj, pd.Series):
                if label is None:
                    self.notebook_table_counters[notebook_id] += 1
                    label = f"Table {self.notebook_table_counters[notebook_id]}"

                column_name = obj.name if obj.name else 'Value'
                df = obj.to_frame(name=column_name).reset_index()
                table_data = self._dataframe_to_table_data(df, "displayed_result")
                table_data['source'] = 'display'
                table_data['label'] = label
                table_data['type'] = 'table'
                return table_data

            # Priority 3: Matplotlib figures (BEFORE _repr_html_ check to avoid HTML rendering)
            if hasattr(obj, 'savefig') and callable(getattr(obj, 'savefig')):
                # Preserve explicit labels; only auto-label when no label is provided.
                # Notebook-wide numbering is applied later by NotebookAssetNumberingService.
                if label is None:
                    self.notebook_figure_counters[notebook_id] += 1
                    label = f"Figure {self.notebook_figure_counters[notebook_id]}"

                buffer = io.BytesIO()
                obj.savefig(buffer, format='png', bbox_inches='tight', dpi=150)
                buffer.seek(0)
                plot_data = base64.b64encode(buffer.getvalue()).decode('utf-8')
                buffer.close()

                # Close the figure to prevent it from being auto-captured again
                # This fixes the bug where display(fig) results in duplicate figures
                try:
                    plt.close(obj)
                    logger.debug(f"Closed matplotlib figure after display: {label}")
                except Exception as close_err:
                    logger.warning(f"Could not close matplotlib figure: {close_err}")

                return {
                    'type': 'image',
                    'data': plot_data,
                    'label': label,
                    'source': 'display'
                }

            # Priority 4: Check for Jupyter-standard _repr_html_() method (after matplotlib)
            if hasattr(obj, '_repr_html_') and callable(getattr(obj, '_repr_html_')):
                try:
                    html_content = obj._repr_html_()
                    if label is None:
                        self.notebook_table_counters[notebook_id] += 1
                        label = f"Table {self.notebook_table_counters[notebook_id]}"

                    return {
                        'type': 'html',
                        'content': html_content,
                        'label': label,
                        'source': 'display'
                    }
                except Exception as e:
                    logger.warning(f"Failed to get _repr_html_(): {e}")

            # Priority 5: NumPy arrays
            if isinstance(obj, np.ndarray):
                if label is None:
                    self.notebook_table_counters[notebook_id] += 1
                    label = f"Table {self.notebook_table_counters[notebook_id]}"

                # 1D array - convert to Series then DataFrame
                if obj.ndim == 1:
                    df = pd.Series(obj).to_frame('values').reset_index()
                    df.columns = ['index', 'value']
                # 2D array - convert directly to DataFrame
                elif obj.ndim == 2:
                    df = pd.DataFrame(obj)
                # Higher dimensional - show as formatted text
                else:
                    content = f"Array shape: {obj.shape}\nDtype: {obj.dtype}\n\nFirst elements:\n{repr(obj.flat[:100])}"
                    if len(obj.flat) > 100:
                        content += f"\n... ({len(obj.flat) - 100} more elements)"
                    return {
                        'type': 'text',
                        'content': content,
                        'label': label,
                        'source': 'display'
                    }

                table_data = self._dataframe_to_table_data(df, "displayed_result")
                table_data['source'] = 'display'
                table_data['label'] = label
                table_data['type'] = 'table'
                return table_data

            # Priority 6: pandas Index / MultiIndex
            if isinstance(obj, (pd.Index, pd.MultiIndex)):
                if label is None:
                    self.notebook_table_counters[notebook_id] += 1
                    label = f"Table {self.notebook_table_counters[notebook_id]}"

                df = pd.Series(obj).to_frame('values').reset_index()
                df.columns = ['index', 'value']
                table_data = self._dataframe_to_table_data(df, "displayed_result")
                table_data['source'] = 'display'
                table_data['label'] = label
                table_data['type'] = 'table'
                return table_data

            # Priority 7: Dictionaries - format as JSON
            if isinstance(obj, dict):
                if label is None:
                    label = "Data"

                try:
                    # Try to serialize as JSON with pretty printing
                    content = json.dumps(obj, indent=2, default=str)
                    return {
                        'type': 'json',
                        'content': content,
                        'label': label,
                        'source': 'display'
                    }
                except (TypeError, ValueError) as e:
                    # Fall back to repr if JSON serialization fails
                    logger.warning(f"Failed to JSON serialize dict: {e}")
                    return {
                        'type': 'text',
                        'content': repr(obj),
                        'label': label,
                        'source': 'display'
                    }

            # Priority 8: Lists and tuples
            if isinstance(obj, (list, tuple)):
                if label is None:
                    label = "Data"

                # Small collections - show as JSON
                if len(obj) <= 100:
                    try:
                        content = json.dumps(obj, indent=2, default=str)
                        return {
                            'type': 'json',
                            'content': content,
                            'label': label,
                            'source': 'display'
                        }
                    except (TypeError, ValueError):
                        pass

                # Large collections or if JSON fails - convert to DataFrame
                self.notebook_table_counters[notebook_id] += 1
                label = f"Table {self.notebook_table_counters[notebook_id]}" if label == "Data" else label

                df = pd.DataFrame({'index': range(len(obj)), 'value': list(obj)})
                table_data = self._dataframe_to_table_data(df, "displayed_result")
                table_data['source'] = 'display'
                table_data['label'] = label
                table_data['type'] = 'table'
                return table_data

            # Priority 9: sklearn models / estimators
            if hasattr(obj, 'fit') and hasattr(obj, 'predict'):
                if label is None:
                    label = "Model"

                # Extract model information
                info = {
                    'model_type': type(obj).__name__,
                    'module': type(obj).__module__,
                }

                # Get parameters if available
                if hasattr(obj, 'get_params'):
                    try:
                        info['parameters'] = obj.get_params()
                    except Exception:
                        pass

                # Add coefficients if available
                if hasattr(obj, 'coef_'):
                    try:
                        info['coefficients'] = obj.coef_.tolist() if hasattr(obj.coef_, 'tolist') else str(obj.coef_)
                    except Exception:
                        pass

                # Add feature importances if available
                if hasattr(obj, 'feature_importances_'):
                    try:
                        info['feature_importances'] = obj.feature_importances_.tolist()
                    except Exception:
                        pass

                # Format as JSON
                try:
                    content = json.dumps(info, indent=2, default=str)
                    return {
                        'type': 'model',
                        'content': content,
                        'label': label,
                        'source': 'display'
                    }
                except Exception:
                    return {
                        'type': 'text',
                        'content': repr(obj),
                        'label': label,
                        'source': 'display'
                    }

            # Priority 10: PIL/Pillow Images
            try:
                from PIL import Image
                if isinstance(obj, Image.Image):
                    if label is None:
                        self.notebook_figure_counters[notebook_id] += 1
                        label = f"Figure {self.notebook_figure_counters[notebook_id]}"

                    # Convert PIL image to PNG base64
                    buffer = io.BytesIO()
                    obj.save(buffer, format='PNG')
                    buffer.seek(0)
                    plot_data = base64.b64encode(buffer.getvalue()).decode('utf-8')
                    buffer.close()

                    return {
                        'type': 'image',
                        'data': plot_data,
                        'label': label,
                        'source': 'display'
                    }
            except ImportError:
                pass  # PIL not installed

            # Priority 11: Plotly figures (placeholder for future implementation)
            if hasattr(obj, 'to_dict') and hasattr(obj, 'data'):
                if label is None:
                    self.notebook_figure_counters[notebook_id] += 1
                    label = f"Figure {self.notebook_figure_counters[notebook_id]}"

                logger.info(f"📊 Plotly figure detected: {label} (interactive display not yet implemented)")
                # For now, return as text - future: implement interactive plotly display
                return {
                    'type': 'text',
                    'content': f"Plotly figure: {label}\n(Interactive display coming soon)",
                    'label': label,
                    'source': 'display'
                }

            # Final fallback: Use repr() for everything else
            if label is None:
                label = "Data"

            repr_str = repr(obj)

            # Smart truncation for very long representations
            if len(repr_str) > 2000:
                repr_str = (
                    repr_str[:1000] +
                    f"\n\n... ({len(repr_str) - 2000} chars omitted) ...\n\n" +
                    repr_str[-1000:]
                )

            return {
                'type': 'text',
                'content': repr_str,
                'label': label,
                'source': 'display'
            }

        except Exception as e:
            # Even if conversion fails, return something displayable
            logger.error(f"Error converting object to display format: {e}")
            logger.error(traceback.format_exc())

            return {
                'type': 'text',
                'content': f"Error displaying object: {str(e)}\n\nObject type: {type(obj).__name__}",
                'label': label or "Error",
                'source': 'display'
            }

    def _capture_displayed_results(self, globals_dict: Dict[str, Any], notebook_id: str) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Capture results explicitly marked for display using the display() function.

        This captures objects that were registered via display() and returns them
        with their labels for article presentation. Auto-numbers results sequentially
        across the entire notebook (Table 1, 2, 3... Figure 1, 2, 3...).

        Uses the universal converter to handle ANY object type without silent failures.

        Args:
            globals_dict: The globals dictionary containing the display function
            notebook_id: The notebook identifier for global counter management

        Returns:
            Tuple of (tables, plots, other_displays) - lists of captured displayed results
            - tables: table-type displays (DataFrame, Series, arrays, etc.)
            - plots: image-type displays (matplotlib, PIL images, etc.)
            - other_displays: other display types (HTML, JSON, text, model info)
        """
        tables = []
        plots = []
        other_displays = []

        # Ensure counters exist (should have been initialized by _initialize_counters_from_notebook)
        # If not initialized yet, default to 0 (will be fixed on next execution)
        if notebook_id not in self.notebook_table_counters:
            self.notebook_table_counters[notebook_id] = 0
        if notebook_id not in self.notebook_figure_counters:
            self.notebook_figure_counters[notebook_id] = 0

        try:
            # Check if display function exists and has results
            if 'display' in globals_dict and hasattr(globals_dict['display'], 'results'):
                for entry in globals_dict['display'].results:
                    obj = entry['object']
                    label = entry['label']

                    # Use universal converter to handle ANY type
                    try:
                        display_data = self._convert_to_display_format(obj, label, notebook_id)

                        # Route to appropriate list based on display type
                        display_type = display_data.get('type')

                        if display_type == 'table':
                            tables.append(display_data)
                            logger.info(f"✅ Captured displayed table: {display_data.get('label')}")

                        elif display_type == 'image':
                            plots.append(display_data)
                            logger.info(f"✅ Captured displayed image: {display_data.get('label')}")

                        elif display_type in ('html', 'json', 'text', 'model'):
                            other_displays.append(display_data)
                            logger.info(f"✅ Captured displayed {display_type}: {display_data.get('label')}")

                        else:
                            # Unknown type - add to other_displays as failsafe
                            other_displays.append(display_data)
                            logger.warning(f"⚠️ Unknown display type '{display_type}': {display_data.get('label')}")

                    except Exception as convert_err:
                        # Even if conversion fails, log it (converter returns error display)
                        logger.error(f"Error converting displayed object: {convert_err}")
                        logger.error(traceback.format_exc())

                        # Add error display to other_displays
                        other_displays.append({
                            'type': 'text',
                            'content': f"Error displaying object: {str(convert_err)}",
                            'label': label or "Error",
                            'source': 'display'
                        })

        except Exception as e:
            logger.warning(f"Failed to capture displayed results: {e}")
            logger.warning(traceback.format_exc())

        return tables, plots, other_displays

    def _capture_tables(self, globals_dict: Dict[str, Any], pre_execution_vars: set = None, pre_execution_dataframes: dict = None) -> List[Dict[str, Any]]:
        """
        Capture pandas DataFrames and other tabular data created by the current execution.

        Args:
            globals_dict: The globals dictionary to search for DataFrames
            pre_execution_vars: Set of variable names that existed before execution
            pre_execution_dataframes: Dict of DataFrames that existed before execution

        Returns:
            List of table data as dictionaries
        """
        tables = []

        try:
            # Look for DataFrames in the global namespace
            for name, obj in globals_dict.items():
                if isinstance(obj, pd.DataFrame) and not name.startswith('_'):
                    # Only capture DataFrames that are new or have been modified
                    is_new_variable = pre_execution_vars is None or name not in pre_execution_vars
                    is_modified_dataframe = (
                        pre_execution_dataframes is not None and
                        name in pre_execution_dataframes and
                        (
                            # If the variable was reassigned to a new DataFrame object,
                            # capture it even if the values are identical.
                            #
                            # Rationale:
                            # - We want to capture what this execution produced.
                            # - Value-based equality alone misses reassignments with identical content.
                            id(obj) != id(pre_execution_dataframes[name]) or
                            not obj.equals(pre_execution_dataframes[name])
                        )
                    )

                    if is_new_variable or is_modified_dataframe:
                        table_data = self._dataframe_to_table_data(obj, name)
                        table_data['source'] = 'variable'  # Mark as variable table
                        tables.append(table_data)
                        logger.info(f"Captured {'new' if is_new_variable else 'modified'} DataFrame: {name} {obj.shape}")

        except Exception as e:
            logger.warning(f"Failed to capture tables: {e}")

        return tables

    def _dataframe_to_table_data(self, df: pd.DataFrame, name: str = "table") -> Dict[str, Any]:
        """
        Convert a pandas DataFrame to TableData format with robust shape validation.

        Args:
            df: DataFrame to convert
            name: Name for the table

        Returns:
            TableData dictionary
        """
        def make_json_serializable(obj):
            """Convert numpy and pandas types to Python native types for JSON serialization."""
            import numpy as np
            import pandas as pd

            # Handle pandas Period types (convert to string representation)
            if hasattr(pd, 'Period') and isinstance(obj, pd.Period):
                return str(obj)

            # Handle pandas Timestamp types (convert to ISO format)
            if hasattr(pd, 'Timestamp') and isinstance(obj, pd.Timestamp):
                return obj.isoformat()

            # Handle pandas NaT (Not-a-Time)
            if pd.isna(obj):
                return None

            # Handle numpy scalar types (int64, float64, etc.)
            if isinstance(obj, (np.integer, np.floating)):
                return obj.item()  # Convert to Python native type
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            elif hasattr(obj, 'dtype'):
                # Fallback for other numpy types
                if hasattr(obj, 'tolist'):
                    return obj.tolist()
                elif hasattr(obj, 'item'):
                    return obj.item()
            elif isinstance(obj, dict):
                return {k: make_json_serializable(v) for k, v in obj.items()}
            elif isinstance(obj, (list, tuple)):
                return type(obj)([make_json_serializable(item) for item in obj])
            return obj

        # CRITICAL: Extract shape BEFORE any serialization (prevent silent failures)
        actual_shape = [int(df.shape[0]), int(df.shape[1])]  # [rows, cols] as Python ints
        actual_columns = df.columns.tolist()

        logger.info(f"📊 Table '{name}': {actual_shape[0]} rows × {actual_shape[1]} cols")

        # Safely convert DataFrame data
        safe_data = []
        try:
            for record in df.to_dict('records'):
                safe_record = make_json_serializable(record)
                safe_data.append(safe_record)
        except Exception as e:
            logger.error(f"❌ Serialization failed for table '{name}': {e}")
            # Fallback: try different serialization strategy
            try:
                logger.warning(f"⚠️ Attempting fallback serialization with head(100)...")
                for record in df.head(100).to_dict('records'):
                    safe_record = make_json_serializable(record)
                    safe_data.append(safe_record)
            except Exception as fallback_e:
                logger.error(f"❌ Fallback serialization also failed: {fallback_e}")
                safe_data = []  # Last resort: empty data

        # VALIDATION: Check if serialization produced expected number of records
        if actual_shape[0] > 0 and len(safe_data) == 0:
            logger.error(
                f"❌ CRITICAL: Table '{name}' has {actual_shape[0]} rows but serialization produced 0 records! "
                f"Shape will be preserved but data is missing."
            )
        elif len(safe_data) != actual_shape[0]:
            logger.warning(
                f"⚠️ Shape mismatch for '{name}': DataFrame has {actual_shape[0]} rows "
                f"but serialized data has {len(safe_data)} records"
            )

        # Use make_json_serializable for all potentially-numpy data
        table_data = {
            'name': name,
            'shape': actual_shape,  # Use validated shape extracted BEFORE serialization
            'columns': actual_columns,
            'data': safe_data,
            'html': df.to_html(classes='table table-striped'),
            'info': {
                'dtypes': {col: str(dtype) for col, dtype in df.dtypes.to_dict().items()},
                'memory_usage': make_json_serializable(df.memory_usage(deep=True).to_dict())
            }
        }

        return table_data

    def _parse_pandas_stdout(self, stdout: str) -> List[Dict[str, Any]]:
        """
        Parse pandas DataFrame output from stdout text.

        Detects pandas DataFrame string representations and converts them to TableData format.

        Handles:
        - print(df)
        - print(df.head())
        - print(df.to_string())
        - DataFrames with truncated columns (...)

        Args:
            stdout: Console output text

        Returns:
            List of TableData dictionaries
        """
        tables = []

        if not stdout or len(stdout.strip()) < 20:
            return tables

        try:
            # IMPORTANT: do NOT `strip()` the whole stdout before splitting.
            # Pandas DataFrame rendering uses leading spaces to align single-column headers;
            # global `.strip()` would remove that indentation and break detection/parsing.
            lines = stdout.splitlines()
            while lines and not lines[-1].strip():
                lines.pop()
            i = 0
            table_count = 0

            while i < len(lines):
                # Skip empty lines
                if not lines[i].strip():
                    i += 1
                    continue

                # Check if this looks like a pandas DataFrame header
                if self._is_pandas_header_line(lines[i]) and i + 1 < len(lines):
                    # Try to parse the table starting from this line
                    table_data, lines_consumed = self._parse_pandas_table_from_lines(lines[i:])

                    if table_data:
                        # Generate a name for this table
                        table_count += 1
                        table_data['name'] = f"Analysis Result {table_count}"
                        tables.append(table_data)
                        logger.info(f"✅ Parsed table from stdout: {table_data['shape']}")
                        i += lines_consumed
                    else:
                        i += 1
                else:
                    i += 1

        except Exception as e:
            logger.warning(f"Failed to parse pandas stdout: {e}")
            import traceback
            logger.warning(traceback.format_exc())

        return tables

    def _is_pandas_header_line(self, line: str) -> bool:
        """Check if a line looks like a pandas DataFrame header."""
        if not line.strip():
            return False

        # Should NOT be a footer line like "[5 rows x 8 columns]"
        if '[' in line and 'rows' in line and 'columns' in line:
            return False

        # Should NOT be descriptive text lines
        if line.strip().endswith(':'):
            return False

        # Should have words that look like column names (letters, numbers, underscores)
        # More lenient: allow lowercase, mixed case, numbers
        potential_columns = re.findall(r'[A-Za-z_][A-Za-z0-9_]*', line)

        # Should have at least 1 potential column name
        if len(potential_columns) < 1:
            return False

        # For single column, require it to be indented (pandas adds spacing for index)
        if len(potential_columns) == 1:
            if not line.startswith(' ') and not line.startswith('\t'):
                return False

        return True

    def _parse_pandas_table_from_lines(self, lines: List[str]) -> Tuple[Optional[Dict[str, Any]], int]:
        """
        Parse a pandas DataFrame from console output lines using fixed-width format detection.

        Args:
            lines: Lines starting with the header

        Returns:
            Tuple of (TableData dict or None, number of lines consumed)
        """
        try:
            if len(lines) < 2:
                return None, 0

            # Collect all lines that are part of this table
            table_lines = []
            row_index = 0

            # Add header
            table_lines.append(lines[0])
            row_index = 1

            # Add data rows
            while row_index < len(lines):
                line = lines[row_index]

                # Stop at empty line
                if not line.strip():
                    break

                # Stop at footer line like "[5 rows x 8 columns]"
                if '[' in line and 'rows' in line and 'columns' in line:
                    row_index += 1
                    break

                # Stop if line doesn't look like data (starts with letter but no digit)
                if line and line[0].isalpha() and not re.search(r'\d', line):
                    break

                # Check if line has index-like start (number or spaces)
                if re.match(r'^\s*\d+\s+', line) or line.startswith('  '):
                    table_lines.append(line)
                    row_index += 1
                else:
                    break

            if len(table_lines) < 2:
                return None, 0

            # Try to parse using pandas read_fwf (fixed-width format)
            try:
                table_text = '\n'.join(table_lines)
                df = pd.read_fwf(io.StringIO(table_text), widths='infer')

                # Check if we got valid data
                if df.empty or len(df.columns) < 1:
                    raise ValueError("Empty or invalid DataFrame from read_fwf")

                # Clean up: Remove columns that are just '...' or NaN
                cols_to_keep = []
                for col in df.columns:
                    col_str = str(col)
                    if '...' not in col_str and col_str != 'nan' and col_str.strip():
                        cols_to_keep.append(col)

                if len(cols_to_keep) < 1:
                    raise ValueError("Not enough valid columns after cleanup")

                df = df[cols_to_keep]

                # Remove '...' rows if they exist
                mask = pd.Series([True] * len(df))
                for col in df.columns:
                    mask &= ~df[col].astype(str).str.contains(r'\.\.\.', na=False)

                df = df[mask]

                if df.empty:
                    raise ValueError("No valid rows after cleanup")

                # Convert to TableData format
                table_data = self._dataframe_to_table_data(df, "stdout_table")

                logger.debug(f"Successfully parsed table with read_fwf: {df.shape}")
                return table_data, row_index

            except Exception as e:
                logger.debug(f"read_fwf failed ({e}), trying manual parsing")

                # Fallback to manual parsing
                header_parts = lines[0].split()
                columns = [part for part in header_parts if part and part != '...']

                if len(columns) < 1:
                    return None, 0

                # Parse data rows manually
                data_rows = []
                for line in table_lines[1:]:
                    row_parts = line.split()
                    if len(row_parts) < 2:
                        continue

                    # Skip index column (first element)
                    row_values = row_parts[1:]

                    # Remove '...' from row values
                    row_values = [v for v in row_values if v != '...']

                    # Create row dictionary
                    row_dict = {}
                    for idx, col in enumerate(columns):
                        if idx < len(row_values):
                            value = row_values[idx]
                            # Convert to appropriate type
                            try:
                                if '.' in value:
                                    row_dict[col] = float(value)
                                else:
                                    row_dict[col] = int(value)
                            except ValueError:
                                row_dict[col] = value
                        else:
                            row_dict[col] = None

                    if row_dict:
                        data_rows.append(row_dict)

                if data_rows and columns:
                    table_data = {
                        'name': 'stdout_table',
                        'shape': [len(data_rows), len(columns)],
                        'columns': columns,
                        'data': data_rows,
                        'html': '<table></table>',
                        'info': {
                            'dtypes': {col: 'object' for col in columns},
                            'memory_usage': {}
                        }
                    }

                    return table_data, row_index

                return None, 0

        except Exception as e:
            logger.warning(f"Failed to parse pandas table: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return None, 0
    
    def _capture_interactive_plots(self, globals_dict: Dict[str, Any], notebook_id: str, pre_execution_figures: dict = None) -> List[Dict[str, Any]]:
        """
        Capture Plotly interactive plots created during the current cell execution.

        Only captures NEW Plotly figures that were created during this execution,
        preventing figures from previous cells from being re-captured.

        Args:
            globals_dict: The notebook's global namespace
            notebook_id: Notebook ID (kept for backward compatibility; numbering is applied later)
            pre_execution_figures: Dict mapping figure variable names to their object IDs
                                   that existed before execution. If None, all figures are captured.

        Returns:
            List of Plotly figure JSON data (only new figures; labels are assigned later)
        """
        interactive_plots = []
        pre_execution_figures = pre_execution_figures or {}

        try:
            # Look for Plotly figures in the global namespace
            for name, obj in globals_dict.items():
                if hasattr(obj, 'to_dict') and hasattr(obj, 'data') and hasattr(obj, 'layout'):
                    # Skip if this is the SAME figure object (same memory address) from a previous cell
                    # But allow if the variable has been reassigned to a NEW figure object
                    if name in pre_execution_figures and id(obj) == pre_execution_figures[name]:
                        logger.debug(f"⏭️ Skipping pre-existing Plotly figure: {name} (same object)")
                        continue

                    # This is a NEW Plotly figure created in the current cell
                    # (either a new variable name, or an existing name reassigned to a new object)
                    try:
                        # Convert to JSON-serializable format
                        figure_dict = obj.to_dict()
                        
                        # Make sure all numpy arrays are converted to lists
                        def convert_numpy_in_dict(d):
                            if isinstance(d, dict):
                                return {k: convert_numpy_in_dict(v) for k, v in d.items()}
                            elif isinstance(d, list):
                                return [convert_numpy_in_dict(item) for item in d]
                            elif hasattr(d, 'tolist'):  # numpy array
                                return d.tolist()
                            elif hasattr(d, 'item'):  # numpy scalar
                                return d.item()
                            else:
                                return d
                        
                        safe_figure = convert_numpy_in_dict(figure_dict)

                        plot_data = {
                            'name': name,
                            'figure': safe_figure,
                            'json': obj.to_json(),
                            'source': 'auto-captured'
                        }
                        interactive_plots.append(plot_data)
                        logger.info(f"Captured interactive plot: {name}")
                    except Exception as plot_error:
                        logger.warning(f"Failed to serialize plot {name}: {plot_error}")
                    
        except Exception as e:
            logger.warning(f"Failed to capture interactive plots: {e}")
        
        return interactive_plots
    
    def clear_namespace(self, notebook_id: str, keep_imports: bool = True, clear_saved_state: bool = True):
        """
        Clear the execution namespace for a specific notebook.

        Args:
            notebook_id: Unique identifier for the notebook
            keep_imports: Whether to keep imported modules
        """
        # It's normal for a notebook to have no in-memory environment yet:
        # - first execution after backend start/restart
        # - user requests a clean rerun before any execution has occurred
        # - the notebook was never executed in this process
        #
        # In those cases, "clearing" is a no-op for memory, but we may still want to clear
        # persisted state on disk (if requested).
        if notebook_id not in self.notebook_globals:
            logger.info(f"🧹 No in-memory execution environment for notebook {notebook_id} (nothing to clear)")

            if clear_saved_state:
                try:
                    if self.state_persistence.clear_notebook_state(notebook_id):
                        logger.info(f"🗑️  Cleared saved state for notebook {notebook_id}")
                except Exception as e:
                    logger.error(f"Failed to clear saved state: {e}")

            self.execution_count = 0
            plt.close("all")
            return

        globals_dict = self.notebook_globals[notebook_id]

        if keep_imports:
            # Keep only built-ins and imported modules
            to_keep = {
                k: v for k, v in globals_dict.items()
                if k.startswith('_') or hasattr(v, '__module__')
            }
            globals_dict.clear()
            globals_dict.update(to_keep)
            logger.info(f"🧹 Cleared namespace for notebook {notebook_id} (kept imports)")
        else:
            # Complete reset - create fresh environment
            self.notebook_globals[notebook_id] = self._initialize_globals()
            logger.info(f"🧹 Completely reset namespace for notebook {notebook_id}")

        # Clear saved state as well (optional)
        if clear_saved_state:
            try:
                if self.state_persistence.clear_notebook_state(notebook_id):
                    logger.info(f"🗑️  Cleared saved state for notebook {notebook_id}")
            except Exception as e:
                logger.error(f"Failed to clear saved state: {e}")

        self.execution_count = 0
        plt.close('all')
        
        logger.info("Execution namespace cleared")
    
