"""
Test suite for SciPy trapz deprecation fix.

This test suite ensures that the trapz → trapezoid migration is properly
handled at all levels: persona guidance, error analysis, and system prompts.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.error_analyzer import ErrorAnalyzer
import json


def test_error_analyzer_catches_trapz():
    """Test that error analyzer provides specific guidance for trapz import errors."""
    analyzer = ErrorAnalyzer()

    # Simulate the actual error message from SciPy 1.14+
    error_msg = "ImportError: cannot import name 'trapz' from 'scipy.integrate' (/path/to/scipy/integrate/__init__.py)"
    code = """
from scipy.integrate import trapz
auc = trapz(concentration, time)
"""

    result = analyzer._analyze_import_error(
        error_message=error_msg,
        error_type="ImportError",
        traceback="",
        code=code,
        context=None
    )

    assert result is not None, "Error analyzer should handle trapz import error"
    assert "trapezoid" in result.enhanced_message.lower(), "Should mention trapezoid replacement"

    # Check that suggestions include the fix
    suggestions_text = "\n".join(result.suggestions)
    assert "trapezoid" in suggestions_text, "Suggestions should mention trapezoid"
    assert "trapz" in suggestions_text, "Suggestions should mention deprecated trapz"
    assert "1.14" in suggestions_text or "deprecated" in suggestions_text.lower(), "Should mention deprecation"

    print("✅ PASS: Error analyzer provides trapz → trapezoid guidance")


def test_error_analyzer_trapz_partial_match():
    """Test that error analyzer catches various trapz-related errors."""
    analyzer = ErrorAnalyzer()

    test_cases = [
        "cannot import name 'trapz' from 'scipy.integrate'",
        "ImportError: trapz",
        "name 'trapz' is not defined after importing from scipy",
    ]

    for error_msg in test_cases:
        result = analyzer._analyze_import_error(
            error_message=error_msg,
            error_type="ImportError",
            traceback="",
            code="",
            context=None
        )

        assert result is not None, f"Should handle: {error_msg}"
        assert "trapezoid" in result.enhanced_message.lower(), f"Should suggest trapezoid for: {error_msg}"
        print(f"✅ PASS: Caught '{error_msg[:50]}...'")


def test_ms_persona_has_trapezoid_constraint():
    """Test that M&S persona has explicit trapezoid guidance."""
    persona_file = Path(__file__).parent.parent.parent.parent / "data" / "personas" / "system" / "modeling-simulation.json"

    assert persona_file.exists(), f"M&S persona file should exist at {persona_file}"

    with open(persona_file) as f:
        persona = json.load(f)

    # Check that code_generation scope has trapezoid constraint
    code_gen_guidance = None
    for guidance in persona.get('guidance', []):
        if guidance.get('scope') == 'code_generation':
            code_gen_guidance = guidance
            break

    assert code_gen_guidance is not None, "M&S persona should have code_generation guidance"

    constraints_text = "\n".join(code_gen_guidance.get('constraints', []))
    assert "trapezoid" in constraints_text.lower(), "Should mention trapezoid"
    assert "trapz" in constraints_text, "Should mention deprecated trapz"
    assert "1.14" in constraints_text or "deprecated" in constraints_text.lower(), "Should mention deprecation"

    # Check preferred_methods includes trapezoid
    preferred = persona.get('preferred_methods', [])
    assert "trapezoid" in preferred, "trapezoid should be in preferred_methods"

    print("✅ PASS: M&S persona has trapezoid constraint and preferred method")


def test_system_prompt_has_trapz_warning():
    """Test that system prompt warns about trapz deprecation."""
    from app.services.llm_service import LLMService

    service = LLMService(provider='ollama', model='test')

    # Build system prompt without context
    prompt = service._build_system_prompt()

    assert "trapz" in prompt, "System prompt should mention trapz"
    assert "trapezoid" in prompt, "System prompt should mention trapezoid"
    assert "WRONG" in prompt or "❌" in prompt, "Should show trapz as wrong"
    assert "RIGHT" in prompt or "✅" in prompt, "Should show trapezoid as right"

    print("✅ PASS: System prompt has trapz → trapezoid warning")


def test_complete_integration():
    """Test that all three layers work together."""
    print("\n" + "="*80)
    print("Testing Complete Integration of trapz Deprecation Fix")
    print("="*80)

    # Layer 1: M&S Persona
    test_ms_persona_has_trapezoid_constraint()

    # Layer 2: Error Analyzer
    test_error_analyzer_catches_trapz()
    test_error_analyzer_trapz_partial_match()

    # Layer 3: System Prompt
    test_system_prompt_has_trapz_warning()

    print("\n" + "="*80)
    print("✅ ALL LAYERS WORKING CORRECTLY!")
    print("="*80)
    print("\nThree-Layer Defense:")
    print("  1. ✅ M&S Persona: Guides LLM to use trapezoid from the start")
    print("  2. ✅ Error Analyzer: Provides clear fix if trapz is used")
    print("  3. ✅ System Prompt: Shows correct vs incorrect usage")
    print("\nResult: trapz deprecation should NEVER cause issues again!")
    print("="*80)


if __name__ == "__main__":
    test_complete_integration()
