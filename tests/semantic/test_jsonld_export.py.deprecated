"""
Tests for JSON-LD export functionality in Digital Article.

Tests cover:
- JSON-LD format validation
- Context and namespace handling
- Export integration with NotebookService
- Semantic graph structure
- Cross-notebook knowledge graph potential
"""

import pytest
import json
from uuid import uuid4

from backend.app.models.notebook import Notebook, Cell, CellType, ExecutionResult, ExecutionStatus
from backend.app.services.notebook_service import NotebookService
from backend.app.services.semantic_service import SemanticExtractionService


@pytest.fixture
def notebook_service(tmp_path):
    """Create a notebook service with temporary directory."""
    return NotebookService(notebooks_dir=str(tmp_path / "notebooks"))


@pytest.fixture
def semantic_service():
    """Create a semantic extraction service."""
    return SemanticExtractionService()


class TestJSONLDStructure:
    """Test JSON-LD export structure and format."""

    def test_jsonld_export_has_context(self, notebook_service):
        """Test that JSON-LD export includes @context."""
        notebook = Notebook(
            id=uuid4(),
            title="Test Notebook",
            description="Test",
            author="Test Author"
        )

        cell = Cell(
            id=uuid4(),
            cell_type=CellType.PROMPT,
            prompt="Load data.csv",
            code="import pandas as pd"
        )
        notebook.cells.append(cell)

        notebook_service._notebooks[str(notebook.id)] = notebook

        jsonld_str = notebook_service.export_notebook(str(notebook.id), format="jsonld")
        jsonld = json.loads(jsonld_str)

        assert "@context" in jsonld
        context = jsonld["@context"]
        assert "dcterms" in context
        assert "schema" in context
        assert "prov" in context
        assert "da" in context

    def test_jsonld_export_has_graph(self, notebook_service):
        """Test that JSON-LD export includes @graph."""
        notebook = Notebook(id=uuid4(), title="Test")
        cell = Cell(id=uuid4(), cell_type=CellType.PROMPT, prompt="Test")
        notebook.cells.append(cell)

        notebook_service._notebooks[str(notebook.id)] = notebook

        jsonld_str = notebook_service.export_notebook(str(notebook.id), format="jsonld")
        jsonld = json.loads(jsonld_str)

        assert "@graph" in jsonld
        assert isinstance(jsonld["@graph"], list)

    def test_jsonld_export_includes_triples(self, notebook_service):
        """Test that JSON-LD export includes triples."""
        notebook = Notebook(id=uuid4(), title="Test")
        cell = Cell(
            id=uuid4(),
            cell_type=CellType.PROMPT,
            prompt="Load data.csv",
            code="import pandas as pd"
        )
        notebook.cells.append(cell)

        notebook_service._notebooks[str(notebook.id)] = notebook

        jsonld_str = notebook_service.export_notebook(str(notebook.id), format="jsonld")
        jsonld = json.loads(jsonld_str)

        assert "triples" in jsonld
        assert isinstance(jsonld["triples"], list)

    def test_jsonld_export_includes_metadata(self, notebook_service):
        """Test that JSON-LD export includes comprehensive metadata."""
        notebook = Notebook(
            id=uuid4(),
            title="Gene Expression Analysis",
            description="Analysis of gene expression patterns",
            author="Dr. Scientist"
        )
        cell = Cell(id=uuid4(), cell_type=CellType.PROMPT, prompt="Test")
        notebook.cells.append(cell)

        notebook_service._notebooks[str(notebook.id)] = notebook

        jsonld_str = notebook_service.export_notebook(str(notebook.id), format="jsonld")
        jsonld = json.loads(jsonld_str)

        assert "metadata" in jsonld
        metadata = jsonld["metadata"]

        assert "notebook" in metadata
        assert metadata["notebook"]["title"] == "Gene Expression Analysis"
        assert metadata["notebook"]["author"] == "Dr. Scientist"

        assert "semantic_summary" in metadata


class TestSemanticSummary:
    """Test semantic summary in JSON-LD export."""

    def test_semantic_summary_lists_datasets(self, notebook_service):
        """Test that semantic summary includes datasets used."""
        notebook = Notebook(id=uuid4(), title="Test")

        cell1 = Cell(
            id=uuid4(),
            cell_type=CellType.PROMPT,
            prompt="Load gene_expression.csv",
            code="import pandas as pd\ndf = pd.read_csv('gene_expression.csv')"
        )
        cell2 = Cell(
            id=uuid4(),
            cell_type=CellType.PROMPT,
            prompt="Load metadata.xlsx",
            code="meta = pd.read_excel('metadata.xlsx')"
        )
        notebook.cells.extend([cell1, cell2])

        notebook_service._notebooks[str(notebook.id)] = notebook

        jsonld_str = notebook_service.export_notebook(str(notebook.id), format="jsonld")
        jsonld = json.loads(jsonld_str)

        summary = jsonld["metadata"]["semantic_summary"]
        assert "datasets_used" in summary
        assert "gene_expression.csv" in summary["datasets_used"]
        assert "metadata.xlsx" in summary["datasets_used"]

    def test_semantic_summary_lists_libraries(self, notebook_service):
        """Test that semantic summary includes libraries used."""
        notebook = Notebook(id=uuid4(), title="Test")

        cell = Cell(
            id=uuid4(),
            cell_type=CellType.PROMPT,
            prompt="Analyze data",
            code="""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
"""
        )
        notebook.cells.append(cell)

        notebook_service._notebooks[str(notebook.id)] = notebook

        jsonld_str = notebook_service.export_notebook(str(notebook.id), format="jsonld")
        jsonld = json.loads(jsonld_str)

        summary = jsonld["metadata"]["semantic_summary"]
        assert "libraries_used" in summary
        assert "pandas" in summary["libraries_used"]
        assert "numpy" in summary["libraries_used"]
        assert "matplotlib" in summary["libraries_used"]

    def test_semantic_summary_lists_methods(self, notebook_service):
        """Test that semantic summary includes statistical methods."""
        notebook = Notebook(id=uuid4(), title="Test")

        cell1 = Cell(
            id=uuid4(),
            cell_type=CellType.PROMPT,
            prompt="Create histogram",
            code="plt.hist(data, bins=50)"
        )
        cell2 = Cell(
            id=uuid4(),
            cell_type=CellType.PROMPT,
            prompt="Run t-test",
            code="from scipy.stats import ttest_ind\nttest_ind(g1, g2)"
        )
        notebook.cells.extend([cell1, cell2])

        notebook_service._notebooks[str(notebook.id)] = notebook

        jsonld_str = notebook_service.export_notebook(str(notebook.id), format="jsonld")
        jsonld = json.loads(jsonld_str)

        summary = jsonld["metadata"]["semantic_summary"]
        assert "methods_used" in summary
        assert "histogram" in summary["methods_used"]
        assert "t_test" in summary["methods_used"]


class TestCellSemantics:
    """Test cell-level semantics in JSON-LD export."""

    def test_cells_include_semantic_annotations(self, notebook_service):
        """Test that cells include semantic annotations."""
        notebook = Notebook(id=uuid4(), title="Test")

        cell = Cell(
            id=uuid4(),
            cell_type=CellType.PROMPT,
            prompt="Load data.csv and calculate mean",
            code="import pandas as pd\ndf = pd.read_csv('data.csv')\nprint(df.mean())"
        )
        notebook.cells.append(cell)

        notebook_service._notebooks[str(notebook.id)] = notebook

        jsonld_str = notebook_service.export_notebook(str(notebook.id), format="jsonld")
        jsonld = json.loads(jsonld_str)

        cells = jsonld["cells"]
        assert len(cells) > 0

        cell_data = cells[0]
        assert "semantics" in cell_data
        semantics = cell_data["semantics"]

        assert "intent_tags" in semantics
        assert "libraries_used" in semantics
        assert "datasets_used" in semantics
        assert "entity_count" in semantics
        assert "triple_count" in semantics

    def test_cell_semantics_include_intent_tags(self, notebook_service):
        """Test that cell semantics include extracted intent tags."""
        notebook = Notebook(id=uuid4(), title="Test")

        cell = Cell(
            id=uuid4(),
            cell_type=CellType.PROMPT,
            prompt="Load patient_data.csv and create a scatter plot",
            code="import pandas as pd\nimport matplotlib.pyplot as plt"
        )
        notebook.cells.append(cell)

        notebook_service._notebooks[str(notebook.id)] = notebook

        jsonld_str = notebook_service.export_notebook(str(notebook.id), format="jsonld")
        jsonld = json.loads(jsonld_str)

        cell_semantics = jsonld["cells"][0]["semantics"]
        assert "data_loading" in cell_semantics["intent_tags"]
        assert "visualization" in cell_semantics["intent_tags"]

    def test_cell_content_preserved(self, notebook_service):
        """Test that cell content is preserved in JSON-LD export."""
        notebook = Notebook(id=uuid4(), title="Test")

        test_prompt = "Analyze gene expression data"
        test_code = "import pandas as pd\ndf = pd.read_csv('data.csv')"

        cell = Cell(
            id=uuid4(),
            cell_type=CellType.PROMPT,
            prompt=test_prompt,
            code=test_code
        )
        notebook.cells.append(cell)

        notebook_service._notebooks[str(notebook.id)] = notebook

        jsonld_str = notebook_service.export_notebook(str(notebook.id), format="jsonld")
        jsonld = json.loads(jsonld_str)

        cell_data = jsonld["cells"][0]
        assert cell_data["content"]["prompt"] == test_prompt
        assert cell_data["content"]["code"] == test_code


class TestGraphEntities:
    """Test entity representation in @graph."""

    def test_graph_includes_notebook_entity(self, notebook_service):
        """Test that @graph includes notebook as an entity."""
        notebook = Notebook(
            id=uuid4(),
            title="Test Notebook",
            description="A test notebook"
        )
        cell = Cell(id=uuid4(), cell_type=CellType.PROMPT, prompt="Test")
        notebook.cells.append(cell)

        notebook_service._notebooks[str(notebook.id)] = notebook

        jsonld_str = notebook_service.export_notebook(str(notebook.id), format="jsonld")
        jsonld = json.loads(jsonld_str)

        graph = jsonld["@graph"]
        # Should have notebook entity
        notebook_entities = [
            node for node in graph
            if "@type" in node and "Notebook" in node["@type"]
        ]
        assert len(notebook_entities) > 0

    def test_graph_includes_cell_entities(self, notebook_service):
        """Test that @graph includes cell entities."""
        notebook = Notebook(id=uuid4(), title="Test")

        cell = Cell(
            id=uuid4(),
            cell_type=CellType.PROMPT,
            prompt="Test prompt",
            code="import pandas as pd"
        )
        notebook.cells.append(cell)

        notebook_service._notebooks[str(notebook.id)] = notebook

        jsonld_str = notebook_service.export_notebook(str(notebook.id), format="jsonld")
        jsonld = json.loads(jsonld_str)

        graph = jsonld["@graph"]
        # Should have cell entity
        cell_entities = [
            node for node in graph
            if "@type" in node and "Cell" in node["@type"]
        ]
        assert len(cell_entities) > 0

    def test_graph_includes_library_entities(self, notebook_service):
        """Test that @graph includes library entities."""
        notebook = Notebook(id=uuid4(), title="Test")

        cell = Cell(
            id=uuid4(),
            cell_type=CellType.PROMPT,
            prompt="Test",
            code="import pandas as pd\nimport numpy as np"
        )
        notebook.cells.append(cell)

        notebook_service._notebooks[str(notebook.id)] = notebook

        jsonld_str = notebook_service.export_notebook(str(notebook.id), format="jsonld")
        jsonld = json.loads(jsonld_str)

        graph = jsonld["@graph"]
        # Should have library entities
        library_entities = [
            node for node in graph
            if "@type" in node and "Library" in node["@type"]
        ]
        assert len(library_entities) > 0


class TestFormatAliases:
    """Test that 'semantic' format is an alias for 'jsonld'."""

    def test_semantic_format_works(self, notebook_service):
        """Test that format='semantic' works as alias."""
        notebook = Notebook(id=uuid4(), title="Test")
        cell = Cell(id=uuid4(), cell_type=CellType.PROMPT, prompt="Test")
        notebook.cells.append(cell)

        notebook_service._notebooks[str(notebook.id)] = notebook

        # Both formats should work
        jsonld = notebook_service.export_notebook(str(notebook.id), format="jsonld")
        semantic = notebook_service.export_notebook(str(notebook.id), format="semantic")

        # Both should be valid JSON
        jsonld_data = json.loads(jsonld)
        semantic_data = json.loads(semantic)

        # Both should have same structure
        assert "@context" in jsonld_data
        assert "@context" in semantic_data


class TestErrorHandling:
    """Test error handling in JSON-LD export."""

    def test_export_gracefully_handles_empty_notebook(self, notebook_service):
        """Test that export works with empty notebook."""
        notebook = Notebook(id=uuid4(), title="Empty Notebook")
        # No cells

        notebook_service._notebooks[str(notebook.id)] = notebook

        jsonld_str = notebook_service.export_notebook(str(notebook.id), format="jsonld")
        jsonld = json.loads(jsonld_str)

        # Should still have valid structure
        assert "@context" in jsonld
        assert "cells" in jsonld
        assert len(jsonld["cells"]) == 0

    def test_export_handles_nonexistent_notebook(self, notebook_service):
        """Test that export returns None for nonexistent notebook."""
        result = notebook_service.export_notebook("nonexistent-id", format="jsonld")
        assert result is None


class TestUnicodeHandling:
    """Test handling of Unicode characters in JSON-LD export."""

    def test_export_preserves_unicode_in_prompts(self, notebook_service):
        """Test that Unicode characters are preserved in export."""
        notebook = Notebook(
            id=uuid4(),
            title="Análise de Dados",  # Portuguese
            description="分析データ"  # Japanese
        )

        cell = Cell(
            id=uuid4(),
            cell_type=CellType.PROMPT,
            prompt="Load données.csv",  # French
            code="import pandas as pd"
        )
        notebook.cells.append(cell)

        notebook_service._notebooks[str(notebook.id)] = notebook

        jsonld_str = notebook_service.export_notebook(str(notebook.id), format="jsonld")
        jsonld = json.loads(jsonld_str)

        # Unicode should be preserved
        assert jsonld["metadata"]["notebook"]["title"] == "Análise de Dados"
        assert jsonld["metadata"]["notebook"]["description"] == "分析データ"
        assert jsonld["cells"][0]["content"]["prompt"] == "Load données.csv"


class TestExportIntegrity:
    """Test data integrity in JSON-LD export."""

    def test_export_is_valid_json(self, notebook_service):
        """Test that export produces valid JSON."""
        notebook = Notebook(id=uuid4(), title="Test")
        cell = Cell(
            id=uuid4(),
            cell_type=CellType.PROMPT,
            prompt="Test",
            code="import pandas as pd"
        )
        notebook.cells.append(cell)

        notebook_service._notebooks[str(notebook.id)] = notebook

        jsonld_str = notebook_service.export_notebook(str(notebook.id), format="jsonld")

        # Should not raise exception
        jsonld = json.loads(jsonld_str)
        assert isinstance(jsonld, dict)

    def test_export_has_all_required_fields(self, notebook_service):
        """Test that export includes all required fields."""
        notebook = Notebook(id=uuid4(), title="Test")
        cell = Cell(id=uuid4(), cell_type=CellType.PROMPT, prompt="Test")
        notebook.cells.append(cell)

        notebook_service._notebooks[str(notebook.id)] = notebook

        jsonld_str = notebook_service.export_notebook(str(notebook.id), format="jsonld")
        jsonld = json.loads(jsonld_str)

        # Required top-level fields
        assert "@context" in jsonld
        assert "@graph" in jsonld
        assert "metadata" in jsonld
        assert "cells" in jsonld
        assert "triples" in jsonld

        # Required metadata fields
        metadata = jsonld["metadata"]
        assert "digital_article" in metadata
        assert "notebook" in metadata
        assert "semantic_summary" in metadata


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
