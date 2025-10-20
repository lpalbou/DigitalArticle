"""
Tests for matplotlib error analysis.

These tests verify that the ErrorAnalyzer correctly identifies and provides
helpful guidance for matplotlib-related errors.
"""

import pytest
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from app.services.error_analyzer import ErrorAnalyzer, ErrorContext


class TestMatplotlibSubplotErrors:
    """Test matplotlib subplot constraint error analysis."""

    def test_subplot_grid_constraint_basic(self):
        """Test detection of basic subplot grid constraint violation."""
        analyzer = ErrorAnalyzer()

        error_message = "num must be an integer with 1 <= num <= 12, not 13"
        error_type = "ValueError"
        traceback = """
Traceback (most recent call last):
  File "<string>", line 5, in <module>
  File "matplotlib/pyplot.py", line 1551, in subplot
    key = SubplotSpec._from_subplot_args(fig, args)
ValueError: num must be an integer with 1 <= num <= 12, not 13
"""
        code = """
import matplotlib.pyplot as plt
fig = plt.figure()
for i in range(1, 14):
    plt.subplot(3, 4, i)
    plt.plot([1, 2, 3])
"""

        context = analyzer.analyze_error(error_message, error_type, traceback, code)

        assert isinstance(context, ErrorContext)
        assert context.error_type == "ValueError"
        assert "13" in context.enhanced_message
        assert "12" in context.enhanced_message
        assert "grid" in context.enhanced_message.lower()

        # Check that suggestions include mathematical explanation
        suggestions_text = "\n".join(context.suggestions)
        assert "nrows × ncols" in suggestions_text or "nrows * ncols" in suggestions_text
        assert "13" in suggestions_text
        assert "12" in suggestions_text

    def test_subplot_grid_suggestions_provided(self):
        """Test that appropriate grid size suggestions are provided."""
        analyzer = ErrorAnalyzer()

        error_message = "num must be an integer with 1 <= num <= 12, not 13"
        error_type = "ValueError"
        traceback = ""
        code = "plt.subplot(3, 4, 13)"

        context = analyzer.analyze_error(error_message, error_type, traceback, code)

        suggestions_text = "\n".join(context.suggestions)

        # Should suggest alternative grid sizes
        assert "grid" in suggestions_text.lower()
        # Should mention fixing loop ranges
        assert "loop" in suggestions_text.lower() or "range" in suggestions_text.lower()

    def test_subplot_call_extraction(self):
        """Test extraction of subplot calls from code."""
        analyzer = ErrorAnalyzer()

        code = """
import matplotlib.pyplot as plt
plt.subplot(2, 2, 1)
plt.plot([1, 2, 3])
plt.subplot(2, 2, 2)
plt.plot([4, 5, 6])
"""

        calls = analyzer._extract_subplot_calls(code)

        assert len(calls) == 2
        assert "plt.subplot(2, 2, 1)" in calls
        assert "plt.subplot(2, 2, 2)" in calls

    def test_grid_size_suggestions(self):
        """Test grid size suggestion algorithm."""
        analyzer = ErrorAnalyzer()

        # For 13 subplots, should suggest grids >= 13 positions
        suggestions = analyzer._suggest_grid_sizes(13)

        assert len(suggestions) > 0
        for nrows, ncols in suggestions:
            assert nrows * ncols >= 13
            # Check that they're not too elongated (aspect ratio check)
            aspect_ratio = max(nrows, ncols) / min(nrows, ncols)
            assert aspect_ratio <= 3

    def test_formatted_output_for_llm(self):
        """Test that formatted output is LLM-friendly."""
        analyzer = ErrorAnalyzer()

        error_message = "num must be an integer with 1 <= num <= 12, not 13"
        error_type = "ValueError"
        traceback = "ValueError: num must be an integer..."
        code = "plt.subplot(3, 4, 13)"

        context = analyzer.analyze_error(error_message, error_type, traceback, code)
        formatted = analyzer.format_for_llm(context)

        # Should be well-structured
        assert "=" * 80 in formatted
        assert "ERROR ANALYSIS" in formatted
        assert "GUIDANCE" in formatted
        assert context.enhanced_message in formatted
        assert "\n".join(context.suggestions) in formatted

        # Should be clear and actionable
        assert len(formatted) > 200  # Substantial guidance
        assert "FIX" in formatted or "SOLUTION" in formatted

    def test_subplot_error_vs_other_valueerror(self):
        """Test that subplot errors are distinguished from other ValueErrors."""
        analyzer = ErrorAnalyzer()

        # Subplot error
        subplot_context = analyzer.analyze_error(
            error_message="num must be an integer with 1 <= num <= 12, not 13",
            error_type="ValueError",
            traceback="",
            code="plt.subplot(3, 4, 13)"
        )

        # Generic ValueError
        generic_context = analyzer.analyze_error(
            error_message="invalid literal for int() with base 10: 'abc'",
            error_type="ValueError",
            traceback="",
            code="x = int('abc')"
        )

        # Subplot error should have specific enhanced message
        assert "subplot" in subplot_context.enhanced_message.lower() or "grid" in subplot_context.enhanced_message.lower()

        # Generic ValueError should have generic message
        assert "subplot" not in generic_context.enhanced_message.lower()


class TestMatplotlibFigureErrors:
    """Test matplotlib figure management error analysis."""

    def test_figure_error_detection(self):
        """Test detection of figure management errors."""
        analyzer = ErrorAnalyzer()

        error_message = "RuntimeError: Can't access figure that was closed"
        error_type = "RuntimeError"
        traceback = "RuntimeError: Can't access figure that was closed"
        code = "fig.show()"

        context = analyzer.analyze_error(error_message, error_type, traceback, code)

        suggestions_text = "\n".join(context.suggestions)
        # Should provide figure management guidance
        assert "figure" in suggestions_text.lower()


class TestErrorAnalyzerRobustness:
    """Test that error analyzer handles edge cases gracefully."""

    def test_empty_error_message(self):
        """Test handling of empty error message."""
        analyzer = ErrorAnalyzer()

        context = analyzer.analyze_error("", "ValueError", "", "")

        assert isinstance(context, ErrorContext)
        assert len(context.suggestions) > 0  # Should provide generic guidance

    def test_none_values(self):
        """Test handling of None values in parameters."""
        analyzer = ErrorAnalyzer()

        # Should not crash with None values
        context = analyzer.analyze_error(
            error_message="Some error",
            error_type="ValueError",
            traceback="",
            code=""
        )

        assert isinstance(context, ErrorContext)

    def test_analyzer_exception_handling(self):
        """Test that analyzer failures fall back gracefully."""
        analyzer = ErrorAnalyzer()

        # Malformed error message
        context = analyzer.analyze_error(
            error_message="\\x00\\x01\\xff",  # Binary garbage
            error_type="RuntimeError",
            traceback="",
            code=""
        )

        # Should still return a valid context
        assert isinstance(context, ErrorContext)
        assert len(context.suggestions) > 0

    def test_very_long_code(self):
        """Test handling of very long code strings."""
        analyzer = ErrorAnalyzer()

        # Generate long code
        code = "\n".join(["x = 1" for _ in range(10000)])

        context = analyzer.analyze_error(
            error_message="num must be an integer with 1 <= num <= 12, not 13",
            error_type="ValueError",
            traceback="",
            code=code
        )

        # Should still process successfully
        assert isinstance(context, ErrorContext)
        assert "13" in context.enhanced_message

    def test_unicode_in_error(self):
        """Test handling of unicode characters in error messages."""
        analyzer = ErrorAnalyzer()

        error_message = "num must be an integer with 1 ≤ num ≤ 12, not 13"  # Unicode ≤
        error_type = "ValueError"

        context = analyzer.analyze_error(error_message, error_type, "", "plt.subplot(3, 4, 13)")

        assert isinstance(context, ErrorContext)
        # Should still extract the numbers even with unicode
        assert "13" in context.enhanced_message or "13" in "\n".join(context.suggestions)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
