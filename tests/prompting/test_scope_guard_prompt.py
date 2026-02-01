from __future__ import annotations

from backend.app.services.llm_service import LLMService


def test_build_user_prompt_includes_scope_guard_section():
    llm = LLMService.__new__(LLMService)  # avoid provider initialization
    prompt = llm._build_user_prompt("Compute the mean of x", context=None)

    assert "SCOPE GUARD" in prompt
    assert "Do ONLY what the CURRENT REQUEST asks." in prompt
    assert "CURRENT REQUEST:" in prompt
