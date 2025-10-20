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
from contextlib import redirect_stdout, redirect_stderr
from typing import Dict, Any, List, Optional
import matplotlib
import matplotlib.pyplot as plt
import plotly
import pandas as pd
import numpy as np

from ..models.notebook import ExecutionResult, ExecutionStatus

# Configure matplotlib for non-interactive backend
matplotlib.use('Agg')

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
        
        self.globals_dict = self._initialize_globals()
        self.execution_count = 0
    
    def _initialize_globals(self) -> Dict[str, Any]:
        """Initialize the global namespace for code execution."""
        globals_dict = {
            '__builtins__': __builtins__,
            'pd': pd,
            'np': np,
            'plt': plt,
            'px': None,  # Will import plotly.express lazily
            'go': None,  # Will import plotly.graph_objects lazily
            'sns': None,  # Will import seaborn lazily
            'stats': None,  # Will import scipy.stats lazily
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
        
        return globals_dict
    
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
        
        # Use notebook-specific data manager if provided
        if notebook_id:
            from .data_manager_clean import get_data_manager
            notebook_data_manager = get_data_manager(notebook_id)
            working_dir = notebook_data_manager.get_working_directory()
        else:
            working_dir = self.data_manager.get_working_directory()
        
        # Ensure we're in the correct working directory for this notebook
        import os
        if str(working_dir) != os.getcwd():
            os.chdir(str(working_dir))
        
        # Prepare output capture
        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()
        
        try:
            # Clear any existing plots
            plt.clf()
            plt.close('all')
            
            # Track variables before execution to only capture new DataFrames
            pre_execution_vars = set(self.globals_dict.keys())
            pre_execution_dataframes = {
                name: obj for name, obj in self.globals_dict.items() 
                if isinstance(obj, pd.DataFrame) and not name.startswith('_')
            }
            
            # Add lazy imports to code if needed
            processed_code = self._preprocess_code(code)
            
            # Execute the code with output redirection
            with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
                exec(processed_code, self.globals_dict)
            
            # Capture outputs
            result.stdout = stdout_buffer.getvalue()
            result.stderr = stderr_buffer.getvalue()
            result.status = ExecutionStatus.SUCCESS
            
            # Capture visualizations and rich outputs
            result.plots = self._capture_plots()
            result.tables = self._capture_tables(pre_execution_vars, pre_execution_dataframes)
            result.interactive_plots = self._capture_interactive_plots()
            
            self.execution_count += 1
            logger.info(f"Successfully executed cell {cell_id}")
            
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
    
    def get_variable_info(self) -> Dict[str, Any]:
        """Get information about variables in the current execution context."""
        try:
            variables = {}
            for name, value in self.globals_dict.items():
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
            logger.warning(f"Failed to get variable info: {e}")
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
    
    def _capture_tables(self, pre_execution_vars: set = None, pre_execution_dataframes: dict = None) -> List[Dict[str, Any]]:
        """
        Capture pandas DataFrames and other tabular data created by the current execution.
        
        Args:
            pre_execution_vars: Set of variable names that existed before execution
            pre_execution_dataframes: Dict of DataFrames that existed before execution
        
        Returns:
            List of table data as dictionaries
        """
        tables = []
        
        try:
            # Look for DataFrames in the global namespace
            for name, obj in self.globals_dict.items():
                if isinstance(obj, pd.DataFrame) and not name.startswith('_'):
                    # Only capture DataFrames that are new or have been modified
                    is_new_variable = pre_execution_vars is None or name not in pre_execution_vars
                    is_modified_dataframe = (
                        pre_execution_dataframes is not None and 
                        name in pre_execution_dataframes and 
                        not obj.equals(pre_execution_dataframes[name])
                    )
                    
                    if is_new_variable or is_modified_dataframe:
                        # Convert DataFrame to dictionary format with numpy-safe serialization
                        def make_json_serializable(obj):
                            """Convert numpy types to Python native types for JSON serialization."""
                            # Import numpy locally to handle the conversion
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
                        for record in obj.to_dict('records'):
                            safe_record = make_json_serializable(record)
                            safe_data.append(safe_record)

                        # Use make_json_serializable for all potentially-numpy data
                        table_data = {
                            'name': name,
                            'shape': make_json_serializable(obj.shape),  # Handles any numpy types in shape
                            'columns': obj.columns.tolist(),
                            'data': safe_data,
                            'html': obj.to_html(classes='table table-striped'),
                            'info': {
                                'dtypes': {col: str(dtype) for col, dtype in obj.dtypes.to_dict().items()},
                                'memory_usage': make_json_serializable(obj.memory_usage(deep=True).to_dict())
                            }
                        }
                        tables.append(table_data)
                        logger.info(f"Captured {'new' if is_new_variable else 'modified'} DataFrame: {name} {obj.shape}")
                    
        except Exception as e:
            logger.warning(f"Failed to capture tables: {e}")
        
        return tables
    
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
    
    def clear_namespace(self, keep_imports: bool = True):
        """
        Clear the execution namespace.
        
        Args:
            keep_imports: Whether to keep imported modules
        """
        if keep_imports:
            # Keep only built-ins and imported modules
            to_keep = {
                k: v for k, v in self.globals_dict.items()
                if k.startswith('_') or hasattr(v, '__module__')
            }
            self.globals_dict.clear()
            self.globals_dict.update(to_keep)
        else:
            # Complete reset
            self.globals_dict = self._initialize_globals()
        
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
