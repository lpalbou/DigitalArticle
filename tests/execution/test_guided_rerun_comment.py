import pytest

from backend.app.models.notebook import (
    CellCreateRequest,
    CellExecuteRequest,
    CellType,
    ExecutionStatus,
    NotebookCreateRequest,
)
from backend.app.services.llm_service import LLMService
from backend.app.services.notebook_service import NotebookService


@pytest.mark.asyncio
async def test_guided_rerun_persists_comment_and_includes_previous_code_in_context(monkeypatch, tmp_path):
    """
    Regression guard for backlog 0067:
    - rerun_comment is persisted (cell.metadata.rerun_history)
    - rerun_comment is injected into the context passed to LLM regeneration
    - context includes the current cell's previous code so the LLM can do a partial rewrite
    """

    captured_contexts: list[dict] = []

    async def fake_agenerate_code_from_prompt(self, prompt, context, step_type="code_generation", attempt_number=1):
        captured_contexts.append(context)
        # Return simple code that always succeeds.
        code = "print('v2')" if (context or {}).get("rerun_comment") else "print('v1')"
        return code, 0, "trace_stub", {"trace_id": "trace_stub", "prompt": "stub", "system_prompt": "stub"}

    monkeypatch.setattr(LLMService, "agenerate_code_from_prompt", fake_agenerate_code_from_prompt)

    service = NotebookService(notebooks_dir=str(tmp_path))
    notebook = service.create_notebook(NotebookCreateRequest(title="guided rerun test"))

    cell = service.create_cell(
        CellCreateRequest(
            cell_type=CellType.PROMPT,
            content="Make a simple output",
            notebook_id=notebook.id,
        )
    )
    assert cell is not None

    # First run: generate code normally (creates "previous_code" for the second run)
    first = await service.execute_cell(CellExecuteRequest(cell_id=cell.id, notebook_id=notebook.id, force_regenerate=True))
    assert first is not None
    first_cell, first_result = first
    assert first_result.status == ExecutionStatus.SUCCESS
    assert first_cell.code and "v1" in first_cell.code

    # Second run: guided rerun with a comment; should include previous code in context
    second = await service.execute_cell(
        CellExecuteRequest(
            cell_id=cell.id,
            notebook_id=notebook.id,
            force_regenerate=True,
            clean_rerun=True,
            rerun_comment="Keep the same plot but change colors to a colorblind-friendly palette.",
        )
    )
    assert second is not None
    second_cell, second_result = second
    assert second_result.status == ExecutionStatus.SUCCESS
    assert second_cell.code and "v2" in second_cell.code

    # Provenance: rerun comment must be persisted
    rerun_history = second_cell.metadata.get("rerun_history", [])
    assert isinstance(rerun_history, list)
    assert len(rerun_history) >= 1
    assert rerun_history[-1]["comment"].startswith("Keep the same plot")

    # LLM context injection: ensure rerun comment and previous code are present
    assert len(captured_contexts) >= 2
    guided_ctx = captured_contexts[-1]
    assert guided_ctx.get("rerun_comment")
    current_cell_ctx = guided_ctx.get("current_cell_context") or {}
    assert "v1" in (current_cell_ctx.get("previous_code") or "")


def test_llm_user_prompt_includes_guided_rerun_comment_and_previous_code():
    """
    Ensure the guided rerun "delta request" is visible in the actual user prompt text
    (so it shows up in traces and strongly steers generation).
    """
    llm = LLMService.__new__(LLMService)  # avoid provider initialization in unit test
    user_prompt = llm._build_user_prompt(
        "Original request",
        {
            "rerun_comment": "Change plot colors to a colorblind-friendly palette.",
            "current_cell_context": {"previous_code": "print('v1')\n"},
        },
    )
    assert "GUIDED RERUN" in user_prompt
    assert "Change plot colors" in user_prompt
    assert "print('v1')" in user_prompt

