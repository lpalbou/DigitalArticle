from __future__ import annotations

import os
from pathlib import Path

import pytest

from backend.app.services.data_manager_clean import DataManager
from backend.app.services.file_context_preview import FileContextPreviewBuilder


@pytest.fixture()
def dm(tmp_path: Path) -> DataManager:
    """
    Create a DataManager bound to a temporary workspace root.

    Important: DataManager changes process CWD to the notebook dir; restore after the test.
    """
    prev_cwd = os.getcwd()
    builder = FileContextPreviewBuilder(
        # Keep tests fast and deterministic: never include full content in LLM context.
        max_full_content_tokens=0,
        # Make "large tabular" branch easy to hit in tests.
        max_tabular_full_read_bytes=200,
        # Avoid expensive full hashes for test files.
        max_full_sha256_bytes=10_000,
    )
    mgr = DataManager(notebook_id="test-notebook", workspace_root=str(tmp_path), preview_builder=builder)
    try:
        yield mgr
    finally:
        os.chdir(prev_cwd)


def _write(dm: DataManager, name: str, content: str) -> Path:
    p = dm.data_dir / name
    p.write_text(content, encoding="utf-8")
    return p


def test_markdown_preview_is_structured_and_compacted(dm: DataManager) -> None:
    _write(
        dm,
        "notes.md",
        "# Title\n\n## Section A\n" + ("line\n" * 200),
    )

    files = dm.list_available_files()
    md = next(f for f in files if f["name"] == "notes.md")
    preview = md["preview"]

    assert preview["file_type"] == "markdown"
    assert preview["include_full_content_in_llm_context"] is False
    assert "overview" in preview

    overview = preview["overview"]
    assert "#COMPACTION_NOTICE" in overview["compaction_notice"]
    assert isinstance(overview.get("samples"), list)
    purposes = {s.get("purpose") for s in overview["samples"] if isinstance(s, dict)}
    assert "head" in purposes
    assert "tail" in purposes


def test_json_preview_includes_structure_summary(dm: DataManager) -> None:
    _write(
        dm,
        "data.json",
        '[{"id": 1, "group": "A"}, {"id": 2, "group": "B", "extra": {"flag": true}}]',
    )

    files = dm.list_available_files()
    js = next(f for f in files if f["name"] == "data.json")
    preview = js["preview"]

    assert preview["file_type"] == "json"
    overview = preview["overview"]
    structure = overview.get("structure")
    assert isinstance(structure, dict)
    assert structure.get("type") in {"array", "object"}


def test_csv_preview_contract_preserved(dm: DataManager) -> None:
    # Small CSV (still hits large-branch due to max_tabular_full_read_bytes=200)
    _write(dm, "small.csv", "a,b\n1,2\n3,4\n5,6\n7,8\n")

    files = dm.list_available_files()
    csv = next(f for f in files if f["name"] == "small.csv")
    preview = csv["preview"]

    # Existing contract keys
    assert "columns" in preview
    assert "shape" in preview
    assert "column_stats" in preview
    assert "sample_data" in preview
    assert "is_dictionary" in preview
    assert "sampling" in preview

    assert preview["columns"] == ["a", "b"]
    assert isinstance(preview["sample_data"], list)
    assert len(preview["sample_data"]) > 0


def test_large_csv_uses_head_tail_sampling(dm: DataManager) -> None:
    # Create a CSV above the 200-byte full-read threshold.
    rows = ["x,y\n"] + [f"{i},{i%3}\n" for i in range(200)]
    _write(dm, "large.csv", "".join(rows))

    files = dm.list_available_files()
    csv = next(f for f in files if f["name"] == "large.csv")
    preview = csv["preview"]

    sampling = preview.get("sampling", {})
    assert sampling.get("mode") == "head+tail"
    assert preview.get("columns") == ["x", "y"]
    assert isinstance(preview.get("sample_data"), list)

