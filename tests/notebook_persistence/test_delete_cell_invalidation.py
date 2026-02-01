from __future__ import annotations

from uuid import UUID

from backend.app.models.notebook import CellCreateRequest, CellType, NotebookCreateRequest
from backend.app.services.notebook_service import NotebookService


def test_delete_cell_clears_semantic_caches_and_marks_downstream_stale(tmp_path):
    service = NotebookService(notebooks_dir=str(tmp_path))
    notebook = service.create_notebook(NotebookCreateRequest(title="delete cell test"))

    cell_1 = service.create_cell(
        CellCreateRequest(cell_type=CellType.CODE, content="x = 1\n", notebook_id=notebook.id)
    )
    cell_2 = service.create_cell(
        CellCreateRequest(cell_type=CellType.CODE, content="y = 2\n", notebook_id=notebook.id)
    )
    cell_3 = service.create_cell(
        CellCreateRequest(cell_type=CellType.CODE, content="z = 3\n", notebook_id=notebook.id)
    )
    assert cell_1 and cell_2 and cell_3

    # Seed caches to verify invalidation.
    notebook.metadata["semantic_cache_analysis"] = {"cache_key": "abc", "graph": {"nodes": []}}
    notebook.metadata["semantic_cache_profile"] = {"cache_key": "def", "graph": {"nodes": []}}
    service._save_notebook(notebook)  # persist test setup

    ok = service.delete_cell(str(notebook.id), str(cell_2.id))
    assert ok is True

    updated = service.get_notebook(str(notebook.id))
    assert updated is not None

    # Cell should be gone
    assert updated.get_cell(UUID(str(cell_2.id))) is None

    # Caches should be invalidated
    assert "semantic_cache_analysis" not in updated.metadata
    assert "semantic_cache_profile" not in updated.metadata

    # Downstream should be stale and require clean rerun
    updated_cell_3 = updated.get_cell(UUID(str(cell_3.id)))
    assert updated_cell_3 is not None
    assert updated_cell_3.cell_state.value == "stale"
    assert updated_cell_3.metadata.get("execution", {}).get("needs_clean_rerun") is True

    # Audit trail should exist
    events = updated.metadata.get("audit_events", [])
    assert any(e.get("type") == "cell_deleted" and e.get("cell_id") == str(cell_2.id) for e in events)

