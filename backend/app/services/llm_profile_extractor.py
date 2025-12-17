"""
LLM-based hierarchical profile extraction for Digital Article.

Extracts a rich, structured profile with:
- Domains: Top-level fields of expertise (Biomedical, Data Science, etc.)
- Categories: Mid-level specializations within domains
- Skills: Specific technical competencies
- Hierarchical relationships: Domain → Category → Skill

Uses LLM to understand context and infer implicit skills beyond simple
keyword matching.
"""

import json
import hashlib
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from abstractcore import create_llm
from ..models.notebook import Notebook, Cell
from ..models.semantics import ONTOLOGY_CONTEXT

logger = logging.getLogger(__name__)


class LLMProfileExtractor:
    """LLM-based hierarchical profile extraction."""

    def __init__(self, provider: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize the LLM profile extractor.

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
            logger.info(f"✅ Initialized LLM profile extractor: {self.provider}/{self.model}")
        except Exception as e:
            logger.error(f"❌ Failed to initialize LLM for profile extraction: {e}")
            self.llm = None

    def _generate_cache_key(self, notebook: Notebook) -> str:
        """Generate a cache key based on notebook content state."""
        cache_data = {
            "notebook_id": str(notebook.id),
            "title": notebook.title,
            "description": notebook.description,
            "cells": []
        }

        for cell in notebook.cells:
            cell_data = {
                "id": str(cell.id),
                "prompt": cell.prompt or "",
                "code": cell.code or "",
                "methodology": cell.scientific_explanation or ""
            }
            cache_data["cells"].append(cell_data)

        cache_json = json.dumps(cache_data, sort_keys=True)
        return hashlib.sha256(cache_json.encode()).hexdigest()

    def _get_cached_profile(self, notebook: Notebook) -> Optional[Dict[str, Any]]:
        """Get cached profile graph if valid."""
        cache_key = self._generate_cache_key(notebook)

        if hasattr(notebook, 'metadata') and isinstance(notebook.metadata, dict):
            cached_data = notebook.metadata.get("semantic_cache_profile_llm")

            if cached_data and isinstance(cached_data, dict):
                if cached_data.get("cache_key") == cache_key and cached_data.get("graph"):
                    logger.info(f"✅ Using cached LLM profile graph (key: {cache_key[:8]}...)")
                    return cached_data["graph"]

        return None

    def _cache_profile(self, notebook: Notebook, profile: Dict[str, Any]) -> None:
        """Cache the generated profile graph."""
        cache_key = self._generate_cache_key(notebook)

        if not hasattr(notebook, 'metadata') or not isinstance(notebook.metadata, dict):
            notebook.metadata = {}

        notebook.metadata["semantic_cache_profile_llm"] = {
            "cache_key": cache_key,
            "graph": profile,
            "cached_at": datetime.now().isoformat()
        }

        logger.info(f"💾 Cached LLM profile graph (key: {cache_key[:8]}...)")

    async def extract_profile(self, notebook: Notebook, use_cache: bool = True) -> Dict[str, Any]:
        """
        Extract hierarchical profile using LLM analysis.

        Args:
            notebook: The notebook to extract profile from
            use_cache: If True, use cached profile if available (default: True)

        Returns:
            JSON-LD with hierarchical Domain → Category → Skill structure
        """
        # Check cache first
        if use_cache:
            cached_profile = self._get_cached_profile(notebook)
            if cached_profile:
                return cached_profile

        if not self.llm:
            logger.error("❌ LLM not available for profile extraction")
            return self._empty_profile(notebook)

        logger.info("🔄 Extracting hierarchical profile using LLM...")

        # Build context from notebook
        context = self._build_extraction_context(notebook)

        # Create LLM prompts
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(context)

        # Call LLM (async for multi-user support)
        try:
            logger.info(f"🔍 Calling LLM for profile extraction...")
            response = await self.llm.agenerate(
                user_prompt,
                system_prompt=system_prompt,
                max_tokens=32000,
                max_output_tokens=8192,
                temperature=0.2  # Low temperature for consistent extraction
            )

            # Parse LLM response
            profile_data = self._parse_llm_response(response)

            # Convert to JSON-LD format
            profile_graph = self._build_jsonld_graph(notebook, profile_data)

            # Cache the result
            self._cache_profile(notebook, profile_graph)

            return profile_graph

        except Exception as e:
            logger.error(f"❌ LLM profile extraction failed: {e}")
            logger.error(f"   Traceback: {e}", exc_info=True)
            return self._empty_profile(notebook)

    def _build_extraction_context(self, notebook: Notebook) -> Dict[str, Any]:
        """Build rich context for LLM extraction."""
        context = {
            "notebook": {
                "title": notebook.title,
                "description": notebook.description,
                "author": notebook.author or "Anonymous"
            },
            "cells": []
        }

        for idx, cell in enumerate(notebook.cells, 1):
            cell_data = {
                "step": idx,
                "prompt": cell.prompt or "",
                "methodology": cell.scientific_explanation or "",
                "libraries": []
            }

            # Extract libraries from code
            if cell.code:
                import re
                import_pattern = r'import\s+(\w+)|from\s+(\w+)\s+import'
                matches = re.findall(import_pattern, cell.code)
                for match in matches:
                    lib = match[0] or match[1]
                    if lib and lib not in cell_data["libraries"]:
                        cell_data["libraries"].append(lib)

            context["cells"].append(cell_data)

        return context

    def _build_system_prompt(self) -> str:
        """Build system prompt for LLM profile extraction."""
        return """You are a professional skills analyzer for computational research notebooks.

Your task is to extract a hierarchical profile of the author's demonstrated expertise from their computational notebook.

# HIERARCHICAL STRUCTURE

Extract three levels of expertise:

1. **DOMAINS** (top-level fields):
   - Broad areas of expertise
   - Examples: "Biomedical Sciences", "Data Science", "Finance", "Social Science"

2. **CATEGORIES** (mid-level specializations):
   - Specific areas within domains
   - Under Biomedical: "Clinical Research", "Bioinformatics", "Medical Imaging", "Drug Development"
   - Under Data Science: "Machine Learning", "Statistics", "Data Visualization", "Big Data"

3. **SKILLS** (specific competencies):
   - Concrete technical skills
   - Under Clinical Research: "Survival Analysis", "PK/PD Modeling", "CDISC Standards"
   - Under Machine Learning: "Deep Learning", "Classification", "Clustering"

# PROFICIENCY LEVELS

For each skill, infer proficiency based on usage complexity:
- **Basic**: Simple usage, basic operations
- **Intermediate**: Moderate complexity, multiple operations
- **Advanced**: Complex workflows, custom implementations
- **Expert**: Sophisticated usage, domain-specific expertise

# EVIDENCE EXTRACTION

For each skill, provide brief evidence (1-3 items):
- What libraries/methods were used
- What analysis techniques were applied
- What domain-specific tasks were performed

# OUTPUT FORMAT

Return a JSON object with this exact structure:

```json
{
  "domains": [
    {
      "id": "biomedical",
      "name": "Biomedical Sciences",
      "confidence": 0.95
    }
  ],
  "categories": [
    {
      "id": "clinical_research",
      "name": "Clinical Research",
      "parent_domain": "biomedical"
    }
  ],
  "skills": [
    {
      "id": "survival_analysis",
      "name": "Survival Analysis",
      "parent_category": "clinical_research",
      "proficiency": "Advanced",
      "evidence": [
        "Used lifelines library",
        "Performed Kaplan-Meier analysis",
        "Applied Cox proportional hazards"
      ]
    }
  ]
}
```

# CRITICAL RULES

1. IDs must be lowercase with underscores (e.g., "clinical_research", not "Clinical Research")
2. Only include domains/categories/skills that have CLEAR EVIDENCE in the notebook
3. Be specific: "Survival Analysis" not "Statistics", "Deep Learning" not "Machine Learning"
4. Infer proficiency from complexity, not just presence
5. Provide concrete evidence, not generic descriptions
6. Group related skills under appropriate categories
7. Ensure all categories reference a valid domain
8. Ensure all skills reference a valid category

Return ONLY the JSON object, no other text."""

    def _build_user_prompt(self, context: Dict[str, Any]) -> str:
        """Build user prompt with notebook context."""
        notebook_info = context["notebook"]
        cells = context["cells"]

        prompt = f"""# NOTEBOOK TO ANALYZE

Title: {notebook_info['title']}
Description: {notebook_info['description']}

# ANALYSIS STEPS

"""

        for cell in cells:
            prompt += f"""
## Step {cell['step']}

**What was requested:**
{cell['prompt'] or 'No prompt provided'}

**What was done:**
{cell['methodology'] or 'No methodology available'}

**Libraries used:**
{', '.join(cell['libraries']) if cell['libraries'] else 'None detected'}

---
"""

        prompt += """
# EXTRACTION TASK

Based on the notebook above, extract the hierarchical profile with domains, categories, and skills.

Remember:
- Be specific and evidence-based
- Use the exact JSON format specified in the system prompt
- Infer proficiency levels from usage complexity
- Provide concrete evidence for each skill
- Only include what has clear evidence in the notebook

Return the JSON object now:"""

        return prompt

    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response into structured profile data."""
        try:
            # Try to extract JSON from response
            # LLM might wrap it in ```json...``` or include explanation
            import re

            # Look for JSON object in response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                profile_data = json.loads(json_str)
                return profile_data
            else:
                logger.error("❌ No JSON found in LLM response")
                return {"domains": [], "categories": [], "skills": []}

        except json.JSONDecodeError as e:
            logger.error(f"❌ Failed to parse LLM response as JSON: {e}")
            logger.error(f"   Response: {response[:500]}...")
            return {"domains": [], "categories": [], "skills": []}

    def _build_jsonld_graph(self, notebook: Notebook, profile_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert profile data to JSON-LD format."""
        graph = {
            "@context": ONTOLOGY_CONTEXT,
            "@graph": [],
            "triples": [],
            "metadata": {
                "graph_type": "profile",
                "layout_hint": "hierarchical",
                "notebook_id": str(notebook.id),
                "extracted_at": datetime.now().isoformat()
            }
        }

        # Create author/user node
        author_id = f"user:{notebook.author or 'anonymous'}"
        author_node = {
            "@id": author_id,
            "@type": "schema:Person",
            "schema:name": notebook.author or "Anonymous User",
            "dcterms:created": notebook.created_at.isoformat()
        }
        graph["@graph"].append(author_node)

        # Create domain nodes
        for domain in profile_data.get("domains", []):
            domain_id = f"domain:{domain['id']}"
            domain_node = {
                "@id": domain_id,
                "@type": "da:Domain",
                "schema:name": domain["name"],
                "da:confidence": domain.get("confidence", 0.8)
            }
            graph["@graph"].append(domain_node)

        # Create category nodes
        for category in profile_data.get("categories", []):
            category_id = f"category:{category['id']}"
            category_node = {
                "@id": category_id,
                "@type": "da:Category",
                "schema:name": category["name"],
                "da:parentDomain": f"domain:{category['parent_domain']}"
            }
            graph["@graph"].append(category_node)

            # Add domain → category relationship
            graph["triples"].append({
                "subject": f"domain:{category['parent_domain']}",
                "predicate": "da:contains",
                "object": category_id
            })

        # Create skill nodes
        for skill in profile_data.get("skills", []):
            skill_id = f"skill:{skill['id']}"
            skill_node = {
                "@id": skill_id,
                "@type": "da:Skill",
                "schema:name": skill["name"],
                "da:proficiency": skill.get("proficiency", "Intermediate"),
                "da:parentCategory": f"category:{skill['parent_category']}",
                "da:evidence": skill.get("evidence", [])
            }
            graph["@graph"].append(skill_node)

            # Add category → skill relationship
            graph["triples"].append({
                "subject": f"category:{skill['parent_category']}",
                "predicate": "da:contains",
                "object": skill_id
            })

            # Add user → skill relationship
            graph["triples"].append({
                "subject": author_id,
                "predicate": "schema:knowsAbout",
                "object": skill_id
            })

        return graph

    def _empty_profile(self, notebook: Notebook) -> Dict[str, Any]:
        """Return empty profile structure for error cases."""
        return {
            "@context": ONTOLOGY_CONTEXT,
            "@graph": [{
                "@id": f"user:{notebook.author or 'anonymous'}",
                "@type": "schema:Person",
                "schema:name": notebook.author or "Anonymous User"
            }],
            "triples": [],
            "metadata": {
                "graph_type": "profile",
                "layout_hint": "hierarchical",
                "notebook_id": str(notebook.id),
                "extracted_at": datetime.now().isoformat(),
                "error": "Failed to extract profile"
            }
        }
