"""
LLM-based semantic extraction for rich knowledge graph generation.

This service uses an LLM to extract detailed semantic information from
notebook cells, including data assets, transformations, refined assets,
and outcomes with proper provenance and metadata.
"""

import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from uuid import UUID

from abstractcore import create_llm
from ..models.notebook import Cell, Notebook
from ..models.semantics import (
    SemanticEntity, EntityType, Triple, AssetMetadata,
    ConfidentialityLevel, ONTOLOGY_CONTEXT
)

logger = logging.getLogger(__name__)


class LLMSemanticExtractor:
    """Extract rich semantic information using LLM analysis."""

    def __init__(self, provider: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize the LLM semantic extractor.

        Args:
            provider: LLM provider name (optional, will load from config if not provided)
            model: Model name (optional, will load from config if not provided)
        """
        # Load from config if not provided
        if provider is None or model is None:
            from ..config import config
            self.provider = provider or config.get_llm_provider()
            self.model = model or config.get_llm_model()
        else:
            self.provider = provider
            self.model = model

        self.llm = None
        self._initialize_llm()

    def _initialize_llm(self):
        """Initialize the LLM client."""
        try:
            self.llm = create_llm(self.provider, model=self.model)
            logger.info(f"✅ Initialized LLM semantic extractor: {self.provider}/{self.model}")
        except Exception as e:
            logger.error(f"❌ Failed to initialize LLM for semantic extraction: {e}")
            self.llm = None

    def extract_rich_semantics(
        self,
        cell: Cell,
        notebook: Notebook,
        previous_cells: Optional[List[Cell]] = None
    ) -> Dict[str, Any]:
        """
        Extract rich semantic information from a cell using LLM.

        Returns structured data with:
        - data_assets: Input datasets/files with metadata
        - transformations: Operations/methods with methodology
        - refined_assets: Intermediate outputs (variables, cleaned data)
        - outcomes: Final results (findings, visualizations, conclusions)
        - relationships: Provenance links between all entities

        Args:
            cell: The cell to analyze
            notebook: Parent notebook for context
            previous_cells: List of previous cells for context

        Returns:
            Dict with extracted entities and relationships
        """
        if not self.llm:
            logger.warning("LLM not available for semantic extraction")
            return self._empty_extraction()

        try:
            # Build context from cell and previous cells
            extraction_context = self._build_extraction_context(cell, notebook, previous_cells)

            # Create LLM prompt for semantic extraction
            system_prompt = self._build_extraction_system_prompt()
            user_prompt = self._build_extraction_user_prompt(extraction_context)

            # Call LLM
            logger.info(f"🔍 Calling LLM for semantic extraction of cell {cell.id}...")
            response = self.llm.generate(
                user_prompt,
                system_prompt=system_prompt,
                max_tokens=2000,
                temperature=0.1  # Low temperature for consistent extraction
            )

            # Parse LLM response
            extraction_result = self._parse_extraction_response(response.content, cell, notebook)

            logger.info(
                f"✅ Extracted: {len(extraction_result['data_assets'])} data assets, "
                f"{len(extraction_result['transformations'])} transformations, "
                f"{len(extraction_result['refined_assets'])} refined assets, "
                f"{len(extraction_result['outcomes'])} outcomes"
            )

            return extraction_result

        except Exception as e:
            logger.warning(f"Error in LLM semantic extraction: {e}")
            return self._empty_extraction()

    def _empty_extraction(self) -> Dict[str, Any]:
        """Return empty extraction result."""
        return {
            "data_assets": [],
            "transformations": [],
            "refined_assets": [],
            "outcomes": [],
            "relationships": []
        }

    def _build_extraction_context(
        self,
        cell: Cell,
        notebook: Notebook,
        previous_cells: Optional[List[Cell]] = None
    ) -> Dict[str, Any]:
        """Build context for LLM extraction."""
        context = {
            "notebook_title": notebook.title,
            "notebook_description": notebook.description,
            "cell_id": str(cell.id),
            "cell_type": cell.cell_type.value,
            "prompt": cell.prompt or "",
            "code": cell.code or "",
            "scientific_explanation": cell.scientific_explanation or "",
        }

        # Add execution results if available
        if cell.last_result:
            context["stdout"] = cell.last_result.stdout or ""
            context["has_plots"] = len(cell.last_result.plots) > 0 if cell.last_result.plots else False
            context["has_tables"] = len(cell.last_result.tables) > 0 if cell.last_result.tables else False

        # Add context from previous cells
        if previous_cells:
            context["previous_variables"] = []
            context["previous_datasets"] = []

            for prev_cell in previous_cells:
                # Extract variables defined in previous cells (simple extraction)
                if prev_cell.code:
                    import re
                    var_pattern = r'^(\w+)\s*='
                    vars_found = re.findall(var_pattern, prev_cell.code, re.MULTILINE)
                    context["previous_variables"].extend([v for v in vars_found if not v.startswith('_')])

                # Extract datasets from previous prompts
                if prev_cell.prompt:
                    dataset_pattern = r'\b([\w\-]+\.(?:csv|xlsx|xls|json|txt|tsv|parquet|h5|hdf5))\b'
                    datasets_found = re.findall(dataset_pattern, prev_cell.prompt.lower())
                    context["previous_datasets"].extend(datasets_found)

        return context

    def _build_extraction_system_prompt(self) -> str:
        """Build system prompt for semantic extraction."""
        return """You are a semantic knowledge extraction expert. Your task is to analyze a computational notebook cell and extract structured semantic information to build a knowledge graph.

Your response MUST be a valid JSON object with this exact structure:

{
  "data_assets": [
    {
      "label": "Short readable name (e.g., 'Patient Demographics CSV')",
      "type": "Ontology type (use 'dcat:Dataset' for files, 'da:Variable' for variables)",
      "identifier": "Unique ID (e.g., 'patient_data.csv' or variable name)",
      "description": "Brief description of the asset",
      "confidentiality": "C1 (public), C2 (internal), C3 (confidential), or C4 (restricted)"
    }
  ],
  "transformations": [
    {
      "label": "Readable transformation name (e.g., 'Data Cleaning and Normalization')",
      "method": "Technical method (e.g., 'z-score normalization')",
      "library": "Library used (e.g., 'pandas', 'sklearn')",
      "methodology": "Scientific methodology from prompt/explanation",
      "input_assets": ["List of input asset identifiers"],
      "output_assets": ["List of output asset identifiers"]
    }
  ],
  "refined_assets": [
    {
      "label": "Readable name (e.g., 'Normalized Patient Data')",
      "type": "Asset type ('da:Variable', 'da:CleanedDataset', etc.)",
      "identifier": "Unique ID (variable name)",
      "description": "What this refined asset contains",
      "derived_from": ["List of source asset identifiers"]
    }
  ],
  "outcomes": [
    {
      "label": "Outcome name (e.g., 'Mean Age Distribution')",
      "type": "Outcome type ('da:Finding', 'da:Visualization', 'da:Conclusion')",
      "description": "What was found/shown",
      "value": "Specific value if applicable (e.g., 'mean: 45.3')",
      "derived_from": ["List of assets this outcome is derived from"]
    }
  ]
}

Guidelines:
1. **Data Assets**: Input files, raw datasets, existing variables from previous cells
2. **Transformations**: Operations that change data (cleaning, normalization, aggregation, statistical tests)
3. **Refined Assets**: Intermediate results (cleaned datasets, computed variables, aggregated data)
4. **Outcomes**: Final results (statistical findings, visualizations, conclusions, insights)
5. **Confidentiality**:
   - C1 (public): Public datasets, published data
   - C2 (internal): Default for most research data
   - C3 (confidential): Sensitive data (patient data, financial data)
   - C4 (restricted): Highly sensitive (identifiable patient data, proprietary data)
6. Use the scientific explanation/methodology text to enrich transformation descriptions
7. **CRITICAL - Track provenance across cells**:
   - If "Available Variables from Previous Cells" or "Datasets from Previous Cells" sections are present, CHECK if the current cell uses them
   - When you see code loading/reading/using a variable or dataset from previous cells, MUST link them:
     * In transformations: `"input_assets": ["previous_var_name"]` - list what data is being transformed
     * In refined_assets: `"derived_from": ["source_var_name"]` - where did this come from
     * In outcomes: `"derived_from": ["data_used"]` - what data produced this finding
   - **Identifier format**: Use ONLY the base name (filename or variable name), no prefixes
     * Correct: `"derived_from": ["patient_data.csv"]` or `["df"]`
     * Incorrect: `"derived_from": ["dataset:patient_data.csv"]` or `["variable:df"]`
   - **Example 1**: Previous cells show "patient_data.csv", current code has `df = pd.read_csv('data/patient_data.csv')`
     * Data asset for df: `"identifier": "df", "derived_from": []` (reading file, not derived from variable)
     * Transformation: `"input_assets": ["patient_data.csv"], "output_assets": ["df"]`
   - **Example 2**: Previous cells show variable "df", current code has `result = df.describe()`
     * Refined asset/outcome using df: `"derived_from": ["df"]` - show it came from df
     * Transformation: `"input_assets": ["df"], "output_assets": ["result"]`
   - **Example 3**: Current cell computes correlation from multiple variables
     * Outcome: `"derived_from": ["age", "bp_systolic", "bmi"]` - list all data sources
8. Be specific and technical but readable

Respond ONLY with the JSON object, no additional text."""

    def _build_extraction_user_prompt(self, context: Dict[str, Any]) -> str:
        """Build user prompt with cell context."""
        prompt_parts = [
            f"# Notebook Context",
            f"Title: {context['notebook_title']}",
            f"Description: {context['notebook_description']}",
            f"\n# Cell Information",
            f"Cell ID: {context['cell_id']}",
            f"Cell Type: {context['cell_type']}",
        ]

        if context.get("prompt"):
            prompt_parts.append(f"\n# User Prompt\n{context['prompt']}")

        if context.get("scientific_explanation"):
            prompt_parts.append(f"\n# Scientific Methodology\n{context['scientific_explanation']}")

        if context.get("code"):
            prompt_parts.append(f"\n# Generated Code\n```python\n{context['code']}\n```")

        if context.get("stdout"):
            prompt_parts.append(f"\n# Execution Output\n{context['stdout']}")

        if context.get("has_plots"):
            prompt_parts.append("\n# Note: This cell produced visualization plots")

        if context.get("has_tables"):
            prompt_parts.append("\n# Note: This cell produced data tables")

        # Add context from previous cells
        if context.get("previous_variables"):
            prev_vars = list(set(context["previous_variables"]))[:10]  # Limit to 10
            prompt_parts.append(f"\n# Available Variables from Previous Cells\n{', '.join(prev_vars)}")

        if context.get("previous_datasets"):
            prev_datasets = list(set(context["previous_datasets"]))
            prompt_parts.append(f"\n# Datasets from Previous Cells\n{', '.join(prev_datasets)}")

        prompt_parts.append("\n# Task\nExtract the semantic information as structured JSON following the system prompt format.")

        return "\n".join(prompt_parts)

    def _parse_extraction_response(
        self,
        response_text: str,
        cell: Cell,
        notebook: Notebook
    ) -> Dict[str, Any]:
        """Parse LLM extraction response into structured data."""
        try:
            # Extract JSON from response (handle markdown code blocks)
            json_text = response_text.strip()
            if json_text.startswith("```"):
                # Remove markdown code block markers
                lines = json_text.split("\n")
                json_text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
                json_text = json_text.strip()

            # Parse JSON
            extraction_data = json.loads(json_text)

            # Convert to semantic entities and relationships
            result = {
                "data_assets": self._create_asset_entities(
                    extraction_data.get("data_assets", []),
                    cell,
                    notebook,
                    EntityType.DATASET
                ),
                "transformations": self._create_transformation_entities(
                    extraction_data.get("transformations", []),
                    cell
                ),
                "refined_assets": self._create_asset_entities(
                    extraction_data.get("refined_assets", []),
                    cell,
                    notebook,
                    EntityType.REFINED_ASSET
                ),
                "outcomes": self._create_outcome_entities(
                    extraction_data.get("outcomes", []),
                    cell
                ),
                "relationships": self._create_relationships(
                    extraction_data,
                    cell
                )
            }

            return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM extraction response as JSON: {e}")
            logger.debug(f"Response text: {response_text[:500]}")
            return self._empty_extraction()
        except Exception as e:
            logger.error(f"Error parsing extraction response: {e}")
            return self._empty_extraction()

    def _create_asset_entities(
        self,
        assets_data: List[Dict],
        cell: Cell,
        notebook: Notebook,
        entity_type: EntityType
    ) -> List[SemanticEntity]:
        """Create semantic entities for data assets."""
        entities = []

        for asset_info in assets_data:
            try:
                # Parse confidentiality
                conf_str = asset_info.get("confidentiality", "C2").upper()
                confidentiality = {
                    "C1": ConfidentialityLevel.C1_PUBLIC,
                    "C2": ConfidentialityLevel.C2_INTERNAL,
                    "C3": ConfidentialityLevel.C3_CONFIDENTIAL,
                    "C4": ConfidentialityLevel.C4_RESTRICTED,
                }.get(conf_str, ConfidentialityLevel.C2_INTERNAL)

                # Create metadata
                metadata = AssetMetadata(
                    label=asset_info.get("label", "Unnamed asset"),
                    asset_type=asset_info.get("type", "dcat:Dataset"),
                    confidentiality=confidentiality,
                    created=datetime.now(),
                    owner=notebook.author,
                    description=asset_info.get("description"),
                    provenance=asset_info.get("derived_from", [])
                )

                # Create CURIE
                identifier = asset_info.get("identifier", f"asset_{len(entities)}")
                curie = f"{entity_type.value}:{identifier}"

                entity = SemanticEntity(
                    id=curie,
                    type=entity_type,
                    label=asset_info.get("label", identifier),
                    metadata=metadata,
                    properties={
                        "da:identifier": identifier,
                        "da:cellId": f"cell:{cell.id}"
                    }
                )

                entities.append(entity)

            except Exception as e:
                logger.warning(f"Error creating asset entity: {e}")
                continue

        return entities

    def _create_transformation_entities(
        self,
        transformations_data: List[Dict],
        cell: Cell
    ) -> List[SemanticEntity]:
        """Create semantic entities for transformations."""
        entities = []

        for i, trans_info in enumerate(transformations_data):
            try:
                trans_id = f"transformation:{cell.id}_{i}"

                entity = SemanticEntity(
                    id=trans_id,
                    type=EntityType.TRANSFORMATION,
                    label=trans_info.get("label", f"Transformation {i+1}"),
                    properties={
                        "da:method": trans_info.get("method"),
                        "da:library": trans_info.get("library"),
                        "da:methodology": trans_info.get("methodology"),
                        "da:cellId": f"cell:{cell.id}",
                        "prov:used": trans_info.get("input_assets", []),
                        "prov:generated": trans_info.get("output_assets", [])
                    }
                )

                entities.append(entity)

            except Exception as e:
                logger.warning(f"Error creating transformation entity: {e}")
                continue

        return entities

    def _create_outcome_entities(
        self,
        outcomes_data: List[Dict],
        cell: Cell
    ) -> List[SemanticEntity]:
        """Create semantic entities for outcomes."""
        entities = []

        for i, outcome_info in enumerate(outcomes_data):
            try:
                outcome_id = f"{outcome_info.get('type', 'da:Finding').split(':')[1].lower()}:{cell.id}_{i}"

                entity = SemanticEntity(
                    id=outcome_id,
                    type=EntityType.FINDING,  # Map all outcomes to FINDING for now
                    label=outcome_info.get("label", f"Outcome {i+1}"),
                    properties={
                        "da:outcomeType": outcome_info.get("type", "da:Finding"),
                        "dcterms:description": outcome_info.get("description"),
                        "da:value": outcome_info.get("value"),
                        "prov:wasDerivedFrom": outcome_info.get("derived_from", []),
                        "da:cellId": f"cell:{cell.id}"
                    }
                )

                entities.append(entity)

            except Exception as e:
                logger.warning(f"Error creating outcome entity: {e}")
                continue

        return entities

    def _create_relationships(
        self,
        extraction_data: Dict,
        cell: Cell
    ) -> List[Triple]:
        """Create provenance relationships between entities."""
        triples = []
        cell_id = f"cell:{cell.id}"

        try:
            # Transformations use data assets
            for trans in extraction_data.get("transformations", []):
                trans_id = f"transformation:{cell.id}_{extraction_data['transformations'].index(trans)}"

                for input_asset in trans.get("input_assets", []):
                    triples.append(Triple(
                        subject=trans_id,
                        predicate="prov:used",
                        object=input_asset
                    ))

                for output_asset in trans.get("output_assets", []):
                    triples.append(Triple(
                        subject=output_asset,
                        predicate="prov:wasGeneratedBy",
                        object=trans_id
                    ))

            # Refined assets derived from data assets
            for refined in extraction_data.get("refined_assets", []):
                refined_id = f"refined_asset:{refined.get('identifier', 'unknown')}"

                for source in refined.get("derived_from", []):
                    triples.append(Triple(
                        subject=refined_id,
                        predicate="prov:wasDerivedFrom",
                        object=source
                    ))

            # Outcomes derived from assets
            for i, outcome in enumerate(extraction_data.get("outcomes", [])):
                outcome_id = f"{outcome.get('type', 'da:Finding').split(':')[1].lower()}:{cell.id}_{i}"

                for source in outcome.get("derived_from", []):
                    triples.append(Triple(
                        subject=outcome_id,
                        predicate="prov:wasDerivedFrom",
                        object=source
                    ))

        except Exception as e:
            logger.warning(f"Error creating relationships: {e}")

        return triples
