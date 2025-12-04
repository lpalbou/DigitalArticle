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

    REVIEWER_SYSTEM_PROMPT = """You are the Scientific Reviewer who just completed a peer review of this Digital Article.

You have access to:
- The complete article (cells, code, methodology, results)
- Your comprehensive review (overall assessment, dimensional ratings, issues, recommendations)

Your role is to answer questions about your review findings and help the author improve their work.

INSTRUCTIONS:
1. Answer questions about your review findings
2. Help the author understand specific feedback
3. Suggest concrete ways to address issues you identified
4. Prioritize which issues are most important to fix
5. Recommend implementation approaches when asked
6. Be constructive and specific - reference your review findings
7. Explain WHY certain things matter for scientific rigor
8. Draw from your review's dimensional assessments (Research Question, Methodology, Results Communication)

EXAMPLES:
- "What did you mean by [issue]?" → Explain the specific concern in more detail
- "How should I fix [issue]?" → Provide concrete implementation steps
- "Which issues are most critical?" → Rank issues by importance
- "Do you recommend method X?" → Evaluate based on your review findings
- "Why is reproducibility important here?" → Explain scientific reasoning

Be helpful, specific, and always reference your review findings when relevant."""

    def __init__(self, notebook_service: NotebookService):
        self.notebook_service = notebook_service
        # Access LLM service from notebook service
        self.llm_service = notebook_service.llm_service

    def ask_question(
        self,
        notebook_id: str,
        question: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        mode: str = 'article'
    ) -> Dict[str, Any]:
        """
        Answer a question about the notebook.

        Args:
            notebook_id: UUID of the notebook
            question: User's question
            conversation_history: Previous messages in the conversation
            mode: 'article' for article questions, 'reviewer' for review questions

        Returns:
            Dictionary with answer, context_used, and timestamp
        """
        # Load notebook (read-only)
        notebook = self.notebook_service.get_notebook(notebook_id)
        if not notebook:
            raise ValueError(f"Notebook {notebook_id} not found")

        # Build context based on mode
        if mode == 'reviewer':
            context = self._build_reviewer_context(notebook)
            system_prompt = self.REVIEWER_SYSTEM_PROMPT
        else:
            context = self._build_article_context(notebook)
            system_prompt = self.SYSTEM_PROMPT

        # Build conversation prompt with history
        prompt_parts = [f"CONTEXT:\n{context}\n"]

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
                system_prompt=system_prompt,  # Use mode-specific prompt
                max_tokens=32000,  # Full active context (article + question + history)
                max_output_tokens=8192,  # 8k output limit
                temperature=0.3  # Lower temperature for more factual responses
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

    def _build_reviewer_context(self, notebook: Notebook) -> str:
        """
        Build reviewer-specific context including article content AND review findings.

        Includes:
        - Article content (via _build_article_context)
        - Review findings (overall assessment, dimensional ratings, issues, recommendations)
        """
        import json

        # Start with article context
        article_context = self._build_article_context(notebook)

        # Add review data if available
        review_data = notebook.metadata.get('article_review')
        if review_data:
            review_parts = ["\n\n=== YOUR REVIEW ==="]

            # Overall assessment
            if 'overall_assessment' in review_data:
                review_parts.append(f"\nOVERALL ASSESSMENT:\n{review_data['overall_assessment']}")

            # Dimensional ratings
            if 'research_question' in review_data:
                rq = review_data['research_question']
                rating = rq.get('rating', {})
                review_parts.append(f"\nRESEARCH QUESTION RATING: {rating.get('score', '?')}/5 - {rating.get('label', 'N/A')}")
                review_parts.append(f"Summary: {rating.get('summary', 'N/A')}")

            if 'methodology' in review_data:
                meth = review_data['methodology']
                rating = meth.get('rating', {})
                review_parts.append(f"\nMETHODOLOGY RATING: {rating.get('score', '?')}/5 - {rating.get('label', 'N/A')}")
                review_parts.append(f"Summary: {rating.get('summary', 'N/A')}")

            if 'results_communication' in review_data:
                results = review_data['results_communication']
                rating = results.get('rating', {})
                review_parts.append(f"\nRESULTS COMMUNICATION RATING: {rating.get('score', '?')}/5 - {rating.get('label', 'N/A')}")
                review_parts.append(f"Summary: {rating.get('summary', 'N/A')}")

            # Recommendation
            if 'recommendation' in review_data:
                review_parts.append(f"\nRECOMMENDATION: {review_data['recommendation']}")

            # Strengths
            if 'strengths' in review_data and review_data['strengths']:
                review_parts.append("\nKEY STRENGTHS:")
                for i, strength in enumerate(review_data['strengths'], 1):
                    review_parts.append(f"{i}. {strength}")

            # Issues
            if 'enhanced_issues' in review_data and review_data['enhanced_issues']:
                review_parts.append("\nISSUES IDENTIFIED:")
                for i, issue in enumerate(review_data['enhanced_issues'], 1):
                    review_parts.append(f"\n{i}. {issue.get('title', 'Issue')}")
                    review_parts.append(f"   Severity: {issue.get('severity', 'unknown')}")
                    review_parts.append(f"   Description: {issue.get('description', 'N/A')}")
                    review_parts.append(f"   Impact: {issue.get('impact', 'N/A')}")
                    review_parts.append(f"   Suggestion: {issue.get('suggestion', 'N/A')}")

            # Recommendations
            if 'recommendations' in review_data and review_data['recommendations']:
                review_parts.append("\nRECOMMENDATIONS FOR IMPROVEMENT:")
                for i, rec in enumerate(review_data['recommendations'], 1):
                    review_parts.append(f"{i}. {rec}")

            return article_context + "\n".join(review_parts)
        else:
            # No review available yet
            return article_context + "\n\n=== YOUR REVIEW ===\n(Review not yet generated)"

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
