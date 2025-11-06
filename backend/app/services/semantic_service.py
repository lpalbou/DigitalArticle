"""
Semantic extraction service for Digital Article knowledge graph.

This service extracts semantic information from notebook cells, including:
- Datasets and variables from prompts and code
- Statistical methods and libraries from code
- Findings and statistics from execution results
- Domain concepts from scientific explanations
"""

import ast
import re
import logging
from typing import Dict, List, Optional, Any, Set, Tuple
from uuid import UUID

from ..models.notebook import Cell, Notebook, ExecutionResult, CellType
from ..models.semantics import (
    CellSemantics, NotebookSemantics, Triple, SemanticEntity,
    EntityType, ONTOLOGY_CONTEXT
)

logger = logging.getLogger(__name__)


class SemanticExtractionService:
    """Service for extracting semantic information from notebook cells."""

    # Common statistical libraries and their methods
    LIBRARY_METHODS = {
        "pandas": ["read_csv", "read_excel", "DataFrame", "Series", "merge", "groupby", "pivot"],
        "numpy": ["array", "mean", "std", "median", "percentile", "histogram"],
        "matplotlib": ["plot", "scatter", "hist", "bar", "boxplot", "heatmap", "imshow"],
        "seaborn": ["histplot", "scatterplot", "boxplot", "heatmap", "violinplot", "pairplot"],
        "scipy": ["ttest_ind", "ttest_rel", "pearsonr", "spearmanr", "chi2_contingency"],
        "sklearn": ["PCA", "LinearRegression", "LogisticRegression", "train_test_split", "StandardScaler"],
        "plotly": ["scatter", "bar", "histogram", "box", "heatmap"],
        "statsmodels": ["OLS", "Logit", "anova_lm", "ttest_ind"]
    }

    # Statistical method patterns
    STATISTICAL_METHODS = {
        "histogram": ["hist", "histplot", "histogram"],
        "scatter_plot": ["scatter", "scatterplot"],
        "box_plot": ["boxplot", "box"],
        "heatmap": ["heatmap"],
        "bar_chart": ["bar", "barplot"],
        "line_plot": ["plot", "lineplot"],
        "t_test": ["ttest_ind", "ttest_rel", "ttest"],
        "correlation": ["corr", "pearsonr", "spearmanr"],
        "pca": ["PCA", "pca"],
        "regression": ["LinearRegression", "Logit", "OLS", "regression"],
        "anova": ["anova", "anova_lm"],
        "chi_square": ["chi2", "chi2_contingency"],
        "clustering": ["KMeans", "DBSCAN", "AgglomerativeClustering"],
    }

    # Intent keywords for prompt analysis
    INTENT_KEYWORDS = {
        "data_loading": ["load", "read", "import data", "open"],
        "visualization": ["plot", "chart", "graph", "visualize", "show", "display"],
        "statistics": ["mean", "median", "std", "statistics", "describe", "summary"],
        "comparison": ["compare", "difference", "vs", "versus", "between"],
        "correlation": ["correlate", "correlation", "relationship", "association"],
        "test": ["test", "significance", "p-value", "hypothesis"],
        "transformation": ["transform", "normalize", "scale", "convert"],
        "aggregation": ["aggregate", "group", "summarize", "count"],
        "filter": ["filter", "select", "subset", "where"],
        "model": ["model", "predict", "train", "fit", "machine learning"],
    }

    def extract_cell_semantics(self, cell: Cell, notebook: Notebook) -> CellSemantics:
        """
        Extract semantic information from a cell.

        Args:
            cell: The cell to extract semantics from
            notebook: The parent notebook for context

        Returns:
            CellSemantics object with extracted entities and triples
        """
        try:
            cell_id = f"cell:{cell.id}"
            semantics = CellSemantics(cell_id=cell_id)
            entities: List[SemanticEntity] = []
            triples: List[Triple] = []

            # Extract from prompt
            if cell.prompt:
                prompt_data = self._extract_from_prompt(cell.prompt, cell_id)
                semantics.intent_tags = prompt_data["intents"]
                semantics.datasets_used = prompt_data["datasets"]
                semantics.concepts_mentioned = prompt_data["concepts"]
                entities.extend(prompt_data["entities"])
                triples.extend(prompt_data["triples"])

            # Extract from code
            if cell.code:
                code_data = self._extract_from_code(cell.code, cell_id)
                semantics.libraries_used = code_data["libraries"]
                semantics.methods_used = code_data["methods"]
                semantics.variables_defined = code_data["variables"]
                entities.extend(code_data["entities"])
                triples.extend(code_data["triples"])

            # Extract from execution results
            if cell.last_result:
                result_data = self._extract_from_result(cell.last_result, cell_id)
                semantics.statistical_findings = result_data["findings"]
                entities.extend(result_data["entities"])
                triples.extend(result_data["triples"])

            # Extract from scientific explanation
            if cell.scientific_explanation:
                concept_data = self._extract_concepts_from_text(cell.scientific_explanation)
                semantics.concepts_mentioned.extend(concept_data)

            # Add cell entity
            cell_entity = SemanticEntity(
                id=cell_id,
                type=EntityType.CELL,
                label=cell.prompt[:100] if cell.prompt else "Code cell",
                properties={
                    "da:cellType": cell.cell_type.value,
                    "da:executionCount": cell.execution_count,
                    "dcterms:created": cell.created_at.isoformat()
                }
            )
            entities.append(cell_entity)

            # Add cell to notebook relationship
            notebook_id = f"notebook:{notebook.id}"
            triples.append(Triple(
                subject=notebook_id,
                predicate="dcterms:hasPart",
                object=cell_id,
                object_type="da:Cell"
            ))

            semantics.entities = entities
            semantics.triples = triples

            return semantics

        except Exception as e:
            logger.warning(f"Error extracting semantics from cell {cell.id}: {e}")
            # Return empty semantics on error
            return CellSemantics(cell_id=f"cell:{cell.id}")

    def _extract_from_prompt(self, prompt: str, cell_id: str) -> Dict[str, Any]:
        """Extract semantic information from a natural language prompt."""
        entities = []
        triples = []
        intents = []
        datasets = []
        concepts = []

        prompt_lower = prompt.lower()

        # Extract intent tags
        for intent, keywords in self.INTENT_KEYWORDS.items():
            if any(keyword in prompt_lower for keyword in keywords):
                intents.append(intent)
                triples.append(Triple(
                    subject=cell_id,
                    predicate="da:hasIntent",
                    object=f"intent:{intent}",
                    confidence=0.8
                ))

        # Extract dataset references (files with extensions)
        dataset_pattern = r'\b([\w\-]+\.(?:csv|xlsx|xls|json|txt|tsv|parquet|h5|hdf5))\b'
        found_datasets = re.findall(dataset_pattern, prompt_lower)
        for dataset_name in found_datasets:
            if dataset_name not in datasets:
                datasets.append(dataset_name)
                dataset_id = f"dataset:{dataset_name}"
                entities.append(SemanticEntity(
                    id=dataset_id,
                    type=EntityType.DATASET,
                    label=dataset_name,
                    properties={"schema:name": dataset_name}
                ))
                triples.append(Triple(
                    subject=cell_id,
                    predicate="da:usesDataset",
                    object=dataset_id,
                    confidence=0.9
                ))

        # Extract domain concepts (simple keyword extraction)
        # Look for capitalized terms or quoted terms
        concept_patterns = [
            r'"([^"]+)"',  # Quoted terms
            r'\b([A-Z][a-z]+(?: [A-Z][a-z]+)*)\b',  # Capitalized phrases
        ]
        for pattern in concept_patterns:
            matches = re.findall(pattern, prompt)
            for match in matches:
                if len(match) > 3 and match.lower() not in ["load", "show", "create", "plot"]:
                    concepts.append(match)

        return {
            "intents": intents,
            "datasets": datasets,
            "concepts": concepts,
            "entities": entities,
            "triples": triples
        }

    def _extract_from_code(self, code: str, cell_id: str) -> Dict[str, Any]:
        """Extract semantic information from Python code using AST parsing."""
        entities = []
        triples = []
        libraries = []
        methods = []
        variables = []

        try:
            tree = ast.parse(code)

            # Extract imports
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        lib_name = alias.name.split('.')[0]
                        if lib_name not in libraries:
                            libraries.append(lib_name)
                            lib_id = f"library:{lib_name}"
                            entities.append(SemanticEntity(
                                id=lib_id,
                                type=EntityType.LIBRARY,
                                label=lib_name,
                                properties={"schema:name": lib_name}
                            ))
                            triples.append(Triple(
                                subject=cell_id,
                                predicate="da:usesLibrary",
                                object=lib_id
                            ))

                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        lib_name = node.module.split('.')[0]
                        if lib_name not in libraries:
                            libraries.append(lib_name)
                            lib_id = f"library:{lib_name}"
                            entities.append(SemanticEntity(
                                id=lib_id,
                                type=EntityType.LIBRARY,
                                label=lib_name,
                                properties={"schema:name": lib_name}
                            ))
                            triples.append(Triple(
                                subject=cell_id,
                                predicate="da:usesLibrary",
                                object=lib_id
                            ))

                # Extract variable assignments
                elif isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            var_name = target.id
                            if var_name not in variables and not var_name.startswith('_'):
                                variables.append(var_name)
                                var_id = f"variable:{var_name}"
                                entities.append(SemanticEntity(
                                    id=var_id,
                                    type=EntityType.VARIABLE,
                                    label=var_name,
                                    properties={"schema:name": var_name}
                                ))
                                triples.append(Triple(
                                    subject=cell_id,
                                    predicate="da:definesVariable",
                                    object=var_id
                                ))

                # Extract function calls to identify methods
                elif isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Attribute):
                        method_name = node.func.attr
                        method_category = self._categorize_method(method_name)
                        if method_category and method_category not in methods:
                            methods.append(method_category)
                            method_id = f"method:{method_category}"
                            triples.append(Triple(
                                subject=cell_id,
                                predicate="da:appliesMethod",
                                object=method_id,
                                confidence=0.7
                            ))
                    elif isinstance(node.func, ast.Name):
                        func_name = node.func.id
                        method_category = self._categorize_method(func_name)
                        if method_category and method_category not in methods:
                            methods.append(method_category)
                            method_id = f"method:{method_category}"
                            triples.append(Triple(
                                subject=cell_id,
                                predicate="da:appliesMethod",
                                object=method_id,
                                confidence=0.7
                            ))

        except SyntaxError as e:
            logger.debug(f"Could not parse code in cell: {e}")
        except Exception as e:
            logger.warning(f"Error extracting from code: {e}")

        return {
            "libraries": libraries,
            "methods": methods,
            "variables": variables,
            "entities": entities,
            "triples": triples
        }

    def _categorize_method(self, method_name: str) -> Optional[str]:
        """Categorize a method name into a semantic method type."""
        method_lower = method_name.lower()

        for category, patterns in self.STATISTICAL_METHODS.items():
            if any(pattern.lower() in method_lower for pattern in patterns):
                return category

        return None

    def _extract_from_result(self, result: ExecutionResult, cell_id: str) -> Dict[str, Any]:
        """Extract semantic information from execution results."""
        entities = []
        triples = []
        findings = []

        # Extract statistical findings from stdout
        if result.stdout:
            stats = self._extract_statistics(result.stdout)
            findings.extend(stats)

            # Create finding entities and triples
            for i, finding in enumerate(stats):
                finding_id = f"finding:{cell_id}_stat_{i}"
                entities.append(SemanticEntity(
                    id=finding_id,
                    type=EntityType.FINDING,
                    label=finding.get("label", "Statistical finding"),
                    properties={
                        "da:metric": finding.get("metric"),
                        "da:value": finding.get("value"),
                        "schema:value": finding.get("value")
                    }
                ))
                triples.append(Triple(
                    subject=cell_id,
                    predicate="da:producedFinding",
                    object=finding_id,
                    confidence=0.8
                ))

        # Extract visualization information
        if result.plots:
            for i, plot in enumerate(result.plots):
                plot_id = f"visualization:{cell_id}_plot_{i}"
                entities.append(SemanticEntity(
                    id=plot_id,
                    type=EntityType.VISUALIZATION,
                    label=f"Plot {i+1}",
                    properties={"da:format": "image/png"}
                ))
                triples.append(Triple(
                    subject=cell_id,
                    predicate="da:producesVisualization",
                    object=plot_id
                ))

        if result.interactive_plots:
            for i, plot in enumerate(result.interactive_plots):
                plot_id = f"visualization:{cell_id}_interactive_{i}"
                entities.append(SemanticEntity(
                    id=plot_id,
                    type=EntityType.VISUALIZATION,
                    label=f"Interactive plot {i+1}",
                    properties={"da:format": "application/json", "da:library": "plotly"}
                ))
                triples.append(Triple(
                    subject=cell_id,
                    predicate="da:producesVisualization",
                    object=plot_id
                ))

        # Extract table information
        if result.tables:
            for i, table in enumerate(result.tables):
                table_id = f"table:{cell_id}_table_{i}"
                table_info = table.get("info", {})
                entities.append(SemanticEntity(
                    id=table_id,
                    type=EntityType.FINDING,
                    label=f"Table {i+1}",
                    properties={
                        "da:rows": table_info.get("shape", [0])[0] if table_info.get("shape") else 0,
                        "da:columns": len(table.get("columns", [])),
                        "schema:name": f"Table {i+1}"
                    }
                ))
                triples.append(Triple(
                    subject=cell_id,
                    predicate="da:producesTable",
                    object=table_id
                ))

        return {
            "findings": findings,
            "entities": entities,
            "triples": triples
        }

    def _extract_statistics(self, text: str) -> List[Dict[str, Any]]:
        """Extract statistical values from text output."""
        findings = []

        # Common statistical patterns
        patterns = {
            "mean": r'mean[:\s=]+(-?\d+\.?\d*)',
            "median": r'median[:\s=]+(-?\d+\.?\d*)',
            "std": r'std[:\s=]+(-?\d+\.?\d*)',
            "count": r'count[:\s=]+(\d+)',
            "p_value": r'p[-\s]?value[:\s=]+(-?\d+\.?\d*)',
            "t_statistic": r't[-\s]?stat(?:istic)?[:\s=]+(-?\d+\.?\d*)',
            "correlation": r'corr(?:elation)?[:\s=]+(-?\d+\.?\d*)',
            "r_squared": r'r[²\^2]?[:\s=]+(-?\d+\.?\d*)',
        }

        for metric, pattern in patterns.items():
            matches = re.finditer(pattern, text.lower())
            for match in matches:
                try:
                    value = float(match.group(1))
                    findings.append({
                        "metric": metric,
                        "value": value,
                        "label": f"{metric}: {value}"
                    })
                except (ValueError, IndexError):
                    continue

        return findings

    def _extract_concepts_from_text(self, text: str) -> List[str]:
        """Extract domain concepts from scientific text."""
        concepts = []

        # Extract capitalized multi-word terms (likely to be concepts)
        concept_pattern = r'\b([A-Z][a-z]+(?: [A-Z][a-z]+)+)\b'
        matches = re.findall(concept_pattern, text)

        # Filter out common non-concept terms
        stop_terms = {"The", "This", "That", "These", "Those", "Figure", "Table"}
        for match in matches:
            if match not in stop_terms and len(match) > 5:
                concepts.append(match)

        return concepts

    def extract_notebook_semantics(self, notebook: Notebook) -> NotebookSemantics:
        """
        Extract semantic information from an entire notebook.

        Args:
            notebook: The notebook to extract semantics from

        Returns:
            NotebookSemantics with aggregated cell semantics
        """
        notebook_id = f"notebook:{notebook.id}"
        notebook_semantics = NotebookSemantics(notebook_id=notebook_id)

        # Create notebook entity
        notebook_entity = SemanticEntity(
            id=notebook_id,
            type=EntityType.NOTEBOOK,
            label=notebook.title,
            properties={
                "dcterms:title": notebook.title,
                "dcterms:description": notebook.description,
                "dcterms:creator": notebook.author,
                "dcterms:created": notebook.created_at.isoformat(),
                "dcterms:modified": notebook.updated_at.isoformat(),
                "da:llmProvider": notebook.llm_provider,
                "da:llmModel": notebook.llm_model
            }
        )
        notebook_semantics.global_entities.append(notebook_entity)

        # Extract semantics from each cell
        for cell in notebook.cells:
            try:
                cell_semantics = self.extract_cell_semantics(cell, notebook)
                notebook_semantics.cell_semantics.append(cell_semantics)
            except Exception as e:
                logger.warning(f"Error extracting semantics from cell {cell.id}: {e}")

        return notebook_semantics
