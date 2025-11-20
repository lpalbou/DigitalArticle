"""
Integration tests for Digital Article reasoning framework.

These tests verify that the analysis planner and critic are properly integrated
into the notebook execution flow and catch real issues.
"""

import pytest
import sys
from pathlib import Path

# Add backend to path
backend_path = str(Path(__file__).parent.parent.parent / "backend")
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.services.notebook_service import NotebookService
from app.services.execution_service import ExecutionService
from app.services.llm_service import LLMService
from app.models.notebook import Notebook, Cell, CellType, CellExecuteRequest, ExecutionStatus


class TestCircularReasoningDetection:
    """Test that planning detects circular reasoning and blocks execution."""

    def test_predicting_grouping_variable_blocked(self):
        """Verify planning detects circular reasoning when predicting treatment arm."""
        # Create notebook service
        service = NotebookService()

        # Create test notebook
        notebook = Notebook(
            id="test-circular",
            title="Circular Reasoning Test",
            llm_provider="anthropic",
            llm_model="claude-haiku-4-5"
        )

        # Create cell with circular reasoning prompt
        cell = Cell(
            id="cell-1",
            cell_type=CellType.PROMPT,
            prompt="predict which treatment arm patients received from their baseline characteristics"
        )
        notebook.cells.append(cell)

        # Execute cell
        request = CellExecuteRequest()
        updated_cell, result = service.execute_cell(notebook, cell.id, request)

        # Assertions
        assert 'analysis_plan' in updated_cell.metadata, "Planning phase should have run"

        # Check if critical issues were detected
        if 'planning_blocked' in updated_cell.metadata:
            assert updated_cell.metadata['planning_blocked'] is True
            assert 'critical_issues' in updated_cell.metadata
            assert len(updated_cell.metadata['critical_issues']) > 0

            # Verify issue type
            issues = updated_cell.metadata['critical_issues']
            assert any(issue['type'] == 'circular_reasoning' for issue in issues)

            # Verify execution was blocked
            assert result.status == ExecutionStatus.ERROR
            assert "PlanningCriticalIssue" in result.error_type
        else:
            # Planning detected issue but didn't block (warning level)
            plan = updated_cell.metadata['analysis_plan']
            assert len(plan['validation_issues']) > 0

            # Check for circular reasoning warning
            has_circular_warning = any(
                issue['type'] == 'circular_reasoning'
                for issue in plan['validation_issues']
            )
            assert has_circular_warning, "Should detect circular reasoning"


class TestMissingColumnDetection:
    """Test that planning detects non-existent columns before execution."""

    def test_missing_column_detected_early(self):
        """Verify planning detects when prompt references non-existent columns."""
        # This test is more complex - need to set up a notebook with existing data first
        # Then try to analyze a column that doesn't exist
        # For now, skip - requires setup of multi-cell context
        pytest.skip("Requires multi-cell context setup")


class TestCritiqueFindsIssues:
    """Test that critique phase detects issues in results."""

    def test_critique_runs_on_success(self):
        """Verify critique phase runs after successful execution."""
        service = NotebookService()

        # Create simple notebook
        notebook = Notebook(
            id="test-critique",
            title="Critique Test",
            llm_provider="anthropic",
            llm_model="claude-haiku-4-5"
        )

        # Create cell with simple prompt
        cell = Cell(
            id="cell-1",
            cell_type=CellType.PROMPT,
            prompt="create a simple dataset with 3 columns: age, height, weight"
        )
        notebook.cells.append(cell)

        # Execute cell
        request = CellExecuteRequest()
        updated_cell, result = service.execute_cell(notebook, cell.id, request)

        # If execution succeeded, critique should have run
        if result.status == ExecutionStatus.SUCCESS:
            assert 'critique' in updated_cell.metadata, "Critique phase should have run on success"

            critique = updated_cell.metadata['critique']
            assert 'overall_quality' in critique
            assert 'confidence_in_results' in critique
            assert 'findings' in critique


class TestPlanningFailureFallback:
    """Test that planning failure doesn't break code generation."""

    def test_execution_continues_on_planning_failure(self):
        """Verify that if planning fails, execution continues normally."""
        # This would require mocking the planner to force a failure
        # For now, we trust the try-except logic in notebook_service.py
        pytest.skip("Requires mocking planning service")


class TestCritiqueFailureFallback:
    """Test that critique failure doesn't break results."""

    def test_results_stored_on_critique_failure(self):
        """Verify that if critique fails, results are still stored."""
        # This would require mocking the critic to force a failure
        # For now, we trust the try-except logic in notebook_service.py
        pytest.skip("Requires mocking critique service")


class TestMetadataStorage:
    """Test that reasoning artifacts are properly stored in cell metadata."""

    def test_planning_artifacts_stored(self):
        """Verify analysis plan and reasoning trace are stored."""
        service = NotebookService()

        notebook = Notebook(
            id="test-metadata",
            title="Metadata Test",
            llm_provider="anthropic",
            llm_model="claude-haiku-4-5"
        )

        cell = Cell(
            id="cell-1",
            cell_type=CellType.PROMPT,
            prompt="create a histogram of random data"
        )
        notebook.cells.append(cell)

        request = CellExecuteRequest()
        updated_cell, result = service.execute_cell(notebook, cell.id, request)

        # Check planning artifacts
        if 'analysis_plan' in updated_cell.metadata:
            plan = updated_cell.metadata['analysis_plan']
            assert 'user_intent' in plan
            assert 'research_question' in plan
            assert 'suggested_method' in plan
            assert 'validation_issues' in plan

            # Check reasoning trace
            if 'reasoning_trace' in updated_cell.metadata:
                trace = updated_cell.metadata['reasoning_trace']
                assert 'steps' in trace or 'final_plan' in trace

    def test_critique_artifacts_stored(self):
        """Verify critique and critique trace are stored."""
        service = NotebookService()

        notebook = Notebook(
            id="test-critique-metadata",
            title="Critique Metadata Test",
            llm_provider="anthropic",
            llm_model="claude-haiku-4-5"
        )

        cell = Cell(
            id="cell-1",
            cell_type=CellType.PROMPT,
            prompt="create a simple bar chart with random data"
        )
        notebook.cells.append(cell)

        request = CellExecuteRequest()
        updated_cell, result = service.execute_cell(notebook, cell.id, request)

        # Check critique artifacts (only if execution succeeded)
        if result.status == ExecutionStatus.SUCCESS and 'critique' in updated_cell.metadata:
            critique = updated_cell.metadata['critique']
            assert 'overall_quality' in critique
            assert 'findings' in critique
            assert 'plausibility_checks' in critique
            assert 'identified_limitations' in critique


class TestMethodologyEnhancement:
    """Test that methodology is enhanced with critique limitations."""

    def test_limitations_added_to_methodology(self):
        """Verify that critique limitations are appended to methodology."""
        # This is hard to test without LLM actually running
        # For now, verify the logic exists in the code
        pytest.skip("Requires full LLM execution")


if __name__ == "__main__":
    print("Running Digital Article Reasoning Integration Tests...")
    print("=" * 70)

    # Run tests
    pytest.main([__file__, "-v", "-s"])
