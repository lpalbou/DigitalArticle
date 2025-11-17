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
import re
from contextlib import redirect_stdout, redirect_stderr
from typing import Dict, Any, List, Optional, Tuple
import matplotlib
import matplotlib.pyplot as plt
import plotly
import pandas as pd
import numpy as np

from ..models.notebook import ExecutionResult, ExecutionStatus

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
                match = re.search(r'(random|np|pd|plt|sns|stats)\.\w+\s*=', stripped)
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
            if re.search(r'(int|float|str|list|dict|tuple)\[', stripped) and '=' in stripped:
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
    
    def execute_code(self, code: str, cell_id: str, notebook_id: Optional[str] = None) -> ExecutionResult:
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

        # PHASE 2: Proceed with execution setup
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

        # Get or create notebook-specific globals
        globals_dict = self._get_notebook_globals(notebook_id)

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

            # Track variables before execution to only capture new DataFrames
            pre_execution_vars = set(globals_dict.keys())
            pre_execution_dataframes = {
                name: obj for name, obj in globals_dict.items()
                if isinstance(obj, pd.DataFrame) and not name.startswith('_')
            }

            # Add lazy imports to code if needed
            processed_code = self._preprocess_code(code)

            # Execute the code with output redirection in notebook-specific namespace
            with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
                exec(processed_code, globals_dict)
            
            # Capture outputs
            result.stdout = stdout_buffer.getvalue()
            result.stderr = stderr_buffer.getvalue()
            result.status = ExecutionStatus.SUCCESS

            # Capture visualizations and rich outputs
            result.plots = self._capture_plots()
            result.tables = self._capture_tables(globals_dict, pre_execution_vars, pre_execution_dataframes)
            result.interactive_plots = self._capture_interactive_plots()

            # Parse pandas DataFrames from stdout and add to tables
            stdout_tables = self._parse_pandas_stdout(result.stdout)
            if stdout_tables:
                logger.info(f"📊 Parsed {len(stdout_tables)} table(s) from stdout")
                # Mark stdout tables with source indicator
                for table in stdout_tables:
                    table['source'] = 'stdout'
                result.tables.extend(stdout_tables)
            
            self.execution_count += 1
            logger.info(f"Successfully executed cell {cell_id}")

            # Auto-save notebook state after successful execution
            if notebook_id:
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
    
    def get_variable_info(self, notebook_id: str) -> Dict[str, Any]:
        """
        Get information about variables in the notebook-specific execution context.

        Args:
            notebook_id: Unique identifier for the notebook

        Returns:
            Dict mapping variable names to their type info
        """
        try:
            # Get notebook-specific globals
            globals_dict = self._get_notebook_globals(notebook_id)

            variables = {}
            for name, value in globals_dict.items():
                if not name.startswith('_') and not callable(value):
                    try:
                        # Get basic info about the variable
                        var_type = type(value).__name__
                        if hasattr(value, 'shape'):  # pandas DataFrame, numpy array
                            variables[name] = f"{var_type} {getattr(value, 'shape', 'N/A')}"
                        else:
                            variables[name] = var_type
                    except:
                        variables[name] = "unknown"
            return variables
        except Exception as e:
            logger.warning(f"Failed to get variable info for notebook {notebook_id}: {e}")
            return {}
    
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
    
    def _capture_plots(self) -> List[str]:
        """
        Capture matplotlib plots as base64-encoded PNG images.
        
        Returns:
            List of base64-encoded plot images
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
                plots.append(plot_data)
                
                buffer.close()
            
            # Clear figures after capturing
            plt.close('all')
            
        except Exception as e:
            logger.warning(f"Failed to capture plots: {e}")
        
        return plots
    
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
                        not obj.equals(pre_execution_dataframes[name])
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
        Convert a pandas DataFrame to TableData format.

        Args:
            df: DataFrame to convert
            name: Name for the table

        Returns:
            TableData dictionary
        """
        def make_json_serializable(obj):
            """Convert numpy types to Python native types for JSON serialization."""
            import numpy as np

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

        # Safely convert DataFrame data
        safe_data = []
        for record in df.to_dict('records'):
            safe_record = make_json_serializable(record)
            safe_data.append(safe_record)

        # Use make_json_serializable for all potentially-numpy data
        table_data = {
            'name': name,
            'shape': make_json_serializable(df.shape),  # Handles any numpy types in shape
            'columns': df.columns.tolist(),
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
            lines = stdout.strip().split('\n')
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
    
    def _capture_interactive_plots(self) -> List[Dict[str, Any]]:
        """
        Capture Plotly interactive plots.
        
        Returns:
            List of Plotly figure JSON data
        """
        interactive_plots = []
        
        try:
            # Look for Plotly figures in the global namespace
            for name, obj in self.globals_dict.items():
                if hasattr(obj, 'to_dict') and hasattr(obj, 'data') and hasattr(obj, 'layout'):
                    # This is likely a Plotly figure
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
                            'json': obj.to_json()
                        }
                        interactive_plots.append(plot_data)
                        logger.info(f"Captured interactive plot: {name}")
                    except Exception as plot_error:
                        logger.warning(f"Failed to serialize plot {name}: {plot_error}")
                    
        except Exception as e:
            logger.warning(f"Failed to capture interactive plots: {e}")
        
        return interactive_plots
    
    def get_variable_info(self) -> Dict[str, Any]:
        """
        Get information about variables in the current namespace.
        
        Returns:
            Dictionary containing variable information
        """
        variable_info = {}
        
        for name, obj in self.globals_dict.items():
            if not name.startswith('_') and not callable(obj):
                try:
                    info = {
                        'type': type(obj).__name__,
                        'size': sys.getsizeof(obj) if hasattr(obj, '__sizeof__') else None
                    }
                    
                    # Add specific info for common types
                    if isinstance(obj, (pd.DataFrame, pd.Series)):
                        info['shape'] = getattr(obj, 'shape', None)
                        info['columns'] = getattr(obj, 'columns', None)
                        if hasattr(obj.columns, 'tolist'):
                            info['columns'] = obj.columns.tolist()
                    elif isinstance(obj, (list, tuple, dict)):
                        info['length'] = len(obj)
                    elif isinstance(obj, np.ndarray):
                        info['shape'] = obj.shape
                        info['dtype'] = str(obj.dtype)
                    
                    variable_info[name] = info
                    
                except Exception as e:
                    logger.warning(f"Failed to get info for variable {name}: {e}")
        
        return variable_info
    
    def clear_namespace(self, notebook_id: str, keep_imports: bool = True):
        """
        Clear the execution namespace for a specific notebook.

        Args:
            notebook_id: Unique identifier for the notebook
            keep_imports: Whether to keep imported modules
        """
        if notebook_id not in self.notebook_globals:
            logger.warning(f"⚠️ No execution environment found for notebook {notebook_id}")
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

        # Clear saved state as well
        try:
            if self.state_persistence.clear_notebook_state(notebook_id):
                logger.info(f"🗑️  Cleared saved state for notebook {notebook_id}")
        except Exception as e:
            logger.error(f"Failed to clear saved state: {e}")

        self.execution_count = 0
        plt.close('all')
        
        logger.info("Execution namespace cleared")
    
    def set_variable(self, name: str, value: Any):
        """
        Set a variable in the execution namespace.
        
        Args:
            name: Variable name
            value: Variable value
        """
        self.globals_dict[name] = value
    
    def get_variable(self, name: str) -> Any:
        """
        Get a variable from the execution namespace.
        
        Args:
            name: Variable name
            
        Returns:
            Variable value or None if not found
        """
        return self.globals_dict.get(name)
