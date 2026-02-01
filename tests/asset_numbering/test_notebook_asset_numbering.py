"""
Tests for notebook-wide figure/table numbering.

These tests validate that numbering is:
- Sequential across the whole notebook (not per-cell)
- Deterministic (based on cell order)
- Robust to LLM/user labels that incorrectly restart at 1
- Robust to legacy plot formats (base64 strings)
"""

import os
import sys

import pytest

# Add backend to path (tests import `app.*`)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../backend"))

from app.models.notebook import Notebook, CellType, ExecutionResult, ExecutionStatus  # noqa: E402
from app.services.notebook_asset_numbering_service import (  # noqa: E402
    NotebookAssetNumberingService,
)


def test_notebook_wide_numbering_overrides_per_cell_labels_and_dedupes_plots():
    nb = Notebook(title="Test Notebook")

    c1 = nb.add_cell(cell_type=CellType.PROMPT, content="")
    c2 = nb.add_cell(cell_type=CellType.PROMPT, content="")
    c3 = nb.add_cell(cell_type=CellType.PROMPT, content="")

    # Cell 1: one display table + Plotly HTML "label carrier" + one interactive plot without label
    c1.last_result = ExecutionResult(
        status=ExecutionStatus.SUCCESS,
        tables=[
            {
                "type": "table",
                "source": "display",
                "label": "Table 1: Demographics",
                "name": "displayed_result",
                "shape": [1, 1],
                "columns": ["a"],
                "data": [{"a": 1}],
                "html": "<table></table>",
                "info": {},
            },
            {
                "type": "html",
                "source": "display",
                "label": "Figure 1: Swimmer Plot",
                "content": "<div>plotly</div>",
            },
        ],
        plots=[],
        interactive_plots=[
            {
                "name": "swimmer",
                "figure": {"data": [], "layout": {}},
                "json": "{\"data\":[]}",
            }
        ],
    )

    # Cell 2: duplicate plot payloads + a display table that restarts numbering at 1
    c2.last_result = ExecutionResult(
        status=ExecutionStatus.SUCCESS,
        tables=[
            {
                "type": "table",
                "source": "display",
                "label": "Table 1: Outcomes",
                "name": "displayed_result",
                "shape": [1, 1],
                "columns": ["b"],
                "data": [{"b": 2}],
                "html": "<table></table>",
                "info": {},
            }
        ],
        plots=["AAA", "AAA"],  # duplicate base64 payload
        interactive_plots=[],
    )

    # Cell 3: a figure dict that restarts at 1
    c3.last_result = ExecutionResult(
        status=ExecutionStatus.SUCCESS,
        tables=[],
        plots=[{"type": "image", "data": "BBB", "label": "Figure 1: KM Curve", "source": "display"}],
        interactive_plots=[],
    )

    svc = NotebookAssetNumberingService()
    svc.renumber_in_place(nb)

    # Tables should be numbered across the notebook and preserve descriptions
    assert c1.last_result.tables[0]["label"] == "Table 1: Demographics"
    assert c2.last_result.tables[0]["label"] == "Table 2: Outcomes"

    # Duplicate plot payloads should be removed and the remaining plot should be labeled
    assert len(c2.last_result.plots) == 1
    assert c2.last_result.plots[0]["label"] == "Figure 2"

    # Interactive plot should pick up its description from the Plotly HTML label carrier
    assert c1.last_result.interactive_plots[0]["label"] == "Figure 1: Swimmer Plot"

    # Dict plots should be renumbered and preserve their description
    assert c3.last_result.plots[0]["label"] == "Figure 3: KM Curve"

