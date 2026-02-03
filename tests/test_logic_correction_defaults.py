"""
Guardrails for logic self-correction default policy (ADR 0004).

Critical principle:
- By default, the system should auto-correct HIGH severity issues only.
- MEDIUM/LOW issues are logged but should not trigger correction unless user opts in.
"""

from backend.app.services.user_settings_service import ExecutionSettings


def test_default_logic_correction_policy_only_high() -> None:
    settings = ExecutionSettings()
    assert settings.logic_validation_enabled is True
    assert settings.max_logic_corrections == 3
    # Default policy: do NOT auto-correct MEDIUM/LOW unless explicitly enabled
    assert settings.medium_retry_max_corrections == 0
    assert settings.low_retry_max_corrections == 0

