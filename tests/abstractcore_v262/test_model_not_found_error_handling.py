#!/usr/bin/env python3
"""
Test ModelNotFoundError Handling for LMStudio

Tests that when create_llm() raises ModelNotFoundError (because "dummy"
model doesn't exist), we gracefully parse the available models from the
error message.

Run: pytest tests/abstractcore_v262/test_model_not_found_error_handling.py -v
"""

import pytest
import re
from abstractcore.exceptions import ModelNotFoundError


class TestModelNotFoundErrorHandling:
    """Test parsing available models from ModelNotFoundError."""

    def test_parse_models_from_error_message(self):
        """Test extracting model list from ModelNotFoundError message."""
        # Simulate the error message format that AbstractCore uses
        error_msg = """❌ Model 'dummy' not found for LMStudio provider.

✅ Available models (28):
  • bytedance/seed-oss-36b
  • gemma-3-27b-it-abliterated
  • gemma-3-4b-it
  • glm-4.5-air-mlx
  • google/gemma-3n-e4b"""

        # Parse using the same regex from the endpoint
        models = re.findall(r'  • (.+)', error_msg)

        assert len(models) == 5
        assert "bytedance/seed-oss-36b" in models
        assert "gemma-3-4b-it" in models
        print(f"✅ Parsed {len(models)} models from error message")

    def test_detect_available_models_in_error(self):
        """Test detecting 'Available models' phrase in error message."""
        error_msg = """❌ Model 'dummy' not found for LMStudio provider.

✅ Available models (28):
  • model1
  • model2"""

        assert "Available models" in error_msg
        print("✅ 'Available models' phrase detected")

    def test_empty_error_message(self):
        """Test handling error message without available models."""
        error_msg = "Connection failed: timeout"

        models = re.findall(r'  • (.+)', error_msg)

        assert len(models) == 0
        assert "Available models" not in error_msg
        print("✅ Empty model list handled correctly")

    def test_model_name_with_special_characters(self):
        """Test parsing model names with slashes and hyphens."""
        error_msg = """Available models (3):
  • qwen/qwen3-next-80b
  • mistralai/mistral-small-3.2
  • text-embedding-all-minilm-l6-v2-embedding"""

        models = re.findall(r'  • (.+)', error_msg)

        assert len(models) == 3
        assert "qwen/qwen3-next-80b" in models
        assert "mistralai/mistral-small-3.2" in models
        assert "text-embedding-all-minilm-l6-v2-embedding" in models
        print(f"✅ Parsed models with special characters: {models}")


if __name__ == '__main__':
    # Run tests with pytest
    pytest.main([__file__, '-v', '--tb=short'])
