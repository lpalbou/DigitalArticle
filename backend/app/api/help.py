"""
Help / Documentation API endpoints.

Exposes internal docs (repo `docs/`) and an optional product overview PDF for the frontend Help modal.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel

from ..services.help_service import HelpService


router = APIRouter(prefix="/api/help", tags=["help"])


class HelpDoc(BaseModel):
    doc_id: str
    title: str


class HelpInfoResponse(BaseModel):
    contact_email: str
    pdf_available: bool
    pdf_url: str
    docs: list[HelpDoc]


class HelpDocContentResponse(BaseModel):
    doc_id: str
    title: str
    content: str


class HelpSearchHitResponse(BaseModel):
    doc_id: str
    title: str
    snippet: str


@router.get("/info", response_model=HelpInfoResponse)
async def get_help_info():
    service = HelpService()
    docs = [HelpDoc(doc_id=e.doc_id, title=e.title) for e in service.get_docs_index()]
    return HelpInfoResponse(
        contact_email=service.get_contact_email(),
        pdf_available=service.pdf_available(),
        pdf_url="/api/help/digital-article.pdf",
        docs=docs,
    )


@router.get("/docs/{doc_id:path}", response_model=HelpDocContentResponse)
async def get_help_doc(doc_id: str):
    service = HelpService()
    try:
        content = service.read_doc(doc_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Doc not found: {doc_id}")
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read doc: {e}")

    # Find title from the index (deterministic); fallback to doc_id
    title = next((d.title for d in service.get_docs_index() if d.doc_id == doc_id), doc_id)
    return HelpDocContentResponse(doc_id=doc_id, title=title, content=content)


@router.get("/search", response_model=list[HelpSearchHitResponse])
async def search_docs(q: str = Query(..., min_length=1, max_length=200), limit: int = Query(20, ge=1, le=50)):
    service = HelpService()
    hits = service.search(query=q, limit=limit)
    return [HelpSearchHitResponse(doc_id=h.doc_id, title=h.title, snippet=h.snippet) for h in hits]


@router.get("/digital-article.pdf")
async def get_digital_article_pdf():
    """
    Serve the product overview PDF if present at `untracked/digital-article.pdf`.

    Note: This file is intentionally not committed; deployments should mount it if they want it available.
    """
    service = HelpService()
    pdf_path = service.get_pdf_path()
    if not service.pdf_available():
        raise HTTPException(status_code=404, detail="digital-article.pdf not available on this deployment")

    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        filename="digital-article.pdf",
        # Critical for iframe rendering: default is "attachment" which triggers download.
        content_disposition_type="inline",
    )

