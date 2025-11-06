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
from datetime import datetime
import logging
from .h5_service import h5_processor

logger = logging.getLogger(__name__)

class DataManager:
    """Manages data files with clean notebook-specific directory structure."""
    
    def __init__(self, notebook_id: Optional[str] = None):
        """
        Initialize data manager with structure: backend/notebook_workspace/{notebook_id}/data/
        
        Args:
            notebook_id: Unique identifier for the notebook (generates UUID if None)
        """
        # Generate notebook_id if not provided
        if notebook_id is None:
            notebook_id = str(uuid.uuid4())
            
        self.notebook_id = notebook_id
        
        # Clean structure: backend/notebook_workspace/{notebook_id}/data/
        self.workspace_root = Path(__file__).parent.parent.parent / "notebook_workspace"
        self.notebook_dir = self.workspace_root / notebook_id
        self.data_dir = self.notebook_dir / "data"
        
        # Create directories
        self.workspace_root.mkdir(exist_ok=True)
        self.notebook_dir.mkdir(exist_ok=True)
        self.data_dir.mkdir(exist_ok=True)
        
        # Set working directory to notebook_dir so 'data/file.csv' works
        os.chdir(str(self.notebook_dir))
        
        logger.info(f"✅ Clean Data Manager initialized:")
        logger.info(f"   Notebook ID: {self.notebook_id}")
        logger.info(f"   Notebook Dir: {self.notebook_dir}")
        logger.info(f"   Data Dir: {self.data_dir}")
        logger.info(f"   Working Dir: {os.getcwd()}")
        
        # NOTE: Sample data is no longer automatically copied to new notebooks
        # Users must upload their own data files or manually copy sample data if needed
        
        logger.info(f"   Available files: {[f['name'] for f in self.list_available_files()]}")
    
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
                        df_preview = pd.read_csv(file_path, nrows=5)
                        df_full = pd.read_csv(file_path)
                        file_info['preview'] = {
                            'rows': len(df_full),
                            'columns': df_preview.columns.tolist(),
                            'shape': [len(df_full), len(df_preview.columns)],
                            'sample_data': df_preview.head(3).to_dict('records') if len(df_preview) > 0 else []
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
                        # Basic Excel file info
                        import openpyxl
                        wb = openpyxl.load_workbook(file_path, read_only=True)
                        file_info['preview'] = {
                            'sheets': wb.sheetnames,
                            'total_sheets': len(wb.sheetnames)
                        }
                        wb.close()
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
