"""
Persona Service for Digital Article.

Handles CRUD operations, persona combination, and prompt building.
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional
from uuid import UUID

from ..models.persona import (
    Persona,
    PersonaCategory,
    PersonaCombination,
    PersonaGuidance,
    PersonaScope,
    PersonaSelection,
    PersonaCreateRequest,
    PersonaUpdateRequest,
)


class PersonaService:
    """Service for managing personas and persona combinations."""

    def __init__(self, workspace_dir: Optional[str] = None):
        """Initialize persona service.

        Args:
            workspace_dir: Root workspace directory containing personas/ folder
                          If None, uses project root / "data"
        """
        self.logger = logging.getLogger(__name__)

        if workspace_dir is None:
            # Find project root (where backend/ directory is)
            current_file = Path(__file__).resolve()
            backend_dir = current_file.parent.parent.parent  # backend/app/services/ -> backend/
            project_root = backend_dir.parent  # backend/ -> project root
            workspace_dir = str(project_root / "data")

        self.workspace_dir = Path(workspace_dir)
        self.system_personas_dir = self.workspace_dir / "personas" / "system"
        self.custom_personas_dir = self.workspace_dir / "personas" / "custom"

        self.logger.info(f"📁 PersonaService initialized with workspace: {self.workspace_dir.resolve()}")
        self.logger.info(f"📁 System personas directory: {self.system_personas_dir.resolve()}")

        # Ensure directories exist
        self.system_personas_dir.mkdir(parents=True, exist_ok=True)
        self.custom_personas_dir.mkdir(parents=True, exist_ok=True)

        # Cache for loaded personas
        self._persona_cache: Dict[str, Persona] = {}

    # ===== CRUD Operations =====

    def get_persona(self, slug: str, username: Optional[str] = None) -> Optional[Persona]:
        """Get persona by slug.

        Args:
            slug: Persona slug identifier
            username: Username for custom personas (optional)

        Returns:
            Persona if found, None otherwise
        """
        # Check cache first
        cache_key = f"{username}:{slug}" if username else slug
        if cache_key in self._persona_cache:
            return self._persona_cache[cache_key]

        # Try system personas first
        system_path = self.system_personas_dir / f"{slug}.json"
        if system_path.exists():
            persona = self._load_persona_from_file(system_path)
            self._persona_cache[cache_key] = persona
            return persona

        # Try custom personas if username provided
        if username:
            custom_path = self.custom_personas_dir / username / f"{slug}.json"
            if custom_path.exists():
                persona = self._load_persona_from_file(custom_path)
                self._persona_cache[cache_key] = persona
                return persona

        return None

    def list_personas(
        self,
        username: Optional[str] = None,
        category: Optional[PersonaCategory] = None,
        include_inactive: bool = False,
    ) -> List[Persona]:
        """List all personas.

        Args:
            username: Username for custom personas (optional)
            category: Filter by category (optional)
            include_inactive: Include inactive personas (default: False)

        Returns:
            List of personas
        """
        self.logger.info(f"📋 Listing personas (username={username}, category={category}, include_inactive={include_inactive})")
        personas = []

        # Load system personas
        system_files = list(self.system_personas_dir.glob("*.json"))
        self.logger.info(f"📂 Found {len(system_files)} system persona files in {self.system_personas_dir}")
        for file_path in system_files:
            persona = self._load_persona_from_file(file_path)
            if persona:
                personas.append(persona)

        # Load custom personas if username provided
        if username:
            user_dir = self.custom_personas_dir / username
            if user_dir.exists():
                for file_path in user_dir.glob("*.json"):
                    persona = self._load_persona_from_file(file_path)
                    if persona:
                        personas.append(persona)

        # Apply filters
        if category:
            personas = [p for p in personas if p.category == category]

        if not include_inactive:
            personas = [p for p in personas if p.is_active]

        self.logger.info(f"✅ Returning {len(personas)} personas (after filtering)")
        return personas

    def create_persona(
        self,
        request: PersonaCreateRequest,
        username: str,
    ) -> Persona:
        """Create a new custom persona.

        Args:
            request: Persona creation request
            username: Username of creator

        Returns:
            Created persona

        Raises:
            ValueError: If slug already exists or username not provided
        """
        if not username:
            raise ValueError("Username required for creating custom personas")

        # Check if slug already exists
        if self.get_persona(request.slug, username):
            raise ValueError(f"Persona with slug '{request.slug}' already exists")

        # Create persona
        persona = Persona(
            name=request.name,
            slug=request.slug,
            description=request.description,
            icon=request.icon,
            color=request.color,
            category=request.category,
            priority=request.priority,
            is_system=False,
            expertise_description=request.expertise_description,
            domain_context=request.domain_context,
            methodology_style=request.methodology_style,
            guidance=request.guidance,
            preferred_libraries=request.preferred_libraries,
            avoid_libraries=request.avoid_libraries,
            preferred_methods=request.preferred_methods,
            review_capabilities=request.review_capabilities,
            created_by=username,
            tags=request.tags,
            compatible_with=request.compatible_with,
            incompatible_with=request.incompatible_with,
        )

        # Save to file
        user_dir = self.custom_personas_dir / username
        user_dir.mkdir(parents=True, exist_ok=True)

        file_path = user_dir / f"{persona.slug}.json"
        self._save_persona_to_file(persona, file_path)

        # Update cache
        cache_key = f"{username}:{persona.slug}"
        self._persona_cache[cache_key] = persona

        return persona

    def update_persona(
        self,
        slug: str,
        request: PersonaUpdateRequest,
        username: str,
    ) -> Optional[Persona]:
        """Update an existing custom persona.

        Args:
            slug: Persona slug identifier
            request: Update request
            username: Username of owner

        Returns:
            Updated persona, or None if not found or not custom

        Raises:
            ValueError: If trying to update system persona
        """
        persona = self.get_persona(slug, username)
        if not persona:
            return None

        if persona.is_system:
            raise ValueError("Cannot update system personas")

        # Update fields
        update_data = request.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(persona, field, value)

        # Save to file
        file_path = self.custom_personas_dir / username / f"{slug}.json"
        self._save_persona_to_file(persona, file_path)

        # Update cache
        cache_key = f"{username}:{slug}"
        self._persona_cache[cache_key] = persona

        return persona

    def delete_persona(self, slug: str, username: str) -> bool:
        """Delete a custom persona.

        Args:
            slug: Persona slug identifier
            username: Username of owner

        Returns:
            True if deleted, False if not found

        Raises:
            ValueError: If trying to delete system persona
        """
        persona = self.get_persona(slug, username)
        if not persona:
            return False

        if persona.is_system:
            raise ValueError("Cannot delete system personas")

        # Delete file
        file_path = self.custom_personas_dir / username / f"{slug}.json"
        if file_path.exists():
            file_path.unlink()

        # Remove from cache
        cache_key = f"{username}:{slug}"
        if cache_key in self._persona_cache:
            del self._persona_cache[cache_key]

        return True

    # ===== Combination Logic =====

    def combine_personas(
        self,
        selection: PersonaSelection,
        username: Optional[str] = None,
    ) -> PersonaCombination:
        """Combine multiple personas into effective guidance.

        Uses priority-based merging: lower priority number = applied last = wins conflicts.

        Args:
            selection: Persona selection
            username: Username for custom personas

        Returns:
            Combined persona guidance
        """
        # Load all selected personas
        personas = []

        # Base persona (required)
        base = self.get_persona(selection.base_persona, username)
        if base:
            personas.append(base)

        # Domain personas (optional)
        for slug in selection.domain_personas:
            persona = self.get_persona(slug, username)
            if persona:
                personas.append(persona)

        # Role modifier (optional)
        if selection.role_modifier:
            role = self.get_persona(selection.role_modifier, username)
            if role:
                personas.append(role)

        # Sort by priority (ascending - lower number = higher priority = applied last)
        personas.sort(key=lambda p: p.priority, reverse=True)

        # Merge guidance for each scope
        effective_guidance: Dict[PersonaScope, PersonaGuidance] = {}
        conflict_resolutions = []

        for scope in PersonaScope:
            merged = self._merge_guidance_for_scope(
                scope, personas, conflict_resolutions
            )
            if merged:
                effective_guidance[scope] = merged

        return PersonaCombination(
            effective_guidance=effective_guidance,
            source_personas=[p.slug for p in personas],
            conflict_resolutions=conflict_resolutions,
        )

    def _merge_guidance_for_scope(
        self,
        scope: PersonaScope,
        personas: List[Persona],
        conflict_log: List[str],
    ) -> Optional[PersonaGuidance]:
        """Merge guidance for a specific scope from multiple personas.

        Args:
            scope: The scope to merge guidance for
            personas: List of personas (sorted by priority, lowest priority first)
            conflict_log: List to append conflict resolutions to

        Returns:
            Merged guidance, or None if no guidance for scope
        """
        # Collect all guidance for this scope (including ALL guidance)
        guidance_items = []
        for persona in personas:
            for guidance in persona.guidance:
                if guidance.scope == scope or guidance.scope == PersonaScope.ALL:
                    guidance_items.append((persona, guidance))

        if not guidance_items:
            return None

        # Initialize merged guidance
        merged = PersonaGuidance(scope=scope)

        # Merge system prompt additions (concatenate in priority order)
        system_prompts = []
        for persona, guidance in guidance_items:
            if guidance.system_prompt_addition:
                system_prompts.append(
                    f"# {persona.name} Guidance:\n{guidance.system_prompt_addition}"
                )
        merged.system_prompt_addition = "\n\n".join(system_prompts)

        # Merge constraints (union, keeping track of sources)
        constraints_set = set()
        for _, guidance in guidance_items:
            constraints_set.update(guidance.constraints)
        merged.constraints = sorted(list(constraints_set))

        # Merge preferences (union, later personas' preferences take precedence)
        preferences_dict = {}
        for persona, guidance in guidance_items:
            for pref in guidance.preferences:
                preferences_dict[pref] = persona.slug  # Track source
        merged.preferences = list(preferences_dict.keys())

        # Merge examples (limit to last 3 examples)
        all_examples = []
        for _, guidance in reversed(guidance_items):  # Reverse to prioritize higher priority
            all_examples.extend(guidance.examples)
        merged.examples = all_examples[:3]

        # Merge user prompt modifications (last one wins)
        if guidance_items:
            last_persona, last_guidance = guidance_items[-1]
            merged.user_prompt_prefix = last_guidance.user_prompt_prefix
            merged.user_prompt_suffix = last_guidance.user_prompt_suffix
            if last_guidance.user_prompt_prefix or last_guidance.user_prompt_suffix:
                conflict_log.append(
                    f"{scope.value}: Using user prompt modifications from '{last_persona.name}'"
                )

        return merged

    # ===== Prompt Building Helpers =====

    def build_system_prompt_addition(
        self,
        combination: PersonaCombination,
        scope: PersonaScope,
    ) -> str:
        """Build system prompt addition for a specific scope.

        Args:
            combination: Combined persona guidance
            scope: The scope to build prompt for

        Returns:
            System prompt addition string
        """
        if scope not in combination.effective_guidance:
            return ""

        guidance = combination.effective_guidance[scope]
        parts = []

        # Add main system prompt addition
        if guidance.system_prompt_addition:
            parts.append(guidance.system_prompt_addition)

        # Add constraints as rules
        if guidance.constraints:
            constraints_text = "\n".join(f"- {c}" for c in guidance.constraints)
            parts.append(f"CRITICAL CONSTRAINTS:\n{constraints_text}")

        # Add preferences as guidance
        if guidance.preferences:
            preferences_text = "\n".join(f"- {p}" for p in guidance.preferences)
            parts.append(f"PREFERENCES:\n{preferences_text}")

        # Add examples if present
        if guidance.examples:
            examples_text = "\n\n".join(guidance.examples)
            parts.append(f"EXAMPLES:\n{examples_text}")

        return "\n\n".join(parts)

    def build_user_prompt_modifications(
        self,
        combination: PersonaCombination,
        scope: PersonaScope,
    ) -> tuple[str, str]:
        """Get user prompt prefix and suffix for a specific scope.

        Args:
            combination: Combined persona guidance
            scope: The scope to build prompt for

        Returns:
            Tuple of (prefix, suffix)
        """
        if scope not in combination.effective_guidance:
            return ("", "")

        guidance = combination.effective_guidance[scope]
        return (guidance.user_prompt_prefix, guidance.user_prompt_suffix)

    # ===== Helper Methods =====

    def _load_persona_from_file(self, file_path: Path) -> Optional[Persona]:
        """Load persona from JSON file.

        Args:
            file_path: Path to persona JSON file

        Returns:
            Loaded persona, or None if error
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                persona = Persona(**data)
                self.logger.debug(f"✅ Loaded persona: {persona.name} ({persona.slug})")
                return persona
        except Exception as e:
            self.logger.error(f"❌ Error loading persona from {file_path}: {e}")
            return None

    def _save_persona_to_file(self, persona: Persona, file_path: Path) -> None:
        """Save persona to JSON file.

        Args:
            persona: Persona to save
            file_path: Path to save to
        """
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(persona.model_dump(), f, indent=2, ensure_ascii=False, default=str)
