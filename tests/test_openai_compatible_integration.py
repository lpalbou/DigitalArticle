#!/usr/bin/env python3
"""
Integration test for OpenAI-compatible provider with LMStudio.

Tests:
1. Connection to LMStudio on port 1234
2. Model listing
3. Simple generation with qwen/qwen3-next-80b
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def test_openai_compatible_with_lmstudio():
    """Test OpenAI-compatible provider connecting to LMStudio."""
    print("=" * 60)
    print("Testing OpenAI-Compatible Provider with LMStudio")
    print("=" * 60)
    
    try:
        from abstractcore import create_llm
        from abstractcore.config import configure_provider
        from abstractcore.providers import get_all_providers_with_models
        
        print("\n✅ AbstractCore imported successfully")
        
        # Check AbstractCore version
        from abstractcore.utils.version import __version__
        print(f"📦 AbstractCore version: {__version__}")
        
        # Configure the openai-compatible provider with LMStudio base URL
        lmstudio_url = "http://localhost:1234/v1"
        print(f"\n📍 Configuring openai-compatible provider with: {lmstudio_url}")
        configure_provider("openai-compatible", base_url=lmstudio_url)
        
        # Test 1: List models via openai-compatible provider
        print("\n" + "-" * 60)
        print("TEST 1: List models from OpenAI-Compatible provider")
        print("-" * 60)
        
        # Create a minimal instance to list models
        llm_for_models = create_llm("openai-compatible", model="default", base_url=lmstudio_url)
        models = llm_for_models.list_available_models()
        
        print(f"✅ Found {len(models)} models:")
        for i, model in enumerate(models[:10], 1):  # Show first 10
            print(f"   {i}. {model}")
        if len(models) > 10:
            print(f"   ... and {len(models) - 10} more")
        
        # Test 2: Create LLM with specific model
        print("\n" + "-" * 60)
        print("TEST 2: Create LLM with qwen/qwen3-next-80b")
        print("-" * 60)
        
        model_name = "qwen/qwen3-next-80b"
        if model_name not in models:
            print(f"⚠️ Model '{model_name}' not found in available models")
            if models:
                model_name = models[0]
                print(f"   Using first available model: {model_name}")
            else:
                print("❌ No models available!")
                return False
        
        llm = create_llm("openai-compatible", model=model_name, base_url=lmstudio_url)
        print(f"✅ Created LLM: {llm.provider}/{llm.model}")
        print(f"   Base URL: {llm.base_url}")
        
        # Test 3: Simple generation
        print("\n" + "-" * 60)
        print("TEST 3: Simple generation")
        print("-" * 60)
        
        prompt = "What is 2+2? Answer with just the number."
        print(f"📝 Prompt: {prompt}")
        
        response = llm.generate(prompt, max_tokens=50)
        print(f"✅ Response: {response.content}")
        
        if hasattr(response, 'usage') and response.usage:
            print(f"   Usage: {response.usage}")
        if hasattr(response, 'gen_time') and response.gen_time:
            print(f"   Generation time: {response.gen_time}ms")
        
        # Test 4: Test via Digital Article's LLM service
        print("\n" + "-" * 60)
        print("TEST 4: Test via Digital Article's LLM service")
        print("-" * 60)
        
        # Temporarily set config to use openai-compatible
        os.environ["OPENAI_COMPATIBLE_BASE_URL"] = lmstudio_url
        
        from backend.app.services.llm_service import LLMService
        
        # Create LLM service with openai-compatible provider
        service = LLMService(provider="openai-compatible", model=model_name)
        print(f"✅ Created Digital Article LLMService")
        print(f"   Provider: {service.provider}")
        print(f"   Model: {service.model}")
        
        # Check health
        health = service.check_provider_health()
        print(f"   Health: {health}")
        
        print("\n" + "=" * 60)
        print("ALL TESTS PASSED! ✅")
        print("=" * 60)
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("   Make sure abstractcore >= 2.6.5 is installed")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_vllm_provider_structure():
    """Test vLLM provider is properly registered."""
    print("\n" + "=" * 60)
    print("Testing vLLM Provider Registration")
    print("=" * 60)
    
    try:
        from abstractcore.providers import (
            VLLMProvider,
            get_provider_info,
            is_provider_available
        )
        
        print("\n✅ VLLMProvider imported successfully")
        
        # Check provider registration
        info = get_provider_info("vllm")
        if info:
            print(f"✅ vLLM provider registered:")
            print(f"   Name: {info.name}")
            print(f"   Display Name: {info.display_name}")
            print(f"   Description: {info.description}")
            # ProviderInfo has 'capabilities_list' attribute, not 'capabilities'
            if hasattr(info, 'capabilities_list'):
                print(f"   Capabilities: {info.capabilities_list}")
        else:
            print("❌ vLLM provider not found in registry")
            return False
        
        print("\n✅ vLLM provider structure verified!")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n🚀 Running OpenAI-Compatible Integration Tests\n")
    
    # Test vLLM registration first (doesn't need server)
    vllm_ok = test_vllm_provider_structure()
    
    # Test OpenAI-compatible with LMStudio
    openai_compat_ok = test_openai_compatible_with_lmstudio()
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"vLLM Provider Structure: {'✅ PASS' if vllm_ok else '❌ FAIL'}")
    print(f"OpenAI-Compatible with LMStudio: {'✅ PASS' if openai_compat_ok else '❌ FAIL'}")
    
    sys.exit(0 if (vllm_ok and openai_compat_ok) else 1)
