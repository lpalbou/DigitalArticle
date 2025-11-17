"""
Test suite for LLM retry context passing improvements.

This test suite verifies that the fixes for passing full execution context
during retries work correctly:
1. Full context is built and passed during retries
2. Error analyzer receives context
3. DataFrame column information is included in error messages
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from backend.app.services.error_analyzer import ErrorAnalyzer


class TestErrorAnalyzerContextPassing:
    """Test that ErrorAnalyzer receives and uses context correctly."""

    def test_analyze_error_accepts_context(self):
        """Test that analyze_error method accepts context parameter."""
        analyzer = ErrorAnalyzer()

        # Should not raise TypeError about unexpected keyword argument
        result = analyzer.analyze_error(
            error_message="KeyError: 'ADAS13'",
            error_type="KeyError",
            traceback="  File test.py, line 1\n    df['ADAS13']\nKeyError: 'ADAS13'",
            code="df['ADAS13']",
            context={'available_variables': {}}
        )

        assert result is not None
        assert result.error_type == "KeyError"

    def test_pandas_key_error_with_dataframe_context(self):
        """Test that pandas KeyError shows actual DataFrame columns when context provided."""
        analyzer = ErrorAnalyzer()

        # Simulate context with DataFrame info
        context = {
            'available_variables': {
                'sdtm_dataset': "DataFrame (50 rows, 4 columns: ['AGE', 'SEX', 'RACE', 'ARM'])"
            }
        }

        result = analyzer.analyze_error(
            error_message="KeyError: 'ADAS13'",
            error_type="KeyError",
            traceback="  File test.py, line 1\n    df['ADAS13']\nKeyError: 'ADAS13'",
            code="df = sdtm_dataset.copy()\ndf['ADAS13']",
            context=context
        )

        assert result is not None
        # Check that suggestions include actual DataFrame info
        suggestions_text = "\n".join(result.suggestions)
        assert "ACTUAL AVAILABLE DATA" in suggestions_text
        assert "sdtm_dataset" in suggestions_text
        assert "DataFrame (50 rows, 4 columns" in suggestions_text

    def test_pandas_key_error_without_context_fallback(self):
        """Test that pandas KeyError falls back to generic guidance without context."""
        analyzer = ErrorAnalyzer()

        result = analyzer.analyze_error(
            error_message="KeyError: 'ADAS13'",
            error_type="KeyError",
            traceback="  File test.py, line 1\n    df['ADAS13']\nKeyError: 'ADAS13'",
            code="df['ADAS13']",
            context=None  # No context provided
        )

        assert result is not None
        # Should fall back to generic guidance
        suggestions_text = "\n".join(result.suggestions)
        assert "Common causes:" in suggestions_text
        assert "print(df.columns.tolist())" in suggestions_text

    def test_pandas_key_error_with_empty_context(self):
        """Test that pandas KeyError handles empty context gracefully."""
        analyzer = ErrorAnalyzer()

        result = analyzer.analyze_error(
            error_message="KeyError: 'ADAS13'",
            error_type="KeyError",
            traceback="  File test.py, line 1\n    df['ADAS13']\nKeyError: 'ADAS13'",
            code="df['ADAS13']",
            context={}  # Empty context
        )

        assert result is not None
        # Should fall back to generic guidance
        suggestions_text = "\n".join(result.suggestions)
        assert "Common causes:" in suggestions_text


class TestLLMServiceContextPassing:
    """Test that LLMService passes context to error analyzer."""

    def test_enhance_error_context_passes_context(self):
        """Test that _enhance_error_context passes context to analyzer."""
        from backend.app.services.llm_service import LLMService

        # Create service without initializing LLM
        # LLMService.__init__ takes provider and model, but we can use defaults
        service = LLMService()

        # Test context
        context = {
            'available_variables': {
                'sdtm_dataset': "DataFrame (50 rows, 4 columns: ['AGE', 'SEX', 'RACE', 'ARM'])"
            }
        }

        # Call _enhance_error_context with context
        result = service._enhance_error_context(
            error_message="KeyError: 'ADAS13'",
            error_type="KeyError",
            traceback="  File test.py, line 1\n    df['ADAS13']\nKeyError: 'ADAS13'",
            code="df = sdtm_dataset.copy()\ndf['ADAS13']",
            context=context
        )

        # Verify the result includes DataFrame info
        assert "ACTUAL AVAILABLE DATA" in result
        assert "sdtm_dataset" in result


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])
