"""
Semantic data models for Digital Article knowledge graph.

This module defines data structures for representing semantic knowledge extracted
from notebooks, cells, and execution results as RDF-style triples in JSON-LD format.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Union
from uuid import UUID
from pydantic import BaseModel, Field


# Standard ontology namespaces
ONTOLOGY_CONTEXT = {
    "dcterms": "http://purl.org/dc/terms/",
    "schema": "https://schema.org/",
    "skos": "http://www.w3.org/2004/02/skos/core#",
    "cito": "http://purl.org/spar/cito/",
    "prov": "http://www.w3.org/ns/prov#",
    "stato": "http://purl.obolibrary.org/obo/STATO_",
    "dcat": "http://www.w3.org/ns/dcat#",
    "da": "https://digitalarticle.org/ontology#",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
}


class EntityType(str, Enum):
    """Types of semantic entities."""
    NOTEBOOK = "notebook"
    CELL = "cell"
    DATASET = "dataset"
    VARIABLE = "variable"
    METHOD = "method"
    LIBRARY = "library"
    VISUALIZATION = "visualization"
    FINDING = "finding"
    CONCEPT = "concept"
    CLAIM = "claim"
    TRANSFORMATION = "transformation"
    USER = "user"
    REFINED_ASSET = "refined_asset"


class ConfidentialityLevel(str, Enum):
    """Data confidentiality levels."""
    C1_PUBLIC = "C1"  # Public data
    C2_INTERNAL = "C2"  # Internal use
    C3_CONFIDENTIAL = "C3"  # Confidential
    C4_RESTRICTED = "C4"  # Highly restricted


class AssetMetadata(BaseModel):
    """Rich metadata for data assets."""
    label: str  # Human-readable label
    asset_type: str  # Ontology type (e.g., "dcat:Dataset", "da:Variable")
    confidentiality: ConfidentialityLevel = ConfidentialityLevel.C2_INTERNAL
    created: datetime = Field(default_factory=datetime.now)
    owner: Optional[str] = None  # User ID or author
    description: Optional[str] = None
    provenance: List[str] = Field(default_factory=list)  # prov:wasDerivedFrom URIs

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON-LD properties."""
        return {
            "rdfs:label": self.label,
            "rdf:type": self.asset_type,
            "da:confidentiality": self.confidentiality.value,
            "dcterms:created": self.created.isoformat(),
            "dcterms:creator": self.owner,
            "dcterms:description": self.description,
            "prov:wasDerivedFrom": self.provenance
        }


class Triple(BaseModel):
    """RDF-style triple (subject, predicate, object)."""

    subject: str
    predicate: str
    object: Union[str, int, float, bool]
    object_type: Optional[str] = None  # Optional: type of the object entity
    confidence: float = 1.0  # Confidence score (0-1) for extracted knowledge

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        result = {
            "subject": self.subject,
            "predicate": self.predicate,
            "object": self.object
        }
        if self.object_type:
            result["object_type"] = self.object_type
        if self.confidence < 1.0:
            result["confidence"] = self.confidence
        return result


class SemanticEntity(BaseModel):
    """A semantic entity (subject or object in triples)."""

    id: str  # URI or CURIE (e.g., "cell:uuid", "dataset:filename")
    type: EntityType
    label: str  # Human-readable label
    properties: Dict[str, Any] = Field(default_factory=dict)  # Additional properties
    metadata: Optional[AssetMetadata] = None  # Rich metadata for assets

    def to_jsonld(self) -> Dict[str, Any]:
        """Convert to JSON-LD node representation."""
        node = {
            "@id": self.id,
            "@type": f"da:{self.type.value.capitalize()}",
            "rdfs:label": self.label
        }

        # Add rich metadata if available
        if self.metadata:
            node.update(self.metadata.to_dict())

        # Add additional properties
        node.update(self.properties)
        return node


class CellSemantics(BaseModel):
    """Semantic information extracted from a single cell."""

    cell_id: str
    entities: List[SemanticEntity] = Field(default_factory=list)
    triples: List[Triple] = Field(default_factory=list)
    extracted_at: datetime = Field(default_factory=datetime.now)

    # Structured extraction results
    intent_tags: List[str] = Field(default_factory=list)  # e.g., ["data_loading", "visualization"]
    methods_used: List[str] = Field(default_factory=list)  # e.g., ["histogram", "t-test"]
    libraries_used: List[str] = Field(default_factory=list)  # e.g., ["pandas", "matplotlib"]
    datasets_used: List[str] = Field(default_factory=list)  # e.g., ["gene_expression.csv"]
    variables_defined: List[str] = Field(default_factory=list)  # e.g., ["df", "corr_matrix"]
    concepts_mentioned: List[str] = Field(default_factory=list)  # e.g., ["gene_expression", "correlation"]
    statistical_findings: List[Dict[str, Any]] = Field(default_factory=list)  # Extracted stats

    def to_jsonld(self) -> Dict[str, Any]:
        """Convert to JSON-LD format for storage and export."""
        return {
            "cell_id": self.cell_id,
            "entities": [entity.to_jsonld() for entity in self.entities],
            "triples": [triple.to_dict() for triple in self.triples],
            "extracted_at": self.extracted_at.isoformat(),
            "intent_tags": self.intent_tags,
            "methods_used": self.methods_used,
            "libraries_used": self.libraries_used,
            "datasets_used": self.datasets_used,
            "variables_defined": self.variables_defined,
            "concepts_mentioned": self.concepts_mentioned,
            "statistical_findings": self.statistical_findings
        }

    @classmethod
    def from_jsonld(cls, data: Dict[str, Any]) -> "CellSemantics":
        """Create from JSON-LD format."""
        entities = [
            SemanticEntity(
                id=e["@id"],
                type=EntityType(e["@type"].replace("da:", "").lower()),
                label=e.get("rdfs:label", ""),
                properties={k: v for k, v in e.items() if k not in ["@id", "@type", "rdfs:label"]}
            )
            for e in data.get("entities", [])
        ]

        triples = [
            Triple(
                subject=t["subject"],
                predicate=t["predicate"],
                object=t["object"],
                object_type=t.get("object_type"),
                confidence=t.get("confidence", 1.0)
            )
            for t in data.get("triples", [])
        ]

        return cls(
            cell_id=data["cell_id"],
            entities=entities,
            triples=triples,
            extracted_at=datetime.fromisoformat(data["extracted_at"]),
            intent_tags=data.get("intent_tags", []),
            methods_used=data.get("methods_used", []),
            libraries_used=data.get("libraries_used", []),
            datasets_used=data.get("datasets_used", []),
            variables_defined=data.get("variables_defined", []),
            concepts_mentioned=data.get("concepts_mentioned", []),
            statistical_findings=data.get("statistical_findings", [])
        )


class NotebookSemantics(BaseModel):
    """Aggregated semantic information for an entire notebook."""

    notebook_id: str
    cell_semantics: List[CellSemantics] = Field(default_factory=list)
    global_entities: List[SemanticEntity] = Field(default_factory=list)  # Notebook-level entities
    global_triples: List[Triple] = Field(default_factory=list)  # Notebook-level relationships
    extracted_at: datetime = Field(default_factory=datetime.now)

    def to_jsonld_graph(self) -> Dict[str, Any]:
        """Convert to full JSON-LD graph representation."""
        graph_nodes = []

        # Add notebook-level entities
        for entity in self.global_entities:
            graph_nodes.append(entity.to_jsonld())

        # Add cell-level entities
        for cell_sem in self.cell_semantics:
            for entity in cell_sem.entities:
                graph_nodes.append(entity.to_jsonld())

        # Collect all triples
        all_triples = self.global_triples + [
            triple for cell_sem in self.cell_semantics for triple in cell_sem.triples
        ]

        return {
            "@context": ONTOLOGY_CONTEXT,
            "@graph": graph_nodes,
            "triples": [triple.to_dict() for triple in all_triples],
            "metadata": {
                "notebook_id": self.notebook_id,
                "extracted_at": self.extracted_at.isoformat(),
                "total_cells": len(self.cell_semantics),
                "total_entities": len(graph_nodes),
                "total_triples": len(all_triples)
            }
        }

    def get_all_datasets(self) -> List[str]:
        """Get all datasets referenced in the notebook."""
        datasets = set()
        for cell_sem in self.cell_semantics:
            datasets.update(cell_sem.datasets_used)
        return sorted(list(datasets))

    def get_all_methods(self) -> List[str]:
        """Get all methods/techniques used in the notebook."""
        methods = set()
        for cell_sem in self.cell_semantics:
            methods.update(cell_sem.methods_used)
        return sorted(list(methods))

    def get_all_libraries(self) -> List[str]:
        """Get all libraries used in the notebook."""
        libraries = set()
        for cell_sem in self.cell_semantics:
            libraries.update(cell_sem.libraries_used)
        return sorted(list(libraries))

    def get_all_concepts(self) -> List[str]:
        """Get all domain concepts mentioned in the notebook."""
        concepts = set()
        for cell_sem in self.cell_semantics:
            concepts.update(cell_sem.concepts_mentioned)
        return sorted(list(concepts))


class SemanticSearchQuery(BaseModel):
    """Query for semantic search across notebooks."""

    method: Optional[str] = None  # Search by method
    dataset: Optional[str] = None  # Search by dataset
    library: Optional[str] = None  # Search by library
    concept: Optional[str] = None  # Search by concept
    entity_type: Optional[EntityType] = None  # Filter by entity type
    min_confidence: float = 0.5  # Minimum confidence threshold


class SemanticSearchResult(BaseModel):
    """Result from semantic search."""

    notebook_id: str
    notebook_title: str
    cell_id: Optional[str] = None
    match_type: str  # "exact", "partial", "related"
    relevance_score: float
    matched_entities: List[str] = Field(default_factory=list)
    snippet: Optional[str] = None  # Relevant text snippet
