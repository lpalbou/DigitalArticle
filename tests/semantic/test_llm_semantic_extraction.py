"""
Tests for LLM-based semantic extraction.

Tests the LLM semantic extractor's ability to extract rich semantic information
including data assets, transformations, refined assets, and outcomes.
"""

import pytest
from datetime import datetime
from uuid import uuid4

from backend.app.models.notebook import Notebook, Cell, CellType, ExecutionResult, ExecutionStatus
from backend.app.models.semantics import (
    EntityType, AssetMetadata, ConfidentialityLevel, SemanticEntity
)
from backend.app.services.llm_semantic_extractor import LLMSemanticExtractor


@pytest.fixture
def sample_notebook():
    """Create a sample notebook for testing."""
    return Notebook(
        id=uuid4(),
        title="Test Analysis Notebook",
        description="A test notebook for semantic extraction",
        author="Test User",
        cells=[],
        llm_provider="lmstudio",
        llm_model="qwen/qwen3-next-80b",
        created_at=datetime.now(),
        updated_at=datetime.now()
    )


@pytest.fixture
def data_loading_cell():
    """Create a cell that loads data."""
    return Cell(
        id=uuid4(),
        cell_type=CellType.PROMPT,
        prompt="Load the patient_data.csv file and display basic statistics",
        code="import pandas as pd\ndf = pd.read_csv('patient_data.csv')\nprint(df.describe())",
        scientific_explanation="Data loading and initial exploratory analysis",
        last_result=ExecutionResult(
            stdout="count    100\nmean     45.3\nstd      12.5",
            status=ExecutionStatus.SUCCESS
        ),
        created_at=datetime.now()
    )


@pytest.fixture
def transformation_cell():
    """Create a cell that transforms data."""
    return Cell(
        id=uuid4(),
        cell_type=CellType.PROMPT,
        prompt="Normalize the age column using z-score normalization",
        code="from sklearn.preprocessing import StandardScaler\nscaler = StandardScaler()\ndf['age_normalized'] = scaler.fit_transform(df[['age']])",
        scientific_explanation="Z-score normalization to standardize age distribution for statistical analysis",
        last_result=ExecutionResult(
            stdout="Normalization complete",
            status=ExecutionStatus.SUCCESS
        ),
        created_at=datetime.now()
    )


class TestLLMSemanticExtractor:
    """Test suite for LLM semantic extractor."""

    def test_extractor_initialization(self):
        """Test that extractor initializes correctly."""
        extractor = LLMSemanticExtractor(provider="lmstudio", model="test-model")
        assert extractor is not None
        assert extractor.provider == "lmstudio"
        assert extractor.model == "test-model"

    def test_empty_extraction_on_llm_failure(self, sample_notebook, data_loading_cell):
        """Test that empty extraction is returned when LLM is not available."""
        # Initialize without LLM
        extractor = LLMSemanticExtractor(provider="invalid", model="invalid")
        extractor.llm = None  # Ensure LLM is None

        result = extractor.extract_rich_semantics(data_loading_cell, sample_notebook)

        # Should return empty extraction
        assert result["data_assets"] == []
        assert result["transformations"] == []
        assert result["refined_assets"] == []
        assert result["outcomes"] == []
        assert result["relationships"] == []

    def test_build_extraction_context(self, sample_notebook, data_loading_cell):
        """Test context building for extraction."""
        extractor = LLMSemanticExtractor(provider="lmstudio", model="test")

        context = extractor._build_extraction_context(
            data_loading_cell,
            sample_notebook,
            previous_cells=None
        )

        assert context["notebook_title"] == "Test Analysis Notebook"
        assert context["cell_id"] == str(data_loading_cell.id)
        assert context["prompt"] == data_loading_cell.prompt
        assert context["code"] == data_loading_cell.code
        assert context["scientific_explanation"] == data_loading_cell.scientific_explanation
        assert context["stdout"] == "count    100\nmean     45.3\nstd      12.5"

    def test_build_extraction_context_with_previous_cells(
        self,
        sample_notebook,
        data_loading_cell,
        transformation_cell
    ):
        """Test context building includes information from previous cells."""
        extractor = LLMSemanticExtractor(provider="lmstudio", model="test")

        context = extractor._build_extraction_context(
            transformation_cell,
            sample_notebook,
            previous_cells=[data_loading_cell]
        )

        # Should extract variables from previous cell
        assert "previous_variables" in context
        assert "df" in context["previous_variables"]

        # Should extract datasets from previous cell
        assert "previous_datasets" in context
        assert "patient_data.csv" in context["previous_datasets"]

    def test_parse_extraction_response_valid_json(
        self,
        sample_notebook,
        data_loading_cell
    ):
        """Test parsing of valid JSON extraction response."""
        extractor = LLMSemanticExtractor(provider="lmstudio", model="test")

        mock_response = '''
{
  "data_assets": [
    {
      "label": "Patient Data CSV",
      "type": "dcat:Dataset",
      "identifier": "patient_data.csv",
      "description": "Patient demographic and clinical data",
      "confidentiality": "C3"
    }
  ],
  "transformations": [
    {
      "label": "Data Loading",
      "method": "CSV import",
      "library": "pandas",
      "methodology": "Standard data import for exploratory analysis",
      "input_assets": ["patient_data.csv"],
      "output_assets": ["df"]
    }
  ],
  "refined_assets": [
    {
      "label": "Patient DataFrame",
      "type": "da:Variable",
      "identifier": "df",
      "description": "Loaded patient data as pandas DataFrame",
      "derived_from": ["patient_data.csv"]
    }
  ],
  "outcomes": [
    {
      "label": "Basic Statistics",
      "type": "da:Finding",
      "description": "Descriptive statistics of the dataset",
      "value": "mean: 45.3, std: 12.5",
      "derived_from": ["df"]
    }
  ]
}
        '''

        result = extractor._parse_extraction_response(
            mock_response,
            data_loading_cell,
            sample_notebook
        )

        # Verify data assets
        assert len(result["data_assets"]) == 1
        assert result["data_assets"][0].label == "Patient Data CSV"
        assert result["data_assets"][0].type == EntityType.DATASET
        assert result["data_assets"][0].metadata.confidentiality == ConfidentialityLevel.C3_CONFIDENTIAL

        # Verify transformations
        assert len(result["transformations"]) == 1
        assert result["transformations"][0].label == "Data Loading"
        assert result["transformations"][0].type == EntityType.TRANSFORMATION

        # Verify refined assets
        assert len(result["refined_assets"]) == 1
        assert result["refined_assets"][0].label == "Patient DataFrame"
        assert result["refined_assets"][0].type == EntityType.REFINED_ASSET

        # Verify outcomes
        assert len(result["outcomes"]) == 1
        assert result["outcomes"][0].label == "Basic Statistics"
        assert result["outcomes"][0].type == EntityType.FINDING

        # Verify relationships exist
        assert len(result["relationships"]) > 0

    def test_parse_extraction_response_with_markdown_code_block(
        self,
        sample_notebook,
        data_loading_cell
    ):
        """Test parsing response wrapped in markdown code block."""
        extractor = LLMSemanticExtractor(provider="lmstudio", model="test")

        mock_response = '''```json
{
  "data_assets": [],
  "transformations": [],
  "refined_assets": [],
  "outcomes": []
}
```'''

        result = extractor._parse_extraction_response(
            mock_response,
            data_loading_cell,
            sample_notebook
        )

        # Should successfully parse despite markdown wrapper
        assert result["data_assets"] == []
        assert result["transformations"] == []
        assert result["refined_assets"] == []
        assert result["outcomes"] == []

    def test_parse_extraction_response_invalid_json(
        self,
        sample_notebook,
        data_loading_cell
    ):
        """Test handling of invalid JSON response."""
        extractor = LLMSemanticExtractor(provider="lmstudio", model="test")

        mock_response = "This is not valid JSON"

        result = extractor._parse_extraction_response(
            mock_response,
            data_loading_cell,
            sample_notebook
        )

        # Should return empty extraction on JSON parse error
        assert result["data_assets"] == []
        assert result["transformations"] == []
        assert result["refined_assets"] == []
        assert result["outcomes"] == []
        assert result["relationships"] == []

    def test_create_asset_entities(self, sample_notebook, data_loading_cell):
        """Test creation of asset entities with rich metadata."""
        extractor = LLMSemanticExtractor(provider="lmstudio", model="test")

        assets_data = [
            {
                "label": "Test Dataset",
                "type": "dcat:Dataset",
                "identifier": "test.csv",
                "description": "A test dataset",
                "confidentiality": "C2",
                "derived_from": ["source1.csv"]
            }
        ]

        entities = extractor._create_asset_entities(
            assets_data,
            data_loading_cell,
            sample_notebook,
            EntityType.DATASET
        )

        assert len(entities) == 1
        assert entities[0].label == "Test Dataset"
        assert entities[0].type == EntityType.DATASET
        assert entities[0].metadata is not None
        assert entities[0].metadata.label == "Test Dataset"
        assert entities[0].metadata.asset_type == "dcat:Dataset"
        assert entities[0].metadata.confidentiality == ConfidentialityLevel.C2_INTERNAL
        assert entities[0].metadata.owner == "Test User"
        assert len(entities[0].metadata.provenance) == 1

    def test_create_transformation_entities(self, transformation_cell):
        """Test creation of transformation entities."""
        extractor = LLMSemanticExtractor(provider="lmstudio", model="test")

        transformations_data = [
            {
                "label": "Z-Score Normalization",
                "method": "StandardScaler",
                "library": "sklearn",
                "methodology": "Standardization using z-scores",
                "input_assets": ["df"],
                "output_assets": ["age_normalized"]
            }
        ]

        entities = extractor._create_transformation_entities(
            transformations_data,
            transformation_cell
        )

        assert len(entities) == 1
        assert entities[0].label == "Z-Score Normalization"
        assert entities[0].type == EntityType.TRANSFORMATION
        assert entities[0].properties["da:method"] == "StandardScaler"
        assert entities[0].properties["da:library"] == "sklearn"
        assert entities[0].properties["da:methodology"] == "Standardization using z-scores"

    def test_create_relationships(self, data_loading_cell):
        """Test creation of provenance relationships."""
        extractor = LLMSemanticExtractor(provider="lmstudio", model="test")

        extraction_data = {
            "transformations": [
                {
                    "label": "Test Transform",
                    "input_assets": ["input1", "input2"],
                    "output_assets": ["output1"]
                }
            ],
            "refined_assets": [
                {
                    "identifier": "refined1",
                    "derived_from": ["source1", "source2"]
                }
            ],
            "outcomes": [
                {
                    "type": "da:Finding",
                    "derived_from": ["refined1"]
                }
            ]
        }

        relationships = extractor._create_relationships(
            extraction_data,
            data_loading_cell
        )

        # Should create relationships for:
        # - Transformation uses inputs (2)
        # - Transformation generates outputs (1)
        # - Refined asset derived from sources (2)
        # - Outcome derived from refined asset (1)
        assert len(relationships) >= 6

        # Check some relationships
        used_rels = [r for r in relationships if r.predicate == "prov:used"]
        assert len(used_rels) >= 2

        derived_rels = [r for r in relationships if r.predicate == "prov:wasDerivedFrom"]
        assert len(derived_rels) >= 3


class TestAssetMetadata:
    """Test asset metadata model."""

    def test_asset_metadata_creation(self):
        """Test creating asset metadata with all fields."""
        metadata = AssetMetadata(
            label="Test Asset",
            asset_type="dcat:Dataset",
            confidentiality=ConfidentialityLevel.C3_CONFIDENTIAL,
            owner="test_user",
            description="A test asset",
            provenance=["source1", "source2"]
        )

        assert metadata.label == "Test Asset"
        assert metadata.asset_type == "dcat:Dataset"
        assert metadata.confidentiality == ConfidentialityLevel.C3_CONFIDENTIAL
        assert metadata.owner == "test_user"
        assert metadata.description == "A test asset"
        assert len(metadata.provenance) == 2

    def test_asset_metadata_to_dict(self):
        """Test converting metadata to dictionary."""
        metadata = AssetMetadata(
            label="Test Asset",
            asset_type="dcat:Dataset",
            confidentiality=ConfidentialityLevel.C2_INTERNAL,
            owner="test_user",
            description="Test description",
            provenance=["source1"]
        )

        metadata_dict = metadata.to_dict()

        assert metadata_dict["rdfs:label"] == "Test Asset"
        assert metadata_dict["rdf:type"] == "dcat:Dataset"
        assert metadata_dict["da:confidentiality"] == "C2"
        assert metadata_dict["dcterms:creator"] == "test_user"
        assert metadata_dict["dcterms:description"] == "Test description"
        assert metadata_dict["prov:wasDerivedFrom"] == ["source1"]

    def test_confidentiality_levels(self):
        """Test all confidentiality levels."""
        levels = [
            (ConfidentialityLevel.C1_PUBLIC, "C1"),
            (ConfidentialityLevel.C2_INTERNAL, "C2"),
            (ConfidentialityLevel.C3_CONFIDENTIAL, "C3"),
            (ConfidentialityLevel.C4_RESTRICTED, "C4"),
        ]

        for level, expected_value in levels:
            metadata = AssetMetadata(
                label="Test",
                asset_type="dcat:Dataset",
                confidentiality=level
            )
            assert metadata.confidentiality.value == expected_value


class TestSemanticEntityWithMetadata:
    """Test semantic entity with rich metadata."""

    def test_entity_with_metadata_to_jsonld(self):
        """Test entity with metadata converts to proper JSON-LD."""
        metadata = AssetMetadata(
            label="Patient Data",
            asset_type="dcat:Dataset",
            confidentiality=ConfidentialityLevel.C3_CONFIDENTIAL,
            owner="researcher1",
            description="Clinical trial data",
            provenance=["raw_data.csv"]
        )

        entity = SemanticEntity(
            id="dataset:patient_data.csv",
            type=EntityType.DATASET,
            label="Patient Data",
            metadata=metadata,
            properties={"da:fileFormat": "CSV"}
        )

        jsonld = entity.to_jsonld()

        # Check basic structure
        assert jsonld["@id"] == "dataset:patient_data.csv"
        assert jsonld["@type"] == "da:Dataset"
        assert jsonld["rdfs:label"] == "Patient Data"

        # Check metadata was included
        assert jsonld["rdf:type"] == "dcat:Dataset"
        assert jsonld["da:confidentiality"] == "C3"
        assert jsonld["dcterms:creator"] == "researcher1"
        assert jsonld["dcterms:description"] == "Clinical trial data"
        assert jsonld["prov:wasDerivedFrom"] == ["raw_data.csv"]

        # Check properties were included
        assert jsonld["da:fileFormat"] == "CSV"

    def test_entity_without_metadata_to_jsonld(self):
        """Test entity without metadata still works."""
        entity = SemanticEntity(
            id="cell:123",
            type=EntityType.CELL,
            label="Test Cell",
            properties={"da:executionOrder": 1}
        )

        jsonld = entity.to_jsonld()

        assert jsonld["@id"] == "cell:123"
        assert jsonld["@type"] == "da:Cell"
        assert jsonld["rdfs:label"] == "Test Cell"
        assert jsonld["da:executionOrder"] == 1
        # Should not have metadata fields
        assert "rdf:type" not in jsonld or jsonld["rdf:type"] == jsonld["@type"]
