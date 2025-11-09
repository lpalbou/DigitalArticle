"""
Chat service for answering questions about Digital Articles.

This service provides read-only question-answering capabilities about
notebook content without modifying any article data.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from ..models.notebook import Notebook
from .notebook_service import NotebookService

logger = logging.getLogger(__name__)


class ArticleChatService:
    """Service for handling chat questions about Digital Articles."""

    SYSTEM_PROMPT = """You are an intelligent assistant for a Digital Article - a computational notebook that generates publication-ready scientific analysis.

Your role is to answer questions about THIS specific article's content, methodology, and results.

CONTEXT PROVIDED:
- Article metadata (title, description)
- All cells with their prompts, code, and results
- Scientific methodology explanations
- Generated plots and tables

INSTRUCTIONS:
1. Answer questions based ONLY on the provided article content
2. Reference specific cells when relevant (e.g., "In Cell 3, the code performs...")
3. Explain technical concepts clearly
4. Be concise but informative
5. DO NOT suggest modifications to the article (read-only access)
6. If asked about something not in the article, say so clearly

EXAMPLES:
- "How many cells are in this article?" → Count and summarize
- "What datasets are used?" → List datasets from context
- "Explain the methodology in Cell 2" → Explain the scientific_explanation
- "What were the main findings?" → Summarize results from all cells
- "What does the code in Cell 4 do?" → Explain the code implementation
"""

    def __init__(self, notebook_service: NotebookService):
        self.notebook_service = notebook_service
        # Access LLM service from notebook service
        self.llm_service = notebook_service.llm_service

    def ask_question(
        self,
        notebook_id: str,
        question: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Answer a question about the notebook.

        Args:
            notebook_id: UUID of the notebook
            question: User's question
            conversation_history: Previous messages in the conversation

        Returns:
            Dictionary with answer, context_used, and timestamp
        """
        # Load notebook (read-only)
        notebook = self.notebook_service.get_notebook(notebook_id)
        if not notebook:
            raise ValueError(f"Notebook {notebook_id} not found")

        # Build article context
        article_context = self._build_article_context(notebook)

        # Build conversation prompt with history
        prompt_parts = [f"ARTICLE CONTEXT:\n{article_context}\n"]

        # Add conversation history if provided
        if conversation_history:
            prompt_parts.append("CONVERSATION HISTORY:")
            for msg in conversation_history[-10:]:  # Last 10 messages for context
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role == "user":
                    prompt_parts.append(f"User: {content}")
                else:
                    prompt_parts.append(f"Assistant: {content}")
            prompt_parts.append("")  # Empty line

        # Add current question
        prompt_parts.append(f"CURRENT QUESTION:\n{question}")

        user_prompt = "\n".join(prompt_parts)

        # Get answer from LLM
        try:
            if not self.llm_service.llm:
                raise ValueError("LLM service not initialized")

            response = self.llm_service.llm.generate(
                user_prompt,  # First positional argument
                system_prompt=self.SYSTEM_PROMPT,
                temperature=0.3,  # Lower temperature for more factual responses
                max_tokens=1000
            )

            answer = response.content.strip()

            # Extract which cells were referenced (simple heuristic)
            context_used = self._extract_referenced_cells(answer, notebook)

            return {
                "message": answer,
                "context_used": context_used,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error answering question: {e}")
            raise

    def _build_article_context(self, notebook: Notebook) -> str:
        """
        Build comprehensive context from notebook.

        Includes:
        - Article title and description
        - Number of cells and structure
        - All prompts (user's intentions)
        - All code (implementation)
        - All results (outputs, plots, tables)
        - All methodology (explanations)
        """
        context_parts = []

        # Article metadata
        context_parts.append(f"ARTICLE TITLE: {notebook.title}")
        if notebook.description:
            context_parts.append(f"DESCRIPTION: {notebook.description}")

        # Structure overview
        context_parts.append(f"\nARTICLE STRUCTURE: {len(notebook.cells)} cells")

        # Per-cell context (limit to prevent token overflow)
        max_cells = 20  # Limit to most recent cells if notebook is very large
        cells_to_include = notebook.cells[-max_cells:] if len(notebook.cells) > max_cells else notebook.cells

        for i, cell in enumerate(cells_to_include, 1):
            cell_context = [f"\n=== CELL {i} (ID: {str(cell.id)}) ==="]

            if cell.prompt:
                # Truncate very long prompts
                prompt = cell.prompt[:500] + "..." if len(cell.prompt) > 500 else cell.prompt
                cell_context.append(f"USER INTENT: {prompt}")

            if cell.code:
                # Truncate very long code
                code = cell.code[:1000] + "..." if len(cell.code) > 1000 else cell.code
                cell_context.append(f"CODE:\n{code}")

            if cell.scientific_explanation:
                # Truncate very long explanations
                methodology = cell.scientific_explanation[:800] + "..." if len(cell.scientific_explanation) > 800 else cell.scientific_explanation
                cell_context.append(f"METHODOLOGY: {methodology}")

            if cell.last_result:
                result = cell.last_result
                result_summary = []

                if result.stdout:
                    # Truncate long output
                    stdout = result.stdout[:500] + "..." if len(result.stdout) > 500 else result.stdout
                    result_summary.append(f"OUTPUT: {stdout}")

                if result.tables:
                    result_summary.append(f"TABLES: {len(result.tables)} table(s) generated")

                if result.plots:
                    result_summary.append(f"PLOTS: {len(result.plots)} plot(s) generated")

                if result.error_message:
                    result_summary.append(f"ERROR: {result.error_message}")

                if result_summary:
                    cell_context.append("RESULTS: " + ", ".join(result_summary))

            context_parts.append("\n".join(cell_context))

        if len(notebook.cells) > max_cells:
            context_parts.append(f"\n(Note: Showing most recent {max_cells} cells out of {len(notebook.cells)} total)")

        return "\n".join(context_parts)

    def _extract_referenced_cells(self, answer: str, notebook: Notebook) -> List[str]:
        """
        Extract which cells were referenced in the answer.

        Simple heuristic: look for "Cell X" mentions.
        """
        referenced = []
        for i, cell in enumerate(notebook.cells, 1):
            if f"Cell {i}" in answer or str(cell.id) in answer:
                referenced.append(str(cell.id))
        return referenced
