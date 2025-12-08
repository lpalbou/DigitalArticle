"""
Review Service for Digital Article.

Orchestrates scientific review of cells and articles using Reviewer persona templates.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, AsyncIterator

from ..models.notebook import Cell, Notebook, ExecutionResult
from ..models.persona import Persona, ReviewPhase, ReviewCapability
from ..models.review import (
    CellReview,
    ArticleReview,
    ReviewFinding,
    ReviewSeverity,
    ReviewCategory,
    # Enhanced models
    DimensionRating,
    ResearchQuestionAssessment,
    MethodologyAssessment,
    ResultsCommunicationAssessment,
    EnhancedIssue,
)
from ..services.llm_service import LLMService
from ..services.persona_service import PersonaService

logger = logging.getLogger(__name__)


class ReviewService:
    """Service for conducting scientific reviews of analyses."""

    # SOTA System Prompt for Article Review
    REVIEW_SYSTEM_PROMPT = """You are a senior scientific peer reviewer following Nature/Science/Cell/PLOS review standards.

## WHAT IS A DIGITAL ARTICLE?

A Digital Article inverts the traditional computational notebook paradigm:
- Users describe their analysis in NATURAL LANGUAGE (the Prompt/Intent)
- The system generates CODE to implement that analysis
- The code is EXECUTED to produce results (tables, plots, statistics)
- The system generates METHODOLOGY TEXT explaining the analysis scientifically

This creates a publication-ready scientific narrative.

## STRUCTURE OF EACH CELL

Each cell has FOUR components you must evaluate:

1. **INTENT (Prompt)**: What the user wanted to accomplish
   - Is the research question clear and scientifically meaningful?
   - Is it appropriately scoped for the data and methods?
   - Does it address an important problem?

2. **CODE (Implementation)**: How the analysis was performed
   - Are the statistical/analytical methods appropriate?
   - Are assumptions properly checked?
   - Is the code correct and reproducible?
   - Are edge cases handled?

3. **RESULTS (Output)**: What was produced
   - Tables: Are they correctly formatted? Do they show appropriate statistics?
   - Plots: Are visualizations informative and properly labeled?
   - Statistics: Are significance levels appropriate? Effect sizes reported?

4. **METHODOLOGY (Communication)**: Scientific explanation
   - Does it accurately describe what was done?
   - Does it explain WHY these methods were chosen?
   - Does it acknowledge limitations?
   - Is it publication-ready prose?

## 🚨 CRITICAL: THINK ABOUT DATA PROVENANCE

**What is the actual source and quality of the data being analyzed?**

Ask yourself:
- Is this real experimental/clinical data, or is it synthetic/simulated/mock data?
- Look for: np.random in code, variable names like "synthetic_*" or "mock_*", comments about "test data"
- Are the results scientifically meaningful, or are they just demonstrations of methodology?

**Key principle**:
Synthetic/mock/test data can demonstrate methodological competence, but it is fundamentally different from real scientific data. A technically perfect analysis of fake data is NOT the same as publication-ready science.

Be appropriately critical. Don't claim work is "publication-ready" or "meets Nature/Science standards" if it's using synthetic data for demonstration purposes. You can praise the methodology while being honest about the limitations.

## HOW TO EVALUATE (SOTA JOURNAL PRACTICES)

Following Nature/Science/Cell/PLOS reviewer guidelines:

**Research Question Assessment**:
- RELEVANCE: Is this question significant and timely?
- CLARITY: Is it unambiguous with well-defined objectives?
- SCOPE: Is it appropriate for the available data?

**Methodology Assessment**:
- VALIDITY: Are methods appropriate for the question?
- ASSUMPTIONS: Are statistical assumptions checked and justified?
- REPRODUCIBILITY: Could another researcher replicate this?

**Results Communication Assessment**:
- ACCURACY: Do conclusions match the evidence?
- CLARITY: Are figures/tables professional and informative?
- COMPLETENESS: Are all relevant results reported (not just significant)?
- METHODOLOGY TEXT: Does it explain how results were obtained?

## YOUR ROLE

Be CONSTRUCTIVE, not destructive. Your goal is to help improve the work:
- Identify both strengths AND areas for improvement
- Provide SPECIFIC, ACTIONABLE feedback
- Distinguish between CRITICAL issues (must fix) and suggestions (nice to have)
- Reference the specific cell/component when giving feedback
- Explain WHY something matters for scientific rigor

Write as a senior colleague helping a junior researcher, not as a gatekeeper.

## CRITICAL - OUTPUT FORMAT REQUIREMENTS

You MUST follow the EXACT markdown structure specified in the user prompt. This is NON-NEGOTIABLE.

**SECTION HEADERS**: Use markdown headers (##), NOT bold:
```
## 1. RESEARCH QUESTION ASSESSMENT
## 2. METHODOLOGY ASSESSMENT
## 3. RESULTS COMMUNICATION ASSESSMENT
## 4. OVERALL ASSESSMENT
## 5. KEY STRENGTHS
## 6. ISSUES REQUIRING ATTENTION
## 7. RECOMMENDATIONS FOR IMPROVEMENT
```

**FIELD FORMATTING**: Within each section, use **bold** for field labels followed by colon:

```
**Rating**: 4/5 - Excellent
**Summary**: One sentence explaining the rating

**Relevance**: 2-3 sentences discussing relevance

**Clarity**: 2-3 sentences discussing clarity

**Scope**: 2-3 sentences discussing scope
```

CRITICAL FORMATTING RULES:
1. Section headers MUST use ## (double hash), NOT **bold**
2. Field labels MUST use **bold** and be followed by colon (:) and space
3. Each field MUST start on a new line
4. Write substantial 2-3 sentence paragraphs for each field, not single words
5. NO placeholder text like "Not assessed" - always provide actual analysis
6. NO generic statements - be specific and reference actual cells/code/results

EXAMPLE OF CORRECT FORMAT:
```markdown
## 1. RESEARCH QUESTION ASSESSMENT

**Rating**: 4/5 - Excellent
**Summary**: The research question effectively addresses...

**Relevance**: This research question is highly relevant because... (2-3 sentences)

**Clarity**: The objectives are clearly stated through... (2-3 sentences)

**Scope**: The scope is appropriate given... (2-3 sentences)
```"""

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
            response = self.llm_service.llm.generate(
                review_prompt,
                system_prompt="You are a scientific code reviewer. Provide structured, actionable feedback.",
                temperature=0.3,  # Lower temperature for more consistent reviews
            )
            # Extract text from GenerateResponse object
            review_text = response.content if hasattr(response, 'content') else str(response)

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
            response = self.llm_service.llm.generate(
                review_prompt,
                system_prompt="You are a scientific results reviewer. Focus on interpretation accuracy and completeness.",
                temperature=0.3,
            )
            # Extract text from GenerateResponse object
            review_text = response.content if hasattr(response, 'content') else str(response)

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
    ) -> tuple[ArticleReview, Optional[Dict[str, Any]]]:
        """Review entire article holistically.

        Args:
            notebook: Notebook to review
            force: Force re-review even if cached

        Returns:
            Tuple of (article review, LLM trace dict or None)
        """
        logger.info(f"🔍 Reviewing article: {notebook.title}")

        # Get reviewer persona
        reviewer = self.persona_service.get_persona('reviewer')
        if not reviewer:
            logger.error("Reviewer persona not found!")
            return self._empty_article_review(str(notebook.id)), None

        # Find synthesis review template
        synthesis_capability = next(
            (c for c in reviewer.review_capabilities if c.phase == ReviewPhase.SYNTHESIS),
            None
        )
        if not synthesis_capability:
            logger.error("No synthesis review capability found")
            return self._empty_article_review(str(notebook.id)), None

        # Build COMPLETE article context (intent, code, results, methodology for ALL cells)
        cells_context = self._build_full_article_context(notebook)

        # Build context
        context = {
            'title': notebook.title,
            'cells_summary': cells_context,  # Full context, not truncated summary
            'abstract': notebook.abstract or "No abstract generated",
        }

        # Fill template
        review_prompt = synthesis_capability.prompt_template.format(**context)

        # Call LLM for synthesis review with SOTA system prompt
        try:
            logger.info("🤖 Calling LLM for article review with SOTA guidance...")
            response = self.llm_service.llm.generate(
                review_prompt,
                system_prompt=self.REVIEW_SYSTEM_PROMPT,  # Comprehensive SOTA prompt
                temperature=0.3,
                trace_metadata={
                    'step_type': 'article_review',
                    'attempt_number': 1,
                    'notebook_id': str(notebook.id),
                },
            )
            # Extract text from GenerateResponse object
            review_text = response.content if hasattr(response, 'content') else str(response)
            logger.info(f"✅ LLM returned {len(review_text)} characters")

            # Extract trace (same pattern as llm_service.py:266-286)
            trace_id = response.metadata.get('trace_id') if hasattr(response, 'metadata') else None
            full_trace = None
            if trace_id and self.llm_service.llm:
                try:
                    traces = self.llm_service.llm.get_traces(trace_id=trace_id)
                    full_trace = traces[0] if isinstance(traces, list) and traces else traces
                    logger.info(f"✅ Captured review trace: {trace_id}")
                except Exception as trace_error:
                    logger.warning(f"Failed to capture review trace: {trace_error}")

            # Parse article review from structured response
            article_review = self._parse_article_review(review_text, str(notebook.id))
            logger.info(f"✅ Article review complete: {article_review.rating}/5 stars")

            # Mark trace as successful
            if full_trace:
                full_trace['status'] = 'success'
                full_trace['result_summary'] = f"Review complete: {article_review.rating}/5 stars"

            return article_review, full_trace

        except Exception as e:
            logger.error(f"❌ Article review failed: {type(e).__name__}: {str(e)}")
            import traceback
            error_traceback = traceback.format_exc()
            logger.error(f"Traceback: {error_traceback}")

            # Create error trace with full details
            error_trace = {
                'step': 'article_review',
                'status': 'error',
                'error_type': type(e).__name__,
                'error_message': str(e),
                'error_traceback': error_traceback,
                'timestamp': None,  # Will be set by API layer
                'context': {
                    'notebook_id': str(notebook.id),
                    'notebook_title': notebook.title,
                    'num_cells': len(notebook.cells),
                }
            }

            # Try to capture LLM trace even on failure
            try:
                trace_id = response.metadata.get('trace_id') if 'response' in locals() and hasattr(response, 'metadata') else None
                if trace_id and self.llm_service.llm:
                    traces = self.llm_service.llm.get_traces(trace_id=trace_id)
                    llm_trace = traces[0] if isinstance(traces, list) and traces else traces
                    error_trace['llm_trace'] = llm_trace
                    error_trace['trace_id'] = trace_id
            except Exception as trace_error:
                logger.warning(f"Failed to capture error trace: {trace_error}")

            # Return error trace instead of raising (so API can save it)
            return self._empty_article_review(str(notebook.id)), error_trace

    async def review_article_streaming(
        self,
        notebook: Notebook,
        force: bool = False,
    ) -> AsyncIterator[Dict[str, Any]]:
        """Review article with streaming progress updates.

        Streams progress via Server-Sent Events during LLM generation.
        Yields dictionaries with stage, progress, message, and optional data.

        Args:
            notebook: Notebook to review
            force: Force re-review even if cached

        Yields:
            Dict with keys:
            - stage: 'reviewing', 'parsing', 'complete', 'error'
            - progress: 0-100 percentage
            - message: Human-readable status
            - tokens: Token count (during reviewing stage)
            - review: Final review dict (at complete stage)
            - trace: LLM trace dict (at complete stage)
        """
        logger.info(f"🔍 Streaming review for article: {notebook.title}")

        try:
            # Get reviewer persona
            reviewer = self.persona_service.get_persona('reviewer')
            if not reviewer:
                logger.error("Reviewer persona not found!")
                yield {'stage': 'error', 'message': 'Reviewer persona not found'}
                return

            # Find synthesis review template
            synthesis_capability = next(
                (c for c in reviewer.review_capabilities if c.phase == ReviewPhase.SYNTHESIS),
                None
            )
            if not synthesis_capability:
                logger.error("No synthesis review capability found")
                yield {'stage': 'error', 'message': 'No synthesis review capability found'}
                return

            # Build COMPLETE article context
            cells_context = self._build_full_article_context(notebook)
            context = {
                'title': notebook.title,
                'cells_summary': cells_context,
                'abstract': notebook.abstract or "No abstract generated",
            }

            # Fill template
            review_prompt = synthesis_capability.prompt_template.format(**context)

            yield {'stage': 'reviewing', 'progress': 30, 'message': 'Starting AI analysis...'}

            # Stream LLM response using AbstractCore stream=True
            accumulated_content = ""
            token_count = 0

            logger.info("🤖 Calling LLM for streaming article review...")
            response_stream = self.llm_service.llm.generate(
                review_prompt,
                system_prompt=self.REVIEW_SYSTEM_PROMPT,
                temperature=0.3,
                stream=True,  # Enable streaming
                trace_metadata={
                    'step_type': 'article_review_streaming',
                    'attempt_number': 1,
                    'notebook_id': str(notebook.id),
                },
            )

            # Process streaming chunks
            for chunk in response_stream:
                if hasattr(chunk, 'content') and chunk.content:
                    accumulated_content += chunk.content
                    token_count += len(chunk.content.split())  # Approximate token count

                    # Report progress every ~100 tokens to avoid too many updates
                    if token_count % 100 < 10:
                        progress = min(30 + (token_count / 20), 85)  # Scale from 30% to 85%
                        yield {
                            'stage': 'reviewing',
                            'progress': int(progress),
                            'message': f'Generating review... ({token_count} tokens)',
                            'tokens': token_count
                        }

            logger.info(f"✅ LLM streaming complete: {len(accumulated_content)} characters, ~{token_count} tokens")

            # Parsing stage
            yield {'stage': 'parsing', 'progress': 90, 'message': 'Processing review results...'}

            # Parse the accumulated response
            article_review = self._parse_article_review(accumulated_content, str(notebook.id))
            logger.info(f"✅ Article review parsed: {article_review.rating}/5 stars")

            # Try to capture trace
            trace_dict = None
            try:
                # Get trace from last chunk's metadata
                if hasattr(response_stream, 'metadata') and response_stream.metadata:
                    trace_id = response_stream.metadata.get('trace_id')
                elif hasattr(chunk, 'metadata') and chunk.metadata:
                    trace_id = chunk.metadata.get('trace_id')
                else:
                    trace_id = None

                if trace_id and self.llm_service.llm:
                    traces = self.llm_service.llm.get_traces(trace_id=trace_id)
                    trace_dict = traces[0] if isinstance(traces, list) and traces else traces
                    if trace_dict:
                        trace_dict['status'] = 'success'
                        trace_dict['result_summary'] = f"Review complete: {article_review.rating}/5 stars"
                        logger.info(f"✅ Captured review trace: {trace_id}")
            except Exception as trace_error:
                logger.warning(f"Failed to capture review trace: {trace_error}")

            # Complete stage - yield final review
            yield {
                'stage': 'complete',
                'progress': 100,
                'message': 'Review complete',
                'review': article_review.model_dump(),
                'trace': trace_dict
            }

        except Exception as e:
            logger.error(f"❌ Article review streaming failed: {type(e).__name__}: {str(e)}")
            import traceback
            error_traceback = traceback.format_exc()
            logger.error(f"Traceback: {error_traceback}")

            # Yield error state
            yield {
                'stage': 'error',
                'message': str(e),
                'error_type': type(e).__name__,
                'error_traceback': error_traceback
            }

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

    def _build_full_article_context(self, notebook: Notebook) -> str:
        """Build COMPLETE context for article review - NO TRUNCATION.

        The Digital Article structure for each cell:
        - Prompt (intent): What the user wanted to accomplish
        - Code (implementation): How the analysis was performed
        - Results (output): What was produced (stdout, tables, plots)
        - Methodology (communication): Scientific explanation of the analysis

        Args:
            notebook: Notebook to build context from

        Returns:
            Complete article context with all cell details
        """
        context_parts = []

        for i, cell in enumerate(notebook.cells, 1):
            cell_context = []
            cell_context.append(f"═══════════════════════════════════════════════════")
            cell_context.append(f"CELL {i}")
            cell_context.append(f"═══════════════════════════════════════════════════")

            # 1. INTENT (Prompt) - FULL TEXT
            cell_context.append(f"\n### INTENT (What the user wanted):")
            cell_context.append(cell.prompt if cell.prompt else "No prompt specified")

            # 2. IMPLEMENTATION (Code) - FULL CODE
            cell_context.append(f"\n### CODE (How it was implemented):")
            if cell.code:
                cell_context.append(f"```python\n{cell.code}\n```")
            else:
                cell_context.append("No code generated")

            # 3. RESULTS (Output) - FULL RESULTS
            cell_context.append(f"\n### RESULTS (What was produced):")
            if cell.last_result:
                result = cell.last_result
                if result.status == "success":
                    cell_context.append(f"Status: SUCCESS (execution time: {result.execution_time:.2f}s)")

                    # Stdout output
                    if result.stdout:
                        cell_context.append(f"\nStandard Output:\n{result.stdout}")

                    # Tables info
                    if result.tables:
                        cell_context.append(f"\nTables Generated: {len(result.tables)}")
                        for j, table in enumerate(result.tables, 1):
                            label = table.get('label', f'Table {j}')
                            shape = table.get('shape', 'unknown')
                            columns = table.get('columns', [])
                            cell_context.append(f"  - {label}: {shape}, columns: {columns[:10] if len(columns) > 10 else columns}")

                    # Plots info
                    if result.plots:
                        cell_context.append(f"\nPlots Generated: {len(result.plots)}")
                        for j, plot in enumerate(result.plots, 1):
                            if isinstance(plot, dict):
                                label = plot.get('label', f'Figure {j}')
                                cell_context.append(f"  - {label}")
                            else:
                                cell_context.append(f"  - Figure {j}")
                else:
                    cell_context.append(f"Status: {result.status}")
                    if result.error_message:
                        cell_context.append(f"Error: {result.error_message}")
            else:
                cell_context.append("Cell not yet executed")

            # 4. METHODOLOGY (Communication) - FULL TEXT
            cell_context.append(f"\n### METHODOLOGY (Scientific explanation):")
            if cell.scientific_explanation:
                cell_context.append(cell.scientific_explanation)
            else:
                cell_context.append("No methodology text generated")

            context_parts.append("\n".join(cell_context))

        return "\n\n".join(context_parts) if context_parts else "No cells to review"

    def _summarize_cells(self, notebook: Notebook) -> str:
        """DEPRECATED: Use _build_full_article_context() instead.

        This method severely truncates content and should not be used for review.
        Kept for backward compatibility only.
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
        """Parse enhanced article synthesis review.

        Extracts dimensional assessments, structured issues, and overall assessment
        from LLM-generated review following SOTA journal review format.

        Args:
            review_text: LLM synthesis review with structured sections
            notebook_id: Notebook ID

        Returns:
            Enhanced article review with dimensional assessments
        """
        import re

        # Helper to extract rating from text like "4/5 - Good"
        def extract_rating(text: str) -> tuple[int, str]:
            """Extract rating score and label from formatted string."""
            rating_match = re.search(r'(\d+)/5\s*-?\s*(\w+)', text)
            if rating_match:
                score = int(rating_match.group(1))
                label = rating_match.group(2)
                return max(1, min(5, score)), label
            return 3, "Adequate"

        # Helper to extract content between section headers
        def get_section_content(section_name: str) -> str:
            """Extract content between section header and next header."""
            pattern = rf'##\s*\d*\.?\s*{re.escape(section_name)}[^\n]*\n(.*?)(?=##|\Z)'
            match = re.search(pattern, review_text, re.DOTALL | re.IGNORECASE)
            return match.group(1).strip() if match else ""

        # Helper to extract dimensional assessment from structured text
        def parse_dimension_assessment(section_content: str) -> tuple[DimensionRating, dict]:
            """Parse dimensional assessment with rating and details."""
            details = {}

            # Extract rating - try multiple patterns
            rating_line = [l for l in section_content.split('\n') if 'rating' in l.lower() and '/5' in l]
            if rating_line:
                score, label = extract_rating(rating_line[0])
            else:
                score, label = 3, "Adequate"

            # Extract summary - try multiple patterns
            summary_match = re.search(r'\*\*Summary\*\*:\s*(.+?)(?:\n\n|\n\*\*|\Z)', section_content, re.DOTALL)
            if not summary_match:
                # Try without bold
                summary_match = re.search(r'Summary:\s*(.+?)(?:\n\n|\n\*\*|\Z)', section_content, re.DOTALL)
            summary = summary_match.group(1).strip() if summary_match else f"{label} rating based on analysis."

            rating = DimensionRating(score=score, label=label, summary=summary)

            # Extract detail fields - more flexible matching
            for field_name in ['relevance', 'clarity', 'scope', 'approach_validity', 'assumptions',
                               'reproducibility', 'accuracy', 'completeness', 'methodology_text']:

                # Try multiple patterns for field matching
                field_title = field_name.replace("_", " ").title()

                # Pattern 1: Bold field at line start: **Relevance**: content
                pattern1 = rf'^\*\*{re.escape(field_title)}\*\*:\s*(.+?)(?=\n\*\*|\n\n|\Z)'

                # Pattern 2: Bold field not at line start: some space **Relevance**: content
                pattern2 = rf'\*\*{re.escape(field_title)}\*\*:\s*(.+?)(?=\n\*\*|\n\n|\Z)'

                # Pattern 3: Non-bold field: Relevance: content
                pattern3 = rf'^{re.escape(field_title)}:\s*(.+?)(?=\n[A-Z][a-z]+:|\n\n|\Z)'

                # Try all patterns in order
                for pattern in [pattern1, pattern2, pattern3]:
                    field_match = re.search(pattern, section_content, re.DOTALL | re.IGNORECASE | re.MULTILINE)
                    if field_match:
                        content = field_match.group(1).strip()
                        # Clean up: remove nested field labels
                        content = re.sub(r'\n\s*\*\*[A-Z][^:]*\*\*:.*', '', content, flags=re.DOTALL)
                        # Remove any remaining line breaks followed by field-like patterns
                        content = re.sub(r'\n\s*[A-Z][a-z\s]+:.*', '', content)
                        details[field_name] = content.strip()
                        break

            return rating, details

        # Parse dimensional assessments
        try:
            # Research Question Assessment
            rq_content = get_section_content("RESEARCH QUESTION ASSESSMENT")
            logger.info(f"📝 Research Question section length: {len(rq_content)} chars")
            if rq_content:
                logger.info(f"📝 First 200 chars: {rq_content[:200]}")
            rq_rating, rq_details = parse_dimension_assessment(rq_content)
            logger.info(f"📝 Parsed fields: {list(rq_details.keys())}")

            # If any field is missing, set rating to 0 stars
            rq_relevance = rq_details.get('relevance', 'Not assessed')
            rq_clarity = rq_details.get('clarity', 'Not assessed')
            rq_scope = rq_details.get('scope', 'Not assessed')

            if any(field == 'Not assessed' for field in [rq_relevance, rq_clarity, rq_scope]):
                rq_rating = DimensionRating(score=0, label="Not Assessed", summary="Assessment incomplete - missing required fields")

            research_question = ResearchQuestionAssessment(
                rating=rq_rating,
                relevance=rq_relevance,
                clarity=rq_clarity,
                scope=rq_scope,
            )

            # Methodology Assessment
            method_content = get_section_content("METHODOLOGY ASSESSMENT")
            method_rating, method_details = parse_dimension_assessment(method_content)

            # If any field is missing, set rating to 0 stars
            method_validity = method_details.get('approach_validity', 'Not assessed')
            method_assumptions = method_details.get('assumptions', 'Not assessed')
            method_reproducibility = method_details.get('reproducibility', 'Not assessed')

            if any(field == 'Not assessed' for field in [method_validity, method_assumptions, method_reproducibility]):
                method_rating = DimensionRating(score=0, label="Not Assessed", summary="Assessment incomplete - missing required fields")

            methodology = MethodologyAssessment(
                rating=method_rating,
                approach_validity=method_validity,
                assumptions=method_assumptions,
                reproducibility=method_reproducibility,
            )

            # Results Communication Assessment
            results_content = get_section_content("RESULTS COMMUNICATION ASSESSMENT")
            results_rating, results_details = parse_dimension_assessment(results_content)

            # If any field is missing, set rating to 0 stars
            results_accuracy = results_details.get('accuracy', 'Not assessed')
            results_clarity = results_details.get('clarity', 'Not assessed')
            results_completeness = results_details.get('completeness', 'Not assessed')
            results_methodology_text = results_details.get('methodology_text', 'Not assessed')

            if any(field == 'Not assessed' for field in [results_accuracy, results_clarity, results_completeness, results_methodology_text]):
                results_rating = DimensionRating(score=0, label="Not Assessed", summary="Assessment incomplete - missing required fields")

            results_communication = ResultsCommunicationAssessment(
                rating=results_rating,
                accuracy=results_accuracy,
                clarity=results_clarity,
                completeness=results_completeness,
                methodology_text=results_methodology_text,
            )

        except Exception as e:
            logger.warning(f"Failed to parse dimensional assessments: {e}")
            # Create default assessments with 0 stars (not assessed)
            default_rating = DimensionRating(score=0, label="Not Assessed", summary="Assessment failed - parser error")
            research_question = ResearchQuestionAssessment(
                rating=default_rating,
                relevance="Not assessed", clarity="Not assessed", scope="Not assessed"
            )
            methodology = MethodologyAssessment(
                rating=default_rating,
                approach_validity="Not assessed", assumptions="Not assessed", reproducibility="Not assessed"
            )
            results_communication = ResultsCommunicationAssessment(
                rating=default_rating,
                accuracy="Not assessed", clarity="Not assessed",
                completeness="Not assessed", methodology_text="Not assessed"
            )

        # Parse overall assessment
        overall_content = get_section_content("OVERALL ASSESSMENT")
        overall_rating_match = re.search(r'(\d+)/5', overall_content)
        overall_rating = int(overall_rating_match.group(1)) if overall_rating_match else 3

        recommendation_match = re.search(r'\*\*Recommendation\*\*:\s*(\w+(?:\s+\w+)?)', overall_content, re.IGNORECASE)
        recommendation = recommendation_match.group(1) if recommendation_match else "Minor Revisions"

        summary_match = re.search(r'\*\*Summary\*\*:\s*(.+?)(?=\n##|\Z)', overall_content, re.DOTALL)
        overall_assessment = summary_match.group(1).strip() if summary_match else review_text[:500]

        # Parse strengths
        strengths_content = get_section_content("KEY STRENGTHS")
        raw_strengths = [line.strip('- •').strip() for line in strengths_content.split('\n')
                         if line.strip() and (line.strip().startswith('-') or line.strip().startswith('•'))]
        strengths = [s for s in raw_strengths if s]  # Filter out empty strings

        # Parse enhanced issues
        issues_content = get_section_content("ISSUES REQUIRING ATTENTION")
        enhanced_issues = []

        # Split by issue blocks (look for Title: pattern)
        issue_blocks = re.split(r'-\s*\*\*Title\*\*:', issues_content)
        for block in issue_blocks[1:]:  # Skip first empty split
            try:
                title_match = re.search(r'^(.+?)(?:\n|$)', block)
                desc_match = re.search(r'\*\*Description\*\*:\s*(.+?)(?=\n\*\*|\Z)', block, re.DOTALL)
                impact_match = re.search(r'\*\*Impact\*\*:\s*(.+?)(?=\n\*\*|\Z)', block, re.DOTALL)
                suggestion_match = re.search(r'\*\*Suggestion\*\*:\s*(.+?)(?=\n\*\*|\Z)', block, re.DOTALL)
                severity_match = re.search(r'\*\*Severity\*\*:\s*(\w+)', block, re.IGNORECASE)

                if title_match and desc_match:
                    title = title_match.group(1).strip()
                    description = desc_match.group(1).strip()
                    impact = impact_match.group(1).strip() if impact_match else "Impact assessment pending"
                    suggestion = suggestion_match.group(1).strip() if suggestion_match else "Suggestion pending"

                    severity_str = severity_match.group(1).lower() if severity_match else "warning"
                    severity = ReviewSeverity.CRITICAL if 'critical' in severity_str else \
                               ReviewSeverity.WARNING if 'warning' in severity_str else ReviewSeverity.INFO

                    enhanced_issues.append(EnhancedIssue(
                        severity=severity,
                        category=ReviewCategory.METHODOLOGY,
                        title=title,
                        description=description,
                        impact=impact,
                        suggestion=suggestion,
                    ))
            except Exception as e:
                logger.warning(f"Failed to parse issue block: {e}")
                continue

        # Parse recommendations
        rec_content = get_section_content("RECOMMENDATIONS FOR IMPROVEMENT")
        raw_recs = [line.strip('- •').strip() for line in rec_content.split('\n')
                    if line.strip() and (line.strip().startswith('-') or line.strip().startswith('•'))]
        recommendations = [r for r in raw_recs if r]  # Filter out empty strings

        return ArticleReview(
            notebook_id=notebook_id,
            # Dimensional assessments
            research_question=research_question,
            methodology=methodology,
            results_communication=results_communication,
            recommendation=recommendation,
            # Overall
            overall_assessment=overall_assessment,
            rating=max(1, min(5, overall_rating)),
            # Detailed feedback
            strengths=strengths or ["Analysis completed successfully"],
            enhanced_issues=enhanced_issues,
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
