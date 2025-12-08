"""
Analysis flow semantic extraction for Digital Article.

Creates a knowledge graph showing the complete data lineage:
- Data assets (input datasets, files)
- Transformations (operations with methodology)
- Refined assets (intermediate outputs, variables)
- Outcomes (findings, visualizations, conclusions)

All connected with provenance relationships (prov:wasDerivedFrom, prov:wasGeneratedBy, prov:used).

Implements caching to avoid expensive LLM extraction when notebook hasn't changed.
"""

import logging
import hashlib
import json
from typing import Dict, List, Any, Optional
from collections import defaultdict

from ..models.notebook import Notebook, Cell
from ..models.semantics import ONTOLOGY_CONTEXT, Triple, SemanticEntity, EntityType
from .llm_semantic_extractor import LLMSemanticExtractor

logger = logging.getLogger(__name__)


class SemanticAnalysisService:
    """Extract analysis workflow and data lineage from notebooks."""

    def __init__(self):
        """Initialize the analysis service with LLM extractor."""
        self.llm_extractor = LLMSemanticExtractor()

    def _generate_cache_key(self, notebook: Notebook) -> str:
        """
        Generate a cache key based on notebook state.

        The cache key changes when:
        - Cells are added/removed/reordered
        - Cell content changes (prompt, code, results)
        - Cell execution state changes

        Returns:
            Hash string representing current notebook state
        """
        cache_data = {
            "notebook_id": str(notebook.id),
            # NOTE: We exclude updated_at from cache key because it changes
            # on every save, which would invalidate cache unnecessarily.
            # The cache should only invalidate when semantic content changes
            # (cells, code, results, prompts, etc.), not metadata timestamps.
            "cells": []
        }

        for cell in notebook.cells:
            cell_data = {
                "id": str(cell.id),
                "prompt": cell.prompt or "",
                "code": cell.code or "",
                "execution_count": cell.execution_count,
                "scientific_explanation": cell.scientific_explanation or "",
            }

            # Include result state if available
            if cell.last_result:
                cell_data["result_status"] = cell.last_result.status.value
                cell_data["has_stdout"] = bool(cell.last_result.stdout)
                cell_data["has_plots"] = len(cell.last_result.plots or [])
                cell_data["has_tables"] = len(cell.last_result.tables or [])

            cache_data["cells"].append(cell_data)

        # Create hash
        cache_json = json.dumps(cache_data, sort_keys=True)
        cache_hash = hashlib.sha256(cache_json.encode()).hexdigest()

        return cache_hash

    def _get_cached_graph(self, notebook: Notebook, graph_type: str) -> Optional[Dict[str, Any]]:
        """
        Get cached graph if it exists and is still valid.

        Args:
            notebook: The notebook to get cached graph for
            graph_type: 'analysis' or 'profile'

        Returns:
            Cached graph dict or None if cache invalid/missing
        """
        cache_key = self._generate_cache_key(notebook)
        cache_metadata_key = f"semantic_cache_{graph_type}"

        # Check if notebook has cached graph in metadata
        if hasattr(notebook, 'metadata') and isinstance(notebook.metadata, dict):
            cached_data = notebook.metadata.get(cache_metadata_key)

            if cached_data and isinstance(cached_data, dict):
                cached_key = cached_data.get("cache_key")
                cached_graph = cached_data.get("graph")

                if cached_key == cache_key and cached_graph:
                    logger.info(f"✅ Using cached {graph_type} graph (key: {cache_key[:8]}...)")
                    return cached_graph

        return None

    def _cache_graph(self, notebook: Notebook, graph_type: str, graph: Dict[str, Any]) -> None:
        """
        Cache the generated graph in notebook metadata.

        Args:
            notebook: The notebook to cache graph for
            graph_type: 'analysis' or 'profile'
            graph: The generated graph to cache
        """
        cache_key = self._generate_cache_key(notebook)
        cache_metadata_key = f"semantic_cache_{graph_type}"

        # Ensure notebook has metadata dict
        if not hasattr(notebook, 'metadata') or not isinstance(notebook.metadata, dict):
            notebook.metadata = {}

        # Store cache
        notebook.metadata[cache_metadata_key] = {
            "cache_key": cache_key,
            "graph": graph,
            "cached_at": notebook.updated_at.isoformat()
        }

        logger.info(f"💾 Cached {graph_type} graph (key: {cache_key[:8]}...)")

    def extract_analysis_graph(self, notebook: Notebook, use_cache: bool = True) -> Dict[str, Any]:
        """
        Extract analysis-focused knowledge graph showing data lineage.

        Creates a graph with:
        - Data assets → Transformations → Refined assets → Outcomes
        - Complete provenance chain
        - Methodology and scientific context
        - Cell execution sequence

        Args:
            notebook: The notebook to extract graph from
            use_cache: If True, use cached graph if available (default: True)

        Returns:
            JSON-LD graph with @context, @graph, triples, and metadata
        """
        # Check cache first
        if use_cache:
            cached_graph = self._get_cached_graph(notebook, 'analysis')
            if cached_graph:
                return cached_graph

        logger.info("🔄 Extracting analysis graph with LLM (no valid cache)...")

        analysis = {
            "@context": ONTOLOGY_CONTEXT,
            "@graph": [],
            "triples": [],
            "metadata": {
                "graph_type": "analysis_flow",
                "notebook_id": str(notebook.id),
                "notebook_title": notebook.title,
                "extracted_at": notebook.updated_at.isoformat()
            }
        }

        graph_nodes = []
        triples = []
        notebook_id = f"notebook:{notebook.id}"

        # Add notebook node
        notebook_node = {
            "@id": notebook_id,
            "@type": "dcterms:Text",
            "dcterms:title": notebook.title,
            "dcterms:description": notebook.description or "Digital Article notebook",
            "dcterms:creator": notebook.author or "Anonymous",
            "dcterms:created": notebook.created_at.isoformat(),
            "dcterms:modified": notebook.updated_at.isoformat(),
            "da:llmProvider": notebook.llm_provider,
            "da:llmModel": notebook.llm_model
        }
        graph_nodes.append(notebook_node)

        # Add abstract/methodology as narrative node if present
        if notebook.description:
            abstract_id = f"narrative:abstract_{notebook.id}"
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

        # Process cells in order using LLM extraction
        all_assets = {}  # Track all assets by identifier
        all_transformations = {}
        all_outcomes = {}

        for idx, cell in enumerate(notebook.cells):
            cell_id = f"cell:{cell.id}"

            # Create cell node with step number as label
            cell_node = {
                "@id": cell_id,
                "@type": "da:Cell",
                "rdfs:label": f"Step {idx + 1}",
                "dcterms:title": f"Analysis Step {idx + 1}",
                "da:executionOrder": idx + 1,
                "da:cellType": cell.cell_type.value
            }

            # Add prompt as property (not label)
            if cell.prompt:
                cell_node["da:prompt"] = cell.prompt

            # Add methodology as property
            if cell.scientific_explanation:
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

            # Use LLM to extract rich semantics
            try:
                logger.info(f"🔍 Extracting semantics for cell {idx+1}/{len(notebook.cells)} using LLM...")

                # Get previous cells for context
                previous_cells = notebook.cells[:idx] if idx > 0 else None

                # Extract using LLM
                extraction = self.llm_extractor.extract_rich_semantics(
                    cell=cell,
                    notebook=notebook,
                    previous_cells=previous_cells
                )

                # Add data assets
                for asset_entity in extraction.get("data_assets", []):
                    node = asset_entity.to_jsonld()
                    graph_nodes.append(node)
                    all_assets[asset_entity.id] = asset_entity

                    # Link cell uses asset
                    triples.append({
                        "subject": cell_id,
                        "predicate": "prov:used",
                        "object": asset_entity.id
                    })

                # Add transformations
                for trans_entity in extraction.get("transformations", []):
                    node = trans_entity.to_jsonld()
                    graph_nodes.append(node)
                    all_transformations[trans_entity.id] = trans_entity

                    # Link cell performs transformation
                    triples.append({
                        "subject": cell_id,
                        "predicate": "da:performsTransformation",
                        "object": trans_entity.id
                    })

                # Add refined assets
                for refined_entity in extraction.get("refined_assets", []):
                    node = refined_entity.to_jsonld()
                    graph_nodes.append(node)
                    all_assets[refined_entity.id] = refined_entity

                    # Link cell generates refined asset
                    triples.append({
                        "subject": refined_entity.id,
                        "predicate": "prov:wasGeneratedBy",
                        "object": cell_id
                    })

                # Add outcomes
                for outcome_entity in extraction.get("outcomes", []):
                    node = outcome_entity.to_jsonld()
                    graph_nodes.append(node)
                    all_outcomes[outcome_entity.id] = outcome_entity

                    # Link cell produces outcome
                    triples.append({
                        "subject": cell_id,
                        "predicate": "da:produces",
                        "object": outcome_entity.id
                    })

                # Add provenance relationships from extraction
                for relationship in extraction.get("relationships", []):
                    triples.append(relationship.to_dict())

                logger.info(
                    f"✅ Cell {idx+1}: {len(extraction.get('data_assets', []))} assets, "
                    f"{len(extraction.get('transformations', []))} transformations, "
                    f"{len(extraction.get('outcomes', []))} outcomes"
                )

            except Exception as e:
                logger.warning(f"⚠️ Failed to extract semantics for cell {cell.id}: {e}")
                # Continue with next cell even if extraction fails
                continue

        # Create summary statistics
        analysis["metadata"]["total_cells"] = len(notebook.cells)
        analysis["metadata"]["total_assets"] = len(all_assets)
        analysis["metadata"]["total_transformations"] = len(all_transformations)
        analysis["metadata"]["total_outcomes"] = len(all_outcomes)
        analysis["metadata"]["total_triples"] = len(triples)

        # Add asset summary
        asset_types = defaultdict(int)
        for asset in all_assets.values():
            asset_type = asset.metadata.asset_type if asset.metadata else "unknown"
            asset_types[asset_type] += 1

        analysis["metadata"]["asset_types"] = dict(asset_types)

        analysis["@graph"] = graph_nodes
        analysis["triples"] = triples

        logger.info(
            f"📊 Analysis graph complete: {len(all_assets)} assets, "
            f"{len(all_transformations)} transformations, "
            f"{len(all_outcomes)} outcomes, "
            f"{len(triples)} relationships"
        )

        # ALWAYS cache the generated graph (even if use_cache=False for reading)
        # use_cache=False only means "don't read from cache", NOT "don't write to cache"
        self._cache_graph(notebook, 'analysis', analysis)

        return analysis
