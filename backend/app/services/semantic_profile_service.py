"""
Profile-focused semantic extraction for Digital Article.

Extracts high-level information about:
- User profile and attribution
- Data types and standards used
- Analysis categories and methodologies
- Technical and domain skills inferred
- Research interests and domains
"""

import re
from typing import Dict, List, Set, Any
from collections import defaultdict

from ..models.notebook import Notebook, Cell
from ..models.semantics import (
    NotebookSemantics, CellSemantics, Triple, SemanticEntity,
    EntityType, ONTOLOGY_CONTEXT
)


class SemanticProfileService:
    """Extract profile and high-level categorization from notebooks."""

    # Technical skills mapping from libraries/methods
    TECHNICAL_SKILLS = {
        "pandas": {"skill": "Data Manipulation", "level": "technical", "category": "data_science"},
        "numpy": {"skill": "Numerical Computing", "level": "technical", "category": "data_science"},
        "matplotlib": {"skill": "Data Visualization", "level": "technical", "category": "visualization"},
        "seaborn": {"skill": "Statistical Visualization", "level": "technical", "category": "visualization"},
        "plotly": {"skill": "Interactive Visualization", "level": "technical", "category": "visualization"},
        "scipy": {"skill": "Scientific Computing", "level": "technical", "category": "statistics"},
        "sklearn": {"skill": "Machine Learning", "level": "technical", "category": "machine_learning"},
        "statsmodels": {"skill": "Statistical Modeling", "level": "technical", "category": "statistics"},
        "tensorflow": {"skill": "Deep Learning", "level": "advanced", "category": "machine_learning"},
        "pytorch": {"skill": "Deep Learning", "level": "advanced", "category": "machine_learning"},
        "keras": {"skill": "Neural Networks", "level": "advanced", "category": "machine_learning"},
    }

    # Domain interest inference from keywords and data types
    DOMAIN_INTERESTS = {
        "bioinformatics": ["gene", "rna", "dna", "protein", "genomic", "sequencing", "fastq", "bam", "vcf"],
        "clinical_research": ["patient", "clinical", "trial", "diagnosis", "treatment", "medical", "health"],
        "finance": ["stock", "portfolio", "trading", "financial", "price", "market", "investment"],
        "social_science": ["survey", "respondent", "demographic", "social", "behavior", "psychology"],
        "image_analysis": ["image", "pixel", "opencv", "pillow", "segmentation", "detection"],
        "natural_language": ["text", "nlp", "sentiment", "tokeniz", "language", "corpus"],
        "time_series": ["time series", "temporal", "forecast", "trend", "seasonal"],
    }

    # Analysis type categorization
    ANALYSIS_CATEGORIES = {
        "exploratory_analysis": ["explore", "describe", "summary", "distribution", "overview"],
        "statistical_testing": ["test", "hypothesis", "p-value", "significance", "anova", "t-test"],
        "predictive_modeling": ["predict", "model", "train", "forecast", "regression", "classification"],
        "clustering": ["cluster", "kmeans", "hierarchical", "dbscan", "grouping"],
        "dimensionality_reduction": ["pca", "tsne", "umap", "factor analysis", "component"],
        "data_cleaning": ["clean", "missing", "impute", "outlier", "normalize", "preprocess"],
        "visualization": ["plot", "chart", "graph", "visualiz", "show", "display"],
    }

    # Data standards and formats
    DATA_STANDARDS = {
        "csv": {"type": "Tabular", "standard": "CSV", "domain": "general"},
        "xlsx": {"type": "Tabular", "standard": "Excel", "domain": "general"},
        "json": {"type": "Structured", "standard": "JSON", "domain": "general"},
        "parquet": {"type": "Columnar", "standard": "Parquet", "domain": "big_data"},
        "hdf5": {"type": "Hierarchical", "standard": "HDF5", "domain": "scientific"},
        "fastq": {"type": "Sequence", "standard": "FASTQ", "domain": "genomics"},
        "bam": {"type": "Alignment", "standard": "BAM", "domain": "genomics"},
        "vcf": {"type": "Variant", "standard": "VCF", "domain": "genomics"},
        "tiff": {"type": "Image", "standard": "TIFF", "domain": "imaging"},
        "dicom": {"type": "Medical Image", "standard": "DICOM", "domain": "medical"},
    }

    def extract_profile_graph(self, notebook: Notebook) -> Dict[str, Any]:
        """
        Extract profile-focused knowledge graph.

        Returns structured data with:
        - User profile
        - Data types and standards
        - Analysis categories
        - Skills (technical and domain)
        - Research interests
        """
        profile = {
            "@context": ONTOLOGY_CONTEXT,
            "@graph": [],
            "triples": [],
            "metadata": {
                "graph_type": "profile",
                "notebook_id": str(notebook.id),
                "extracted_at": notebook.updated_at.isoformat()
            }
        }

        graph_nodes = []
        triples = []

        # Create user/author node
        author_id = f"user:{notebook.author or 'anonymous'}"
        author_node = {
            "@id": author_id,
            "@type": "schema:Person",
            "schema:name": notebook.author or "Anonymous User",
            "dcterms:created": notebook.created_at.isoformat()
        }
        graph_nodes.append(author_node)

        # Link notebook to author
        notebook_id = f"notebook:{notebook.id}"
        triples.append({
            "subject": notebook_id,
            "predicate": "dcterms:creator",
            "object": author_id
        })

        # Collect skills, interests, data types
        skills = self._extract_skills(notebook)
        interests = self._extract_interests(notebook)
        data_types = self._extract_data_types(notebook)
        analysis_cats = self._extract_analysis_categories(notebook)

        # Create skill nodes
        for skill_id, skill_info in skills.items():
            skill_node = {
                "@id": skill_id,
                "@type": "schema:DefinedTerm",
                "schema:name": skill_info["skill"],
                "da:skillLevel": skill_info["level"],
                "da:skillCategory": skill_info["category"]
            }
            graph_nodes.append(skill_node)

            # Link user to skill
            triples.append({
                "subject": author_id,
                "predicate": "schema:knowsAbout",
                "object": skill_id
            })

        # Create interest/domain nodes
        for interest_id, interest_info in interests.items():
            interest_node = {
                "@id": interest_id,
                "@type": "skos:Concept",
                "skos:prefLabel": interest_info["domain"],
                "da:confidence": interest_info["confidence"]
            }
            graph_nodes.append(interest_node)

            # Link user to interest
            triples.append({
                "subject": author_id,
                "predicate": "schema:hasInterest",
                "object": interest_id
            })

        # Create data type nodes
        for data_id, data_info in data_types.items():
            data_node = {
                "@id": data_id,
                "@type": "schema:Dataset",
                "schema:name": data_info["name"],
                "da:dataType": data_info["type"],
                "da:dataStandard": data_info["standard"],
                "da:domain": data_info["domain"]
            }
            graph_nodes.append(data_node)

            # Link notebook to data type
            triples.append({
                "subject": notebook_id,
                "predicate": "da:usesDataType",
                "object": data_id
            })

        # Create analysis category nodes
        for cat_id, cat_info in analysis_cats.items():
            cat_node = {
                "@id": cat_id,
                "@type": "da:AnalysisCategory",
                "schema:name": cat_info["category"],
                "da:frequency": cat_info["count"]
            }
            graph_nodes.append(cat_node)

            # Link notebook to category
            triples.append({
                "subject": notebook_id,
                "predicate": "da:performsAnalysisType",
                "object": cat_id
            })

        profile["@graph"] = graph_nodes
        profile["triples"] = triples

        return profile

    def _extract_skills(self, notebook: Notebook) -> Dict[str, Dict]:
        """Extract technical and domain skills from library usage."""
        skills = {}

        for cell in notebook.cells:
            if not cell.code:
                continue

            # Extract libraries from code
            import_pattern = r'import\s+(\w+)|from\s+(\w+)\s+import'
            matches = re.findall(import_pattern, cell.code)

            for match in matches:
                lib = match[0] or match[1]
                lib_lower = lib.lower()

                if lib_lower in self.TECHNICAL_SKILLS:
                    skill_info = self.TECHNICAL_SKILLS[lib_lower]
                    skill_id = f"skill:{lib_lower}"
                    skills[skill_id] = skill_info

        return skills

    def _extract_interests(self, notebook: Notebook) -> Dict[str, Dict]:
        """Infer research interests from content."""
        interests = {}
        domain_scores = defaultdict(int)

        # Collect all text content
        all_text = f"{notebook.title} {notebook.description}".lower()

        for cell in notebook.cells:
            if cell.prompt:
                all_text += f" {cell.prompt.lower()}"
            if cell.scientific_explanation:
                all_text += f" {cell.scientific_explanation.lower()}"

        # Score each domain
        for domain, keywords in self.DOMAIN_INTERESTS.items():
            for keyword in keywords:
                count = len(re.findall(r'\b' + re.escape(keyword) + r'\b', all_text))
                domain_scores[domain] += count

        # Convert to interests (threshold: at least 2 mentions)
        for domain, score in domain_scores.items():
            if score >= 2:
                interest_id = f"interest:{domain}"
                interests[interest_id] = {
                    "domain": domain.replace("_", " ").title(),
                    "confidence": min(score / 10.0, 1.0)  # Normalize to 0-1
                }

        return interests

    def _extract_data_types(self, notebook: Notebook) -> Dict[str, Dict]:
        """Extract data types and standards from dataset usage."""
        data_types = {}
        seen_extensions = set()

        for cell in notebook.cells:
            if not cell.prompt:
                continue

            # Extract file extensions
            file_pattern = r'\b[\w\-]+\.(csv|xlsx|xls|json|parquet|h5|hdf5|fastq|bam|vcf|tiff|dicom)\b'
            matches = re.findall(file_pattern, cell.prompt.lower())

            for ext in matches:
                if ext not in seen_extensions:
                    seen_extensions.add(ext)

                    if ext in self.DATA_STANDARDS:
                        std_info = self.DATA_STANDARDS[ext]
                        data_id = f"datatype:{ext}"
                        data_types[data_id] = {
                            "name": f"{ext.upper()} Data",
                            **std_info
                        }

        return data_types

    def _extract_analysis_categories(self, notebook: Notebook) -> Dict[str, Dict]:
        """Categorize the types of analyses performed."""
        categories = {}
        category_counts = defaultdict(int)

        # Collect all text
        all_text = ""
        for cell in notebook.cells:
            if cell.prompt:
                all_text += f" {cell.prompt.lower()}"
            if cell.code:
                all_text += f" {cell.code.lower()}"

        # Score each category
        for category, keywords in self.ANALYSIS_CATEGORIES.items():
            for keyword in keywords:
                count = len(re.findall(r'\b' + re.escape(keyword) + r'\b', all_text))
                category_counts[category] += count

        # Convert to categories (threshold: at least 1 mention)
        for category, count in category_counts.items():
            if count >= 1:
                cat_id = f"analysis:{category}"
                categories[cat_id] = {
                    "category": category.replace("_", " ").title(),
                    "count": count
                }

        return categories
