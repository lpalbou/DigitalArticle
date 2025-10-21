"""
Data Manager for the Digital Article.

This service handles data file management, storage, and access for notebook execution.
It provides a centralized way to manage datasets that biologists upload or reference.
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
    """Manages data files and their metadata for notebook execution."""
    
    def __init__(self, workspace_root: Optional[str] = None):
        """
        Initialize the data manager.
        
        Args:
            workspace_root: Root directory for the notebook workspace
        """
        # Set up the workspace structure
        if workspace_root:
            self.workspace_root = Path(workspace_root)
        else:
            # Default to a dedicated workspace directory
            self.workspace_root = Path.cwd() / "notebook_workspace"
        
        # Create workspace structure
        self.workspace_root.mkdir(exist_ok=True)
        self.data_dir = self.workspace_root / "data"
        self.data_dir.mkdir(exist_ok=True)
        self.metadata_file = self.workspace_root / "data_registry.json"
        
        # Ensure we have a clean execution environment
        os.chdir(str(self.workspace_root))
        
        logger.info(f"Data manager initialized:")
        logger.info(f"  Workspace root: {self.workspace_root}")
        logger.info(f"  Data directory: {self.data_dir}")
        logger.info(f"  Working directory: {os.getcwd()}")
        
        # Load or create data registry
        self.data_registry = self._load_data_registry()
        
    def _load_data_registry(self) -> Dict[str, Any]:
        """Load the data registry file or create a new one."""
        try:
            if self.metadata_file.exists():
                with open(self.metadata_file, 'r') as f:
                    return json.load(f)
            else:
                return {"files": {}, "created_at": datetime.now().isoformat()}
        except Exception as e:
            logger.warning(f"Could not load data registry: {e}")
            return {"files": {}, "created_at": datetime.now().isoformat()}
    
    def _save_data_registry(self):
        """Save the data registry to file."""
        try:
            self.data_registry["updated_at"] = datetime.now().isoformat()
            with open(self.metadata_file, 'w') as f:
                json.dump(self.data_registry, f, indent=2)
        except Exception as e:
            logger.error(f"Could not save data registry: {e}")
    
    def register_file(self, file_path: str, original_name: str = None) -> Dict[str, Any]:
        """
        Register a file in the data directory and extract metadata.
        
        Args:
            file_path: Path to the source file
            original_name: Original filename (if different from file_path)
            
        Returns:
            File metadata dictionary
        """
        source_path = Path(file_path)
        if not source_path.exists():
            raise FileNotFoundError(f"Source file not found: {file_path}")
        
        # Generate a clean filename
        file_name = original_name or source_path.name
        file_id = str(uuid.uuid4())[:8]
        clean_name = f"{file_id}_{file_name}"
        
        # Copy file to data directory
        dest_path = self.data_dir / clean_name
        shutil.copy2(source_path, dest_path)
        
        # Extract metadata
        metadata = self._extract_file_metadata(dest_path, file_name)
        
        # Register in the registry
        self.data_registry["files"][clean_name] = metadata
        self._save_data_registry()
        
        logger.info(f"Registered file: {clean_name} -> {dest_path}")
        return metadata
    
    def _extract_file_metadata(self, file_path: Path, original_name: str) -> Dict[str, Any]:
        """Extract metadata from a data file."""
        metadata = {
            "original_name": original_name,
            "path": f"data/{file_path.name}",
            "absolute_path": str(file_path),
            "size": file_path.stat().st_size,
            "type": self._get_file_type(file_path),
            "registered_at": datetime.now().isoformat()
        }
        
        # Try to extract data-specific metadata
        try:
            if file_path.suffix.lower() == '.csv':
                df = pd.read_csv(file_path)
                metadata.update({
                    "preview": {
                        "rows": len(df),
                        "columns": df.columns.tolist(),
                        "shape": list(df.shape),
                        "dtypes": df.dtypes.astype(str).to_dict(),
                        "sample_data": df.head(3).to_dict('records') if len(df) > 0 else []
                    }
                })
            elif file_path.suffix.lower() == '.json':
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        metadata["preview"] = {
                            "type": "list",
                            "length": len(data),
                            "sample": data[:3] if len(data) > 0 else []
                        }
                    elif isinstance(data, dict):
                        metadata["preview"] = {
                            "type": "dict", 
                            "keys": list(data.keys())[:10],
                            "sample": {k: data[k] for k in list(data.keys())[:3]}
                        }
        except Exception as e:
            logger.warning(f"Could not extract preview for {file_path}: {e}")
            metadata["preview"] = {"error": str(e)}
        
        return metadata
    
    def _get_file_type(self, file_path: Path) -> str:
        """Determine the file type from extension."""
        ext = file_path.suffix.lower()
        type_map = {
            '.csv': 'csv',
            '.json': 'json',
            '.xlsx': 'excel',
            '.xls': 'excel',
            '.txt': 'text',
            '.tsv': 'tsv'
        }
        return type_map.get(ext, 'other')
    
    def list_available_files(self) -> List[Dict[str, Any]]:
        """Get a list of all available data files."""
        files = []
        for filename, metadata in self.data_registry["files"].items():
            # Verify file still exists
            file_path = self.data_dir / filename
            if file_path.exists():
                files.append(metadata)
            else:
                logger.warning(f"File missing from disk: {filename}")
        
        return files
    
    def get_file_info(self, filename: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a specific file."""
        return self.data_registry["files"].get(filename)
    
    def get_execution_context(self) -> Dict[str, Any]:
        """Get context information for LLM code generation."""
        return {
            "workspace_root": str(self.workspace_root),
            "data_directory": "data",  # Relative to workspace root
            "working_directory": os.getcwd(),
            "available_files": self.list_available_files()
        }
    
    def setup_sample_data(self):
        """Set up sample datasets for demonstration."""
        sample_data_dir = Path(__file__).parent.parent.parent.parent / "sample_data"
        
        if sample_data_dir.exists():
            logger.info("Setting up sample data from sample_data directory")
            for csv_file in sample_data_dir.glob("*.csv"):
                try:
                    self.register_file(str(csv_file))
                    logger.info(f"Registered sample file: {csv_file.name}")
                except Exception as e:
                    logger.error(f"Failed to register {csv_file.name}: {e}")
        else:
            logger.info("No sample_data directory found, creating minimal sample data")
            self._create_minimal_sample_data()
    
    def _create_minimal_sample_data(self):
        """Create minimal sample data if no sample files exist."""
        # Create a simple gene expression dataset
        gene_data = {
            'Gene_ID': ['BRCA1', 'TP53', 'EGFR', 'MYC', 'PIK3CA'],
            'Sample_1': [145.2, 234.5, 89.7, 178.9, 67.8],
            'Sample_2': [158.7, 221.8, 95.4, 185.2, 72.1],
            'Control_1': [98.1, 167.3, 45.6, 123.4, 38.9],
            'Control_2': [105.6, 172.9, 48.3, 128.7, 41.2]
        }
        
        gene_df = pd.DataFrame(gene_data)
        gene_file = self.data_dir / "gene_expression_sample.csv"
        gene_df.to_csv(gene_file, index=False)
        
        # Register the created file
        metadata = self._extract_file_metadata(gene_file, "gene_expression_sample.csv")
        self.data_registry["files"]["gene_expression_sample.csv"] = metadata
        
        logger.info("Created minimal sample gene expression data")
        self._save_data_registry()

# Global data manager instance
_data_manager = None

def get_data_manager() -> DataManager:
    """Get the global data manager instance."""
    global _data_manager
    if _data_manager is None:
        _data_manager = DataManager()
        # NOTE: Sample data is no longer automatically set up for new notebooks
        # _data_manager.setup_sample_data()  # Commented out - users must upload their own data
    return _data_manager
