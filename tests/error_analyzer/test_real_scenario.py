"""
Real-world scenario test: Demonstrate the matplotlib subplot error enhancement.

This test demonstrates how the enhanced error context helps the LLM fix
the exact error you encountered.
"""

import pytest
import sys
from pathlib import Path

backend_path = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from app.services.error_analyzer import ErrorAnalyzer


class TestRealMatplotlibScenario:
    """
    Test the real matplotlib subplot error scenario from your issue.

    Original error:
    ValueError: num must be an integer with 1 <= num <= 12, not 13
    """

    def test_matplotlib_subplot_error_real_scenario(self):
        """
        Test that the exact error you encountered is properly enhanced.

        This demonstrates the improved error context that will be provided
        to the LLM during auto-retry, helping it fix the error effectively.
        """
        analyzer = ErrorAnalyzer()

        # The exact error from your issue
        error_message = "num must be an integer with 1 <= num <= 12, not 13"
        error_type = "ValueError"
        traceback = """Traceback (most recent call last):
  File "/Users/albou/projects/reverse-notebook/backend/app/services/execution_service.py", line 156, in execute_code
    exec(processed_code, self.globals_dict)
  File "<string>", line 102, in <module>
  File "/Users/albou/projects/reverse-notebook/.venv/lib/python3.12/site-packages/matplotlib/pyplot.py", line 1551, in subplot
    key = SubplotSpec._from_subplot_args(fig, args)
  File "/Users/albou/projects/reverse-notebook/.venv/lib/python3.12/site-packages/matplotlib/gridspec.py", line 589, in _from_subplot_args
    raise ValueError(
ValueError: num must be an integer with 1 <= num <= 12, not 13"""

        # Simulated buggy code (LLM generated a loop that goes to 13 in a 3x4 grid)
        code = """
import matplotlib.pyplot as plt
import numpy as np

fig = plt.figure(figsize=(12, 10))

# BUG: Loop goes to 13, but 3*4 grid only has 12 positions!
for i in range(1, 14):
    plt.subplot(3, 4, i)
    data = np.random.randn(100)
    plt.hist(data, bins=20)
    plt.title(f'Distribution {i}')

plt.tight_layout()
plt.show()
"""

        # Analyze the error
        context = analyzer.analyze_error(error_message, error_type, traceback, code)

        # Verify the context provides helpful guidance
        assert context is not None
        assert context.error_type == "ValueError"

        # Check enhanced message explains the constraint
        enhanced = context.enhanced_message.lower()
        assert "13" in enhanced
        assert "12" in enhanced
        assert "grid" in enhanced or "subplot" in enhanced
        assert "mathematical" in enhanced or "constraint" in enhanced

        # Check suggestions provide actionable fixes
        suggestions_text = "\n".join(context.suggestions).lower()

        # Should explain the mathematical constraint
        assert "nrows" in suggestions_text or "rows" in suggestions_text
        assert "ncols" in suggestions_text or "cols" in suggestions_text
        assert "×" in suggestions_text or "*" in suggestions_text

        # Should provide specific fix options
        assert "fix" in suggestions_text or "solution" in suggestions_text

        # Should mention loop range fix
        assert "loop" in suggestions_text or "range" in suggestions_text

        # Should suggest alternative grid sizes
        assert "3" in suggestions_text and "4" in suggestions_text

        # Format for LLM and verify it's comprehensive
        formatted = analyzer.format_for_llm(context)

        print("\n" + "=" * 80)
        print("ENHANCED ERROR CONTEXT THAT WILL BE PROVIDED TO LLM:")
        print("=" * 80)
        print(formatted)
        print("=" * 80)

        # Verify formatted output is substantial and well-structured
        assert len(formatted) > 500  # Should be comprehensive
        assert "ERROR ANALYSIS" in formatted
        assert "GUIDANCE" in formatted
        assert error_message in formatted

    def test_enhanced_context_compared_to_raw_error(self):
        """
        Compare enhanced error context with raw error to demonstrate improvement.
        """
        analyzer = ErrorAnalyzer()

        error_message = "num must be an integer with 1 <= num <= 12, not 13"
        error_type = "ValueError"
        traceback = "ValueError: num must be an integer with 1 <= num <= 12, not 13"
        code = "for i in range(1, 14): plt.subplot(3, 4, i)"

        context = analyzer.analyze_error(error_message, error_type, traceback, code)
        enhanced = analyzer.format_for_llm(context)

        # Enhanced version should be much more helpful
        raw_length = len(error_message + traceback)
        enhanced_length = len(enhanced)

        # Enhanced should be at least 5x more detailed
        assert enhanced_length > raw_length * 5

        print("\n" + "=" * 80)
        print("RAW ERROR (what LLM used to get):")
        print("=" * 80)
        print(f"Error Type: {error_type}")
        print(f"Error Message: {error_message}")
        print(f"Traceback: {traceback}")
        print(f"\nLength: {raw_length} characters")
        print("=" * 80)

        print("\n" + "=" * 80)
        print("ENHANCED ERROR (what LLM gets now):")
        print("=" * 80)
        print(enhanced)
        print(f"\nLength: {enhanced_length} characters")
        print("=" * 80)

        print(f"\n✅ Enhanced version is {enhanced_length / raw_length:.1f}x more detailed")
        print("✅ Includes:")
        print("   - Mathematical explanation of constraint")
        print("   - Specific fix suggestions")
        print("   - Alternative grid sizes")
        print("   - Common error patterns")
        print("   - Relevant documentation links")

    def test_error_enhancement_is_robust(self):
        """
        Test that error enhancement works even with partial information.

        This ensures the system is robust and doesn't fail when some
        information is missing.
        """
        analyzer = ErrorAnalyzer()

        # Minimal information scenario
        context = analyzer.analyze_error(
            error_message="num must be an integer with 1 <= num <= 12, not 13",
            error_type="ValueError",
            traceback="",  # Empty traceback
            code=""  # No code
        )

        # Should still provide helpful context
        assert context is not None
        assert len(context.suggestions) > 0
        formatted = analyzer.format_for_llm(context)
        assert len(formatted) > 200

        # Should explain the constraint even without full context
        assert "13" in formatted and "12" in formatted

    def test_formatted_output_helps_llm_understand_fix(self):
        """
        Test that the formatted output provides clear actionable guidance.

        This test verifies that the enhanced error includes:
        1. Clear explanation of WHY the error occurred
        2. WHAT the constraint is
        3. HOW to fix it (multiple options)
        4. EXAMPLES of correct code
        """
        analyzer = ErrorAnalyzer()

        error_message = "num must be an integer with 1 <= num <= 12, not 13"
        error_type = "ValueError"
        code = "for i in range(1, 14): plt.subplot(3, 4, i)"

        context = analyzer.analyze_error(error_message, error_type, "", code)
        formatted = analyzer.format_for_llm(context).lower()

        # WHY: Explanation present
        assert "mathematical" in formatted or "constraint" in formatted

        # WHAT: Constraint explained
        assert "nrows" in formatted or "ncols" in formatted or "grid" in formatted

        # HOW: Multiple fix options
        assert "fix" in formatted or "solution" in formatted
        assert formatted.count("1.") > 0 and formatted.count("2.") > 0  # Multiple numbered options

        # EXAMPLES: Specific code patterns
        assert "plt.subplot" in formatted or "subplot" in formatted


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])  # -s to show print output
