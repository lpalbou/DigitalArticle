"""
Persona API endpoints for Digital Article.

Provides REST API for persona CRUD operations and notebook persona selection.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from uuid import UUID

from ..models.persona import (
    Persona,
    PersonaCategory,
    PersonaCombination,
    PersonaCreateRequest,
    PersonaUpdateRequest,
    PersonaSelection,
    PersonaSelectionUpdateRequest,
)
from ..services.persona_service import PersonaService
from ..services.shared import notebook_service

# Initialize router
router = APIRouter(prefix="/api/personas", tags=["personas"])

# Initialize persona service (in production, this would be dependency injected)
persona_service = PersonaService()


def get_current_user() -> str:
    """Get current username from session.

    TODO: Integrate with actual auth system when available.
    For now, returns a default username.
    """
    import getpass
    return getpass.getuser()


# ===== Persona CRUD Endpoints =====

@router.get("", response_model=List[Persona])
async def list_personas(
    category: Optional[PersonaCategory] = Query(None, description="Filter by category"),
    include_inactive: bool = Query(False, description="Include inactive personas"),
    username: str = Depends(get_current_user),
):
    """List all personas (system + custom).

    Args:
        category: Optional category filter
        include_inactive: Include inactive personas
        username: Current username (from dependency)

    Returns:
        List of personas
    """
    try:
        personas = persona_service.list_personas(
            username=username,
            category=category,
            include_inactive=include_inactive,
        )
        return personas
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing personas: {str(e)}")


@router.get("/{slug}", response_model=Persona)
async def get_persona(
    slug: str,
    username: str = Depends(get_current_user),
):
    """Get a specific persona by slug.

    Args:
        slug: Persona slug identifier
        username: Current username (from dependency)

    Returns:
        Persona details

    Raises:
        HTTPException: 404 if persona not found
    """
    persona = persona_service.get_persona(slug, username)
    if not persona:
        raise HTTPException(status_code=404, detail=f"Persona '{slug}' not found")
    return persona


@router.post("", response_model=Persona, status_code=201)
async def create_persona(
    request: PersonaCreateRequest,
    username: str = Depends(get_current_user),
):
    """Create a new custom persona.

    Args:
        request: Persona creation request
        username: Current username (from dependency)

    Returns:
        Created persona

    Raises:
        HTTPException: 400 if slug already exists or validation error
    """
    try:
        persona = persona_service.create_persona(request, username)
        return persona
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating persona: {str(e)}")


@router.put("/{slug}", response_model=Persona)
async def update_persona(
    slug: str,
    request: PersonaUpdateRequest,
    username: str = Depends(get_current_user),
):
    """Update an existing custom persona.

    Args:
        slug: Persona slug identifier
        request: Update request
        username: Current username (from dependency)

    Returns:
        Updated persona

    Raises:
        HTTPException: 404 if not found, 400 if system persona
    """
    try:
        persona = persona_service.update_persona(slug, request, username)
        if not persona:
            raise HTTPException(status_code=404, detail=f"Persona '{slug}' not found")
        return persona
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating persona: {str(e)}")


@router.delete("/{slug}", status_code=204)
async def delete_persona(
    slug: str,
    username: str = Depends(get_current_user),
):
    """Delete a custom persona.

    Args:
        slug: Persona slug identifier
        username: Current username (from dependency)

    Raises:
        HTTPException: 404 if not found, 400 if system persona
    """
    try:
        success = persona_service.delete_persona(slug, username)
        if not success:
            raise HTTPException(status_code=404, detail=f"Persona '{slug}' not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting persona: {str(e)}")


# ===== Persona Combination Endpoint =====

@router.post("/combine", response_model=PersonaCombination)
async def combine_personas(
    selection: PersonaSelection,
    username: str = Depends(get_current_user),
):
    """Combine multiple personas and preview effective guidance.

    Useful for UI to show what the combined persona will look like.

    Args:
        selection: Persona selection
        username: Current username (from dependency)

    Returns:
        Combined persona guidance
    """
    try:
        combination = persona_service.combine_personas(selection, username)
        return combination
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error combining personas: {str(e)}")


# ===== Notebook Persona Selection Endpoints =====

@router.get("/notebooks/{notebook_id}/personas", response_model=Optional[PersonaSelection])
async def get_notebook_personas(
    notebook_id: str,
    username: str = Depends(get_current_user),
):
    """Get persona selection for a specific notebook.

    Args:
        notebook_id: Notebook UUID
        username: Current username (from dependency)

    Returns:
        Persona selection, or null if not set
    """
    try:
        # Load notebook from NotebookService
        notebook = notebook_service.get_notebook(notebook_id)

        # Get personas from metadata
        personas_data = notebook.metadata.get('personas')

        # Log for debugging
        print(f"📖 Loading personas for notebook {notebook_id}: {personas_data}")

        if not personas_data:
            # Return default selection if not set
            print(f"⚠️  No personas found, returning default 'clinical'")
            return PersonaSelection(
                base_persona='clinical',
                domain_personas=[],
                role_modifier=None,
                custom_overrides={},
            )

        return PersonaSelection(**personas_data)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load notebook personas: {str(e)}"
        )


@router.put("/notebooks/{notebook_id}/personas", response_model=PersonaSelection)
async def update_notebook_personas(
    notebook_id: str,
    request: PersonaSelectionUpdateRequest,
    username: str = Depends(get_current_user),
):
    """Update persona selection for a specific notebook.

    Args:
        notebook_id: Notebook UUID
        request: Persona selection update
        username: Current username (from dependency)

    Returns:
        Updated persona selection
    """
    try:
        # Load notebook from NotebookService
        notebook = notebook_service.get_notebook(notebook_id)

        # Create persona selection
        persona_selection = PersonaSelection(
            base_persona=request.base_persona,
            domain_personas=request.domain_personas or [],
            role_modifier=request.role_modifier,
            custom_overrides=request.custom_overrides or {},
        )

        # Update notebook metadata
        personas_dict = persona_selection.model_dump()
        notebook.metadata['personas'] = personas_dict

        # Save notebook
        notebook_service._save_notebook(notebook)

        # Log for debugging
        print(f"✅ Saved personas for notebook {notebook_id}: {personas_dict}")

        return persona_selection
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update notebook personas: {str(e)}"
        )
