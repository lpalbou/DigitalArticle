"""
State Persistence Service for Digital Article

This service handles saving and restoring the complete execution state of notebooks,
enabling seamless continuation of work across backend restarts.

Design Philosophy:
- Automatic: State saved after every successful execution, restored on notebook access
- Complete: All serializable Python objects preserved (DataFrames, models, arrays, etc.)
- Reliable: Atomic writes prevent corruption, error recovery handles edge cases
- Transparent: Users don't need to manually save/restore, it just works

Architecture:
- Per-notebook state files stored in notebook_workspace/{notebook_id}/state/
- Pickle-based serialization for complete Python object fidelity
- Lazy loading: State only loaded when notebook is accessed
- Metadata tracking: Save time, variable count, file size for monitoring
"""

import pickle
import logging
import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import hashlib

logger = logging.getLogger(__name__)


class StatePersistenceService:
    """
    Service for persisting and restoring notebook execution state.

    This service provides automatic state persistence for Digital Article notebooks,
    ensuring that all variables created during execution are preserved across
    backend restarts.
    """

    def __init__(self, workspace_root: Path = None):
        """
        Initialize the state persistence service.

        Args:
            workspace_root: Root directory for notebook workspaces.
                          Defaults to backend/notebook_workspace/
        """
        if workspace_root is None:
            # Default to backend/notebook_workspace/
            self.workspace_root = Path(__file__).parent.parent.parent / "notebook_workspace"
        else:
            self.workspace_root = Path(workspace_root)

        self.workspace_root.mkdir(parents=True, exist_ok=True)
        logger.info(f"State persistence service initialized with workspace: {self.workspace_root}")

    def _get_state_dir(self, notebook_id: str) -> Path:
        """Get the state directory for a notebook."""
        state_dir = self.workspace_root / notebook_id / "state"
        state_dir.mkdir(parents=True, exist_ok=True)
        return state_dir

    def _get_state_file(self, notebook_id: str) -> Path:
        """Get the checkpoint file path for a notebook."""
        return self._get_state_dir(notebook_id) / "checkpoint.pkl"

    def _get_metadata_file(self, notebook_id: str) -> Path:
        """Get the metadata file path for a notebook."""
        return self._get_state_dir(notebook_id) / "metadata.json"

    def _prepare_for_pickle(self, globals_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare globals dictionary for pickling by filtering out non-serializable items.

        Filters out:
        - Built-in modules and functions (__, builtins, etc.)
        - Matplotlib figures (already captured as images in results)
        - Module objects
        - Lambda functions and generators

        Args:
            globals_dict: The raw globals dictionary from execution

        Returns:
            Filtered dictionary safe for pickling
        """
        safe_dict = {}
        skipped = []

        for key, value in globals_dict.items():
            # Skip built-in modules and private attributes
            if key.startswith('__'):
                continue

            # Skip imported modules
            if hasattr(value, '__module__') and hasattr(value, '__name__'):
                # This is likely a module or imported function
                if callable(value) and not hasattr(value, '__self__'):
                    # It's a function, not a method - skip
                    skipped.append((key, 'function'))
                    continue

            # Skip matplotlib figures (already captured as images)
            type_str = str(type(value))
            if 'matplotlib.figure.Figure' in type_str:
                skipped.append((key, 'matplotlib.Figure'))
                continue

            # Skip plotly figures (already captured in results)
            if 'plotly.graph' in type_str:
                skipped.append((key, 'plotly.Figure'))
                continue

            # Try to include everything else
            try:
                # Test if it's pickle-able by attempting to pickle it
                pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL)
                safe_dict[key] = value
            except (pickle.PicklingError, TypeError, AttributeError) as e:
                skipped.append((key, f"{type(value).__name__} - {str(e)[:50]}"))
                logger.warning(f"Cannot pickle variable '{key}' ({type(value).__name__}): {e}")

        if skipped:
            logger.info(f"Skipped {len(skipped)} non-serializable variables: "
                       f"{', '.join([f'{k}({t})' for k, t in skipped[:5]])}"
                       f"{'...' if len(skipped) > 5 else ''}")

        return safe_dict

    def save_notebook_state(self, notebook_id: str, globals_dict: Dict[str, Any]) -> bool:
        """
        Save the complete execution state for a notebook.

        This method:
        1. Filters out non-serializable objects
        2. Pickles the globals dictionary
        3. Saves atomically (write to .tmp, then rename)
        4. Saves metadata (timestamp, variable count, size)

        Args:
            notebook_id: Unique identifier for the notebook
            globals_dict: Dictionary of all variables in execution context

        Returns:
            True if save successful, False otherwise
        """
        try:
            # Prepare safe dictionary for pickling
            state_to_save = self._prepare_for_pickle(globals_dict)

            if not state_to_save:
                logger.info(f"No serializable variables to save for notebook {notebook_id}")
                return True

            # Get file paths
            state_file = self._get_state_file(notebook_id)
            temp_file = state_file.with_suffix('.tmp')
            metadata_file = self._get_metadata_file(notebook_id)

            # Pickle the state
            pickled_data = pickle.dumps(state_to_save, protocol=pickle.HIGHEST_PROTOCOL)

            # Calculate checksum for integrity verification
            checksum = hashlib.sha256(pickled_data).hexdigest()

            # Write to temporary file first (atomic write pattern)
            with open(temp_file, 'wb') as f:
                f.write(pickled_data)

            # Atomic rename
            temp_file.replace(state_file)

            # Save metadata
            metadata = {
                'saved_at': datetime.now().isoformat(),
                'variable_count': len(state_to_save),
                'variable_names': list(state_to_save.keys()),
                'file_size_bytes': len(pickled_data),
                'pickle_protocol': pickle.HIGHEST_PROTOCOL,
                'checksum': checksum
            }

            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)

            logger.info(f"✅ Saved state for notebook {notebook_id}: "
                       f"{len(state_to_save)} variables, "
                       f"{len(pickled_data) / 1024:.1f} KB")

            return True

        except Exception as e:
            logger.error(f"❌ Failed to save state for notebook {notebook_id}: {e}", exc_info=True)
            # Don't raise - state persistence failure shouldn't break execution
            return False

    def load_notebook_state(self, notebook_id: str) -> Optional[Dict[str, Any]]:
        """
        Load previously saved execution state for a notebook.

        This method:
        1. Checks if state file exists
        2. Loads and unpickles the state
        3. Verifies integrity using checksum
        4. Returns restored globals dictionary

        Args:
            notebook_id: Unique identifier for the notebook

        Returns:
            Dictionary of restored variables, or None if no saved state or load failed
        """
        try:
            state_file = self._get_state_file(notebook_id)
            metadata_file = self._get_metadata_file(notebook_id)

            # Check if state file exists
            if not state_file.exists():
                logger.debug(f"No saved state found for notebook {notebook_id}")
                return None

            # Load metadata
            metadata = None
            if metadata_file.exists():
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)

            # Load pickled state
            with open(state_file, 'rb') as f:
                pickled_data = f.read()

            # Verify checksum if available
            if metadata and 'checksum' in metadata:
                checksum = hashlib.sha256(pickled_data).hexdigest()
                if checksum != metadata['checksum']:
                    logger.error(f"❌ Checksum mismatch for notebook {notebook_id} state - file may be corrupted")
                    return None

            # Unpickle the state
            restored_state = pickle.loads(pickled_data)

            saved_time = f" (saved {metadata['saved_at']})" if metadata else ""
            logger.info(f"✅ Restored state for notebook {notebook_id}: "
                       f"{len(restored_state)} variables, "
                       f"{len(pickled_data) / 1024:.1f} KB{saved_time}")

            return restored_state

        except FileNotFoundError:
            logger.debug(f"No saved state file for notebook {notebook_id}")
            return None
        except Exception as e:
            logger.error(f"❌ Failed to load state for notebook {notebook_id}: {e}", exc_info=True)
            # Return None to fall back to fresh environment
            return None

    def get_state_metadata(self, notebook_id: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata about saved state without loading the entire state.

        Useful for UI indicators showing state availability and freshness.

        Args:
            notebook_id: Unique identifier for the notebook

        Returns:
            Metadata dictionary, or None if no saved state
        """
        try:
            metadata_file = self._get_metadata_file(notebook_id)

            if not metadata_file.exists():
                return None

            with open(metadata_file, 'r') as f:
                metadata = json.load(f)

            # Add state file existence check
            state_file = self._get_state_file(notebook_id)
            metadata['state_file_exists'] = state_file.exists()

            return metadata

        except Exception as e:
            logger.error(f"Failed to load state metadata for notebook {notebook_id}: {e}")
            return None

    def clear_notebook_state(self, notebook_id: str) -> bool:
        """
        Clear saved state for a notebook.

        This removes both the checkpoint file and metadata.
        Useful for forcing fresh execution or troubleshooting.

        Args:
            notebook_id: Unique identifier for the notebook

        Returns:
            True if state was cleared, False otherwise
        """
        try:
            state_file = self._get_state_file(notebook_id)
            metadata_file = self._get_metadata_file(notebook_id)

            cleared = False

            if state_file.exists():
                state_file.unlink()
                cleared = True

            if metadata_file.exists():
                metadata_file.unlink()
                cleared = True

            if cleared:
                logger.info(f"🗑️  Cleared saved state for notebook {notebook_id}")

            return cleared

        except Exception as e:
            logger.error(f"Failed to clear state for notebook {notebook_id}: {e}")
            return False

    def has_saved_state(self, notebook_id: str) -> bool:
        """
        Check if a notebook has saved state.

        Args:
            notebook_id: Unique identifier for the notebook

        Returns:
            True if saved state exists, False otherwise
        """
        state_file = self._get_state_file(notebook_id)
        return state_file.exists()
