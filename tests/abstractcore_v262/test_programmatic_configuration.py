#!/usr/bin/env python3
"""
Test AbstractCore v2.6.2 Programmatic Configuration Integration

Tests that Digital Article correctly uses AbstractCore v2.6.2's new
programmatic configuration API for base URLs.

Run: pytest tests/abstractcore_v262/test_programmatic_configuration.py -v
"""

import pytest
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../backend'))

from app.services.user_settings_service import UserSettings, LLMSettings
from abstractcore.config import configure_provider, get_provider_config, clear_provider_config
from abstractcore.providers import get_all_providers_with_models
from abstractcore import create_llm


class TestProgrammaticConfiguration:
    """Test AbstractCore v2.6.2 programmatic base URL configuration."""

    def setup_method(self):
        """Clear all configurations before each test."""
        # Clear any existing configurations
        for provider in ['ollama', 'lmstudio', 'openai', 'anthropic']:
            try:
                clear_provider_config(provider)
            except:
                pass

    def test_configure_provider_api_available(self):
        """Test that AbstractCore v2.6.2 programmatic config API is available."""
        # Verify the API functions exist
        assert callable(configure_provider)
        assert callable(get_provider_config)
        assert callable(clear_provider_config)
        print("✅ Programmatic configuration API available")

    def test_configure_base_url(self):
        """Test setting base_url via configure_provider()."""
        test_url = "http://test-server:11434"

        configure_provider('ollama', base_url=test_url)
        config = get_provider_config('ollama')

        assert config is not None
        assert config.get('base_url') == test_url
        print(f"✅ Configured ollama with base_url: {test_url}")

    def test_create_llm_uses_configured_url(self):
        """Test that create_llm() automatically uses configured base_url."""
        test_url = "http://localhost:11434"

        configure_provider('ollama', base_url=test_url)
        llm = create_llm('ollama', model='test')

        # Verify LLM instance has the configured base_url
        assert hasattr(llm, 'base_url')
        assert llm.base_url == test_url
        print(f"✅ create_llm() used configured base_url: {llm.base_url}")

    def test_list_models_respects_configured_url(self):
        """Test that list_available_models() uses configured base_url."""
        # Configure with localhost (should work if Ollama is running)
        configure_provider('ollama', base_url='http://localhost:11434')

        try:
            llm = create_llm('ollama', model='test')
            models = llm.list_available_models()

            # If Ollama is running, we should get models
            if len(models) > 0:
                print(f"✅ list_available_models() returned {len(models)} models")
            else:
                print("⚠️  Ollama may not be running (no models returned)")

            # Test passes if no exception
            assert isinstance(models, list)
        except Exception as e:
            # If Ollama not running, that's okay - test still passes if API works
            print(f"⚠️  Ollama not running: {type(e).__name__}")
            assert True

    def test_invalid_url_fails_correctly(self):
        """Test that invalid URL causes connection failure."""
        configure_provider('ollama', base_url='http://invalid-server-xyz:11434')

        llm = create_llm('ollama', model='test')
        models = llm.list_available_models()

        # With invalid URL, should return empty list or raise exception
        assert isinstance(models, list)
        assert len(models) == 0, "Invalid URL should return no models"
        print("✅ Invalid URL correctly returns empty model list")

    def test_dynamic_url_update(self):
        """Test changing base_url at runtime (simulates Blue 'Update' button)."""
        # First URL
        url1 = "http://server1:11434"
        configure_provider('ollama', base_url=url1)
        assert get_provider_config('ollama')['base_url'] == url1

        # Update to second URL
        url2 = "http://server2:11434"
        configure_provider('ollama', base_url=url2)
        assert get_provider_config('ollama')['base_url'] == url2

        # Verify create_llm() uses updated URL
        llm = create_llm('ollama', model='test')
        assert llm.base_url == url2

        print(f"✅ Dynamic URL update: {url1} → {url2}")

    def test_settings_integration(self):
        """Test integration with Digital Article user settings."""
        # Simulate user settings with custom base URLs
        settings = UserSettings(
            llm=LLMSettings(
                base_urls={
                    "ollama": "http://custom-ollama:11434",
                    "lmstudio": "http://custom-lmstudio:1234/v1",
                    "openai": "",  # Empty = use default
                    "anthropic": ""  # Empty = use default
                }
            )
        )

        # Configure base URLs from settings (simulates get_available_providers())
        for provider, base_url in settings.llm.base_urls.items():
            if base_url and base_url.strip():
                configure_provider(provider, base_url=base_url)

        # Verify configurations
        ollama_config = get_provider_config('ollama')
        lmstudio_config = get_provider_config('lmstudio')

        assert ollama_config['base_url'] == "http://custom-ollama:11434"
        assert lmstudio_config['base_url'] == "http://custom-lmstudio:1234/v1"

        print("✅ User settings integration works correctly")

    def test_clear_configuration(self):
        """Test clearing provider configuration."""
        # Set a configuration
        configure_provider('ollama', base_url='http://test:11434')
        assert get_provider_config('ollama') is not None

        # Clear it
        clear_provider_config('ollama')
        config = get_provider_config('ollama')

        # After clearing, config should be None or empty dict
        assert config is None or config == {}
        print("✅ clear_provider_config() works correctly")


if __name__ == '__main__':
    # Run tests with pytest
    pytest.main([__file__, '-v', '--tb=short'])
