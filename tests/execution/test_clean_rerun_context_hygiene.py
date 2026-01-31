from __future__ import annotations

from uuid import uuid4

import pytest

from backend.app.models.notebook import (
    CellCreateRequest,
    CellExecuteRequest,
    CellType,
    ExecutionStatus,
    NotebookCreateRequest,
)
from backend.app.services.notebook_service import NotebookService


@pytest.mark.asyncio
async def test_clean_rerun_rebuilds_context_and_ignores_downstream_state(tmp_path):
    """
    Regression test for "rerun doesn't start clean".

    Scenario:
    - Cell 2's behavior depends on whether `z` exists in globals()
    - Cell 3 defines `z`
    - A normal rerun of Cell 2 after running Cell 3 will be contaminated by downstream state
    - A clean rerun of Cell 2 must ignore downstream state and behave as if only upstream cells ran
    """
    service = NotebookService(notebooks_dir=str(tmp_path))

    notebook = service.create_notebook(NotebookCreateRequest(title="clean rerun test"))

    cell_1 = service.create_cell(
        CellCreateRequest(
            cell_type=CellType.CODE,
            content="x = 1\n",
            notebook_id=notebook.id,
        )
    )
    assert cell_1 is not None

    cell_2_code = (
        "if 'z' in globals():\n"
        "    y = 999\n"
        "else:\n"
        "    y = 2\n"
        "print(y)\n"
    )
    cell_2 = service.create_cell(
        CellCreateRequest(
            cell_type=CellType.CODE,
            content=cell_2_code,
            notebook_id=notebook.id,
        )
    )
    assert cell_2 is not None

    cell_3 = service.create_cell(
        CellCreateRequest(
            cell_type=CellType.CODE,
            content="z = 3\n",
            notebook_id=notebook.id,
        )
    )
    assert cell_3 is not None

    # Execute cell 1, cell 2 (before z exists), then cell 3 (defines z)
    for cell in (cell_1, cell_2, cell_3):
        _cell, result = await service.execute_cell(CellExecuteRequest(cell_id=cell.id, autofix=True))
        assert result.status == ExecutionStatus.SUCCESS

    notebook_id = str(notebook.id)
    globals_dict = service.execution_service.notebook_globals[notebook_id]
    assert globals_dict["z"] == 3

    # Normal rerun: downstream state contaminates cell 2
    _cell, normal_rerun = await service.execute_cell(CellExecuteRequest(cell_id=cell_2.id, autofix=True))
    assert normal_rerun.status == ExecutionStatus.SUCCESS
    assert service.execution_service.notebook_globals[notebook_id]["y"] == 999

    # Clean rerun: must ignore downstream state (z) and behave like only upstream cells ran
    _cell, clean_rerun = await service.execute_cell(
        CellExecuteRequest(cell_id=cell_2.id, clean_rerun=True, autofix=True)
    )
    assert clean_rerun.status == ExecutionStatus.SUCCESS
    assert service.execution_service.notebook_globals[notebook_id]["y"] == 2

    # Downstream invalidation: cell 3 should be marked stale after rerunning cell 2 successfully
    updated_notebook = service.get_notebook(notebook_id)
    assert updated_notebook is not None
    updated_cell_3 = updated_notebook.get_cell(cell_3.id)
    assert updated_cell_3 is not None
    assert updated_cell_3.cell_state.value == "stale"

