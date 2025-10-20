"""
Tests for pandas error analysis.
"""

import pytest
import sys
from pathlib import Path

backend_path = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from app.services.error_analyzer import ErrorAnalyzer, ErrorContext


class TestPandasKeyErrors:
    """Test pandas KeyError analysis."""

    def test_pandas_column_not_found(self):
        """Test detection of pandas column not found error."""
        analyzer = ErrorAnalyzer()

        error_message = "KeyError: 'Age'"
        error_type = "KeyError"
        traceback = """
Traceback (most recent call last):
  File "<string>", line 3, in <module>
  File "pandas/core/frame.py", line 3761, in __getitem__
    indexer = self.columns.get_loc(key)
KeyError: 'Age'
"""
        code = "df['Age'].mean()"

        context = analyzer.analyze_error(error_message, error_type, traceback, code)

        assert "Age" in context.enhanced_message or "Age" in "\n".join(context.suggestions)
        suggestions_text = "\n".join(context.suggestions)
        assert "column" in suggestions_text.lower()
        assert "df.columns" in suggestions_text

    def test_pandas_merge_error(self):
        """Test detection of pandas merge errors."""
        analyzer = ErrorAnalyzer()

        error_message = "MergeError: No common columns to perform merge on"
        error_type = "MergeError"
        traceback = "MergeError: No common columns..."
        code = "pd.merge(df1, df2)"

        context = analyzer.analyze_error(error_message, error_type, traceback, code)

        suggestions_text = "\n".join(context.suggestions)
        assert "merge" in suggestions_text.lower() or "join" in suggestions_text.lower()


class TestFileNotFoundErrors:
    """Test file not found error analysis."""

    def test_missing_data_prefix(self):
        """Test detection of file access without data/ prefix."""
        analyzer = ErrorAnalyzer()

        error_message = "FileNotFoundError: [Errno 2] No such file or directory: 'gene_expression.csv'"
        error_type = "FileNotFoundError"
        traceback = "FileNotFoundError: No such file or directory: 'gene_expression.csv'"
        code = "df = pd.read_csv('gene_expression.csv')"

        context = analyzer.analyze_error(error_message, error_type, traceback, code)

        suggestions_text = "\n".join(context.suggestions)
        # Should emphasize data/ directory requirement
        assert "data/" in suggestions_text
        assert "gene_expression.csv" in suggestions_text

    def test_correct_data_path_in_suggestions(self):
        """Test that suggestions include correct data/ path examples."""
        analyzer = ErrorAnalyzer()

        error_message = "FileNotFoundError: 'myfile.csv'"
        error_type = "FileNotFoundError"
        code = "pd.read_csv('myfile.csv')"

        context = analyzer.analyze_error(error_message, error_type, "", code)

        suggestions_text = "\n".join(context.suggestions)
        # Should show correct and incorrect patterns
        assert "'data/" in suggestions_text or '"data/' in suggestions_text
        assert "CORRECT" in suggestions_text or "RIGHT" in suggestions_text


class TestImportErrors:
    """Test import error analysis."""

    def test_module_not_found(self):
        """Test detection of module not found errors."""
        analyzer = ErrorAnalyzer()

        error_message = "ModuleNotFoundError: No module named 'tensorflow'"
        error_type = "ModuleNotFoundError"
        traceback = "ModuleNotFoundError: No module named 'tensorflow'"
        code = "import tensorflow as tf"

        context = analyzer.analyze_error(error_message, error_type, traceback, code)

        suggestions_text = "\n".join(context.suggestions)
        # Should list available libraries
        assert "pandas" in suggestions_text
        assert "numpy" in suggestions_text
        assert "matplotlib" in suggestions_text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
