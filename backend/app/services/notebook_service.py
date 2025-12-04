"""
Notebook Service for managing notebook persistence and operations.

This service handles saving, loading, and managing notebook files,
as well as coordinating between LLM and execution services.
"""

import json
import os
import uuid
from uuid import UUID
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

from ..models.notebook import (
    Notebook, Cell, CellType, ExecutionResult, ExecutionStatus, CellState,
    NotebookCreateRequest, NotebookUpdateRequest,
    CellCreateRequest, CellUpdateRequest, CellExecuteRequest
)
from .llm_service import LLMService
from .execution_service import ExecutionService
from .pdf_service_scientific import ScientificPDFService
from .semantic_service import SemanticExtractionService
from .semantic_analysis_service import SemanticAnalysisService
from .semantic_profile_service import SemanticProfileService
from .analysis_planner import AnalysisPlanner
from .analysis_critic import AnalysisCritic
from .review_service import ReviewService
from ..models.analysis_plan import AnalysisPlan
from ..models.analysis_critique import AnalysisCritique

logger = logging.getLogger(__name__)


class NotebookService:
    """Service for managing notebooks and coordinating cell operations."""
    
    def __init__(self, notebooks_dir: str = "notebooks"):
        """
        Initialize the notebook service.
        
        Args:
            notebooks_dir: Directory to store notebook files
        """
        logger.info("🚀 INITIALIZING NOTEBOOK SERVICE")
        
        try:
            # Ensure notebooks directory is relative to project root, not current working directory
            if not os.path.isabs(notebooks_dir):
                # Get the project root (4 levels up from this file)
                project_root = Path(__file__).parent.parent.parent.parent
                self.notebooks_dir = project_root / notebooks_dir
            else:
                self.notebooks_dir = Path(notebooks_dir)
                
            try:
                self.notebooks_dir.mkdir(exist_ok=True, parents=True)
            except PermissionError:
                # In Docker, the directory might be a volume owned by root
                # but mounted correctly. If it exists, we proceed.
                if not self.notebooks_dir.exists():
                    raise
            
            logger.info(f"✅ Notebook service using directory: {self.notebooks_dir}")
            
            # Initialize services
            logger.info("🔄 Initializing LLM service...")
            self.llm_service = LLMService()
            logger.info("✅ LLM service initialized")
            
            logger.info("🔄 Initializing execution service...")
            self.execution_service = ExecutionService()
            logger.info("✅ Execution service initialized")
            
            logger.info("🔄 Initializing scientific PDF service...")
            self.pdf_service = ScientificPDFService()
            logger.info("✅ Scientific PDF service initialized")

            logger.info("🔄 Initializing semantic extraction service...")
            self.semantic_service = SemanticExtractionService()
            logger.info("✅ Semantic extraction service initialized")

            logger.info("🔄 Initializing analysis graph service...")
            self.analysis_graph_service = SemanticAnalysisService()
            logger.info("✅ Analysis graph service initialized")

            logger.info("🔄 Initializing profile graph service...")
            self.profile_graph_service = SemanticProfileService()
            logger.info("✅ Profile graph service initialized")

            logger.info("🔄 Initializing review service...")
            self.review_service = ReviewService(self.llm_service)
            logger.info("✅ Review service initialized")

            # Get data manager for file context
            logger.info("🔄 Getting data manager...")
            from .data_manager_clean import get_data_manager
            self.data_manager = get_data_manager()
            logger.info("✅ Data manager initialized")
            
            # In-memory notebook cache
            self._notebooks: Dict[str, Notebook] = {}
            
            # Load existing notebooks
            logger.info("🔄 Loading existing notebooks...")
            self._load_notebooks()
            logger.info(f"✅ Loaded {len(self._notebooks)} notebooks")
            
            logger.info("🎉 NOTEBOOK SERVICE INITIALIZATION COMPLETE")
            
        except Exception as e:
            logger.error(f"💥 FAILED TO INITIALIZE NOTEBOOK SERVICE: {e}")
            logger.error(f"💥 Exception type: {type(e)}")
            import traceback
            logger.error(f"💥 Full traceback:\n{traceback.format_exc()}")
            raise
    
    def _load_notebooks(self):
        """Load all notebooks from disk."""
        try:
            for notebook_file in self.notebooks_dir.glob("*.json"):
                # Skip temporary files
                if notebook_file.name.endswith('.tmp'):
                    continue
                    
                try:
                    with open(notebook_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    notebook = Notebook(**data)
                    self._notebooks[str(notebook.id)] = notebook
                    logger.info(f"Loaded notebook: {notebook.title}")
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Corrupted JSON in notebook {notebook_file.name}: {e}")
                    logger.error(f"Consider moving {notebook_file.name} to a backup location for manual recovery")
                    # Optionally, move corrupted file to a backup location
                    backup_file = notebook_file.with_suffix('.json.corrupted')
                    try:
                        notebook_file.rename(backup_file)
                        logger.info(f"Moved corrupted file to {backup_file.name}")
                    except Exception as rename_error:
                        logger.error(f"Could not backup corrupted file: {rename_error}")
                        
                except Exception as e:
                    logger.error(f"Failed to load notebook {notebook_file.name}: {e}")
                    
        except Exception as e:
            logger.error(f"Failed to load notebooks: {e}")
    
    def create_notebook(self, request: NotebookCreateRequest) -> Notebook:
        """
        Create a new notebook.
        
        Args:
            request: Notebook creation parameters
            
        Returns:
            Created notebook
        """
        notebook = Notebook(
            title=request.title,
            description=request.description,
            author=request.author,
            llm_model=request.llm_model,
            llm_provider=request.llm_provider
        )
        
        # Add a default empty prompt cell for immediate use
        default_cell = notebook.add_cell(
            cell_type=CellType.PROMPT,
            content=""
        )
        
        # Cache and save
        notebook_id = str(notebook.id)
        self._notebooks[notebook_id] = notebook
        self._save_notebook(notebook)
        
        logger.info(f"Created new notebook: {notebook.title} with ID: {notebook_id}")
        logger.info(f"Notebooks in cache: {list(self._notebooks.keys())}")
        return notebook
    
    def _build_execution_context(self, notebook: Notebook, current_cell: Cell) -> Dict[str, Any]:
        """
        Build comprehensive execution context for LLM code generation.

        Includes:
        - Persona combination (if persona selected for notebook)
        - Available variables in execution context
        - Previous cells (prompts and code) for context awareness
        - Data files available
        - Notebook metadata
        - Notebook ID and Cell ID for token tracking

        Args:
            notebook: Current notebook
            current_cell: Cell being executed

        Returns:
            Context dictionary for LLM with previous cell history and persona guidance
        """
        context = {}

        try:
            # Add basic notebook info
            context['notebook_title'] = notebook.title
            context['cell_type'] = current_cell.cell_type.value

            # Add IDs for token tracking (AbstractCore integration)
            context['notebook_id'] = str(notebook.id)
            context['cell_id'] = str(current_cell.id)

            # Load and combine personas if selected for notebook
            try:
                from ..services.persona_service import PersonaService
                from ..models.persona import PersonaSelection

                if 'personas' in notebook.metadata and notebook.metadata['personas']:
                    persona_data = notebook.metadata['personas']
                    persona_selection = PersonaSelection(**persona_data)

                    persona_service = PersonaService()
                    persona_combination = persona_service.combine_personas(
                        persona_selection,
                        username=None  # Will use only system personas for now
                    )

                    context['persona_combination'] = persona_combination
                    logger.info(f"Loaded persona combination: {persona_combination.source_personas}")
            except Exception as e:
                logger.warning(f"Could not load persona combination: {e}")

            # Add information about available data files
            try:
                execution_context = self.data_manager.get_execution_context()
                context.update(execution_context)
            except Exception as e:
                logger.warning(f"Could not get data manager context: {e}")

            # Get available variables from execution service (notebook-specific)
            try:
                variables = self.execution_service.get_variable_info(str(notebook.id))
                if variables:
                    context['available_variables'] = variables
                    logger.info(f"Added {len(variables)} available variables to context for notebook {notebook.id}")
            except Exception as e:
                logger.warning(f"Could not get variable info for notebook {notebook.id}: {e}")

            # Get previous cells context for LLM awareness
            previous_cells = []
            for cell in notebook.cells:
                if cell.id == current_cell.id:
                    break  # Stop at current cell
                if cell.cell_type in (CellType.PROMPT, CellType.CODE) and cell.code:
                    previous_cells.append({
                        'type': cell.cell_type.value,
                        'prompt': cell.prompt if cell.cell_type == CellType.PROMPT else None,
                        'code': cell.code,  # Full code - LLM needs complete context
                        'success': cell.last_result.status == ExecutionStatus.SUCCESS if cell.last_result else None,
                        'has_dataframes': bool(cell.last_result and cell.last_result.tables) if cell.last_result else False
                    })

            if previous_cells:
                context['previous_cells'] = previous_cells
                logger.info(f"Added {len(previous_cells)} previous cells to context")

            logger.info(f"Built execution context with {len(context)} context items")
            return context

        except Exception as e:
            logger.error(f"Error building execution context: {e}")
            return {}
    
    # REMOVED: _generate_fallback_code() method
    # Fallback code generation is harmful - it masks LLM errors with nonsense code
    # Instead, we rely on:
    # 1. Retry mechanism to fix actual code errors
    # 2. Proper error surfacing when LLM is unavailable
    # 3. User notification of the real problem (API keys, rate limits, etc.)
    
    def get_notebook(self, notebook_id: str) -> Optional[Notebook]:
        """
        Get a notebook by ID.
        
        Args:
            notebook_id: Notebook UUID
            
        Returns:
            Notebook or None if not found
        """
        return self._notebooks.get(notebook_id)
    
    def get_cell(self, cell_id: str) -> Optional[Cell]:
        """
        Get a cell by ID across all notebooks.

        Args:
            cell_id: Cell UUID (as string or UUID)

        Returns:
            Cell or None if not found
        """
        from uuid import UUID

        # Convert string to UUID if needed
        try:
            if isinstance(cell_id, str):
                cell_uuid = UUID(cell_id)
            else:
                cell_uuid = cell_id
        except (ValueError, AttributeError) as e:
            logger.error(f"Invalid cell_id format: {cell_id}, error: {e}")
            return None

        for notebook in self._notebooks.values():
            cell = notebook.get_cell(cell_uuid)
            if cell:
                return cell
        return None
    
    def list_notebooks(self) -> List[Notebook]:
        """
        Get all notebooks.
        
        Returns:
            List of all notebooks
        """
        return list(self._notebooks.values())
    
    def get_notebook_summaries(self) -> List[Dict[str, Any]]:
        """
        Get notebook summaries for browsing interface.
        
        Returns:
            List of notebook summaries with metadata and statistics
        """
        summaries = []
        
        for notebook in self._notebooks.values():
            # Calculate statistics based on content, not cell type
            total_cells = len(notebook.cells)
            executed_cells = sum(1 for cell in notebook.cells if cell.last_result and cell.last_result.status == ExecutionStatus.SUCCESS)
            
            # Count cells by actual content presence (more accurate than cell_type)
            cells_with_prompts = sum(1 for cell in notebook.cells if cell.prompt and cell.prompt.strip())
            cells_with_code = sum(1 for cell in notebook.cells if cell.code and cell.code.strip())
            cells_with_methodology = sum(1 for cell in notebook.cells if cell.scientific_explanation and cell.scientific_explanation.strip())
            cells_with_markdown = sum(1 for cell in notebook.cells if cell.markdown and cell.markdown.strip())
            
            # Get latest activity
            latest_activity = notebook.updated_at
            for cell in notebook.cells:
                if cell.updated_at > latest_activity:
                    latest_activity = cell.updated_at
            
            # Check if has content
            has_content = any(cell.prompt or cell.code or cell.markdown for cell in notebook.cells)
            has_results = any(cell.last_result and cell.last_result.status == ExecutionStatus.SUCCESS for cell in notebook.cells)
            
            # Create summary
            summary = {
                "id": str(notebook.id),
                "title": notebook.title,
                "description": notebook.description,
                "author": notebook.author,
                "created_at": notebook.created_at.isoformat(),
                "updated_at": notebook.updated_at.isoformat(),
                "latest_activity": latest_activity.isoformat(),
                "tags": notebook.tags,
                "llm_provider": notebook.llm_provider,
                "llm_model": notebook.llm_model,
                "statistics": {
                    "total_cells": total_cells,
                    "executed_cells": executed_cells,
                    "cells_with_prompts": cells_with_prompts,
                    "cells_with_code": cells_with_code,
                    "cells_with_methodology": cells_with_methodology,
                    "cells_with_markdown": cells_with_markdown,
                    "execution_rate": round(executed_cells / total_cells * 100, 1) if total_cells > 0 else 0
                },
                "status": {
                    "has_content": has_content,
                    "has_results": has_results,
                    "is_empty": total_cells == 0 or not has_content
                }
            }
            
            summaries.append(summary)
        
        # Sort by latest activity (most recent first)
        summaries.sort(key=lambda x: x["latest_activity"], reverse=True)
        
        return summaries
    
    def mark_cells_as_stale(self, notebook_id: str, from_cell_index: int) -> bool:
        """
        Mark all cells below the given index as stale.
        
        Args:
            notebook_id: Notebook UUID
            from_cell_index: Index of the cell that was re-run (0-based)
            
        Returns:
            True if cells were marked as stale, False if notebook not found
        """
        notebook = self._notebooks.get(notebook_id)
        if not notebook:
            return False
        
        # Mark all cells after the given index as stale
        cells_marked = 0
        for i in range(from_cell_index + 1, len(notebook.cells)):
            cell = notebook.cells[i]
            if cell.cell_state != CellState.STALE:
                cell.cell_state = CellState.STALE
                cell.updated_at = datetime.now()
                cells_marked += 1
        
        if cells_marked > 0:
            notebook.updated_at = datetime.now()
            self._save_notebook(notebook)
            logger.info(f"Marked {cells_marked} cells as stale in notebook {notebook.title}")
        
        return True
    
    def mark_cell_as_fresh(self, notebook_id: str, cell_id: UUID) -> bool:
        """
        Mark a specific cell as fresh (recently executed).
        
        Args:
            notebook_id: Notebook UUID
            cell_id: Cell UUID
            
        Returns:
            True if cell was marked as fresh, False if not found
        """
        notebook = self._notebooks.get(notebook_id)
        if not notebook:
            return False
        
        cell = notebook.get_cell(cell_id)
        if not cell:
            return False
        
        cell.cell_state = CellState.FRESH
        cell.updated_at = datetime.now()
        notebook.updated_at = datetime.now()
        self._save_notebook(notebook)
        
        logger.info(f"Marked cell {cell_id} as fresh in notebook {notebook.title}")
        return True
    
    def bulk_update_cell_states(self, notebook_id: str, cell_updates: List[Dict[str, Any]]) -> bool:
        """
        Update multiple cell states in bulk.
        
        Args:
            notebook_id: Notebook UUID
            cell_updates: List of dicts with 'cell_id' and 'state' keys
            
        Returns:
            True if updates were successful, False if notebook not found
        """
        notebook = self._notebooks.get(notebook_id)
        if not notebook:
            return False
        
        updated_count = 0
        for update in cell_updates:
            cell_id = update.get('cell_id')
            new_state = update.get('state')
            
            if not cell_id or not new_state:
                continue
                
            try:
                cell_uuid = UUID(cell_id) if isinstance(cell_id, str) else cell_id
                cell = notebook.get_cell(cell_uuid)
                
                if cell and hasattr(CellState, new_state.upper()):
                    cell.cell_state = CellState(new_state.lower())
                    cell.updated_at = datetime.now()
                    updated_count += 1
                    
            except (ValueError, AttributeError) as e:
                logger.warning(f"Invalid cell update: {update}, error: {e}")
                continue
        
        if updated_count > 0:
            notebook.updated_at = datetime.now()
            self._save_notebook(notebook)
            logger.info(f"Bulk updated {updated_count} cell states in notebook {notebook.title}")
        
        return True
    
    def get_cells_below_index(self, notebook_id: str, cell_index: int) -> List[Cell]:
        """
        Get all cells below a given index.
        
        Args:
            notebook_id: Notebook UUID
            cell_index: Index of the reference cell (0-based)
            
        Returns:
            List of cells below the given index
        """
        notebook = self._notebooks.get(notebook_id)
        if not notebook or cell_index < 0 or cell_index >= len(notebook.cells):
            return []
        
        return notebook.cells[cell_index + 1:]
    
    def get_cell_index(self, notebook_id: str, cell_id: str) -> int:
        """
        Get the index of a cell in the notebook.
        
        Args:
            notebook_id: Notebook UUID
            cell_id: Cell UUID (as string)
            
        Returns:
            Index of the cell (0-based), or -1 if not found
        """
        notebook = self._notebooks.get(notebook_id)
        if not notebook:
            return -1
        
        # Convert string cell_id to UUID for comparison
        try:
            cell_uuid = UUID(cell_id)
        except ValueError:
            return -1
        
        for i, cell in enumerate(notebook.cells):
            if cell.id == cell_uuid:
                return i
        
        return -1
    
    def _apply_basic_error_fixes(self, code: str, error_message: str, error_type: str) -> Optional[str]:
        """
        EMERGENCY FALLBACK ONLY - when LLM service completely fails.
        
        This should contain ONLY simple, safe transformations.
        All sophisticated error analysis belongs in ErrorAnalyzer.
        
        WARNING: This is a last resort. The primary error handling system is:
        LLMService.suggest_improvements() -> ErrorAnalyzer -> enhanced context
        """
        if not error_message or not code:
            return None
            
        logger.warning(f"🚨 FALLBACK: LLM service failed, applying basic fixes for {error_type}")
        logger.warning("🚨 This indicates ErrorAnalyzer system needs improvement for this error type")
        
        # ONLY simple, safe fixes here - DO NOT duplicate ErrorAnalyzer logic
        
        # Simple file path fix
        if error_type == "FileNotFoundError" and "data/" not in code:
            import re
            # Simple regex to add data/ prefix to common file extensions
            pattern = r"(['\"])([^'\"]*\.(csv|xlsx|json|txt))(['\"])"
            def add_prefix(match):
                quote, filepath, ext, end_quote = match.groups()
                if not filepath.startswith('data/'):
                    return f"{quote}data/{filepath}{end_quote}"
                return match.group(0)
            
            fixed_code = re.sub(pattern, add_prefix, code)
            if fixed_code != code:
                return f"# Emergency fix: Added data/ prefix to file paths\n{fixed_code}"
        
        # Simple import additions
        if error_type in ("ImportError", "ModuleNotFoundError"):
            if "seaborn" in error_message and "import seaborn" not in code:
                return f"# Emergency fix: Added missing import\nimport seaborn as sns\n{code}"
            elif "matplotlib" in error_message and "import matplotlib" not in code:
                return f"# Emergency fix: Added missing import\nimport matplotlib.pyplot as plt\n{code}"
        
        # Simple debugging addition for pandas errors
        if error_type == "KeyError" and "df[" in code:
            return f"""# Emergency fix: Added debugging info
print("Available columns:", df.columns.tolist() if 'df' in locals() and hasattr(df, 'columns') else 'No DataFrame found')

{code}"""
        
        # For pandas length mismatch, just add a helpful comment
        if "Length of values" in error_message and "does not match length of index" in error_message:
            return f"""# Emergency fix: Length mismatch detected
# Consider using safe_assign(df, 'column_name', values) for robust assignment
# This error means you're trying to assign mismatched data lengths

{code}"""
        
        logger.warning("🚨 No basic fixes available - ErrorAnalyzer system needs enhancement")
        return None

    def update_notebook(self, notebook_id: str, request: NotebookUpdateRequest) -> Optional[Notebook]:
        """
        Update notebook metadata.
        
        Args:
            notebook_id: Notebook UUID
            request: Update parameters
            
        Returns:
            Updated notebook or None if not found
        """
        notebook = self._notebooks.get(notebook_id)
        if not notebook:
            return None
        
        # Update fields
        if request.title is not None:
            notebook.title = request.title
        if request.description is not None:
            notebook.description = request.description
        if request.author is not None:
            notebook.author = request.author
        if request.tags is not None:
            notebook.tags = request.tags
        if request.llm_model is not None:
            notebook.llm_model = request.llm_model
        if request.llm_provider is not None:
            notebook.llm_provider = request.llm_provider
        if request.custom_seed is not None:
            notebook.custom_seed = request.custom_seed

        notebook.updated_at = datetime.now()
        self._save_notebook(notebook)
        
        logger.info(f"Updated notebook: {notebook.title}")
        return notebook
    
    def delete_notebook(self, notebook_id: str) -> bool:
        """
        Delete a notebook.
        
        Args:
            notebook_id: Notebook UUID
            
        Returns:
            True if deleted, False if not found
        """
        if notebook_id not in self._notebooks:
            return False
        
        notebook = self._notebooks[notebook_id]
        
        # Remove from cache
        del self._notebooks[notebook_id]
        
        # Remove file
        notebook_file = self.notebooks_dir / f"{notebook_id}.json"
        if notebook_file.exists():
            notebook_file.unlink()
        
        logger.info(f"Deleted notebook: {notebook.title}")
        return True
    
    def create_cell(self, request: CellCreateRequest) -> Optional[Cell]:
        """
        Create a new cell in a notebook.
        
        Args:
            request: Cell creation parameters
            
        Returns:
            Created cell or None if notebook not found
        """
        notebook = self._notebooks.get(str(request.notebook_id))
        if not notebook:
            return None
        
        cell = notebook.add_cell(request.cell_type, request.content)
        self._save_notebook(notebook)
        
        logger.info(f"Created new {request.cell_type} cell in notebook {notebook.title}")
        return cell
    
    def update_cell(self, notebook_id: str, cell_id: str, request: CellUpdateRequest) -> Optional[Cell]:
        """
        Update a cell.
        
        Args:
            notebook_id: Notebook UUID
            cell_id: Cell UUID
            request: Update parameters
            
        Returns:
            Updated cell or None if not found
        """
        notebook = self._notebooks.get(notebook_id)
        if not notebook:
            logger.error(f"Notebook {notebook_id} not found")
            return None
        
        # Debug: Log available cells
        logger.info(f"Looking for cell {cell_id} in notebook {notebook_id}")
        logger.info(f"Available cells: {[str(c.id) for c in notebook.cells]}")
        
        try:
            cell_uuid = uuid.UUID(cell_id)
            cell = notebook.get_cell(cell_uuid)
            if not cell:
                logger.error(f"Cell {cell_id} not found in notebook {notebook_id}")
                return None
        except ValueError as e:
            logger.error(f"Invalid UUID format for cell_id {cell_id}: {e}")
            return None
        
        # Update fields
        if request.prompt is not None:
            cell.prompt = request.prompt
        if request.code is not None:
            cell.code = request.code
        if request.markdown is not None:
            cell.markdown = request.markdown
        if request.show_code is not None:
            cell.show_code = request.show_code
        if request.tags is not None:
            cell.tags = request.tags
        if request.metadata is not None:
            cell.metadata = request.metadata
            
        # Handle cell type changes
        if hasattr(request, 'cell_type') and request.cell_type is not None:
            old_type = cell.cell_type
            cell.cell_type = request.cell_type
            logger.info(f"Changed cell type from {old_type} to {request.cell_type}")
        
        cell.updated_at = datetime.now()
        notebook.updated_at = datetime.now()
        self._save_notebook(notebook)
        
        logger.info(f"Updated cell {cell_id} in notebook {notebook.title}")
        return cell
    
    def delete_cell(self, notebook_id: str, cell_id: str) -> bool:
        """
        Delete a cell from a notebook.
        
        Args:
            notebook_id: Notebook UUID
            cell_id: Cell UUID
            
        Returns:
            True if deleted, False if not found
        """
        notebook = self._notebooks.get(notebook_id)
        if not notebook:
            return False
        
        if notebook.remove_cell(uuid.UUID(cell_id)):
            self._save_notebook(notebook)
            logger.info(f"Deleted cell {cell_id} from notebook {notebook.title}")
            return True
        
        return False
    
    def execute_cell(self, request: CellExecuteRequest) -> Optional[tuple[Cell, ExecutionResult]]:
        """
        Execute a cell (generate code from prompt if needed and run it).
        
        Args:
            request: Execution request parameters
            
        Returns:
            Execution result or None if cell not found
        """
        print(f"📋 NOTEBOOK SERVICE: execute_cell called for {request.cell_id}")
        print(f"📋 NOTEBOOK SERVICE: force_regenerate = {request.force_regenerate}")
        logger.info(f"📋 NOTEBOOK SERVICE: execute_cell called for {request.cell_id}")
        logger.info(f"📋 NOTEBOOK SERVICE: force_regenerate = {request.force_regenerate}")
        # Find the cell
        cell = None
        notebook = None
        
        for nb in self._notebooks.values():
            found_cell = nb.get_cell(request.cell_id)
            if found_cell:
                cell = found_cell
                notebook = nb
                break
        
        if not cell or not notebook:
            logger.error(f"Cell {request.cell_id} not found")
            return None
        
        try:
            # Mark cell as executing
            cell.is_executing = True

            # Clear previous execution traces - only keep traces from current execution
            cell.llm_traces = []
            logger.info(f"🗑️ Cleared previous LLM traces for cell {cell.id}")

            # Handle direct code execution
            if request.code:
                cell.code = request.code
                cell.updated_at = datetime.now()
            elif request.prompt:
                cell.prompt = request.prompt
                cell.updated_at = datetime.now()
            
            # Always build context for LLM (needed for both code generation and methodology)
            try:
                context = self._build_execution_context(notebook, cell)
                logger.info(f"Built context with {len(context)} items")
            except Exception as context_error:
                logger.warning(f"Context building failed: {context_error}, using empty context")
                context = {}

            # Generate code if needed
            if not cell.code or request.force_regenerate:
                if cell.cell_type == CellType.PROMPT and cell.prompt:
                    # ===================================================================
                    # PLANNING PHASE - Reason about analysis before generating code
                    # ===================================================================
                    logger.info(f"🧠 PLANNING PHASE: Analyzing request logic for: {cell.prompt[:100]}...")

                    try:
                        # Initialize planner with notebook-specific LLM config
                        planner = AnalysisPlanner(
                            llm_provider=notebook.llm_provider,
                            llm_model=notebook.llm_model
                        )

                        # Plan analysis with full context
                        analysis_plan, reasoning_trace = planner.plan_analysis(
                            user_prompt=cell.prompt,
                            available_data=context,
                            previous_cells=context.get('previous_cells', [])
                        )

                        # Store plan in cell metadata
                        cell.metadata['analysis_plan'] = analysis_plan.to_dict()
                        cell.metadata['reasoning_trace'] = reasoning_trace.model_dump()

                        logger.info(
                            f"✅ Planning complete: method={analysis_plan.suggested_method}, "
                            f"issues={len(analysis_plan.validation_issues)}, "
                            f"confidence={analysis_plan.confidence_level}"
                        )

                        # ADD ANALYSIS PLAN TO CONTEXT for code generation guidance
                        # This ensures the LLM sees the planning results when generating code
                        context['analysis_plan'] = cell.metadata['analysis_plan']
                        logger.info("📋 Added analysis plan to context for code generation")

                        # CHECK FOR CRITICAL ISSUES
                        if analysis_plan.has_critical_issues():
                            critical_issues = analysis_plan.get_critical_issues()
                            logger.warning(
                                f"🚨 CRITICAL ISSUES DETECTED ({len(critical_issues)}): "
                                f"{[issue.message for issue in critical_issues]}"
                            )

                            # Store critical issues for UI display
                            cell.metadata['planning_blocked'] = True
                            cell.metadata['critical_issues'] = [
                                {
                                    'severity': issue.severity.value,
                                    'type': issue.type.value,
                                    'message': issue.message,
                                    'explanation': issue.explanation,
                                    'suggestion': issue.suggestion,
                                    'affected_variables': issue.affected_variables
                                }
                                for issue in critical_issues
                            ]

                            # Create error result
                            error_result = ExecutionResult(
                                status=ExecutionStatus.ERROR,
                                error_type="PlanningCriticalIssue",
                                error_message=f"Planning detected critical logical issues: {critical_issues[0].message}",
                                traceback=analysis_plan.get_summary()
                            )
                            cell.last_result = error_result
                            cell.is_executing = False
                            self._save_notebook(notebook)

                            logger.warning("🚫 Execution blocked due to critical planning issues")
                            return cell, error_result

                    except Exception as planning_error:
                        logger.warning(f"⚠️ Planning phase failed (non-critical): {planning_error}")
                        # Continue with code generation even if planning fails (fail-safe)
                        pass

                    # ===================================================================
                    # CODE GENERATION PHASE
                    # ===================================================================
                    logger.info(f"Generating code for prompt: {cell.prompt[:100]}...")
                    
                    try:
                        # Update LLM service configuration
                        if notebook.llm_provider != self.llm_service.provider or notebook.llm_model != self.llm_service.model:
                            logger.info(f"Updating LLM service: {notebook.llm_provider}/{notebook.llm_model}")
                            self.llm_service = LLMService(notebook.llm_provider, notebook.llm_model)
                        
                        # Generate code with full tracing
                        logger.info("Calling LLM service for code generation...")
                        generated_code, generation_time, trace_id, full_trace = self.llm_service.generate_code_from_prompt(
                            cell.prompt,
                            context,
                            step_type='code_generation',
                            attempt_number=1
                        )
                        cell.code = generated_code
                        cell.last_generation_time_ms = generation_time
                        cell.last_execution_timestamp = datetime.now()
                        cell.updated_at = datetime.now()

                        # Store trace IDs for backward compatibility
                        if 'trace_ids' not in cell.metadata:
                            cell.metadata['trace_ids'] = []
                        if trace_id:
                            cell.metadata['trace_ids'].append(trace_id)

                        # Store full trace for persistent observability
                        if full_trace:
                            cell.llm_traces.append(full_trace)
                            logger.info(f"✅ Stored full trace for code generation {trace_id}")

                        logger.info(f"Successfully generated {len(generated_code)} characters of code" +
                                  (f" in {generation_time}ms" if generation_time else '') +
                                  (f", trace_id: {trace_id}" if trace_id else ""))

                        # Update notebook's last context tokens from the generation
                        try:
                            # Get the most recent cell usage which should have the input tokens
                            cell_usage = self.llm_service.token_tracker.get_cell_usage(str(cell.id))
                            if cell_usage and cell_usage.get('input_tokens', 0) > 0:
                                notebook.last_context_tokens = cell_usage['input_tokens']
                                logger.info(f"📊 Updated notebook last_context_tokens: {cell_usage['input_tokens']}")
                        except Exception as token_err:
                            logger.warning(f"Could not update last_context_tokens: {token_err}")

                    except Exception as e:
                        logger.error(f"❌ LLM code generation failed for cell {cell.id}")
                        logger.error(f"   Prompt: {cell.prompt[:100]}...")
                        logger.error(f"   Error type: {type(e).__name__}")
                        logger.error(f"   Error message: {str(e)}")
                        import traceback
                        logger.error(f"   Traceback:\n{traceback.format_exc()}")
                        logger.error(f"   Check: API keys, rate limits, network connectivity, or LLM service availability")

                        # DO NOT use fallback code - let the error surface properly
                        # The retry mechanism will attempt to fix real errors
                        # If LLM is completely unavailable, user needs to know
                        cell.code = ""  # Empty code, will show error to user
                        raise  # Re-raise the exception so it's properly handled
            
            # Execute code if available
            if cell.code and cell.cell_type in (CellType.PROMPT, CellType.CODE, CellType.METHODOLOGY):
                # Set up notebook-specific context for execution
                result = self.execution_service.execute_code(cell.code, str(cell.id), str(notebook.id))
                cell.execution_count += 1
                
                # Auto-retry logic: if execution failed and we have a prompt or generated code, try to fix it with LLM
                max_retries = 5
                should_auto_retry = (
                    result.status == ExecutionStatus.ERROR and 
                    (cell.cell_type == CellType.PROMPT or 
                     (cell.cell_type in (CellType.CODE, CellType.METHODOLOGY) and cell.prompt)) and
                    cell.prompt and 
                    cell.retry_count < max_retries and  # Allow up to 3 retries
                    not request.force_regenerate
                )
                
                # Auto-retry loop with up to max_retries attempts
                while should_auto_retry:
                    # Set retry status
                    cell.is_retrying = True
                    cell.retry_count += 1
                    
                    logger.info(f"🔄 EXECUTION FAILED - Attempting auto-retry #{cell.retry_count}/{max_retries} with LLM for cell {cell.id}")
                    logger.info(f"🔄 Error: {result.error_message}")
                    print(f"🔄 AUTO-RETRY #{cell.retry_count}/{max_retries}: Attempting to fix execution error for cell {cell.id}")
                    
                    try:
                        # Build context for LLM including the error
                        context = self._build_execution_context(notebook, cell)
                        
                        # Create error context for the LLM
                        error_context = {
                            **context,
                            'previous_code': cell.code,
                            'error_message': result.error_message,
                            'error_type': result.error_type,
                            'traceback': result.traceback,
                            'stderr': result.stderr
                        }
                        
                        # Ask LLM to fix the code with enhanced error analysis from ErrorAnalyzer
                        logger.info(f"🔄 Asking LLM to fix the failed code (attempt #{cell.retry_count})...")
                        print(f"🔄 AUTO-RETRY #{cell.retry_count}: Analyzing error and generating corrected code...")

                        # Use suggest_improvements with enhanced error context and tracing
                        # This will automatically use ErrorAnalyzer to provide domain-specific guidance
                        try:
                            # Build full context for retry (includes available variables, DataFrames, previous cells)
                            retry_context = self._build_execution_context(notebook, cell)

                            fixed_code, trace_id, full_trace = self.llm_service.suggest_improvements(
                                prompt=cell.prompt,
                                code=cell.code,
                                error_message=result.error_message,
                                error_type=result.error_type,
                                traceback=result.traceback,
                                step_type='code_fix',
                                attempt_number=cell.retry_count + 1,
                                context=retry_context  # Pass full context including available variables
                            )

                            # Store trace_id for backward compatibility
                            if trace_id:
                                if 'trace_ids' not in cell.metadata:
                                    cell.metadata['trace_ids'] = []
                                cell.metadata['trace_ids'].append(trace_id)
                                logger.info(f"📝 Stored retry trace_id: {trace_id}")

                            # Store full trace for persistent observability
                            if full_trace:
                                cell.llm_traces.append(full_trace)
                                logger.info(f"✅ Stored full trace for code fix attempt #{cell.retry_count + 1}")

                        except Exception as llm_error:
                            logger.error(f"🔄 LLM service failed during retry #{cell.retry_count}: {llm_error}")
                            print(f"🔄 LLM ERROR: LLM service failed on retry #{cell.retry_count}: {llm_error}")
                            # Try basic error-specific fixes when LLM fails
                            fixed_code = self._apply_basic_error_fixes(cell.code, result.error_message, result.error_type)
                        
                        if fixed_code and fixed_code != cell.code:
                            logger.info(f"🔄 LLM provided fixed code ({len(fixed_code)} chars)")
                            print(f"🔄 UPDATED: LLM provided corrected code for retry #{cell.retry_count}")
                            cell.code = fixed_code
                            cell.updated_at = datetime.now()
                            
                            # Try executing the fixed code
                            logger.info("🔄 Executing fixed code...")
                            print(f"🔄 EXECUTING: Testing corrected code...")
                            retry_result = self.execution_service.execute_code(cell.code, str(cell.id), str(notebook.id))
                            
                            if retry_result.status == ExecutionStatus.SUCCESS:
                                logger.info(f"🔄 ✅ Auto-retry #{cell.retry_count} successful! Fixed code executed successfully")
                                print(f"🔄 SUCCESS: Auto-retry #{cell.retry_count} fixed the error for cell {cell.id}")
                                result = retry_result
                                cell.execution_count += 1
                                cell.is_retrying = False  # Clear retry status on success
                                break  # Exit retry loop on success
                            else:
                                logger.warning(f"🔄 ❌ Auto-retry #{cell.retry_count} failed: {retry_result.error_message}")
                                print(f"🔄 RETRY #{cell.retry_count} FAILED: {retry_result.error_message}")
                                result = retry_result  # Update result for next iteration
                        else:
                            logger.warning(f"🔄 LLM did not provide different code for retry #{cell.retry_count}")
                            print(f"🔄 NO CHANGE: LLM provided same code on retry #{cell.retry_count}")
                            # When LLM provides same code, we should still continue retrying
                            # The error persists, so we keep the current result
                        
                        # Check if we should continue retrying
                        if cell.retry_count >= max_retries:
                            logger.warning(f"🔄 All {max_retries} retries exhausted for cell {cell.id}")
                            print(f"🔄 EXHAUSTED: All {max_retries} auto-retry attempts failed for cell {cell.id}")
                            cell.is_retrying = False  # Clear retry status
                            break
                        
                        # Update should_auto_retry for next iteration
                        should_auto_retry = (
                            result.status == ExecutionStatus.ERROR and 
                            cell.retry_count < max_retries
                        )
                            
                    except Exception as retry_error:
                        logger.error(f"🔄 Auto-retry #{cell.retry_count} mechanism failed: {retry_error}")
                        print(f"🔄 ERROR: Auto-retry #{cell.retry_count} mechanism failed: {retry_error}")
                        
                        if cell.retry_count >= max_retries:
                            cell.is_retrying = False  # Clear retry status on exception
                            break
                        
                        # Continue to next retry attempt
                        should_auto_retry = (cell.retry_count < max_retries)
            else:
                # For markdown cells or empty cells
                result = ExecutionResult(status=ExecutionStatus.SUCCESS)
            
            # Update cell with result
            cell.last_result = result
            cell.is_executing = False
            notebook.updated_at = datetime.now()

            # ===================================================================
            # CRITIQUE PHASE - Evaluate completed analysis
            # ===================================================================
            if result.status == ExecutionStatus.SUCCESS and cell.prompt and cell.code:
                logger.info(f"🔍 CRITIQUE PHASE: Evaluating analysis quality...")

                try:
                    # Initialize critic with notebook-specific LLM config
                    critic = AnalysisCritic(
                        llm_provider=notebook.llm_provider,
                        llm_model=notebook.llm_model
                    )

                    # Prepare execution result data
                    execution_data = {
                        'stdout': result.stdout,
                        'stderr': result.stderr,
                        'tables': result.tables,
                        'plots': result.plots,
                        'interactive_plots': result.interactive_plots
                    }

                    # Get analysis plan if it exists
                    analysis_plan = None
                    if 'analysis_plan' in cell.metadata:
                        try:
                            analysis_plan = AnalysisPlan.from_dict(cell.metadata['analysis_plan'])
                        except Exception as e:
                            logger.warning(f"Could not load analysis plan from metadata: {e}")

                    # Critique the analysis
                    critique, critique_trace = critic.critique_analysis(
                        user_intent=cell.prompt,
                        code=cell.code,
                        execution_result=execution_data,
                        analysis_plan=analysis_plan,
                        context=context
                    )

                    # Store critique in cell metadata
                    cell.metadata['critique'] = critique.to_dict()
                    cell.metadata['critique_trace'] = critique_trace.model_dump()

                    logger.info(
                        f"✅ Critique complete: quality={critique.overall_quality}, "
                        f"confidence={critique.confidence_in_results}, "
                        f"findings={len(critique.findings)}"
                    )

                    # If critique found critical issues, log them
                    if critique.has_critical_findings():
                        critical_findings = critique.get_critical_findings()
                        logger.warning(
                            f"🚨 CRITICAL FINDINGS IN RESULTS ({len(critical_findings)}): "
                            f"{[f.title for f in critical_findings]}"
                        )

                except Exception as critique_error:
                    logger.warning(f"⚠️ Critique phase failed (non-critical): {critique_error}")
                    # Don't let critique failure break execution (fail-safe)
                    pass

            # Generate scientific explanation for successful prompt cells
            print(f"🔬 ALWAYS CHECKING scientific explanation conditions:")
            print(f"   - Result status: {result.status} (SUCCESS={ExecutionStatus.SUCCESS})")
            print(f"   - Cell type: {cell.cell_type} (PROMPT={CellType.PROMPT}, CODE={CellType.CODE})")
            print(f"   - Has prompt: {bool(cell.prompt)} ('{cell.prompt[:50] if cell.prompt else 'None'}...')")
            print(f"   - Has code: {bool(cell.code)} ('{cell.code[:50] if cell.code else 'None'}...')")
            logger.info(f"🔬 ALWAYS CHECKING scientific explanation conditions:")
            logger.info(f"   - Result status: {result.status} (SUCCESS={ExecutionStatus.SUCCESS})")
            logger.info(f"   - Cell type: {cell.cell_type} (PROMPT={CellType.PROMPT}, CODE={CellType.CODE})")
            logger.info(f"   - Has prompt: {bool(cell.prompt)} ('{cell.prompt[:50] if cell.prompt else 'None'}...')")
            logger.info(f"   - Has code: {bool(cell.code)} ('{cell.code[:50] if cell.code else 'None'}...')")
            
            # Generate scientific explanation for any successful execution with code and prompt
            # This includes both PROMPT cells and CODE cells that have been manually edited
            if (result.status == ExecutionStatus.SUCCESS and 
                cell.prompt and cell.code and
                cell.cell_type in (CellType.PROMPT, CellType.CODE)):
                
                print("🔬 GENERATING SCIENTIFIC EXPLANATION SYNCHRONOUSLY...")
                logger.info("🔬 GENERATING SCIENTIFIC EXPLANATION SYNCHRONOUSLY...")
                
                # Retry loop for methodology generation (up to 3 attempts)
                max_methodology_retries = 3
                methodology_attempt = 0
                explanation = ""

                while methodology_attempt < max_methodology_retries and not explanation:
                    methodology_attempt += 1

                    try:
                        # Prepare execution result data for LLM
                        execution_data = {
                            'status': 'success',
                            'stdout': result.stdout,
                            'plots': result.plots,
                            'tables': result.tables,
                            'interactive_plots': result.interactive_plots
                        }

                        print(f"🔬 Methodology generation attempt #{methodology_attempt}...")
                        logger.info(f"🔬 Methodology generation attempt #{methodology_attempt}...")

                        # Collect previous methodologies for narrative continuity
                        previous_methodologies = []
                        try:
                            current_cell_index = None
                            for i, nb_cell in enumerate(notebook.cells):
                                if nb_cell.id == cell.id:
                                    current_cell_index = i
                                    break

                            if current_cell_index is not None and current_cell_index > 0:
                                # Get last 2-3 cells' methodologies (or fewer if less than 3 previous cells)
                                start_index = max(0, current_cell_index - 3)
                                for prev_cell in notebook.cells[start_index:current_cell_index]:
                                    if prev_cell.scientific_explanation:
                                        previous_methodologies.append(prev_cell.scientific_explanation)
                                logger.info(f"📚 Collected {len(previous_methodologies)} previous methodologies for context")
                        except Exception as prev_error:
                            logger.warning(f"Could not collect previous methodologies: {prev_error}")
                            previous_methodologies = []

                        explanation, explanation_gen_time, trace_id, full_trace = self.llm_service.generate_scientific_explanation(
                            cell.prompt,
                            cell.code,
                            execution_data,
                            context,  # Pass context for seed consistency and tracing
                            step_type='methodology_generation',
                            attempt_number=methodology_attempt,
                            previous_methodologies=previous_methodologies  # Pass previous methodologies for continuity
                        )

                        print(f"🔬 LLM returned explanation: {len(explanation)} chars" +
                              (f" in {explanation_gen_time}ms" if explanation_gen_time else ""))
                        print(f"🔬 Explanation content: {explanation[:200]}...")

                        # Store trace_id for backward compatibility
                        if trace_id:
                            if 'trace_ids' not in cell.metadata:
                                cell.metadata['trace_ids'] = []
                            cell.metadata['trace_ids'].append(trace_id)
                            logger.info(f"📝 Stored methodology trace_id: {trace_id}")

                        # Store full trace for persistent observability (even if failed)
                        if full_trace:
                            cell.llm_traces.append(full_trace)
                            logger.info(f"✅ Stored full trace for methodology attempt #{methodology_attempt}")

                        # Check if we got a valid explanation
                        if explanation and len(explanation.strip()) > 10:
                            # Valid explanation - update cell
                            cell.scientific_explanation = explanation
                            print(f"🔬 ✅ Cell updated with explanation: {len(cell.scientific_explanation)} chars")

                            # Enhance methodology with critique limitations if available
                            if 'critique' in cell.metadata:
                                try:
                                    critique_data = cell.metadata['critique']
                                    if critique_data.get('identified_limitations'):
                                        limitations_section = "\n\n### Limitations and Considerations\n\n"
                                        for limitation in critique_data['identified_limitations']:
                                            limitations_section += f"- {limitation}\n"
                                        cell.scientific_explanation += limitations_section
                                        logger.info("📝 Enhanced methodology with critique limitations")
                                except Exception as e:
                                    logger.warning(f"Could not enhance methodology with critique: {e}")

                            # Update notebook's last context tokens from methodology generation
                            try:
                                cell_usage = self.llm_service.token_tracker.get_cell_usage(str(cell.id))
                                if cell_usage and cell_usage.get('input_tokens', 0) > 0:
                                    notebook.last_context_tokens = cell_usage['input_tokens']
                                    logger.info(f"📊 Updated notebook last_context_tokens from methodology: {cell_usage['input_tokens']}")
                            except Exception as token_err:
                                logger.warning(f"Could not update last_context_tokens from methodology: {token_err}")
                            break  # Success - exit retry loop
                        else:
                            # Empty or invalid explanation
                            logger.warning(f"🔬 ⚠️ Methodology attempt #{methodology_attempt} returned empty/invalid explanation")
                            explanation = ""  # Reset for retry

                    except Exception as e:
                        print(f"🔬 ❌ ERROR on methodology attempt #{methodology_attempt}: {e}")
                        import traceback
                        print(f"🔬 Traceback: {traceback.format_exc()}")
                        logger.error(f"Error on methodology attempt #{methodology_attempt}: {e}")
                        explanation = ""  # Reset for retry

                # If all retries failed, set empty string
                if not explanation:
                    logger.error(f"🔬 ❌ All {max_methodology_retries} methodology attempts failed")
                    cell.scientific_explanation = ""
            else:
                logger.info("🔬 Skipping scientific explanation generation (conditions not met)")
            
            # Update cell state management
            if result.status == ExecutionStatus.SUCCESS:
                # Mark this cell as fresh
                cell.cell_state = CellState.FRESH

                # Mark downstream cells as stale
                try:
                    cell_index = self.get_cell_index(str(notebook.id), str(cell.id))
                    if cell_index >= 0:
                        self.mark_cells_as_stale(str(notebook.id), cell_index)
                        logger.info(f"Marked cells below index {cell_index} as stale")
                except Exception as e:
                    logger.warning(f"Failed to mark downstream cells as stale: {e}")

            # Extract semantic information from cell (non-blocking)
            try:
                logger.info(f"🔍 Extracting semantic information from cell {cell.id}...")
                cell_semantics = self.semantic_service.extract_cell_semantics(cell, notebook)
                cell.metadata['semantics'] = cell_semantics.to_jsonld()
                logger.info(f"✅ Extracted {len(cell_semantics.triples)} triples, " +
                           f"{len(cell_semantics.libraries_used)} libraries, " +
                           f"{len(cell_semantics.methods_used)} methods")
            except Exception as e:
                logger.warning(f"⚠️ Semantic extraction failed (non-critical): {e}")
                # Don't let semantic extraction errors break execution
                pass

            # Run auto-review if enabled (non-blocking)
            try:
                review_settings = notebook.metadata.get('review_settings', {})
                if review_settings.get('auto_review_enabled', False):
                    logger.info(f"📋 Auto-review enabled - reviewing cell {cell.id}...")
                    cell_review = self.review_service.review_cell(cell, notebook)
                    cell.metadata['review'] = cell_review.dict()
                    logger.info(f"✅ Auto-review complete: {len(cell_review.findings)} findings")
            except Exception as e:
                logger.warning(f"⚠️ Auto-review failed (non-critical): {e}")
                # Don't let auto-review errors break execution
                pass

            # Save notebook
            self._save_notebook(notebook)
            
            logger.info(f"Executed cell {cell.id} with status {result.status}")
            return cell, result
            
        except Exception as e:
            # Handle execution errors
            error_result = ExecutionResult(
                status=ExecutionStatus.ERROR,
                error_type=type(e).__name__,
                error_message=str(e),
                traceback=str(e)
            )
            
            cell.last_result = error_result
            cell.is_executing = False
            self._save_notebook(notebook)
            
            logger.error(f"Failed to execute cell {cell.id}: {e}")
            return cell, error_result

    def _save_notebook(self, notebook: Notebook):
        """
        Save a notebook to disk using atomic write pattern.
        
        Args:
            notebook: Notebook to save
        """
        try:
            notebook_file = self.notebooks_dir / f"{notebook.id}.json"
            temp_file = self.notebooks_dir / f"{notebook.id}.json.tmp"
            
            # Write to temporary file first
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(
                    notebook.model_dump(),
                    f,
                    indent=2,
                    ensure_ascii=False,
                    default=str  # Handle UUID and datetime serialization
                )
            
            # Atomic rename - this is the critical part that prevents corruption
            temp_file.rename(notebook_file)
            
        except Exception as e:
            logger.error(f"Failed to save notebook {notebook.title}: {e}")
            # Clean up temporary file if it exists
            temp_file = self.notebooks_dir / f"{notebook.id}.json.tmp"
            if temp_file.exists():
                temp_file.unlink()
    
    def export_notebook(self, notebook_id: str, format: str = "json") -> Optional[str]:
        """
        Export a notebook in various formats.

        Args:
            notebook_id: Notebook UUID
            format: Export format (json, html, markdown, jsonld, semantic)

        Returns:
            Exported content or None if notebook not found
        """
        notebook = self._notebooks.get(notebook_id)
        if not notebook:
            return None

        if format == "json":
            return json.dumps(self._create_clean_export_structure(notebook), indent=2, default=str)
        elif format == "jsonld" or format == "semantic" or format == "analysis":
            # All semantic formats now use the same LLM-based analysis graph
            return self._export_analysis_graph(notebook)
        elif format == "profile":
            return self._export_profile_graph(notebook)
        elif format == "markdown":
            return self._export_to_markdown(notebook)
        elif format == "html":
            return self._export_to_html(notebook)
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def _create_clean_export_structure(self, notebook: Notebook) -> Dict[str, Any]:
        """
        Create a clean, optimized export structure for JSON export.
        
        This structure focuses on the essential content and metadata,
        removing internal application state and execution details.
        
        Args:
            notebook: Notebook to export
            
        Returns:
            Clean dictionary structure for export
        """
        # Core notebook metadata
        export_data = {
            "digital_article": {
                "version": "0.0.3",
                "export_timestamp": datetime.now().isoformat()
            },
            "metadata": {
                "id": str(notebook.id),
                "title": notebook.title,
                "description": notebook.description,
                "author": notebook.author,
                "created_at": notebook.created_at.isoformat(),
                "updated_at": notebook.updated_at.isoformat(),
                "version": notebook.version,
                "tags": notebook.tags,
                "abstract": notebook.abstract,
                "abstract_generated_at": notebook.abstract_generated_at.isoformat() if notebook.abstract_generated_at else None
            },
            "configuration": {
                "llm_provider": notebook.llm_provider,
                "llm_model": notebook.llm_model
            },
            "cells": []
        }
        
        # Process cells with clean structure
        for cell in notebook.cells:
            cell_data = {
                "id": str(cell.id),
                "type": cell.cell_type.value,
                "created_at": cell.created_at.isoformat(),
                "updated_at": cell.updated_at.isoformat(),
                "content": {}
            }
            
            # Core content based on cell type
            if cell.cell_type == CellType.PROMPT:
                cell_data["content"] = {
                    "prompt": cell.prompt,
                    "code": cell.code,
                    "methodology": cell.scientific_explanation
                }
            elif cell.cell_type == CellType.CODE:
                cell_data["content"] = {
                    "code": cell.code,
                    "methodology": cell.scientific_explanation if cell.scientific_explanation else None
                }
            elif cell.cell_type == CellType.MARKDOWN:
                cell_data["content"] = {
                    "markdown": cell.markdown
                }
            elif cell.cell_type == CellType.METHODOLOGY:
                cell_data["content"] = {
                    "prompt": cell.prompt,
                    "code": cell.code,
                    "methodology": cell.scientific_explanation
                }
            
            # Execution summary (without heavy data)
            if cell.last_result and cell.last_result.status == ExecutionStatus.SUCCESS:
                cell_data["execution"] = {
                    "status": "success",
                    "execution_count": cell.execution_count,
                    "last_executed": cell.last_result.timestamp.isoformat(),
                    "execution_time": cell.last_result.execution_time,
                    "has_output": bool(cell.last_result.stdout),
                    "has_plots": len(cell.last_result.plots) > 0,
                    "has_tables": len(cell.last_result.tables) > 0,
                    "has_interactive_plots": len(cell.last_result.interactive_plots) > 0
                }
            elif cell.last_result and cell.last_result.status == ExecutionStatus.ERROR:
                cell_data["execution"] = {
                    "status": "error",
                    "execution_count": cell.execution_count,
                    "last_executed": cell.last_result.timestamp.isoformat(),
                    "error_type": cell.last_result.error_type,
                    "error_message": cell.last_result.error_message
                }
            else:
                cell_data["execution"] = {
                    "status": "not_executed",
                    "execution_count": cell.execution_count
                }
            
            # Optional metadata
            if cell.tags:
                cell_data["tags"] = cell.tags
            if cell.metadata:
                cell_data["metadata"] = cell.metadata
                
            export_data["cells"].append(cell_data)
        
        return export_data
    
    def _export_to_markdown(self, notebook: Notebook) -> str:
        """Export notebook to Markdown format."""
        md_lines = [
            f"# {notebook.title}",
            "",
            notebook.description,
            "",
            f"**Author:** {notebook.author}",
            f"**Created:** {notebook.created_at.isoformat()}",
            f"**Updated:** {notebook.updated_at.isoformat()}",
            ""
        ]
        
        for i, cell in enumerate(notebook.cells, 1):
            md_lines.append(f"## Cell {i}")
            
            if cell.cell_type == CellType.PROMPT:
                md_lines.extend([
                    "**Prompt:**",
                    cell.prompt,
                    "",
                    "**Generated Code:**",
                    f"```python",
                    cell.code,
                    "```",
                    ""
                ])
            elif cell.cell_type == CellType.CODE:
                md_lines.extend([
                    "**Code:**",
                    f"```python",
                    cell.code,
                    "```",
                    ""
                ])
            elif cell.cell_type == CellType.MARKDOWN:
                md_lines.extend([cell.markdown, ""])
            
            # Add execution results if available
            if cell.last_result and cell.last_result.status == ExecutionStatus.SUCCESS:
                if cell.last_result.stdout:
                    md_lines.extend([
                        "**Output:**",
                        "```",
                        cell.last_result.stdout,
                        "```",
                        ""
                    ])
        
        return "\n".join(md_lines)

    def _export_analysis_graph(self, notebook: Notebook) -> str:
        """
        Export analysis flow knowledge graph.

        Focuses on workflow and process:
        - Cell execution sequence
        - Variable definitions and reuse
        - Data transformations
        - Method application order
        """
        try:
            analysis_graph = self.analysis_graph_service.extract_analysis_graph(notebook)

            # Save notebook to persist cached graph
            self._save_notebook(notebook)

            return json.dumps(analysis_graph, indent=2, default=str, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error exporting analysis graph: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            # Fallback
            return json.dumps({
                "@context": {},
                "@graph": [],
                "error": f"Analysis graph extraction failed: {str(e)}"
            }, indent=2)

    def _export_profile_graph(self, notebook: Notebook) -> str:
        """
        Export profile knowledge graph.

        Focuses on data and user:
        - Data types and standards
        - Analysis categories
        - User skills (technical and domain)
        - Research interests
        """
        try:
            profile_graph = self.profile_graph_service.extract_profile_graph(notebook)

            # Save notebook to persist cached graph
            self._save_notebook(notebook)

            return json.dumps(profile_graph, indent=2, default=str, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error exporting profile graph: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            # Fallback
            return json.dumps({
                "@context": {},
                "@graph": [],
                "error": f"Profile graph extraction failed: {str(e)}"
            }, indent=2)

    def _export_to_html(self, notebook: Notebook) -> str:
        """Export notebook to HTML format."""
        # This would be implemented with a proper HTML template
        # For now, return basic HTML structure
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{notebook.title}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                .cell {{ margin: 20px 0; padding: 15px; border: 1px solid #ddd; }}
                .prompt {{ background-color: #f8f9fa; }}
                .code {{ background-color: #f1f3f4; font-family: monospace; }}
                .output {{ background-color: #e8f5e8; }}
            </style>
        </head>
        <body>
            <h1>{notebook.title}</h1>
            <p>{notebook.description}</p>
            <p><strong>Author:</strong> {notebook.author}</p>
        """
        
        for i, cell in enumerate(notebook.cells, 1):
            if cell.cell_type == CellType.PROMPT:
                html += f"""
                <div class="cell">
                    <h3>Cell {i} - Prompt</h3>
                    <div class="prompt">{cell.prompt}</div>
                    <div class="code"><pre>{cell.code}</pre></div>
                </div>
                """
        
        html += "</body></html>"
        return html
    
    def export_notebook_pdf(self, notebook_id: str, include_code: bool = False) -> Optional[bytes]:
        """
        Export a notebook to PDF format as a complete scientific article.
        
        This method:
        1. Regenerates the abstract to ensure it's current
        2. Uses LLM to generate a complete article plan and content
        3. Creates a human-readable scientific article with proper structure
        4. Includes empirical evidence and acknowledgments
        
        Args:
            notebook_id: Notebook UUID
            include_code: Whether to include generated code in the PDF
            
        Returns:
            PDF content as bytes or None if notebook not found
        """
        notebook = self._notebooks.get(notebook_id)
        if not notebook:
            return None
        
        try:
            logger.info(f"Exporting notebook {notebook_id} to LLM-generated scientific article PDF (include_code={include_code})")
            
            # Step 1: Regenerate abstract to ensure it's current
            logger.info("🎯 Step 1: Regenerating abstract for PDF export...")
            try:
                self.generate_abstract(notebook_id)
                # Reload notebook to get updated abstract
                notebook = self._notebooks.get(notebook_id)
            except Exception as e:
                logger.warning(f"Failed to regenerate abstract for PDF: {e}")
                # Continue with existing abstract or empty if none
            
            # Step 2: Generate complete scientific article using LLM
            logger.info("🎯 Step 2: Generating complete scientific article...")
            scientific_article = self.generate_scientific_article(notebook_id)
            
            # Step 3: Generate PDF from the LLM-generated article
            logger.info("🎯 Step 3: Creating PDF from scientific article...")
            pdf_bytes = self.pdf_service.generate_scientific_article_pdf(scientific_article, notebook, include_code)
            
            logger.info(f"🎯 LLM-driven scientific PDF export successful: {len(pdf_bytes)} bytes")
            return pdf_bytes
        except Exception as e:
            logger.error(f"Failed to export notebook {notebook_id} to PDF: {e}")
            raise
    
    def set_notebook_custom_seed(self, notebook_id: str, seed: int) -> bool:
        """
        Set a custom seed for notebook reproducibility.
        
        This seed will be used for both LLM generation and execution environment
        to ensure complete reproducibility.
        
        Args:
            notebook_id: Notebook identifier
            seed: Custom seed value (0-2147483647)
            
        Returns:
            True if successful, False if notebook not found
        """
        notebook = self._notebooks.get(notebook_id)
        if not notebook:
            return False
        
        # Store custom seed in notebook metadata
        if not hasattr(notebook, 'custom_seed'):
            notebook.custom_seed = None
        notebook.custom_seed = seed
        
        # Update both LLM and execution services to use this seed
        try:
            # Update LLM service seed (will be used in next generation)
            if not hasattr(self.llm_service, '_custom_seeds'):
                self.llm_service._custom_seeds = {}
            self.llm_service._custom_seeds[notebook_id] = seed
            
            # Update execution service seed (will be used in next execution)
            self.execution_service.notebook_execution_seed = None  # Reset to force re-initialization
            if not hasattr(self.execution_service, '_custom_seeds'):
                self.execution_service._custom_seeds = {}
            self.execution_service._custom_seeds[notebook_id] = seed
            
            logger.info(f"🎲 Set custom seed {seed} for notebook {notebook_id}")
            
            # Save notebook with new seed
            self._save_notebook(notebook)
            return True
            
        except Exception as e:
            logger.error(f"Failed to set custom seed: {e}")
            return False

    def generate_abstract(self, notebook_id: str) -> str:
        """
        Generate a scientific abstract for the entire digital article.
        
        Args:
            notebook_id: ID of the notebook to generate abstract for
            
        Returns:
            Generated abstract as a string
            
        Raises:
            ValueError: If notebook not found
            Exception: If abstract generation fails
        """
        notebook = self._notebooks.get(notebook_id)
        if not notebook:
            raise ValueError(f"Notebook {notebook_id} not found")
        
        try:
            # Convert notebook to dictionary format for LLM service
            notebook_data = {
                'id': str(notebook.id),
                'title': notebook.title,
                'description': notebook.description,
                'author': notebook.author,
                'cells': []
            }
            
            # Convert cells to dictionary format
            for cell in notebook.cells:
                cell_data = {
                    'prompt': cell.prompt,
                    'code': cell.code,
                    'scientific_explanation': cell.scientific_explanation,
                    'last_result': None
                }
                
                # Include execution results if available
                if cell.last_result:
                    cell_data['last_result'] = {
                        'output': cell.last_result.stdout,  # Use stdout instead of output
                        'status': cell.last_result.status.value if cell.last_result.status else None,
                        'execution_time': cell.last_result.execution_time
                    }
                
                notebook_data['cells'].append(cell_data)
            
            # Generate abstract using LLM service
            abstract = self.llm_service.generate_abstract(notebook_data)
            
            # Save abstract to notebook
            notebook.abstract = abstract
            notebook.abstract_generated_at = datetime.now()
            self._save_notebook(notebook)
            
            logger.info(f"🎯 Generated and saved abstract for notebook {notebook_id}: {len(abstract)} characters")
            return abstract
            
        except Exception as e:
            logger.error(f"Failed to generate abstract for notebook {notebook_id}: {e}")
            raise

    def generate_scientific_article(self, notebook_id: str) -> Dict[str, Any]:
        """
        Generate a complete scientific article with LLM-driven content.
        
        Args:
            notebook_id: ID of the notebook to generate article for
            
        Returns:
            Dictionary with article structure and content
            
        Raises:
            ValueError: If notebook not found
            Exception: If article generation fails
        """
        notebook = self._notebooks.get(notebook_id)
        if not notebook:
            raise ValueError(f"Notebook {notebook_id} not found")
        
        try:
            logger.info(f"🎯 Generating complete scientific article for notebook {notebook_id}")
            
            # Convert notebook to dictionary format for LLM service
            notebook_data = {
                'id': str(notebook.id),
                'title': notebook.title,
                'description': notebook.description,
                'author': notebook.author,
                'abstract': notebook.abstract,
                'cells': []
            }
            
            # Convert cells to dictionary format
            for cell in notebook.cells:
                cell_data = {
                    'prompt': cell.prompt,
                    'code': cell.code,
                    'scientific_explanation': cell.scientific_explanation,
                    'last_result': None
                }
                
                # Include execution results if available
                if cell.last_result:
                    cell_data['last_result'] = {
                        'output': cell.last_result.stdout,
                        'status': cell.last_result.status.value if cell.last_result.status else None,
                        'execution_time': cell.last_result.execution_time,
                        'plots': cell.last_result.plots if cell.last_result.plots else []
                    }
                
                notebook_data['cells'].append(cell_data)
            
            # Step 1: Generate article plan
            logger.info("🎯 Step 1: Generating article plan...")
            article_plan = self.llm_service.generate_article_plan(notebook_data)
            
            # Step 2: Generate each section based on the plan
            logger.info("🎯 Step 2: Generating article sections...")
            sections = {}
            section_names = ['introduction', 'methodology', 'results', 'discussion', 'conclusions']
            
            for section_name in section_names:
                if section_name in article_plan.get('sections', {}):
                    logger.info(f"🎯 Generating {section_name} section...")
                    section_plan = article_plan['sections'][section_name]
                    section_content = self.llm_service.generate_article_section(
                        section_name, section_plan, notebook_data, article_plan
                    )
                    sections[section_name] = section_content
                else:
                    logger.warning(f"🎯 No plan found for {section_name} section, skipping...")
            
            # Step 3: Compile complete article
            complete_article = {
                'title': article_plan.get('title', notebook.title),
                'abstract': notebook.abstract,
                'sections': sections,
                'metadata': {
                    'author': notebook.author,
                    'generated_at': datetime.now().isoformat(),
                    'notebook_id': notebook_id,
                    'digital_article_version': '0.0.3'
                },
                'plan': article_plan
            }
            
            logger.info(f"🎯 Generated complete scientific article for notebook {notebook_id}")
            logger.info(f"🎯 Article sections: {list(sections.keys())}")
            logger.info(f"🎯 Total content length: {sum(len(content) for content in sections.values())} characters")
            
            return complete_article
            
        except Exception as e:
            logger.error(f"Failed to generate scientific article for notebook {notebook_id}: {e}")
            raise
