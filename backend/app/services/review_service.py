"""
Review Service for Digital Article.

Orchestrates scientific review of cells and articles using Reviewer persona templates.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

from ..models.notebook import Cell, Notebook, ExecutionResult
from ..models.persona import Persona, ReviewPhase, ReviewCapability
from ..models.review import (
    CellReview,
    ArticleReview,
    ReviewFinding,
    ReviewSeverity,
    ReviewCategory,
)
from ..services.llm_service import LLMService
from ..services.persona_service import PersonaService

logger = logging.getLogger(__name__)


class ReviewService:
    """Service for conducting scientific reviews of analyses."""

    def __init__(self, llm_service: Optional[LLMService] = None):
        """Initialize review service.

        Args:
            llm_service: LLM service for review generation (optional, will create if needed)
        """
        self.llm_service = llm_service or LLMService()
        self.persona_service = PersonaService()

    def review_cell(
        self,
        cell: Cell,
        notebook: Notebook,
        force: bool = False,
    ) -> CellReview:
        """Review a single cell's analysis.

        Runs implementation and results review phases.

        Args:
            cell: Cell to review
            notebook: Parent notebook
            force: Force re-review even if cached

        Returns:
            Cell review with findings
        """
        logger.info(f"🔍 Reviewing cell {cell.id}")

        # Check cache unless forced
        if not force and 'review' in cell.metadata:
            try:
                cached_review = CellReview(**cell.metadata['review'])
                logger.info(f"✅ Using cached review from {cached_review.reviewed_at}")
                return cached_review
            except Exception as e:
                logger.warning(f"Failed to load cached review: {e}")

        # Get reviewer persona
        reviewer = self.persona_service.get_persona('reviewer')
        if not reviewer:
            logger.error("Reviewer persona not found!")
            return self._empty_review(cell.id)

        findings = []

        # Phase 1: Implementation Review (code)
        if cell.code:
            impl_findings = self._review_implementation(cell, notebook, reviewer)
            findings.extend(impl_findings)

        # Phase 2: Results Review (outputs + methodology)
        if cell.last_result and cell.last_result.status == "success":
            results_findings = self._review_results(cell, notebook, reviewer)
            findings.extend(results_findings)

        # Determine overall quality
        critical_count = sum(1 for f in findings if f.severity == ReviewSeverity.CRITICAL)
        warning_count = sum(1 for f in findings if f.severity == ReviewSeverity.WARNING)

        if critical_count > 0:
            overall_quality = "needs_attention"
        elif warning_count > 2:
            overall_quality = "acceptable"
        else:
            overall_quality = "good"

        review = CellReview(
            cell_id=str(cell.id),
            findings=findings,
            overall_quality=overall_quality,
            reviewer_persona="reviewer",
        )

        logger.info(f"✅ Cell review complete: {overall_quality} ({len(findings)} findings)")
        return review

    def _review_implementation(
        self,
        cell: Cell,
        notebook: Notebook,
        reviewer: Persona,
    ) -> List[ReviewFinding]:
        """Review code implementation.

        Args:
            cell: Cell to review
            notebook: Parent notebook
            reviewer: Reviewer persona

        Returns:
            List of implementation findings
        """
        logger.info("  📝 Reviewing implementation...")

        # Find implementation review template
        impl_capability = next(
            (c for c in reviewer.review_capabilities if c.phase == ReviewPhase.IMPLEMENTATION),
            None
        )
        if not impl_capability:
            logger.warning("No implementation review capability found")
            return []

        # Build context
        context = {
            'code': cell.code,
            'prompt': cell.prompt,
            'context': self._build_review_context(cell, notebook),
        }

        # Fill template
        review_prompt = impl_capability.prompt_template.format(**context)

        # Call LLM for review
        try:
            review_text = self.llm_service.llm.generate(
                review_prompt,
                system_prompt="You are a scientific code reviewer. Provide structured, actionable feedback.",
                temperature=0.3,  # Lower temperature for more consistent reviews
            )

            # Parse findings from review text
            findings = self._parse_review_findings(review_text, cell.id)
            logger.info(f"  ✅ Found {len(findings)} implementation issues")
            return findings

        except Exception as e:
            logger.error(f"Implementation review failed: {e}")
            return []

    def _review_results(
        self,
        cell: Cell,
        notebook: Notebook,
        reviewer: Persona,
    ) -> List[ReviewFinding]:
        """Review results and interpretation.

        Args:
            cell: Cell to review
            notebook: Parent notebook
            reviewer: Reviewer persona

        Returns:
            List of results findings
        """
        logger.info("  📊 Reviewing results...")

        # Find results review template
        results_capability = next(
            (c for c in reviewer.review_capabilities if c.phase == ReviewPhase.RESULTS),
            None
        )
        if not results_capability:
            logger.warning("No results review capability found")
            return []

        # Build context
        context = {
            'code': cell.code,
            'results': self._format_execution_results(cell.last_result),
            'methodology': cell.scientific_explanation or "No methodology text generated",
        }

        # Fill template
        review_prompt = results_capability.prompt_template.format(**context)

        # Call LLM for review
        try:
            review_text = self.llm_service.llm.generate(
                review_prompt,
                system_prompt="You are a scientific results reviewer. Focus on interpretation accuracy and completeness.",
                temperature=0.3,
            )

            # Parse findings
            findings = self._parse_review_findings(review_text, cell.id)
            logger.info(f"  ✅ Found {len(findings)} results issues")
            return findings

        except Exception as e:
            logger.error(f"Results review failed: {e}")
            return []

    def review_article(
        self,
        notebook: Notebook,
        force: bool = False,
    ) -> ArticleReview:
        """Review entire article holistically.

        Args:
            notebook: Notebook to review
            force: Force re-review even if cached

        Returns:
            Article review with synthesis
        """
        logger.info(f"🔍 Reviewing article: {notebook.title}")

        # Get reviewer persona
        reviewer = self.persona_service.get_persona('reviewer')
        if not reviewer:
            logger.error("Reviewer persona not found!")
            return self._empty_article_review(notebook.id)

        # Find synthesis review template
        synthesis_capability = next(
            (c for c in reviewer.review_capabilities if c.phase == ReviewPhase.SYNTHESIS),
            None
        )
        if not synthesis_capability:
            logger.error("No synthesis review capability found")
            return self._empty_article_review(notebook.id)

        # Build article summary
        cells_summary = self._summarize_cells(notebook)

        # Build context
        context = {
            'title': notebook.title,
            'cells_summary': cells_summary,
            'abstract': notebook.abstract or "No abstract generated",
        }

        # Fill template
        review_prompt = synthesis_capability.prompt_template.format(**context)

        # Call LLM for synthesis review
        try:
            review_text = self.llm_service.llm.generate(
                review_prompt,
                system_prompt="You are a scientific peer reviewer conducting holistic article assessment.",
                temperature=0.3,
            )

            # Parse article review from structured response
            article_review = self._parse_article_review(review_text, notebook.id)
            logger.info(f"✅ Article review complete: {article_review.rating}/5 stars")
            return article_review

        except Exception as e:
            logger.error(f"Article review failed: {e}")
            return self._empty_article_review(notebook.id)

    # ===== Helper Methods =====

    def _build_review_context(self, cell: Cell, notebook: Notebook) -> str:
        """Build context string for review.

        Args:
            cell: Current cell
            notebook: Parent notebook

        Returns:
            Context string
        """
        context_parts = []

        # Add available variables if execution happened
        if cell.last_result:
            context_parts.append("Available variables from previous cells")

        # Add previous cell info
        prev_cells = []
        for c in notebook.cells:
            if c.id == cell.id:
                break
            if c.prompt:
                prev_cells.append(f"- {c.prompt[:80]}...")

        if prev_cells:
            context_parts.append("Previous analyses:\n" + "\n".join(prev_cells))

        return "\n\n".join(context_parts) if context_parts else "No additional context"

    def _format_execution_results(self, result: ExecutionResult) -> str:
        """Format execution results for review.

        Args:
            result: Execution result

        Returns:
            Formatted string
        """
        parts = []

        if result.stdout:
            parts.append(f"STDOUT:\n{result.stdout}")

        if result.tables:
            parts.append(f"\nTABLES: {len(result.tables)} table(s) generated")

        if result.plots:
            parts.append(f"PLOTS: {len(result.plots)} plot(s) generated")

        return "\n".join(parts) if parts else "No output"

    def _summarize_cells(self, notebook: Notebook) -> str:
        """Summarize all cells for article review.

        Args:
            notebook: Notebook to summarize

        Returns:
            Summary string
        """
        summaries = []
        for i, cell in enumerate(notebook.cells, 1):
            if cell.prompt:
                summary = f"Cell {i}: {cell.prompt[:100]}"
                if cell.scientific_explanation:
                    summary += f"\n  Methodology: {cell.scientific_explanation[:150]}..."
                summaries.append(summary)

        return "\n\n".join(summaries) if summaries else "No cells with analysis"

    def _parse_review_findings(self, review_text: str, cell_id: Optional[str] = None) -> List[ReviewFinding]:
        """Parse LLM review response into structured findings.

        Simple parser looking for severity markers.

        Args:
            review_text: LLM review response
            cell_id: Optional cell ID to attach

        Returns:
            List of findings
        """
        findings = []
        lines = review_text.split('\n')

        current_severity = None
        current_message = []

        for line in lines:
            line_lower = line.lower().strip()

            # Detect severity markers
            if '🚨' in line or 'critical' in line_lower:
                if current_message:
                    findings.append(self._create_finding(current_severity, current_message, cell_id))
                current_severity = ReviewSeverity.CRITICAL
                current_message = [line]
            elif '⚠️' in line or 'warning' in line_lower:
                if current_message:
                    findings.append(self._create_finding(current_severity, current_message, cell_id))
                current_severity = ReviewSeverity.WARNING
                current_message = [line]
            elif 'ℹ️' in line or 'info' in line_lower or 'suggestion' in line_lower:
                if current_message:
                    findings.append(self._create_finding(current_severity, current_message, cell_id))
                current_severity = ReviewSeverity.INFO
                current_message = [line]
            elif current_severity and line.strip():
                current_message.append(line)

        # Add final finding
        if current_message:
            findings.append(self._create_finding(current_severity, current_message, cell_id))

        return findings

    def _create_finding(
        self,
        severity: Optional[ReviewSeverity],
        message_lines: List[str],
        cell_id: Optional[str],
    ) -> ReviewFinding:
        """Create a review finding from parsed data.

        Args:
            severity: Finding severity
            message_lines: Message lines
            cell_id: Optional cell ID

        Returns:
            Review finding
        """
        message = '\n'.join(message_lines).strip()

        # Extract suggestion if present
        suggestion = None
        if 'suggestion:' in message.lower() or 'fix:' in message.lower():
            parts = message.split(':', 1)
            if len(parts) == 2:
                suggestion = parts[1].strip()

        return ReviewFinding(
            severity=severity or ReviewSeverity.INFO,
            category=ReviewCategory.METHODOLOGY,  # Default, could be smarter
            message=message,
            suggestion=suggestion,
            cell_id=cell_id,
        )

    def _parse_article_review(self, review_text: str, notebook_id: str) -> ArticleReview:
        """Parse article synthesis review.

        Simple parser extracting key sections.

        Args:
            review_text: LLM synthesis review
            notebook_id: Notebook ID

        Returns:
            Article review
        """
        # Extract rating (look for X/5 or star pattern)
        rating = 3  # Default
        if '/5' in review_text:
            try:
                rating_str = review_text.split('/5')[0].split()[-1]
                rating = int(rating_str)
            except:
                pass

        # Extract sections (simple heuristic)
        strengths = []
        issues = []
        recommendations = []

        lines = review_text.split('\n')
        current_section = None

        for line in lines:
            line_lower = line.lower().strip()

            if 'strength' in line_lower:
                current_section = 'strengths'
            elif 'issue' in line_lower or 'critical' in line_lower:
                current_section = 'issues'
            elif 'recommendation' in line_lower or 'suggestion' in line_lower:
                current_section = 'recommendations'
            elif line.strip().startswith('-') or line.strip().startswith('•'):
                item = line.strip()[1:].strip()
                if current_section == 'strengths':
                    strengths.append(item)
                elif current_section == 'issues':
                    # Convert to finding
                    issues.append(ReviewFinding(
                        severity=ReviewSeverity.CRITICAL,
                        category=ReviewCategory.METHODOLOGY,
                        message=item,
                    ))
                elif current_section == 'recommendations':
                    recommendations.append(item)

        return ArticleReview(
            notebook_id=notebook_id,
            overall_assessment=review_text[:500],  # First 500 chars as summary
            rating=max(1, min(5, rating)),  # Clamp to 1-5
            strengths=strengths or ["Analysis completed successfully"],
            issues=issues,
            recommendations=recommendations or ["Consider additional validation"],
            reviewer_persona="reviewer",
        )

    def _empty_review(self, cell_id: str) -> CellReview:
        """Create empty review as fallback.

        Args:
            cell_id: Cell ID

        Returns:
            Empty review
        """
        return CellReview(
            cell_id=cell_id,
            findings=[],
            overall_quality="good",
        )

    def _empty_article_review(self, notebook_id: str) -> ArticleReview:
        """Create empty article review as fallback.

        Args:
            notebook_id: Notebook ID

        Returns:
            Empty review
        """
        return ArticleReview(
            notebook_id=notebook_id,
            overall_assessment="Review service unavailable",
            rating=3,
            strengths=[],
            issues=[],
            recommendations=[],
        )
