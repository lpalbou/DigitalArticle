"""
Notebook Service for managing notebook persistence and operations.

This service handles saving, loading, and managing notebook files,
as well as coordinating between LLM and execution services.
"""

import json
import os
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

from ..models.notebook import (
    Notebook, Cell, CellType, ExecutionResult, ExecutionStatus,
    NotebookCreateRequest, NotebookUpdateRequest,
    CellCreateRequest, CellUpdateRequest, CellExecuteRequest
)
from .llm_service import LLMService
from .execution_service import ExecutionService
from .pdf_service_scientific import ScientificPDFService

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
                
            self.notebooks_dir.mkdir(exist_ok=True)
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
                try:
                    with open(notebook_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    notebook = Notebook(**data)
                    self._notebooks[str(notebook.id)] = notebook
                    logger.info(f"Loaded notebook: {notebook.title}")
                    
                except Exception as e:
                    logger.error(f"Failed to load notebook {notebook_file}: {e}")
                    
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
        - Available variables in execution context
        - Previous cells (prompts and code) for context awareness
        - Data files available
        - Notebook metadata
        - Notebook ID and Cell ID for token tracking

        Args:
            notebook: Current notebook
            current_cell: Cell being executed

        Returns:
            Context dictionary for LLM with previous cell history
        """
        context = {}

        try:
            # Add basic notebook info
            context['notebook_title'] = notebook.title
            context['cell_type'] = current_cell.cell_type.value

            # Add IDs for token tracking (AbstractCore integration)
            context['notebook_id'] = str(notebook.id)
            context['cell_id'] = str(current_cell.id)

            # Add information about available data files
            try:
                execution_context = self.data_manager.get_execution_context()
                context.update(execution_context)
            except Exception as e:
                logger.warning(f"Could not get data manager context: {e}")

            # Get available variables from execution service
            try:
                variables = self.execution_service.get_variable_info()
                if variables:
                    context['available_variables'] = variables
                    logger.info(f"Added {len(variables)} available variables to context")
            except Exception as e:
                logger.warning(f"Could not get variable info: {e}")

            # Get previous cells context for LLM awareness
            previous_cells = []
            for cell in notebook.cells:
                if cell.id == current_cell.id:
                    break  # Stop at current cell
                if cell.cell_type in (CellType.PROMPT, CellType.CODE) and cell.code:
                    previous_cells.append({
                        'type': cell.cell_type.value,
                        'prompt': cell.prompt if cell.cell_type == CellType.PROMPT else None,
                        'code': cell.code[:500],  # Truncate long code to first 500 chars
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
    
    def _generate_fallback_code(self, prompt: str) -> str:
        """Generate simple fallback code when LLM is unavailable."""
        if "gene_expression" in prompt.lower():
            return """
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Load the gene expression data
df = pd.read_csv('data/gene_expression.csv')
print("Dataset shape:", df.shape)
print("\\nColumns:", df.columns.tolist())
print("\\nFirst 5 rows:")
print(df.head())

# Basic analysis
print("\\nBasic statistics:")
print(df.describe())
"""
        elif "patient" in prompt.lower():
            return """
import pandas as pd
import matplotlib.pyplot as plt

# Load patient data
df = pd.read_csv('data/patient_data.csv')
print("Dataset shape:", df.shape)
print("\\nFirst 5 rows:")
print(df.head())
"""
        else:
            return """
# Simple analysis
print("Hello! This is a basic analysis.")
print("LLM service is currently unavailable, using fallback code.")
"""
    
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
            cell_id: Cell UUID
            
        Returns:
            Cell or None if not found
        """
        for notebook in self._notebooks.values():
            cell = notebook.get_cell(cell_id)
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
            
            # Handle direct code execution
            if request.code:
                cell.code = request.code
                cell.updated_at = datetime.now()
            elif request.prompt:
                cell.prompt = request.prompt
                cell.updated_at = datetime.now()
            
            # Generate code if needed
            if not cell.code or request.force_regenerate:
                if cell.cell_type == CellType.PROMPT and cell.prompt:
                    logger.info(f"Generating code for prompt: {cell.prompt[:100]}...")
                    
                    try:
                        # Build context for LLM
                        try:
                            context = self._build_execution_context(notebook, cell)
                            logger.info(f"Built context with {len(context)} items")
                        except Exception as context_error:
                            logger.warning(f"Context building failed: {context_error}, using empty context")
                            context = {}
                        
                        # Update LLM service configuration
                        if notebook.llm_provider != self.llm_service.provider or notebook.llm_model != self.llm_service.model:
                            logger.info(f"Updating LLM service: {notebook.llm_provider}/{notebook.llm_model}")
                            self.llm_service = LLMService(notebook.llm_provider, notebook.llm_model)
                        
                        # Generate code
                        logger.info("Calling LLM service for code generation...")
                        generated_code = self.llm_service.generate_code_from_prompt(cell.prompt, context)
                        cell.code = generated_code
                        cell.updated_at = datetime.now()
                        logger.info(f"Successfully generated {len(generated_code)} characters of code")

                        # Update notebook's last context tokens from the generation
                        try:
                            last_ctx = self.llm_service.token_tracker.get_current_context_tokens(str(notebook.id))
                            if last_ctx > 0:
                                notebook.last_context_tokens = last_ctx
                                logger.info(f"📊 Updated notebook last_context_tokens: {last_ctx}")
                        except Exception as token_err:
                            logger.warning(f"Could not update last_context_tokens: {token_err}")

                    except Exception as e:
                        logger.error(f"LLM code generation failed: {e}")
                        import traceback
                        logger.error(f"LLM error traceback: {traceback.format_exc()}")
                        # Provide fallback code for basic analysis
                        cell.code = self._generate_fallback_code(cell.prompt)
                        logger.info("Using fallback code generation")
            
            # Execute code if available
            if cell.code and cell.cell_type in (CellType.PROMPT, CellType.CODE):
                # Set up notebook-specific context for execution
                result = self.execution_service.execute_code(cell.code, str(cell.id), str(notebook.id))
                cell.execution_count += 1
                
                # Auto-retry logic: if execution failed and we have a prompt or generated code, try to fix it with LLM
                max_retries = 3
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

                        # Use suggest_improvements with enhanced error context
                        # This will automatically use ErrorAnalyzer to provide domain-specific guidance
                        fixed_code = self.llm_service.suggest_improvements(
                            prompt=cell.prompt,
                            code=cell.code,
                            error_message=result.error_message,
                            error_type=result.error_type,
                            traceback=result.traceback
                        )
                        
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
            
            # Generate scientific explanation for successful prompt cells
            print(f"🔬 ALWAYS CHECKING scientific explanation conditions:")
            print(f"   - Result status: {result.status} (SUCCESS={ExecutionStatus.SUCCESS})")
            print(f"   - Cell type: {cell.cell_type} (PROMPT={CellType.PROMPT})")
            print(f"   - Has prompt: {bool(cell.prompt)} ('{cell.prompt[:50] if cell.prompt else 'None'}...')")
            print(f"   - Has code: {bool(cell.code)} ('{cell.code[:50] if cell.code else 'None'}...')")
            logger.info(f"🔬 ALWAYS CHECKING scientific explanation conditions:")
            logger.info(f"   - Result status: {result.status} (SUCCESS={ExecutionStatus.SUCCESS})")
            logger.info(f"   - Cell type: {cell.cell_type} (PROMPT={CellType.PROMPT})")
            logger.info(f"   - Has prompt: {bool(cell.prompt)} ('{cell.prompt[:50] if cell.prompt else 'None'}...')")
            logger.info(f"   - Has code: {bool(cell.code)} ('{cell.code[:50] if cell.code else 'None'}...')")
            
            if (result.status == ExecutionStatus.SUCCESS and 
                cell.cell_type == CellType.PROMPT and 
                cell.prompt and cell.code):
                
                print("🔬 GENERATING SCIENTIFIC EXPLANATION SYNCHRONOUSLY...")
                logger.info("🔬 GENERATING SCIENTIFIC EXPLANATION SYNCHRONOUSLY...")
                
                try:
                    # Prepare execution result data for LLM
                    execution_data = {
                        'status': 'success',
                        'stdout': result.stdout,
                        'plots': result.plots,
                        'tables': result.tables,
                        'interactive_plots': result.interactive_plots
                    }
                    
                    print("🔬 About to call LLM service for methodology...")
                    explanation = self.llm_service.generate_scientific_explanation(
                        cell.prompt, 
                        cell.code, 
                        execution_data
                    )
                    print(f"🔬 LLM returned explanation: {len(explanation)} chars")
                    print(f"🔬 Explanation content: {explanation[:200]}...")
                    
                    # Update cell with explanation
                    cell.scientific_explanation = explanation
                    print(f"🔬 Cell updated with explanation: {len(cell.scientific_explanation)} chars")
                    
                except Exception as e:
                    print(f"🔬 ERROR generating scientific explanation: {e}")
                    import traceback
                    print(f"🔬 Traceback: {traceback.format_exc()}")
                    logger.error(f"Error generating scientific explanation: {e}")
                    cell.scientific_explanation = ""
            else:
                logger.info("🔬 Skipping scientific explanation generation (conditions not met)")
            
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
        Save a notebook to disk.
        
        Args:
            notebook: Notebook to save
        """
        try:
            notebook_file = self.notebooks_dir / f"{notebook.id}.json"
            
            with open(notebook_file, 'w', encoding='utf-8') as f:
                json.dump(
                    notebook.dict(),
                    f,
                    indent=2,
                    ensure_ascii=False,
                    default=str  # Handle UUID and datetime serialization
                )
            
        except Exception as e:
            logger.error(f"Failed to save notebook {notebook.title}: {e}")
    
    def export_notebook(self, notebook_id: str, format: str = "json") -> Optional[str]:
        """
        Export a notebook in various formats.
        
        Args:
            notebook_id: Notebook UUID
            format: Export format (json, html, markdown)
            
        Returns:
            Exported content or None if notebook not found
        """
        notebook = self._notebooks.get(notebook_id)
        if not notebook:
            return None
        
        if format == "json":
            return json.dumps(notebook.dict(), indent=2, default=str)
        elif format == "markdown":
            return self._export_to_markdown(notebook)
        elif format == "html":
            return self._export_to_html(notebook)
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
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
        Export a notebook to PDF format.
        
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
            logger.info(f"Exporting notebook {notebook_id} to PDF (include_code={include_code})")
            pdf_bytes = self.pdf_service.generate_pdf(notebook, include_code)
            logger.info(f"PDF export successful: {len(pdf_bytes)} bytes")
            return pdf_bytes
        except Exception as e:
            logger.error(f"Failed to export notebook {notebook_id} to PDF: {e}")
            raise
