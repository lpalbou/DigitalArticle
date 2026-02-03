"""
Trace Store Service for persistent observability (ADR 0005).

Implements an append-only JSONL trace store with:
- Persistent storage (survives restarts)
- Query by flow_id, notebook_id, cell_id, time range
- Automatic rotation and retention
- Secret redaction before storage
"""

import json
import logging
import os
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from ..config import config
from ..models.trace import (
    TraceEvent,
    TraceLevel,
    TraceStatus,
    StepType,
    redact_secrets,
    truncate_for_storage,
)

logger = logging.getLogger(__name__)


class TraceStore:
    """
    Append-only JSONL trace store for LLM and agentic observability.
    
    Storage layout:
        {workspace_root}/traces/
            traces.jsonl           # Current active trace file
            traces.2026-02-01.jsonl  # Rotated daily archives
            index.json             # Optional index for fast lookups
    """
    
    # Maximum prompt/response length to store (per ADR 0003: explicit truncation)
    MAX_PROMPT_LENGTH = 10000
    MAX_RESPONSE_LENGTH = 20000
    MAX_CODE_LENGTH = 10000
    
    # Rotation settings
    MAX_FILE_SIZE_MB = 50
    RETENTION_DAYS = 30
    
    _instance: Optional["TraceStore"] = None
    _lock = threading.Lock()
    
    def __new__(cls) -> "TraceStore":
        """Singleton pattern for trace store."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._traces_dir = Path(config.get_workspace_root()) / "traces"
        self._traces_dir.mkdir(parents=True, exist_ok=True)
        self._current_file = self._traces_dir / "traces.jsonl"
        self._write_lock = threading.Lock()
        self._initialized = True
        
        logger.info(f"📊 TraceStore initialized at {self._traces_dir}")
    
    def _get_current_file(self) -> Path:
        """Get current trace file, rotating if needed."""
        if self._current_file.exists():
            size_mb = self._current_file.stat().st_size / (1024 * 1024)
            if size_mb >= self.MAX_FILE_SIZE_MB:
                self._rotate_file()
        return self._current_file
    
    def _rotate_file(self):
        """Rotate current trace file to dated archive."""
        if not self._current_file.exists():
            return
        
        date_str = datetime.now().strftime("%Y-%m-%d-%H%M%S")
        archive_name = f"traces.{date_str}.jsonl"
        archive_path = self._traces_dir / archive_name
        
        try:
            self._current_file.rename(archive_path)
            logger.info(f"📦 Rotated trace file to {archive_name}")
        except Exception as e:
            logger.error(f"Failed to rotate trace file: {e}")
    
    def emit(self, event: TraceEvent) -> str:
        """
        Emit a trace event to the store.
        
        Applies redaction and truncation before storage.
        
        Args:
            event: TraceEvent to store
            
        Returns:
            The step_id of the stored event
        """
        # Convert to dict for modification, apply redaction/truncation, then serialize
        data = event.model_dump()
        
        # Apply redaction to sensitive fields
        if data.get("llm_prompt"):
            data["llm_prompt"] = redact_secrets(
                truncate_for_storage(data["llm_prompt"], self.MAX_PROMPT_LENGTH)
            )
        if data.get("llm_system_prompt"):
            data["llm_system_prompt"] = redact_secrets(
                truncate_for_storage(data["llm_system_prompt"], self.MAX_PROMPT_LENGTH)
            )
        if data.get("llm_response"):
            data["llm_response"] = truncate_for_storage(data["llm_response"], self.MAX_RESPONSE_LENGTH)
        if data.get("exec_code"):
            data["exec_code"] = truncate_for_storage(data["exec_code"], self.MAX_CODE_LENGTH)
        if data.get("exec_stdout"):
            data["exec_stdout"] = truncate_for_storage(data["exec_stdout"], self.MAX_RESPONSE_LENGTH)
        if data.get("exec_stderr"):
            data["exec_stderr"] = truncate_for_storage(data["exec_stderr"], self.MAX_RESPONSE_LENGTH)
        
        # Serialize and append
        try:
            # Convert datetime objects to ISO format for JSON serialization
            for key in ["started_at", "ended_at"]:
                if data.get(key) and isinstance(data[key], datetime):
                    data[key] = data[key].isoformat()
            
            line = json.dumps(data) + "\n"
            
            with self._write_lock:
                trace_file = self._get_current_file()
                with open(trace_file, "a", encoding="utf-8") as f:
                    f.write(line)
            
            logger.debug(f"📝 Trace emitted: {event.step_type} ({event.step_id[:8]}...)")
            return event.step_id
            
        except Exception as e:
            logger.error(f"Failed to emit trace: {e}")
            return event.step_id
    
    def start_flow(
        self,
        notebook_id: Optional[str] = None,
        cell_id: Optional[str] = None,
        step_type: StepType = StepType.CODE_EXECUTION,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Start a new flow (root-level operation).
        
        Returns:
            flow_id for linking child tasks/steps
        """
        flow_id = str(uuid4())
        
        event = TraceEvent(
            step_id=flow_id,
            flow_id=flow_id,
            level=TraceLevel.FLOW,
            step_type=step_type,
            status=TraceStatus.STARTED,
            notebook_id=notebook_id,
            cell_id=cell_id,
            metadata=metadata or {},
        )
        
        self.emit(event)
        return flow_id
    
    def start_task(
        self,
        flow_id: str,
        step_type: StepType,
        notebook_id: Optional[str] = None,
        cell_id: Optional[str] = None,
        parent_step_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Start a new task within a flow.
        
        Returns:
            task_id for linking child steps
        """
        task_id = str(uuid4())
        
        event = TraceEvent(
            step_id=task_id,
            flow_id=flow_id,
            task_id=task_id,
            parent_step_id=parent_step_id or flow_id,
            level=TraceLevel.TASK,
            step_type=step_type,
            status=TraceStatus.STARTED,
            notebook_id=notebook_id,
            cell_id=cell_id,
            metadata=metadata or {},
        )
        
        self.emit(event)
        return task_id
    
    def start_step(
        self,
        flow_id: str,
        task_id: str,
        step_type: StepType,
        notebook_id: Optional[str] = None,
        cell_id: Optional[str] = None,
        parent_step_id: Optional[str] = None,
        **kwargs,
    ) -> str:
        """
        Start a new step within a task.
        
        Additional kwargs are passed to TraceEvent (e.g., llm_provider, llm_model).
        
        Returns:
            step_id
        """
        step_id = str(uuid4())
        
        event = TraceEvent(
            step_id=step_id,
            flow_id=flow_id,
            task_id=task_id,
            parent_step_id=parent_step_id or task_id,
            level=TraceLevel.STEP,
            step_type=step_type,
            status=TraceStatus.STARTED,
            notebook_id=notebook_id,
            cell_id=cell_id,
            **kwargs,
        )
        
        self.emit(event)
        return step_id
    
    def complete_step(
        self,
        step_id: str,
        flow_id: str,
        task_id: Optional[str],
        step_type: StepType,
        status: TraceStatus = TraceStatus.SUCCESS,
        started_at: Optional[datetime] = None,
        notebook_id: Optional[str] = None,
        cell_id: Optional[str] = None,
        error_message: Optional[str] = None,
        error_type: Optional[str] = None,
        **kwargs,
    ) -> None:
        """
        Complete a step with final status and timing.
        
        This emits a completion event linked to the original step.
        """
        ended_at = datetime.now()
        duration_ms = None
        if started_at:
            duration_ms = (ended_at - started_at).total_seconds() * 1000
        
        event = TraceEvent(
            step_id=step_id,
            flow_id=flow_id,
            task_id=task_id,
            level=TraceLevel.STEP,
            step_type=step_type,
            status=status,
            started_at=started_at or ended_at,
            ended_at=ended_at,
            duration_ms=duration_ms,
            notebook_id=notebook_id,
            cell_id=cell_id,
            error_message=error_message,
            error_type=error_type,
            **kwargs,
        )
        
        self.emit(event)
    
    def query(
        self,
        flow_id: Optional[str] = None,
        notebook_id: Optional[str] = None,
        cell_id: Optional[str] = None,
        step_type: Optional[StepType] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[TraceEvent]:
        """
        Query traces with filters.
        
        Scans the trace file(s) and returns matching events.
        For production, this should use an index or database.
        """
        results: List[TraceEvent] = []
        
        # Collect all trace files (current + archives within time range)
        trace_files = [self._current_file] if self._current_file.exists() else []
        
        for archive in sorted(self._traces_dir.glob("traces.*.jsonl"), reverse=True):
            # Skip archives outside time range if since is specified
            if since:
                # Extract date from filename
                try:
                    date_str = archive.stem.split(".", 1)[1].split("-", 3)[:3]
                    archive_date = datetime(int(date_str[0]), int(date_str[1]), int(date_str[2]))
                    if archive_date < since - timedelta(days=1):
                        continue
                except (IndexError, ValueError):
                    pass
            trace_files.append(archive)
        
        for trace_file in trace_files:
            try:
                with open(trace_file, "r", encoding="utf-8") as f:
                    for line in f:
                        if not line.strip():
                            continue
                        
                        try:
                            data = json.loads(line)
                            
                            # Apply filters
                            if flow_id and data.get("flow_id") != flow_id:
                                continue
                            if notebook_id and data.get("notebook_id") != notebook_id:
                                continue
                            if cell_id and data.get("cell_id") != cell_id:
                                continue
                            if step_type and data.get("step_type") != step_type:
                                continue
                            
                            # Time filters
                            event_time = datetime.fromisoformat(data.get("started_at", ""))
                            if since and event_time < since:
                                continue
                            if until and event_time > until:
                                continue
                            
                            results.append(TraceEvent(**data))
                            
                            if len(results) >= limit:
                                return results
                                
                        except (json.JSONDecodeError, ValueError) as e:
                            logger.warning(f"Skipping malformed trace line: {e}")
                            continue
                            
            except Exception as e:
                logger.error(f"Error reading trace file {trace_file}: {e}")
                continue
        
        return results
    
    def get_flow(self, flow_id: str) -> List[TraceEvent]:
        """Get all events for a specific flow, ordered by time."""
        events = self.query(flow_id=flow_id, limit=1000)
        return sorted(events, key=lambda e: e.started_at)
    
    def cleanup_old_traces(self, retention_days: Optional[int] = None) -> int:
        """
        Remove trace files older than retention period.
        
        Returns:
            Number of files removed
        """
        retention = retention_days or self.RETENTION_DAYS
        cutoff = datetime.now() - timedelta(days=retention)
        removed = 0
        
        for archive in self._traces_dir.glob("traces.*.jsonl"):
            try:
                # Check file modification time
                mtime = datetime.fromtimestamp(archive.stat().st_mtime)
                if mtime < cutoff:
                    archive.unlink()
                    removed += 1
                    logger.info(f"🗑️ Removed old trace archive: {archive.name}")
            except Exception as e:
                logger.error(f"Failed to remove old trace file {archive}: {e}")
        
        return removed


# Singleton accessor
def get_trace_store() -> TraceStore:
    """Get the global TraceStore instance."""
    return TraceStore()
