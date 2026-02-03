"""
Trace API for observability (ADR 0005).

Provides endpoints to query and view persistent traces of LLM and agentic operations.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ..models.trace import StepType, TraceEvent, TraceLevel, TraceStatus
from ..services.trace_store import get_trace_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/traces", tags=["traces"])


class TraceQueryResponse(BaseModel):
    """Response model for trace queries."""
    traces: List[TraceEvent]
    count: int
    has_more: bool


class FlowSummary(BaseModel):
    """Summary of a flow for list views."""
    flow_id: str
    started_at: datetime
    ended_at: Optional[datetime]
    status: TraceStatus
    notebook_id: Optional[str]
    cell_id: Optional[str]
    step_count: int
    step_types: List[str]
    total_tokens: Optional[int]
    total_duration_ms: Optional[float]


@router.get("/query", response_model=TraceQueryResponse)
async def query_traces(
    flow_id: Optional[str] = Query(None, description="Filter by flow ID"),
    notebook_id: Optional[str] = Query(None, description="Filter by notebook ID"),
    cell_id: Optional[str] = Query(None, description="Filter by cell ID"),
    step_type: Optional[StepType] = Query(None, description="Filter by step type"),
    since_hours: Optional[int] = Query(24, description="Return traces from the last N hours"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of traces to return"),
) -> TraceQueryResponse:
    """
    Query traces with optional filters.
    
    Returns traces matching the specified criteria, ordered by time (newest first).
    """
    try:
        trace_store = get_trace_store()
        
        since = datetime.now() - timedelta(hours=since_hours) if since_hours else None
        
        traces = trace_store.query(
            flow_id=flow_id,
            notebook_id=notebook_id,
            cell_id=cell_id,
            step_type=step_type,
            since=since,
            limit=limit + 1,  # Fetch one extra to detect has_more
        )
        
        has_more = len(traces) > limit
        if has_more:
            traces = traces[:limit]
        
        return TraceQueryResponse(
            traces=traces,
            count=len(traces),
            has_more=has_more,
        )
        
    except Exception as e:
        logger.error(f"Error querying traces: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to query traces: {str(e)}")


@router.get("/flow/{flow_id}", response_model=TraceQueryResponse)
async def get_flow(flow_id: str) -> TraceQueryResponse:
    """
    Get all events for a specific flow, ordered by time.
    
    This returns the complete execution trace for a flow (e.g., a cell execution
    with all its LLM calls, retries, and sub-operations).
    """
    try:
        trace_store = get_trace_store()
        traces = trace_store.get_flow(flow_id)
        
        return TraceQueryResponse(
            traces=traces,
            count=len(traces),
            has_more=False,
        )
        
    except Exception as e:
        logger.error(f"Error getting flow {flow_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get flow: {str(e)}")


@router.get("/flows", response_model=List[FlowSummary])
async def list_flows(
    notebook_id: Optional[str] = Query(None, description="Filter by notebook ID"),
    since_hours: int = Query(24, description="Return flows from the last N hours"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of flows to return"),
) -> List[FlowSummary]:
    """
    List recent flows with summary information.
    
    This provides a high-level view of recent operations without full trace details.
    """
    try:
        trace_store = get_trace_store()
        
        since = datetime.now() - timedelta(hours=since_hours)
        
        # Query flow-level events
        flow_events = trace_store.query(
            notebook_id=notebook_id,
            since=since,
            limit=limit * 10,  # Fetch more to group by flow
        )
        
        # Group by flow_id and build summaries
        flows: dict = {}
        for event in flow_events:
            if event.flow_id not in flows:
                flows[event.flow_id] = {
                    'events': [],
                    'step_types': set(),
                    'total_tokens': 0,
                    'total_duration_ms': 0,
                }
            
            flows[event.flow_id]['events'].append(event)
            flows[event.flow_id]['step_types'].add(event.step_type)
            
            if event.llm_total_tokens:
                flows[event.flow_id]['total_tokens'] += event.llm_total_tokens
            if event.duration_ms:
                flows[event.flow_id]['total_duration_ms'] += event.duration_ms
        
        # Build summaries
        summaries = []
        for flow_id, data in flows.items():
            events = sorted(data['events'], key=lambda e: e.started_at)
            if not events:
                continue
            
            first = events[0]
            last = events[-1]
            
            # Determine overall status
            statuses = [e.status for e in events]
            if TraceStatus.ERROR in statuses:
                overall_status = TraceStatus.ERROR
            elif all(s == TraceStatus.SUCCESS for s in statuses):
                overall_status = TraceStatus.SUCCESS
            elif TraceStatus.STARTED in statuses:
                overall_status = TraceStatus.STARTED
            else:
                overall_status = TraceStatus.SUCCESS
            
            summaries.append(FlowSummary(
                flow_id=flow_id,
                started_at=first.started_at,
                ended_at=last.ended_at,
                status=overall_status,
                notebook_id=first.notebook_id,
                cell_id=first.cell_id,
                step_count=len(events),
                step_types=list(data['step_types']),
                total_tokens=data['total_tokens'] or None,
                total_duration_ms=data['total_duration_ms'] or None,
            ))
        
        # Sort by started_at descending and limit
        summaries.sort(key=lambda s: s.started_at, reverse=True)
        return summaries[:limit]
        
    except Exception as e:
        logger.error(f"Error listing flows: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list flows: {str(e)}")


@router.get("/cell/{notebook_id}/{cell_id}", response_model=TraceQueryResponse)
async def get_cell_traces(
    notebook_id: str,
    cell_id: str,
    since_hours: int = Query(168, description="Return traces from the last N hours (default: 1 week)"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of traces to return"),
) -> TraceQueryResponse:
    """
    Get all traces for a specific cell.
    
    Useful for debugging a specific cell's execution history.
    """
    try:
        trace_store = get_trace_store()
        
        since = datetime.now() - timedelta(hours=since_hours)
        
        traces = trace_store.query(
            notebook_id=notebook_id,
            cell_id=cell_id,
            since=since,
            limit=limit + 1,
        )
        
        has_more = len(traces) > limit
        if has_more:
            traces = traces[:limit]
        
        return TraceQueryResponse(
            traces=traces,
            count=len(traces),
            has_more=has_more,
        )
        
    except Exception as e:
        logger.error(f"Error getting cell traces: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get cell traces: {str(e)}")


@router.delete("/cleanup")
async def cleanup_old_traces(
    retention_days: int = Query(30, ge=1, le=365, description="Remove traces older than N days"),
) -> dict:
    """
    Remove old trace files to free disk space.
    
    This removes archived trace files older than the specified retention period.
    """
    try:
        trace_store = get_trace_store()
        removed = trace_store.cleanup_old_traces(retention_days)
        
        return {
            "status": "success",
            "files_removed": removed,
            "retention_days": retention_days,
        }
        
    except Exception as e:
        logger.error(f"Error cleaning up traces: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to cleanup traces: {str(e)}")
