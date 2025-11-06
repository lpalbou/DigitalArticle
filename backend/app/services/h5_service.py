"""
H5 File Processing Service

This service provides comprehensive support for HDF5 files using state-of-the-art practices:
- h5py for low-level HDF5 access
- scanpy/anndata for single-cell genomics data (h5ad files)
- Efficient memory management and metadata extraction
- Interactive preview generation with proper error handling
"""

import logging
import h5py
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, Tuple
import json
import traceback

class H5JSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for H5 data structures."""
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            if obj.size == 1:
                return obj.item()
            else:
                return obj.tolist()
        elif isinstance(obj, (np.integer, np.floating)):
            return obj.item()
        elif isinstance(obj, np.bool_):
            return bool(obj)
        elif isinstance(obj, bytes):
            return obj.decode('utf-8', errors='ignore')
        elif hasattr(obj, 'tolist'):  # Handle other numpy-like objects
            return obj.tolist()
        elif hasattr(obj, '__dict__'):  # Handle custom objects
            return str(obj)
        else:
            return super().default(obj)

try:
    import scanpy as sc
    import anndata as ad
    SCANPY_AVAILABLE = True
except ImportError:
    SCANPY_AVAILABLE = False
    sc = None
    ad = None

logger = logging.getLogger(__name__)

class H5FileProcessor:
    """
    Robust general-purpose H5 file processor that handles various H5 formats
    including scientific data, genomics data, and general HDF5 files.
    """
    
    def __init__(self):
        self.supported_extensions = {'.h5', '.hdf5', '.h5ad'}
        
    def is_h5_file(self, file_path: Union[str, Path]) -> bool:
        """Check if file is a supported H5 format."""
        file_path = Path(file_path)
        return file_path.suffix.lower() in self.supported_extensions
    
    def process_file(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Process H5 file and extract comprehensive metadata and preview data.
        
        This method implements robust general-purpose logic that works for:
        - Standard HDF5 files (.h5, .hdf5)
        - AnnData files (.h5ad) for single-cell genomics
        - Complex nested structures
        - Large datasets (with memory-efficient sampling)
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"H5 file not found: {file_path}")
        
        if not self.is_h5_file(file_path):
            raise ValueError(f"Unsupported file format: {file_path.suffix}")
        
        try:
            # Determine file type and process accordingly
            if file_path.suffix.lower() == '.h5ad' and SCANPY_AVAILABLE:
                return self._process_anndata_file(file_path)
            else:
                return self._process_hdf5_file(file_path)
                
        except Exception as e:
            logger.error(f"Error processing H5 file {file_path}: {str(e)}")
            logger.error(traceback.format_exc())
            raise
    
    def _process_anndata_file(self, file_path: Path) -> Dict[str, Any]:
        """Process AnnData (.h5ad) files for single-cell genomics data."""
        try:
            # Read AnnData object with memory efficiency
            adata = ad.read_h5ad(file_path, backed='r')  # Read-only backed mode
            
            metadata = {
                'file_type': 'anndata',
                'file_size': file_path.stat().st_size,
                'n_obs': adata.n_obs,
                'n_vars': adata.n_vars,
                'obs_keys': list(adata.obs.columns) if adata.obs is not None else [],
                'var_keys': list(adata.var.columns) if adata.var is not None else [],
                'obsm_keys': list(adata.obsm.keys()) if adata.obsm is not None else [],
                'varm_keys': list(adata.varm.keys()) if adata.varm is not None else [],
                'uns_keys': list(adata.uns.keys()) if adata.uns is not None else [],
                'layers': list(adata.layers.keys()) if adata.layers is not None else [],
            }
            
            # Generate preview data
            preview_data = self._generate_anndata_preview(adata)
            metadata.update(preview_data)
            
            return metadata
            
        except Exception as e:
            logger.error(f"Error processing AnnData file: {str(e)}")
            # Fallback to standard HDF5 processing
            return self._process_hdf5_file(file_path)
    
    def _process_hdf5_file(self, file_path: Path) -> Dict[str, Any]:
        """Process standard HDF5 files with comprehensive structure analysis."""
        metadata = {
            'file_type': 'hdf5',
            'file_size': file_path.stat().st_size,
            'structure': {},
            'datasets': [],
            'groups': [],
            'attributes': {}
        }
        
        try:
            with h5py.File(file_path, 'r') as f:
                # Extract file-level attributes
                metadata['attributes'] = self._extract_attributes(f)
                
                # Recursively analyze structure
                metadata['structure'] = self._analyze_h5_structure(f)
                
                # Extract dataset and group information
                self._extract_datasets_and_groups(f, metadata)
                
                # Generate preview data for key datasets
                metadata['preview_data'] = self._generate_hdf5_preview(f)
                
        except Exception as e:
            logger.error(f"Error reading HDF5 file: {str(e)}")
            metadata['error'] = str(e)
            
        return metadata
    
    def _analyze_h5_structure(self, h5_obj, path: str = "/") -> Dict[str, Any]:
        """Recursively analyze HDF5 structure with depth control."""
        structure = {}
        
        def visitor(name, obj):
            try:
                if isinstance(obj, h5py.Dataset):
                    structure[name] = {
                        'type': 'dataset',
                        'shape': obj.shape,
                        'dtype': str(obj.dtype),
                        'size': obj.size,
                        'attributes': self._extract_attributes(obj)
                    }
                elif isinstance(obj, h5py.Group):
                    structure[name] = {
                        'type': 'group',
                        'attributes': self._extract_attributes(obj),
                        'children': len(obj.keys())
                    }
            except Exception as e:
                logger.warning(f"Error analyzing object {name}: {str(e)}")
                structure[name] = {'type': 'error', 'error': str(e)}
        
        h5_obj.visititems(visitor)
        return structure
    
    def _extract_attributes(self, h5_obj) -> Dict[str, Any]:
        """Extract attributes from HDF5 object with type conversion."""
        attributes = {}
        try:
            for key in h5_obj.attrs.keys():
                try:
                    value = h5_obj.attrs[key]
                    # Convert numpy types to Python types for JSON serialization
                    if isinstance(value, np.ndarray):
                        if value.size == 1:
                            attributes[key] = self._safe_convert(value.item())
                        else:
                            # Limit large arrays to prevent memory issues
                            if value.size > 1000:
                                attributes[key] = f"<array of {value.shape} {value.dtype}>"
                            else:
                                attributes[key] = [self._safe_convert(x) for x in value.tolist()]
                    elif isinstance(value, (np.integer, np.floating, np.bool_)):
                        attributes[key] = value.item()
                    elif isinstance(value, bytes):
                        attributes[key] = value.decode('utf-8', errors='ignore')
                    elif isinstance(value, str):
                        attributes[key] = value
                    else:
                        # For any other type, convert to string as fallback
                        attributes[key] = str(value)
                except Exception as e:
                    logger.warning(f"Error extracting attribute {key}: {str(e)}")
                    attributes[key] = f"<error reading attribute: {str(e)}>"
        except Exception as e:
            logger.warning(f"Error extracting attributes: {str(e)}")
        
        return attributes
    
    def _safe_convert(self, value):
        """Safely convert a value to a JSON-serializable type."""
        if isinstance(value, (int, float, bool, str)):
            return value
        elif isinstance(value, bytes):
            return value.decode('utf-8', errors='ignore')
        elif isinstance(value, (np.integer, np.floating, np.bool_)):
            return value.item()
        else:
            return str(value)
    
    def _extract_datasets_and_groups(self, h5_obj, metadata: Dict[str, Any]):
        """Extract detailed information about datasets and groups."""
        def visitor(name, obj):
            try:
                if isinstance(obj, h5py.Dataset):
                    dataset_info = {
                        'name': name,
                        'shape': list(obj.shape),  # Convert to list for JSON
                        'dtype': str(obj.dtype),
                        'size': int(obj.size),  # Ensure it's a Python int
                        'compression': str(obj.compression) if obj.compression else None,
                        'chunks': list(obj.chunks) if obj.chunks else None,
                        'attributes': self._extract_attributes(obj)
                    }
                    metadata['datasets'].append(dataset_info)
                elif isinstance(obj, h5py.Group):
                    group_info = {
                        'name': name,
                        'attributes': self._extract_attributes(obj),
                        'children': list(obj.keys())
                    }
                    metadata['groups'].append(group_info)
            except Exception as e:
                logger.warning(f"Error processing {name}: {str(e)}")
        
        h5_obj.visititems(visitor)
    
    def _generate_anndata_preview(self, adata) -> Dict[str, Any]:
        """Generate preview data for AnnData objects."""
        preview = {}
        
        try:
            # Sample observations for preview (max 100 rows)
            n_sample = min(100, adata.n_obs)
            sample_indices = np.random.choice(adata.n_obs, n_sample, replace=False)
            
            # Preview observation metadata
            if adata.obs is not None and not adata.obs.empty:
                obs_sample = adata.obs.iloc[sample_indices]
                preview['obs_preview'] = {
                    'columns': list(obs_sample.columns),
                    'sample_data': obs_sample.head(10).to_dict('records'),
                    'dtypes': obs_sample.dtypes.astype(str).to_dict()
                }
            
            # Preview variable metadata
            if adata.var is not None and not adata.var.empty:
                var_sample = adata.var.head(100)
                preview['var_preview'] = {
                    'columns': list(var_sample.columns),
                    'sample_data': var_sample.head(10).to_dict('records'),
                    'dtypes': var_sample.dtypes.astype(str).to_dict()
                }
            
            # Preview expression matrix (small sample)
            if hasattr(adata, 'X') and adata.X is not None:
                # Sample a small portion of the expression matrix
                sample_genes = min(50, adata.n_vars)
                gene_indices = np.random.choice(adata.n_vars, sample_genes, replace=False)
                
                # Get expression data for sample
                if hasattr(adata.X, 'toarray'):  # Sparse matrix
                    expr_sample = adata.X[sample_indices[:10]][:, gene_indices[:10]].toarray()
                else:  # Dense matrix
                    expr_sample = adata.X[sample_indices[:10]][:, gene_indices[:10]]
                
                preview['expression_preview'] = {
                    'shape': expr_sample.shape,
                    'sample_data': expr_sample.tolist(),
                    'is_sparse': hasattr(adata.X, 'toarray')
                }
            
            # Preview embeddings if available
            if adata.obsm is not None:
                for key in list(adata.obsm.keys())[:3]:  # Preview first 3 embeddings
                    embedding = adata.obsm[key]
                    if embedding is not None:
                        preview[f'embedding_{key}'] = {
                            'shape': embedding.shape,
                            'sample_data': embedding[sample_indices[:10]].tolist()
                        }
            
        except Exception as e:
            logger.warning(f"Error generating AnnData preview: {str(e)}")
            preview['preview_error'] = str(e)
        
        return preview
    
    def _generate_hdf5_preview(self, h5_obj) -> Dict[str, Any]:
        """Generate preview data for HDF5 datasets."""
        preview = {}
        
        def visitor(name, obj):
            try:
                if isinstance(obj, h5py.Dataset) and len(preview) < 5:  # Limit previews
                    dataset_preview = self._preview_dataset(obj)
                    if dataset_preview:
                        preview[name] = dataset_preview
            except Exception as e:
                logger.warning(f"Error previewing dataset {name}: {str(e)}")
        
        h5_obj.visititems(visitor)
        return preview
    
    def _preview_dataset(self, dataset: h5py.Dataset) -> Optional[Dict[str, Any]]:
        """Generate preview for a single HDF5 dataset."""
        try:
            # Skip very large datasets for preview
            if dataset.size > 1e6:  # More than 1M elements
                return {
                    'shape': dataset.shape,
                    'dtype': str(dataset.dtype),
                    'size': dataset.size,
                    'preview_note': 'Dataset too large for preview'
                }
            
            # Sample data for preview
            if len(dataset.shape) == 1:
                # 1D array
                sample_size = min(100, dataset.shape[0])
                sample_data = dataset[:sample_size].tolist()
            elif len(dataset.shape) == 2:
                # 2D array
                rows = min(10, dataset.shape[0])
                cols = min(10, dataset.shape[1])
                sample_data = dataset[:rows, :cols].tolist()
            else:
                # Multi-dimensional - just show shape and type
                return {
                    'shape': dataset.shape,
                    'dtype': str(dataset.dtype),
                    'size': dataset.size,
                    'preview_note': f'{len(dataset.shape)}D dataset - shape only'
                }
            
            return {
                'shape': dataset.shape,
                'dtype': str(dataset.dtype),
                'size': dataset.size,
                'sample_data': sample_data
            }
            
        except Exception as e:
            logger.warning(f"Error creating dataset preview: {str(e)}")
            return None

# Global instance
h5_processor = H5FileProcessor()
