"""
Analysis flow semantic extraction for Digital Article.

Extracts workflow and process information:
- Cell execution sequence and dependencies
- Variable definitions and reuse across cells
- Data transformations and lineage
- Method application order
- Narrative flow (abstract, methodology)
"""

import ast
import re
from typing import Dict, List, Set, Any, Tuple
from collections import defaultdict

from ..models.notebook import Notebook, Cell
from ..models.semantics import ONTOLOGY_CONTEXT


class SemanticAnalysisService:
    """Extract analysis workflow and variable flow from notebooks."""

    def extract_analysis_graph(self, notebook: Notebook) -> Dict[str, Any]:
        """
        Extract analysis-focused knowledge graph.

        Returns structured data with:
        - Cell execution sequence
        - Variable definitions and reuse
        - Data lineage and transformations
        - Method dependencies
        - Narrative elements (abstract, methodology)
        """
        analysis = {
            "@context": ONTOLOGY_CONTEXT,
            "@graph": [],
            "triples": [],
            "metadata": {
                "graph_type": "analysis_flow",
                "notebook_id": str(notebook.id),
                "extracted_at": notebook.updated_at.isoformat()
            }
        }

        graph_nodes = []
        triples = []

        notebook_id = f"notebook:{notebook.id}"

        # Add abstract/methodology as narrative node if present
        if notebook.description:
            abstract_id = f"narrative:abstract"
            abstract_node = {
                "@id": abstract_id,
                "@type": "dcterms:Text",
                "dcterms:title": "Abstract",
                "dcterms:description": notebook.description
            }
            graph_nodes.append(abstract_node)

            triples.append({
                "subject": notebook_id,
                "predicate": "dcterms:abstract",
                "object": abstract_id
            })

        # Track variable definitions and usage across cells
        var_definitions = {}  # var_name -> cell_id where defined
        var_usage = defaultdict(list)  # var_name -> [cell_ids where used]

        # Process cells in order
        for idx, cell in enumerate(notebook.cells):
            cell_id = f"cell:{cell.id}"

            # Create cell node with order
            cell_node = {
                "@id": cell_id,
                "@type": "da:Cell",
                "dcterms:title": cell.prompt[:100] if cell.prompt else f"Cell {idx+1}",
                "da:executionOrder": idx + 1,
                "da:cellType": cell.cell_type.value
            }

            if cell.prompt:
                cell_node["da:prompt"] = cell.prompt

            if cell.scientific_explanation:
                # Add methodology as property
                cell_node["da:methodology"] = cell.scientific_explanation

            graph_nodes.append(cell_node)

            # Link to notebook
            triples.append({
                "subject": notebook_id,
                "predicate": "dcterms:hasPart",
                "object": cell_id
            })

            # Sequence relationship to previous cell
            if idx > 0:
                prev_cell_id = f"cell:{notebook.cells[idx-1].id}"
                triples.append({
                    "subject": prev_cell_id,
                    "predicate": "schema:nextItem",
                    "object": cell_id
                })

            # Extract variables from code
            if cell.code:
                defined_vars, used_vars = self._extract_variables(cell.code)

                # Track variable definitions
                for var in defined_vars:
                    if var not in var_definitions:
                        var_definitions[var] = cell_id

                        # Create variable node
                        var_id = f"variable:{var}"
                        var_node = {
                            "@id": var_id,
                            "@type": "da:Variable",
                            "schema:name": var,
                            "da:definedIn": cell_id
                        }
                        graph_nodes.append(var_node)

                        # Link cell defines variable
                        triples.append({
                            "subject": cell_id,
                            "predicate": "da:definesVariable",
                            "object": var_id
                        })

                # Track variable usage
                for var in used_vars:
                    if var in var_definitions and var_definitions[var] != cell_id:
                        var_usage[var].append(cell_id)

                        # Link cell uses variable
                        var_id = f"variable:{var}"
                        triples.append({
                            "subject": cell_id,
                            "predicate": "da:usesVariable",
                            "object": var_id
                        })

                        # Create dependency on defining cell
                        defining_cell = var_definitions[var]
                        triples.append({
                            "subject": cell_id,
                            "predicate": "prov:wasDerivedFrom",
                            "object": defining_cell
                        })

            # Add findings from execution results
            if cell.last_result and cell.last_result.status.value == "success":
                # Link outputs
                if cell.last_result.plots:
                    for i, _ in enumerate(cell.last_result.plots):
                        viz_id = f"visualization:{cell.id}_plot_{i}"
                        viz_node = {
                            "@id": viz_id,
                            "@type": "da:Visualization",
                            "schema:name": f"Plot {i+1}",
                            "da:format": "image/png"
                        }
                        graph_nodes.append(viz_node)

                        triples.append({
                            "subject": cell_id,
                            "predicate": "da:produces",
                            "object": viz_id
                        })

                # Extract and link statistical findings
                if cell.last_result.stdout:
                    findings = self._extract_findings(cell.last_result.stdout)
                    for finding_info in findings:
                        finding_id = f"finding:{cell.id}_{finding_info['metric']}"
                        finding_node = {
                            "@id": finding_id,
                            "@type": "da:Finding",
                            "schema:name": finding_info["metric"],
                            "da:value": finding_info["value"]
                        }
                        graph_nodes.append(finding_node)

                        triples.append({
                            "subject": cell_id,
                            "predicate": "da:produces",
                            "object": finding_id
                        })

        # Add variable transformation relationships
        for var, cell_ids in var_usage.items():
            var_id = f"variable:{var}"
            # Track how variable is transformed across cells
            for cell_id in cell_ids:
                # Check if this cell redefines the variable (transformation)
                cell = self._get_cell_by_id(notebook, cell_id)
                if cell and cell.code:
                    if self._variable_is_reassigned(cell.code, var):
                        # This is a transformation
                        triples.append({
                            "subject": cell_id,
                            "predicate": "da:transforms",
                            "object": var_id
                        })

        analysis["@graph"] = graph_nodes
        analysis["triples"] = triples

        return analysis

    def _extract_variables(self, code: str) -> Tuple[Set[str], Set[str]]:
        """
        Extract variables defined and used in code.

        Returns:
            (defined_vars, used_vars)
        """
        defined = set()
        used = set()

        try:
            tree = ast.parse(code)

            for node in ast.walk(tree):
                # Variables assigned (defined)
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            defined.add(target.id)

                # Variables used
                elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                    used.add(node.id)

        except SyntaxError:
            pass

        # Remove builtins and private vars
        defined = {v for v in defined if not v.startswith('_') and v not in dir(__builtins__)}
        used = {v for v in used if not v.startswith('_') and v not in dir(__builtins__)}

        return defined, used

    def _variable_is_reassigned(self, code: str, var_name: str) -> bool:
        """Check if a variable is reassigned (transformed) in code."""
        try:
            tree = ast.parse(code)

            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name) and target.id == var_name:
                            # Check if variable appears on right side (transformation)
                            for n in ast.walk(node.value):
                                if isinstance(n, ast.Name) and n.id == var_name:
                                    return True
        except SyntaxError:
            pass

        return False

    def _get_cell_by_id(self, notebook: Notebook, cell_id: str) -> Cell:
        """Get cell by ID string (format: 'cell:uuid')."""
        uuid_str = cell_id.split(':')[1] if ':' in cell_id else cell_id

        for cell in notebook.cells:
            if str(cell.id) == uuid_str:
                return cell

        return None

    def _extract_findings(self, text: str) -> List[Dict[str, Any]]:
        """Extract statistical findings from text output."""
        findings = []

        # Common statistical patterns
        patterns = {
            "mean": r'mean[:\s=]+(-?\d+\.?\d*)',
            "median": r'median[:\s=]+(-?\d+\.?\d*)',
            "std": r'std[:\s=]+(-?\d+\.?\d*)',
            "count": r'count[:\s=]+(\d+)',
            "p_value": r'p[-\s]?value[:\s=]+(-?\d+\.?\d*)',
            "correlation": r'corr(?:elation)?[:\s=]+(-?\d+\.?\d*)',
        }

        for metric, pattern in patterns.items():
            matches = re.finditer(pattern, text.lower())
            for match in matches:
                try:
                    value = float(match.group(1))
                    findings.append({
                        "metric": metric,
                        "value": value
                    })
                except (ValueError, IndexError):
                    continue

        return findings
