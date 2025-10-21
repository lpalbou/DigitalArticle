"""
Fixed Data Manager for the Digital Article.

Proper structure: backend/notebook_workspace/data/{notebook_id}/{filename}
No more random prefixes - preserve original filenames!
"""

import os
import shutil
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Any
import pandas as pd
import json
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class DataManager:
    """Manages data files with proper notebook-specific directory structure."""
    
    def __init__(self, notebook_id: str = None, workspace_root: str = "backend/notebook_workspace"):
        """
        Initialize the data manager with proper directory structure.
        
        Args:
            notebook_id: Unique identifier for the notebook
            workspace_root: Root directory for the notebook workspace
        """
        # Generate notebook_id if not provided
        if notebook_id is None:
            notebook_id = str(uuid.uuid4())
            
        self.notebook_id = notebook_id
        self.workspace_root = Path(workspace_root).resolve()
        
        # CORRECT STRUCTURE: data/{notebook_id}/{filename}
        self.notebook_data_dir = self.workspace_root / "data" / notebook_id
        self.sample_data_source = Path(__file__).parent.parent.parent.parent / "data"
        
        # Create directories
        self.workspace_root.mkdir(parents=True, exist_ok=True)
        self.notebook_data_dir.mkdir(parents=True, exist_ok=True)
        
        # Set working directory to the notebook's data parent (so 'data/file.csv' works)
        notebook_working_dir = self.notebook_data_dir.parent  # This is workspace/data/{notebook_id}/..
        os.chdir(str(notebook_working_dir))
        
        # NOTE: Sample data is no longer automatically copied to new notebooks
        # self._copy_sample_data()  # Commented out - users must upload their own data
        
        logger.info(f"Fixed Data Manager initialized:")
        logger.info(f"  Notebook ID: {self.notebook_id}")
        logger.info(f"  Workspace Root: {self.workspace_root}")
        logger.info(f"  Notebook Data Dir: {self.notebook_data_dir}")
        logger.info(f"  Working Directory: {os.getcwd()}")
        logger.info(f"  Available files: {[f['name'] for f in self.list_available_files()]}")
    
    def _copy_sample_data(self):
        """Copy sample data preserving ORIGINAL filenames - NO random prefixes!"""
        if not self.sample_data_source.exists():
            logger.warning(f"Sample data source not found: {self.sample_data_source}")
            return
            
        for item in self.sample_data_source.iterdir():
            if item.is_file() and item.suffix in ['.csv', '.json', '.xlsx', '.txt']:
                # PRESERVE ORIGINAL FILENAME!
                dest_path = self.notebook_data_dir / item.name
                if not dest_path.exists():
                    shutil.copy(item, dest_path)
                    logger.info(f"✅ Copied: {item.name} -> {dest_path}")
    
    def list_available_files(self) -> List[Dict[str, Any]]:
        """List all files in the notebook data directory with original filenames."""
        files_info = []
        
        if not self.notebook_data_dir.exists():
            return files_info
            
        for file_path in self.notebook_data_dir.iterdir():
            if file_path.is_file():
                file_info = {
                    'name': file_path.name,  # ORIGINAL FILENAME!
                    'path': f"data/{file_path.name}",  # Simple path for LLM
                    'absolute_path': str(file_path),
                    'size': file_path.stat().st_size,
                    'type': file_path.suffix[1:] if file_path.suffix else 'other',
                    'lastModified': datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                }
                
                # Add preview for CSV files
                try:
                    if file_path.suffix == '.csv':
                        df_preview = pd.read_csv(file_path, nrows=5)
                        df_full = pd.read_csv(file_path)
                        file_info['preview'] = {
                            'rows': len(df_full),
                            'columns': df_preview.columns.tolist(),
                            'shape': [len(df_full), len(df_preview.columns)]
                        }
                except Exception as e:
                    logger.warning(f"Could not read preview for {file_path.name}: {e}")
                    file_info['preview'] = {'error': str(e)}
                    
                files_info.append(file_info)
                
        return files_info
    
    def get_execution_context(self) -> Dict[str, Any]:
        """Get context for LLM code generation with proper file paths."""
        files = self.list_available_files()
        context = {
            'notebook_id': self.notebook_id,
            'files_in_context': files,
            'data_directory_path': "data",  # LLM should use 'data/filename.csv'
            'working_directory_info': f"Working in notebook {self.notebook_id}, use 'data/filename.csv' paths"
        }
        return context
    
    def get_notebook_working_directory(self) -> Path:
        """Get the working directory for code execution (parent of data/ folder)."""
        return self.notebook_data_dir.parent
    
    def upload_file(self, file_name: str, content: bytes) -> List[Dict[str, Any]]:
        """Upload file with ORIGINAL filename to notebook data directory."""
        file_path = self.notebook_data_dir / file_name  # NO random prefixes!
        with open(file_path, 'wb') as f:
            f.write(content)
        logger.info(f"✅ Uploaded: {file_name} -> {file_path}")
        return self.list_available_files()
    
    def delete_file(self, file_name: str) -> bool:
        """Delete file from notebook data directory."""
        file_path = self.notebook_data_dir / file_name
        if file_path.exists():
            file_path.unlink()
            logger.info(f"🗑️ Deleted: {file_name}")
            return True
        logger.warning(f"❌ File not found: {file_name}")
        return False

# Global instance - will be replaced with notebook-specific instances
_global_data_manager = None

def get_data_manager(notebook_id: str = None) -> DataManager:
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
