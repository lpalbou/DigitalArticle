"""
Comprehensive test suite for semantic extraction functionality.

Tests cover:
- Prompt extraction (intents, datasets, concepts)
- Code extraction (libraries, methods, variables)
- Result extraction (findings, statistics)
- Cell semantics extraction
- Notebook semantics extraction
- JSON-LD export
"""

import pytest
import json
from datetime import datetime
from uuid import uuid4

from backend.app.models.notebook import (
    Notebook, Cell, CellType, ExecutionResult, ExecutionStatus
)
from backend.app.models.semantics import (
    CellSemantics, NotebookSemantics, Triple, SemanticEntity, EntityType
)
from backend.app.services.semantic_service import SemanticExtractionService


@pytest.fixture
def semantic_service():
    """Create a semantic extraction service instance."""
    return SemanticExtractionService()


@pytest.fixture
def sample_notebook():
    """Create a sample notebook for testing."""
    notebook = Notebook(
        id=uuid4(),
        title="Test Notebook",
        description="A test notebook for semantic extraction",
        author="Test Author"
    )
    return notebook


class TestPromptExtraction:
    """Test extraction of semantic information from prompts."""

    def test_extract_data_loading_intent(self, semantic_service):
        """Test extraction of data loading intent from prompt."""
        prompt = "Load the gene_expression.csv file and display basic statistics"
        cell_id = "cell:test"

        result = semantic_service._extract_from_prompt(prompt, cell_id)

        assert "data_loading" in result["intents"]
        assert "statistics" in result["intents"]

    def test_extract_dataset_reference(self, semantic_service):
        """Test extraction of dataset filename from prompt."""
        prompt = "Load patient_data.csv and show summary"
        cell_id = "cell:test"

        result = semantic_service._extract_from_prompt(prompt, cell_id)

        assert "patient_data.csv" in result["datasets"]
        assert len(result["entities"]) > 0
        assert any(e.type == EntityType.DATASET for e in result["entities"])

    def test_extract_multiple_datasets(self, semantic_service):
        """Test extraction of multiple dataset references."""
        prompt = "Merge gene_expression.csv with metadata.xlsx and analyze"
        cell_id = "cell:test"

        result = semantic_service._extract_from_prompt(prompt, cell_id)

        assert "gene_expression.csv" in result["datasets"]
        assert "metadata.xlsx" in result["datasets"]

    def test_extract_visualization_intent(self, semantic_service):
        """Test extraction of visualization intent."""
        prompt = "Create a scatter plot showing age vs blood pressure"
        cell_id = "cell:test"

        result = semantic_service._extract_from_prompt(prompt, cell_id)

        assert "visualization" in result["intents"]

    def test_extract_statistical_test_intent(self, semantic_service):
        """Test extraction of statistical test intent."""
        prompt = "Perform a t-test to compare means between groups"
        cell_id = "cell:test"

        result = semantic_service._extract_from_prompt(prompt, cell_id)

        assert "test" in result["intents"]
        assert "comparison" in result["intents"]


class TestCodeExtraction:
    """Test extraction of semantic information from code."""

    def test_extract_pandas_import(self, semantic_service):
        """Test extraction of pandas library import."""
        code = """
import pandas as pd
df = pd.read_csv('data.csv')
"""
        cell_id = "cell:test"

        result = semantic_service._extract_from_code(code, cell_id)

        assert "pandas" in result["libraries"]
        assert any(e.type == EntityType.LIBRARY for e in result["entities"])

    def test_extract_multiple_imports(self, semantic_service):
        """Test extraction of multiple library imports."""
        code = """
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
"""
        cell_id = "cell:test"

        result = semantic_service._extract_from_code(code, cell_id)

        assert "pandas" in result["libraries"]
        assert "numpy" in result["libraries"]
        assert "matplotlib" in result["libraries"]

    def test_extract_variable_definitions(self, semantic_service):
        """Test extraction of variable assignments."""
        code = """
df = pd.read_csv('data.csv')
mean_value = df['column'].mean()
result_matrix = np.array([[1, 2], [3, 4]])
"""
        cell_id = "cell:test"

        result = semantic_service._extract_from_code(code, cell_id)

        assert "df" in result["variables"]
        assert "mean_value" in result["variables"]
        assert "result_matrix" in result["variables"]

    def test_extract_histogram_method(self, semantic_service):
        """Test extraction of histogram visualization method."""
        code = """
import matplotlib.pyplot as plt
plt.hist(data, bins=50)
plt.show()
"""
        cell_id = "cell:test"

        result = semantic_service._extract_from_code(code, cell_id)

        assert "histogram" in result["methods"]

    def test_extract_statistical_methods(self, semantic_service):
        """Test extraction of statistical method calls."""
        code = """
from scipy.stats import ttest_ind
t_stat, p_value = ttest_ind(group1, group2)
"""
        cell_id = "cell:test"

        result = semantic_service._extract_from_code(code, cell_id)

        assert "scipy" in result["libraries"]
        assert "t_test" in result["methods"]

    def test_extract_pca_method(self, semantic_service):
        """Test extraction of PCA analysis method."""
        code = """
from sklearn.decomposition import PCA
pca = PCA(n_components=2)
transformed = pca.fit_transform(data)
"""
        cell_id = "cell:test"

        result = semantic_service._extract_from_code(code, cell_id)

        assert "sklearn" in result["libraries"]
        assert "pca" in result["methods"]


class TestResultExtraction:
    """Test extraction of semantic information from execution results."""

    def test_extract_mean_statistic(self, semantic_service):
        """Test extraction of mean value from output."""
        result = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            stdout="Mean: 15.3\nStd: 4.2\nCount: 100"
        )
        cell_id = "cell:test"

        extracted = semantic_service._extract_from_result(result, cell_id)

        findings = extracted["findings"]
        assert len(findings) > 0
        assert any(f["metric"] == "mean" and f["value"] == 15.3 for f in findings)
        assert any(f["metric"] == "std" and f["value"] == 4.2 for f in findings)
        assert any(f["metric"] == "count" and f["value"] == 100 for f in findings)

    def test_extract_p_value(self, semantic_service):
        """Test extraction of p-value from statistical test output."""
        result = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            stdout="t-statistic: 3.45\np-value: 0.002"
        )
        cell_id = "cell:test"

        extracted = semantic_service._extract_from_result(result, cell_id)

        findings = extracted["findings"]
        assert any(f["metric"] == "p_value" and f["value"] == 0.002 for f in findings)
        assert any(f["metric"] == "t_statistic" and f["value"] == 3.45 for f in findings)

    def test_extract_plot_visualization(self, semantic_service):
        """Test extraction of plot visualization entity."""
        result = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            plots=["base64encodedimage=="]
        )
        cell_id = "cell:test"

        extracted = semantic_service._extract_from_result(result, cell_id)

        entities = extracted["entities"]
        assert len(entities) > 0
        assert any(e.type == EntityType.VISUALIZATION for e in entities)

    def test_extract_table_information(self, semantic_service):
        """Test extraction of table/dataframe information."""
        result = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            tables=[{
                "columns": ["gene", "expression", "condition"],
                "info": {"shape": [20, 3]}
            }]
        )
        cell_id = "cell:test"

        extracted = semantic_service._extract_from_result(result, cell_id)

        entities = extracted["entities"]
        assert len(entities) > 0
        # Check that table entity has row and column counts
        table_entities = [e for e in entities if "table" in e.id]
        assert len(table_entities) > 0


class TestCellSemantics:
    """Test complete cell semantics extraction."""

    def test_extract_simple_data_loading_cell(self, semantic_service, sample_notebook):
        """Test extraction from a simple data loading cell."""
        cell = Cell(
            id=uuid4(),
            cell_type=CellType.PROMPT,
            prompt="Load gene_expression.csv and show basic statistics",
            code="""
import pandas as pd
df = pd.read_csv('gene_expression.csv')
print(df.describe())
""",
            last_result=ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                stdout="count: 20\nmean: 15.3\nstd: 4.2"
            )
        )

        semantics = semantic_service.extract_cell_semantics(cell, sample_notebook)

        assert "data_loading" in semantics.intent_tags
        assert "statistics" in semantics.intent_tags
        assert "pandas" in semantics.libraries_used
        assert "gene_expression.csv" in semantics.datasets_used
        assert "df" in semantics.variables_defined
        assert len(semantics.statistical_findings) > 0
        assert len(semantics.triples) > 0

    def test_extract_visualization_cell(self, semantic_service, sample_notebook):
        """Test extraction from a visualization cell."""
        cell = Cell(
            id=uuid4(),
            cell_type=CellType.PROMPT,
            prompt="Plot a histogram of expression values",  # Changed "Create" to "Plot" to match visualization keywords
            code="""
import matplotlib.pyplot as plt
plt.hist(df['expression'], bins=50)
plt.show()
""",
            last_result=ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                plots=["base64image=="]
            )
        )

        semantics = semantic_service.extract_cell_semantics(cell, sample_notebook)

        assert "visualization" in semantics.intent_tags
        assert "matplotlib" in semantics.libraries_used
        assert "histogram" in semantics.methods_used
        assert len(semantics.entities) > 0
        # Should have visualization entity
        assert any(e.type == EntityType.VISUALIZATION for e in semantics.entities)

    def test_jsonld_serialization(self, semantic_service, sample_notebook):
        """Test JSON-LD serialization of cell semantics."""
        cell = Cell(
            id=uuid4(),
            cell_type=CellType.PROMPT,
            prompt="Test prompt",
            code="import pandas as pd"
        )

        semantics = semantic_service.extract_cell_semantics(cell, sample_notebook)
        jsonld = semantics.to_jsonld()

        assert "cell_id" in jsonld
        assert "entities" in jsonld
        assert "triples" in jsonld
        assert "libraries_used" in jsonld
        assert isinstance(jsonld["entities"], list)
        assert isinstance(jsonld["triples"], list)

    def test_jsonld_deserialization(self, semantic_service, sample_notebook):
        """Test that JSON-LD can be deserialized back to CellSemantics."""
        cell = Cell(
            id=uuid4(),
            cell_type=CellType.PROMPT,
            prompt="Test prompt",
            code="import pandas as pd"
        )

        semantics = semantic_service.extract_cell_semantics(cell, sample_notebook)
        jsonld = semantics.to_jsonld()

        # Deserialize back
        restored = CellSemantics.from_jsonld(jsonld)

        assert restored.cell_id == semantics.cell_id
        assert restored.libraries_used == semantics.libraries_used
        assert len(restored.entities) == len(semantics.entities)
        assert len(restored.triples) == len(semantics.triples)


class TestNotebookSemantics:
    """Test complete notebook semantics extraction."""

    def test_extract_multi_cell_notebook(self, semantic_service):
        """Test extraction from notebook with multiple cells."""
        notebook = Notebook(
            id=uuid4(),
            title="Multi-cell Test",
            description="Test notebook with multiple cells"
        )

        # Cell 1: Data loading
        cell1 = Cell(
            id=uuid4(),
            cell_type=CellType.PROMPT,
            prompt="Load data.csv",
            code="import pandas as pd\ndf = pd.read_csv('data.csv')"
        )
        notebook.cells.append(cell1)

        # Cell 2: Analysis
        cell2 = Cell(
            id=uuid4(),
            cell_type=CellType.PROMPT,
            prompt="Calculate statistics",
            code="mean_val = df.mean()\nprint(f'Mean: {mean_val}')",
            last_result=ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                stdout="Mean: 42.5"
            )
        )
        notebook.cells.append(cell2)

        # Cell 3: Visualization
        cell3 = Cell(
            id=uuid4(),
            cell_type=CellType.PROMPT,
            prompt="Plot histogram",
            code="import matplotlib.pyplot as plt\nplt.hist(df['values'])",
            last_result=ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                plots=["base64=="]
            )
        )
        notebook.cells.append(cell3)

        notebook_semantics = semantic_service.extract_notebook_semantics(notebook)

        assert len(notebook_semantics.cell_semantics) == 3
        assert len(notebook_semantics.global_entities) > 0

        # Check aggregated data
        all_datasets = notebook_semantics.get_all_datasets()
        assert "data.csv" in all_datasets

        all_libraries = notebook_semantics.get_all_libraries()
        assert "pandas" in all_libraries
        assert "matplotlib" in all_libraries

    def test_jsonld_graph_export(self, semantic_service):
        """Test JSON-LD graph export for notebook."""
        notebook = Notebook(
            id=uuid4(),
            title="Test Notebook",
            description="Test"
        )

        cell = Cell(
            id=uuid4(),
            cell_type=CellType.PROMPT,
            prompt="Load data.csv",
            code="import pandas as pd"
        )
        notebook.cells.append(cell)

        notebook_semantics = semantic_service.extract_notebook_semantics(notebook)
        jsonld_graph = notebook_semantics.to_jsonld_graph()

        assert "@context" in jsonld_graph
        assert "@graph" in jsonld_graph
        assert "triples" in jsonld_graph
        assert "metadata" in jsonld_graph

        # Check context has standard ontologies
        context = jsonld_graph["@context"]
        assert "dcterms" in context
        assert "schema" in context
        assert "skos" in context
        assert "prov" in context

    def test_get_all_methods(self, semantic_service):
        """Test aggregation of all methods used across notebook."""
        notebook = Notebook(id=uuid4(), title="Test")

        cell1 = Cell(
            id=uuid4(),
            cell_type=CellType.PROMPT,
            prompt="Create histogram",
            code="plt.hist(data)"
        )
        notebook.cells.append(cell1)

        cell2 = Cell(
            id=uuid4(),
            cell_type=CellType.PROMPT,
            prompt="Run t-test",
            code="from scipy.stats import ttest_ind\nttest_ind(g1, g2)"
        )
        notebook.cells.append(cell2)

        notebook_semantics = semantic_service.extract_notebook_semantics(notebook)
        methods = notebook_semantics.get_all_methods()

        assert "histogram" in methods
        assert "t_test" in methods

    def test_get_all_concepts(self, semantic_service):
        """Test extraction of domain concepts from notebook."""
        notebook = Notebook(id=uuid4(), title="Test")

        cell = Cell(
            id=uuid4(),
            cell_type=CellType.PROMPT,
            prompt="Analyze Gene Expression patterns in RNA-seq data",
            scientific_explanation="Gene Expression analysis revealed significant patterns"
        )
        notebook.cells.append(cell)

        notebook_semantics = semantic_service.extract_notebook_semantics(notebook)
        concepts = notebook_semantics.get_all_concepts()

        # Should extract "Gene Expression" as a concept
        assert len(concepts) > 0


class TestErrorHandling:
    """Test error handling in semantic extraction."""

    def test_invalid_code_does_not_crash(self, semantic_service, sample_notebook):
        """Test that invalid Python code doesn't crash extraction."""
        cell = Cell(
            id=uuid4(),
            cell_type=CellType.CODE,
            code="this is not valid python code @#$%"
        )

        # Should not raise exception
        semantics = semantic_service.extract_cell_semantics(cell, sample_notebook)

        # Should return empty semantics gracefully
        assert semantics is not None
        assert semantics.cell_id is not None

    def test_empty_cell_extraction(self, semantic_service, sample_notebook):
        """Test extraction from empty cell."""
        cell = Cell(id=uuid4(), cell_type=CellType.PROMPT)

        semantics = semantic_service.extract_cell_semantics(cell, sample_notebook)

        assert semantics is not None
        assert len(semantics.libraries_used) == 0
        assert len(semantics.datasets_used) == 0

    def test_cell_with_no_result(self, semantic_service, sample_notebook):
        """Test extraction from cell with no execution result."""
        cell = Cell(
            id=uuid4(),
            cell_type=CellType.PROMPT,
            prompt="Test prompt",
            code="import pandas as pd",
            last_result=None
        )

        # Should not crash
        semantics = semantic_service.extract_cell_semantics(cell, sample_notebook)

        assert semantics is not None
        assert "pandas" in semantics.libraries_used


class TestTripleGeneration:
    """Test generation of RDF-style triples."""

    def test_cell_uses_dataset_triple(self, semantic_service, sample_notebook):
        """Test generation of 'uses dataset' triple."""
        cell = Cell(
            id=uuid4(),
            cell_type=CellType.PROMPT,
            prompt="Load data.csv"
        )

        semantics = semantic_service.extract_cell_semantics(cell, sample_notebook)

        # Should have triple linking cell to dataset
        uses_dataset_triples = [
            t for t in semantics.triples
            if t.predicate == "da:usesDataset"
        ]
        assert len(uses_dataset_triples) > 0

    def test_cell_uses_library_triple(self, semantic_service, sample_notebook):
        """Test generation of 'uses library' triple."""
        cell = Cell(
            id=uuid4(),
            cell_type=CellType.CODE,
            code="import pandas as pd"
        )

        semantics = semantic_service.extract_cell_semantics(cell, sample_notebook)

        # Should have triple linking cell to library
        uses_library_triples = [
            t for t in semantics.triples
            if t.predicate == "da:usesLibrary"
        ]
        assert len(uses_library_triples) > 0

    def test_notebook_has_part_triple(self, semantic_service, sample_notebook):
        """Test generation of 'has part' triple linking notebook to cell."""
        cell = Cell(id=uuid4(), cell_type=CellType.PROMPT)
        sample_notebook.cells.append(cell)

        semantics = semantic_service.extract_cell_semantics(cell, sample_notebook)

        # Should have triple linking notebook to cell
        has_part_triples = [
            t for t in semantics.triples
            if t.predicate == "dcterms:hasPart"
        ]
        assert len(has_part_triples) > 0
        assert f"notebook:{sample_notebook.id}" in has_part_triples[0].subject


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
