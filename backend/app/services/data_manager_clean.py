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
        
        # Copy sample data if data directory is empty
        if not any(self.data_dir.iterdir()):
            self._copy_sample_data()
            
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
                
        return sorted(files_info, key=lambda x: x['name'])
    
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
