"""
Clean Data Manager with proper structure: backend/notebook_workspace/{notebook_id}/data/
Each notebook gets its own directory with original filenames preserved.
"""

import os
import shutil
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Any
import pandas as pd
import numpy as np
from datetime import datetime
import logging
from .h5_service import h5_processor

# Optional YAML support
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False
    yaml = None

logger = logging.getLogger(__name__)

class DataManager:
    """Manages data files with clean notebook-specific directory structure."""

    def __init__(self, notebook_id: Optional[str] = None, workspace_root: Optional[str] = None):
        """
        Initialize data manager with structure: backend/notebook_workspace/{notebook_id}/data/

        Args:
            notebook_id: Unique identifier for the notebook (generates UUID if None)
            workspace_root: Custom workspace root path (defaults to config)
        """
        # Generate notebook_id if not provided
        if notebook_id is None:
            notebook_id = str(uuid.uuid4())

        self.notebook_id = notebook_id

        # Use provided workspace_root, or get from config, or fall back to default
        if workspace_root is None:
            from ..config import config
            workspace_root = config.get_workspace_root()

        # Convert to absolute path if relative
        if not os.path.isabs(workspace_root):
            project_root = Path(__file__).parent.parent.parent.parent
            self.workspace_root = project_root / workspace_root
        else:
            self.workspace_root = Path(workspace_root)

        self.notebook_dir = self.workspace_root / notebook_id
        self.data_dir = self.notebook_dir / "data"

        # Create directories
        self.workspace_root.mkdir(parents=True, exist_ok=True)
        self.notebook_dir.mkdir(exist_ok=True)
        self.data_dir.mkdir(exist_ok=True)

        # Set working directory to notebook_dir so 'data/file.csv' works
        os.chdir(str(self.notebook_dir))

        logger.info(f"✅ Clean Data Manager initialized:")
        logger.info(f"   Workspace Root: {self.workspace_root}")
        logger.info(f"   Notebook ID: {self.notebook_id}")
        logger.info(f"   Notebook Dir: {self.notebook_dir}")
        logger.info(f"   Data Dir: {self.data_dir}")
        logger.info(f"   Working Dir: {os.getcwd()}")

        # NOTE: Sample data is no longer automatically copied to new notebooks
        # Users must upload their own data files or manually copy sample data if needed

        logger.info(f"   Available files: {[f['name'] for f in self.list_available_files()]}")
    
    def _is_data_dictionary(self, name: str, df: pd.DataFrame, max_rows: int = 1000, max_cols: int = 30) -> bool:
        """
        Detect if a file or sheet is a data dictionary based on name and structure.
        
        Data dictionaries describe variables/columns in a dataset and should be sent
        in full (no truncation) to the LLM for complete understanding.
        
        Detection criteria:
        1. Name contains dictionary-related keywords (case-insensitive)
        2. Has relatively few rows (< max_rows, typically < 100)
        3. Has relatively few columns (< max_cols)
        
        Args:
            name: Filename or sheet name to check
            df: DataFrame to analyze
            max_rows: Maximum rows for dictionary detection (default 1000)
            max_cols: Maximum columns for dictionary detection (default 30)
        
        Returns:
            True if this appears to be a data dictionary
        """
        # Dictionary-related keywords (case-insensitive)
        DICTIONARY_KEYWORDS = [
            'dictionary', 'dict', 'codebook', 'metadata', 'schema',
            'variables', 'legend', 'definitions', 'definition',
            'data_dict', 'datadict', 'column_desc', 'vardesc',
            'field_desc', 'variable_list', 'var_info'
        ]
        
        name_lower = name.lower()
        
        # Check if name contains any dictionary keyword
        has_keyword = any(keyword in name_lower for keyword in DICTIONARY_KEYWORDS)
        
        # Check structural constraints
        has_few_rows = len(df) <= max_rows
        has_few_cols = len(df.columns) <= max_cols
        
        is_dictionary = has_keyword and has_few_rows and has_few_cols
        
        if is_dictionary:
            logger.info(f"📖 Detected data dictionary: '{name}' ({len(df)} rows × {len(df.columns)} cols)")
        
        return is_dictionary
    
    def _analyze_column(self, series: pd.Series) -> Dict[str, Any]:
        """
        Analyze a column to provide semantic type and useful statistics for the LLM.
        
        Returns a compact summary with:
        - Inferred semantic type (not just pandas dtype)
        - Missing value info
        - For numeric: min, max, mean
        - For categorical: unique count, top values
        """
        # Special NA markers commonly used in datasets
        NA_MARKERS = {'', 'NA', 'N/A', 'na', 'n/a', 'ND', 'nd', 'NaN', 'nan', 
                      'NULL', 'null', 'None', 'none', '.', '-', '--', '?'}
        
        total = len(series)
        null_count = series.isna().sum()
        
        # Count special NA markers in string values
        special_na_count = 0
        if series.dtype == 'object':
            special_na_count = series.apply(
                lambda x: str(x).strip() in NA_MARKERS if pd.notna(x) else False
            ).sum()
        
        # Calculate effective missing (null + special NA markers)
        effective_missing = null_count + special_na_count
        missing_pct = round(100 * effective_missing / total, 1) if total > 0 else 0
        
        # Try to infer the semantic type
        non_null = series.dropna()
        if series.dtype == 'object':
            # Filter out special NA markers for type inference
            clean_values = non_null[~non_null.astype(str).str.strip().isin(NA_MARKERS)]
            
            if len(clean_values) == 0:
                semantic_type = "empty"
            else:
                # Try to detect if it's actually numeric
                try:
                    numeric_vals = pd.to_numeric(clean_values, errors='coerce')
                    numeric_pct = numeric_vals.notna().sum() / len(clean_values)
                    if numeric_pct > 0.9:  # 90%+ values are numeric
                        if (numeric_vals.dropna() % 1 == 0).all():
                            semantic_type = "integer (as text)"
                        else:
                            semantic_type = "float (as text)"
                    elif numeric_pct > 0.5:
                        semantic_type = "mixed (mostly numeric)"
                    else:
                        # Check if categorical (few unique values) vs free text
                        unique_ratio = clean_values.nunique() / len(clean_values)
                        if unique_ratio < 0.05 or clean_values.nunique() <= 20:
                            semantic_type = "categorical"
                        else:
                            semantic_type = "text"
                except:
                    semantic_type = "text"
        elif pd.api.types.is_integer_dtype(series):
            semantic_type = "integer"
        elif pd.api.types.is_float_dtype(series):
            semantic_type = "float"
        elif pd.api.types.is_bool_dtype(series):
            semantic_type = "boolean"
        elif pd.api.types.is_datetime64_any_dtype(series):
            semantic_type = "datetime"
        else:
            semantic_type = str(series.dtype)
        
        # Build result
        result = {
            'type': semantic_type,
            'missing': f"{effective_missing}/{total} ({missing_pct}%)" if effective_missing > 0 else "0"
        }
        
        # Add type-specific stats
        if semantic_type in ['integer', 'float', 'integer (as text)', 'float (as text)']:
            try:
                if semantic_type in ['integer (as text)', 'float (as text)']:
                    numeric_series = pd.to_numeric(non_null, errors='coerce').dropna()
                else:
                    numeric_series = non_null
                
                if len(numeric_series) > 0:
                    result['range'] = f"[{numeric_series.min():.4g}, {numeric_series.max():.4g}]"
                    result['mean'] = f"{numeric_series.mean():.4g}"
            except:
                pass
        elif semantic_type == 'categorical':
            unique_count = non_null.nunique()
            result['unique'] = unique_count
            if unique_count <= 10:
                # Show all values if few
                result['values'] = list(non_null.value_counts().head(10).index)
            else:
                # Show top 5
                result['top_values'] = list(non_null.value_counts().head(5).index)
        elif semantic_type == 'datetime':
            try:
                result['range'] = f"[{non_null.min()}, {non_null.max()}]"
            except:
                pass
        
        return result
    
    def _get_column_stats(self, df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
        """
        Get statistics for all columns in a DataFrame.
        Returns a dict mapping column name to its analysis.
        """
        stats = {}
        for col in df.columns:
            stats[str(col)] = self._analyze_column(df[col])
        return stats
    
    def _copy_sample_data(self):
        """Copy sample data preserving ORIGINAL filenames."""
        sample_data_source = Path(__file__).parent.parent.parent.parent / "data"
        
        if not sample_data_source.exists():
            logger.warning(f"Sample data source not found: {sample_data_source}")
            return
            
        for item in sample_data_source.iterdir():
            if item.is_file() and item.suffix in ['.csv', '.json', '.xlsx', '.txt']:
                # PRESERVE ORIGINAL FILENAME!
                dest_path = self.data_dir / item.name
                if not dest_path.exists():
                    shutil.copy(item, dest_path)
                    logger.info(f"   📄 Copied: {item.name}")
    
    def list_available_files(self) -> List[Dict[str, Any]]:
        """List all files in the notebook's data directory."""
        files_info = []
        
        if not self.data_dir.exists():
            return files_info
            
        for file_path in self.data_dir.iterdir():
            if file_path.is_file():
                # Determine file type
                file_extension = file_path.suffix[1:].lower() if file_path.suffix else 'other'
                if h5_processor.is_h5_file(file_path):
                    file_type = file_extension  # Keep original extension (h5, hdf5, h5ad)
                else:
                    file_type = file_extension
                
                file_info = {
                    'name': file_path.name,  # ORIGINAL FILENAME!
                    'path': f"data/{file_path.name}",  # Simple path for LLM
                    'absolute_path': str(file_path),
                    'size': file_path.stat().st_size,
                    'type': file_type,
                    'lastModified': datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                }
                
                # Add preview for different file types
                try:
                    if file_path.suffix == '.csv':
                        df_full = pd.read_csv(file_path)
                        # Check if this is a data dictionary - if so, send ALL rows
                        is_dictionary = self._is_data_dictionary(file_path.name, df_full)
                        if is_dictionary:
                            df_sample = df_full.replace({np.nan: None, np.inf: None, -np.inf: None})
                        else:
                            # Get 20 sample rows with NaN/Infinity cleaned for JSON compatibility
                            df_sample = df_full.head(20).replace({np.nan: None, np.inf: None, -np.inf: None})
                        # Clean sample data records
                        sample_records = []
                        for record in df_sample.to_dict('records'):
                            clean_record = {str(k): (None if pd.isna(v) else v) for k, v in record.items()}
                            sample_records.append(clean_record)
                        file_info['preview'] = {
                            'rows': len(df_full),
                            'columns': [str(c) for c in df_full.columns.tolist()],  # No truncation
                            'shape': [len(df_full), len(df_full.columns)],
                            'column_stats': self._get_column_stats(df_full),  # Rich column analysis
                            'sample_data': sample_records,  # All rows for dictionaries, 20 for others
                            'is_dictionary': is_dictionary  # Flag for LLM context
                        }
                    elif file_path.suffix == '.tsv':
                        df_full = pd.read_csv(file_path, sep='\t')
                        # Check if this is a data dictionary - if so, send ALL rows
                        is_dictionary = self._is_data_dictionary(file_path.name, df_full)
                        if is_dictionary:
                            df_sample = df_full.replace({np.nan: None, np.inf: None, -np.inf: None})
                        else:
                            # Get 20 sample rows with NaN/Infinity cleaned for JSON compatibility
                            df_sample = df_full.head(20).replace({np.nan: None, np.inf: None, -np.inf: None})
                        # Clean sample data records
                        sample_records = []
                        for record in df_sample.to_dict('records'):
                            clean_record = {str(k): (None if pd.isna(v) else v) for k, v in record.items()}
                            sample_records.append(clean_record)
                        file_info['preview'] = {
                            'rows': len(df_full),
                            'columns': [str(c) for c in df_full.columns.tolist()],  # No truncation
                            'shape': [len(df_full), len(df_full.columns)],
                            'column_stats': self._get_column_stats(df_full),  # Rich column analysis
                            'sample_data': sample_records,  # All rows for dictionaries, 20 for others
                            'is_dictionary': is_dictionary  # Flag for LLM context
                        }
                    elif file_path.suffix == '.md':
                        # First few lines of markdown file
                        with open(file_path, 'r', encoding='utf-8') as f:
                            lines = [f.readline().strip() for _ in range(10)]
                            lines = [line for line in lines if line]
                        file_info['preview'] = {
                            'first_lines': lines,
                            'encoding': 'utf-8',
                            'file_type': 'markdown'
                        }
                    elif file_path.suffix in ['.yaml', '.yml'] and YAML_AVAILABLE:
                        # Parse YAML file for preview
                        with open(file_path, 'r', encoding='utf-8') as f:
                            yaml_data = yaml.safe_load(f)
                        
                        # Analyze YAML structure (similar to JSON)
                        if isinstance(yaml_data, list):
                            file_info['preview'] = {
                                'type': 'array',
                                'length': len(yaml_data),
                                'file_type': 'yaml',
                                'sample_item': yaml_data[0] if len(yaml_data) > 0 else None
                            }
                        elif isinstance(yaml_data, dict):
                            file_info['preview'] = {
                                'type': 'object',
                                'keys': list(yaml_data.keys())[:10],
                                'total_keys': len(yaml_data.keys()),
                                'file_type': 'yaml'
                            }
                        else:
                            file_info['preview'] = {
                                'type': type(yaml_data).__name__,
                                'value': str(yaml_data)[:100],
                                'file_type': 'yaml'
                            }
                    elif file_path.suffix == '.json':
                        import json
                        with open(file_path, 'r', encoding='utf-8') as f:
                            json_data = json.load(f)
                        
                        # Analyze JSON structure
                        if isinstance(json_data, list):
                            file_info['preview'] = {
                                'type': 'array',
                                'length': len(json_data),
                                'sample_item': json_data[0] if len(json_data) > 0 else None,
                                'schema': self._analyze_json_schema(json_data[0] if len(json_data) > 0 else {})
                            }
                        elif isinstance(json_data, dict):
                            file_info['preview'] = {
                                'type': 'object',
                                'keys': list(json_data.keys())[:10],  # First 10 keys
                                'total_keys': len(json_data.keys()),
                                'schema': self._analyze_json_schema(json_data)
                            }
                        else:
                            file_info['preview'] = {
                                'type': type(json_data).__name__,
                                'value': str(json_data)[:100]
                            }
                    elif file_path.suffix in ['.xlsx', '.xls']:
                        # Full Excel file info with all sheets, columns, dtypes, and sample data
                        import openpyxl
                        wb = openpyxl.load_workbook(file_path, read_only=True)
                        sheet_names = wb.sheetnames
                        wb.close()
                        
                        file_info['preview'] = {
                            'sheets': [],
                            'total_sheets': len(sheet_names)
                        }
                        
                        # Load each sheet with pandas for full metadata
                        for sheet_name in sheet_names:
                            try:
                                df = pd.read_excel(file_path, sheet_name=sheet_name)
                                
                                # Check if this sheet is a data dictionary - if so, send ALL rows
                                # Check both filename AND sheet name for dictionary keywords
                                is_dictionary = (
                                    self._is_data_dictionary(sheet_name, df) or 
                                    self._is_data_dictionary(file_path.name, df)
                                )
                                
                                if is_dictionary:
                                    df_sample = df.replace({np.nan: None, np.inf: None, -np.inf: None})
                                else:
                                    # Get 20 sample rows with NaN/Infinity cleaned
                                    df_sample = df.head(20).replace({np.nan: None, np.inf: None, -np.inf: None})
                                
                                # Clean sample data records
                                sample_records = []
                                for record in df_sample.to_dict('records'):
                                    clean_record = {str(k): (None if pd.isna(v) else v) for k, v in record.items()}
                                    sample_records.append(clean_record)
                                
                                sheet_info = {
                                    'name': sheet_name,
                                    'rows': len(df),
                                    'columns': [str(c) for c in df.columns.tolist()],  # No truncation
                                    'shape': [len(df), len(df.columns)],
                                    'column_stats': self._get_column_stats(df),  # Rich column analysis
                                    'sample_data': sample_records,  # All rows for dictionaries, 20 for others
                                    'is_dictionary': is_dictionary  # Flag for LLM context
                                }
                                file_info['preview']['sheets'].append(sheet_info)
                            except Exception as sheet_error:
                                file_info['preview']['sheets'].append({
                                    'name': sheet_name,
                                    'error': str(sheet_error)
                                })
                    elif file_path.suffix == '.txt':
                        # First few lines of text file
                        with open(file_path, 'r', encoding='utf-8') as f:
                            lines = [f.readline().strip() for _ in range(5)]
                            lines = [line for line in lines if line]  # Remove empty lines
                        file_info['preview'] = {
                            'first_lines': lines,
                            'encoding': 'utf-8'
                        }
                    elif h5_processor.is_h5_file(file_path):
                        # H5/HDF5/H5AD file processing
                        h5_metadata = h5_processor.process_file(file_path)
                        file_info['preview'] = h5_metadata
                        file_info['is_h5_file'] = True
                except Exception as e:
                    logger.warning(f"Could not read preview for {file_path.name}: {e}")
                    file_info['preview'] = {'error': str(e)}
                    
                files_info.append(file_info)
                
        return sorted(files_info, key=lambda x: x['name'])
    
    def _analyze_json_schema(self, data: Any, max_depth: int = 2, current_depth: int = 0) -> Dict[str, Any]:
        """Analyze JSON data structure to provide schema information."""
        if current_depth >= max_depth:
            return {'type': type(data).__name__, 'truncated': True}
        
        if isinstance(data, dict):
            schema = {'type': 'object', 'properties': {}}
            for key, value in list(data.items())[:10]:  # Limit to first 10 properties
                schema['properties'][key] = self._analyze_json_schema(value, max_depth, current_depth + 1)
            if len(data) > 10:
                schema['additional_properties'] = f"... and {len(data) - 10} more"
            return schema
        elif isinstance(data, list):
            if len(data) == 0:
                return {'type': 'array', 'items': 'unknown', 'length': 0}
            # Analyze first item to understand array structure
            item_schema = self._analyze_json_schema(data[0], max_depth, current_depth + 1)
            return {'type': 'array', 'items': item_schema, 'length': len(data)}
        else:
            return {'type': type(data).__name__, 'example': str(data)[:50]}
    
    def get_execution_context(self) -> Dict[str, Any]:
        """Get context for LLM code generation."""
        files = self.list_available_files()
        context = {
            'notebook_id': self.notebook_id,
            'files_in_context': files,
            'data_directory_path': "data",  # LLM should use 'data/filename.csv'
            'working_directory': str(self.notebook_dir)
        }
        return context
    
    def get_working_directory(self) -> Path:
        """Get the notebook's working directory."""
        return self.notebook_dir
    
    def get_workspace_path(self) -> str:
        """Get the notebook's workspace path as string."""
        return str(self.notebook_dir)
    
    def upload_file(self, file_name: str, content: bytes) -> List[Dict[str, Any]]:
        """Upload file with ORIGINAL filename to notebook data directory."""
        file_path = self.data_dir / file_name  # NO random prefixes!
        with open(file_path, 'wb') as f:
            f.write(content)
        logger.info(f"✅ Uploaded: {file_name}")
        return self.list_available_files()
    
    def delete_file(self, file_name: str) -> bool:
        """Delete file from notebook data directory."""
        file_path = self.data_dir / file_name
        if file_path.exists():
            file_path.unlink()
            logger.info(f"🗑️ Deleted: {file_name}")
            return True
        logger.warning(f"❌ File not found: {file_name}")
        return False

# Global instance management
_global_data_manager = None

def get_data_manager(notebook_id: Optional[str] = None) -> DataManager:
    """Get a data manager instance for the specified notebook."""
    global _global_data_manager
    
    if notebook_id is None:
        # Use global instance for backward compatibility
        if _global_data_manager is None:
            _global_data_manager = DataManager()
        return _global_data_manager
    else:
        # Create notebook-specific instance
        return DataManager(notebook_id=notebook_id)
