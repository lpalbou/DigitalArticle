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
        # Set up data directory access
        import os
        from pathlib import Path
        
        # Get the project root directory
        self.project_root = Path(__file__).parent.parent.parent.parent
        self.data_dir = self.project_root / "data"
        
        # Ensure data directory exists
        self.data_dir.mkdir(exist_ok=True)
        
        # Set working directory for code execution to project root
        # so that 'data/file.csv' paths work correctly
        os.chdir(str(self.project_root))
        
        logger.info(f"Execution working directory: {os.getcwd()}")
        logger.info(f"Data directory: {self.data_dir}")
        
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
                    parts = module_path.split('.')
                    module = __import__(module_path, fromlist=[parts[-1]])
                    if len(parts) > 1:
                        for part in parts[1:]:
                            module = getattr(module, part)
                    globals_dict[alias] = module
                except ImportError as e:
                    logger.warning(f"Failed to import {module_path}: {e}")
                    globals_dict[alias] = None
            return globals_dict[alias]
        
        # Add lazy import helpers
        globals_dict['_lazy_import'] = lazy_import
        
        return globals_dict
    
    def execute_code(self, code: str, cell_id: str) -> ExecutionResult:
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
        
        # Prepare output capture
        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()
        
        try:
            # Clear any existing plots
            plt.clf()
            plt.close('all')
            
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
            result.tables = self._capture_tables()
            result.interactive_plots = self._capture_interactive_plots()
            
            self.execution_count += 1
            logger.info(f"Successfully executed cell {cell_id}")
            
        except Exception as e:
            # Capture error information
            result.status = ExecutionStatus.ERROR
            result.error_type = type(e).__name__
            result.error_message = str(e)
            result.traceback = traceback.format_exc()
            result.stderr = stderr_buffer.getvalue() + result.traceback
            
            logger.error(f"Execution failed for cell {cell_id}: {e}")
        
        finally:
            result.execution_time = time.time() - start_time
            
        return result
    
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
        
        for line in lines:
            # Handle common import patterns with lazy loading
            if 'import plotly.express as px' in line:
                processed_lines.append("px = _lazy_import('plotly.express', 'px')")
            elif 'import plotly.graph_objects as go' in line:
                processed_lines.append("go = _lazy_import('plotly.graph_objects', 'go')")
            elif 'import seaborn as sns' in line:
                processed_lines.append("sns = _lazy_import('seaborn', 'sns')")
            elif 'import scipy.stats as stats' in line:
                processed_lines.append("stats = _lazy_import('scipy.stats', 'stats')")
            elif 'from sklearn' in line:
                # Handle sklearn imports
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
    
    def _capture_tables(self) -> List[Dict[str, Any]]:
        """
        Capture pandas DataFrames and other tabular data.
        
        Returns:
            List of table data as dictionaries
        """
        tables = []
        
        try:
            # Look for DataFrames in the global namespace
            for name, obj in self.globals_dict.items():
                if isinstance(obj, pd.DataFrame) and not name.startswith('_'):
                    # Convert DataFrame to dictionary format
                    table_data = {
                        'name': name,
                        'shape': obj.shape,
                        'columns': obj.columns.tolist(),
                        'data': obj.to_dict('records'),
                        'html': obj.to_html(classes='table table-striped'),
                        'info': {
                            'dtypes': obj.dtypes.to_dict(),
                            'memory_usage': obj.memory_usage(deep=True).to_dict()
                        }
                    }
                    tables.append(table_data)
                    
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
                    plot_data = {
                        'name': name,
                        'figure': obj.to_dict(),
                        'json': obj.to_json()
                    }
                    interactive_plots.append(plot_data)
                    
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
