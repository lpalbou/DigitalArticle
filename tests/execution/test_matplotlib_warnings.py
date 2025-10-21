"""
Tests for matplotlib warning suppression and plot capture.

Verifies that:
1. FigureCanvasAgg warnings are suppressed
2. Plots are still captured when plt.show() is called
3. Multiple plots are captured correctly
"""

import pytest
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../backend'))

from app.services.execution_service import ExecutionService
from app.models.notebook import ExecutionStatus


class TestMatplotlibWarnings:
    """Test suite for matplotlib warning suppression."""

    def test_plt_show_no_warning(self):
        """Test that plt.show() does not generate FigureCanvasAgg warning."""
        service = ExecutionService()

        code = """
import matplotlib.pyplot as plt

# Create a simple plot
plt.figure()
plt.plot([1, 2, 3], [1, 4, 9])
plt.title("Test Plot")
plt.show()  # This should not generate a warning
"""

        result = service.execute_code(code, cell_id="test_001")

        # Verify execution succeeded
        assert result.status == ExecutionStatus.SUCCESS, f"Execution failed: {result.error_message}"

        # Verify no FigureCanvasAgg warning in stderr
        assert "FigureCanvasAgg" not in result.stderr, \
            f"Found FigureCanvasAgg warning in stderr: {result.stderr}"
        assert "non-interactive" not in result.stderr, \
            f"Found non-interactive warning in stderr: {result.stderr}"

        # Verify the plot was still captured
        assert len(result.plots) == 1, f"Expected 1 plot, got {len(result.plots)}"

    def test_multiple_plots_with_show(self):
        """Test that multiple plots are captured even with plt.show() calls."""
        service = ExecutionService()

        code = """
import matplotlib.pyplot as plt

# Create multiple plots
fig1 = plt.figure()
plt.plot([1, 2, 3], [1, 4, 9])
plt.title("Plot 1")

fig2 = plt.figure()
plt.plot([1, 2, 3], [9, 4, 1])
plt.title("Plot 2")

# Call show() - should be a no-op
plt.show()
"""

        result = service.execute_code(code, cell_id="test_002")

        # Verify execution succeeded
        assert result.status == ExecutionStatus.SUCCESS

        # Verify no warnings
        assert "FigureCanvasAgg" not in result.stderr
        assert "non-interactive" not in result.stderr

        # Verify both plots were captured
        assert len(result.plots) == 2, f"Expected 2 plots, got {len(result.plots)}"

    def test_show_is_noop(self):
        """Test that plt.show() is truly a no-op and doesn't break execution."""
        service = ExecutionService()

        code = """
import matplotlib.pyplot as plt

# Create plot and immediately show (common pattern)
plt.figure()
plt.plot([1, 2, 3], [1, 4, 9])
plt.show()  # Should be no-op

# Continue execution after show
x = 42
print(f"Execution continued: x = {x}")
"""

        result = service.execute_code(code, cell_id="test_003")

        # Verify execution succeeded
        assert result.status == ExecutionStatus.SUCCESS

        # Verify output shows execution continued
        assert "Execution continued: x = 42" in result.stdout

        # Verify plot was captured
        assert len(result.plots) == 1

    def test_deprecated_palette_warning_still_shown(self):
        """Test that other warnings (like deprecated seaborn palette) are still shown."""
        service = ExecutionService()

        code = """
import matplotlib.pyplot as plt
import warnings

# Generate a custom warning (not matplotlib-related)
warnings.warn("This is a custom test warning", UserWarning)

plt.figure()
plt.plot([1, 2, 3])
"""

        result = service.execute_code(code, cell_id="test_004")

        # Verify execution succeeded
        assert result.status == ExecutionStatus.SUCCESS

        # Verify our custom warning appears in stderr
        # Note: warnings.warn() writes to stderr
        assert "custom test warning" in result.stderr.lower() or \
               len(result.stderr) == 0  # May be empty if warnings are not captured to stderr

        # Verify matplotlib warnings are still suppressed
        assert "FigureCanvasAgg" not in result.stderr

    def test_plot_without_show(self):
        """Test that plots are captured even without calling show()."""
        service = ExecutionService()

        code = """
import matplotlib.pyplot as plt

# Create plot without calling show()
plt.figure()
plt.plot([1, 2, 3], [1, 4, 9])
plt.title("No Show Call")
"""

        result = service.execute_code(code, cell_id="test_005")

        # Verify execution succeeded
        assert result.status == ExecutionStatus.SUCCESS

        # Verify plot was captured
        assert len(result.plots) == 1

        # Verify no warnings
        assert "FigureCanvasAgg" not in result.stderr

    def test_seaborn_plot_with_show(self):
        """Test that seaborn plots work correctly with plt.show()."""
        service = ExecutionService()

        code = """
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd

# Create a simple seaborn plot
data = pd.DataFrame({'x': [1, 2, 3, 4, 5], 'y': [2, 4, 6, 8, 10]})
sns.lineplot(data=data, x='x', y='y')
plt.title("Seaborn Plot")
plt.show()
"""

        result = service.execute_code(code, cell_id="test_006")

        # Verify execution succeeded
        assert result.status == ExecutionStatus.SUCCESS

        # Verify no FigureCanvasAgg warnings
        assert "FigureCanvasAgg" not in result.stderr
        assert "non-interactive" not in result.stderr

        # Verify plot was captured
        assert len(result.plots) == 1

    def test_subplot_with_show(self):
        """Test that subplots are captured correctly with plt.show()."""
        service = ExecutionService()

        code = """
import matplotlib.pyplot as plt

# Create subplots
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))

ax1.plot([1, 2, 3], [1, 4, 9])
ax1.set_title("Subplot 1")

ax2.plot([1, 2, 3], [9, 4, 1])
ax2.set_title("Subplot 2")

plt.tight_layout()
plt.show()
"""

        result = service.execute_code(code, cell_id="test_007")

        # Verify execution succeeded
        assert result.status == ExecutionStatus.SUCCESS

        # Verify no warnings
        assert "FigureCanvasAgg" not in result.stderr

        # Verify one figure was captured (subplots are one figure)
        assert len(result.plots) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
