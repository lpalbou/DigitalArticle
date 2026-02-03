"""
Tests for the TraceStore observability system (ADR 0005).

Tests:
- Trace persistence to JSONL
- Secret redaction
- Query by flow_id, notebook_id, cell_id
- Trace hierarchy (flow → task → step)
"""

import json
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from backend.app.models.trace import (
    TraceEvent,
    TraceLevel,
    TraceStatus,
    StepType,
    redact_secrets,
    truncate_for_storage,
)
from backend.app.services.trace_store import TraceStore


@pytest.fixture
def temp_trace_store(tmp_path):
    """Create a TraceStore with a temporary directory."""
    # Reset singleton for testing
    TraceStore._instance = None
    
    # Patch the config to use temp directory
    with patch("backend.app.services.trace_store.config") as mock_config:
        mock_config.get_workspace_root.return_value = str(tmp_path)
        store = TraceStore()
        yield store
        
    # Clean up singleton
    TraceStore._instance = None


class TestSecretRedaction:
    """Test secret redaction in traces."""
    
    def test_redact_api_key_sk_pattern(self):
        """API keys with sk- prefix are redacted."""
        text = "Using API key: sk-abc123def456ghi789jkl012mno345"
        result = redact_secrets(text)
        assert "sk-" not in result
        assert "[REDACTED_API_KEY]" in result
    
    def test_redact_bearer_token(self):
        """Bearer tokens are redacted."""
        text = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0"
        result = redact_secrets(text)
        assert "eyJ" not in result
        assert "[REDACTED_TOKEN]" in result
    
    def test_redact_password_in_config(self):
        """Passwords in config strings are redacted."""
        text = 'password="my_secret_password_123"'
        result = redact_secrets(text)
        assert "my_secret_password" not in result
        assert "[REDACTED]" in result
    
    def test_none_input(self):
        """None input returns None."""
        assert redact_secrets(None) is None
    
    def test_empty_input(self):
        """Empty string returns empty string."""
        assert redact_secrets("") == ""
    
    def test_no_secrets(self):
        """Text without secrets is unchanged."""
        text = "This is normal text with no secrets."
        assert redact_secrets(text) == text


class TestTruncation:
    """Test truncation for storage."""
    
    def test_short_text_unchanged(self):
        """Short text is not truncated."""
        text = "Short text"
        assert truncate_for_storage(text, max_length=100) == text
    
    def test_long_text_truncated(self):
        """Long text is truncated with notice."""
        text = "x" * 10000
        result = truncate_for_storage(text, max_length=1000)
        assert len(result) < len(text)
        assert "#TRUNCATION_NOTICE" in result
    
    def test_truncation_preserves_start_and_end(self):
        """Truncation preserves start and end of text."""
        text = "START_MARKER" + ("x" * 10000) + "END_MARKER"
        result = truncate_for_storage(text, max_length=1000)
        assert result.startswith("START_MARKER")
        assert result.endswith("END_MARKER")


class TestTraceEvent:
    """Test TraceEvent model."""
    
    def test_create_basic_event(self):
        """Can create a basic trace event."""
        event = TraceEvent(
            flow_id="test-flow-123",
            level=TraceLevel.FLOW,
            step_type=StepType.CODE_EXECUTION,
        )
        assert event.flow_id == "test-flow-123"
        assert event.level == TraceLevel.FLOW
        assert event.step_type == StepType.CODE_EXECUTION
        assert event.status == TraceStatus.STARTED
        assert event.step_id  # Auto-generated
    
    def test_event_with_llm_data(self):
        """Can create event with LLM-specific data."""
        event = TraceEvent(
            flow_id="test-flow",
            level=TraceLevel.STEP,
            step_type=StepType.LLM_CODE_GENERATION,
            llm_provider="lmstudio",
            llm_model="qwen/qwen3-4b-2507",
            llm_input_tokens=100,
            llm_output_tokens=50,
        )
        assert event.llm_provider == "lmstudio"
        assert event.llm_model == "qwen/qwen3-4b-2507"
        assert event.llm_input_tokens == 100


class TestTraceStore:
    """Test TraceStore persistence and queries."""
    
    def test_emit_and_query(self, temp_trace_store):
        """Can emit a trace and query it back."""
        # Emit a trace
        event = TraceEvent(
            flow_id="test-flow-001",
            level=TraceLevel.FLOW,
            step_type=StepType.CODE_EXECUTION,
            notebook_id="notebook-123",
            cell_id="cell-456",
        )
        step_id = temp_trace_store.emit(event)
        
        # Query it back
        results = temp_trace_store.query(flow_id="test-flow-001")
        assert len(results) == 1
        assert results[0].flow_id == "test-flow-001"
        assert results[0].notebook_id == "notebook-123"
    
    def test_start_flow(self, temp_trace_store):
        """start_flow creates a flow-level trace."""
        flow_id = temp_trace_store.start_flow(
            notebook_id="nb-1",
            cell_id="cell-1",
            step_type=StepType.CODE_EXECUTION,
        )
        
        results = temp_trace_store.query(flow_id=flow_id)
        assert len(results) == 1
        assert results[0].level == TraceLevel.FLOW
        assert results[0].status == TraceStatus.STARTED
    
    def test_complete_step(self, temp_trace_store):
        """complete_step records a completion event."""
        flow_id = temp_trace_store.start_flow(
            notebook_id="nb-1",
            step_type=StepType.CODE_EXECUTION,
        )
        
        temp_trace_store.complete_step(
            step_id=flow_id,
            flow_id=flow_id,
            task_id=None,
            step_type=StepType.CODE_EXECUTION,
            status=TraceStatus.SUCCESS,
            started_at=datetime.now() - timedelta(seconds=5),
            notebook_id="nb-1",
        )
        
        results = temp_trace_store.query(flow_id=flow_id)
        assert len(results) == 2  # START + COMPLETE
        
        completed = [r for r in results if r.status == TraceStatus.SUCCESS]
        assert len(completed) == 1
        assert completed[0].duration_ms is not None
        assert completed[0].duration_ms > 0
    
    def test_query_by_notebook_id(self, temp_trace_store):
        """Can filter queries by notebook_id."""
        # Emit traces for different notebooks
        for i in range(3):
            temp_trace_store.emit(TraceEvent(
                flow_id=f"flow-{i}",
                level=TraceLevel.FLOW,
                step_type=StepType.CODE_EXECUTION,
                notebook_id="notebook-A" if i < 2 else "notebook-B",
            ))
        
        results_a = temp_trace_store.query(notebook_id="notebook-A")
        results_b = temp_trace_store.query(notebook_id="notebook-B")
        
        assert len(results_a) == 2
        assert len(results_b) == 1
    
    def test_query_by_cell_id(self, temp_trace_store):
        """Can filter queries by cell_id."""
        temp_trace_store.emit(TraceEvent(
            flow_id="flow-1",
            level=TraceLevel.FLOW,
            step_type=StepType.CODE_EXECUTION,
            notebook_id="nb",
            cell_id="cell-123",
        ))
        temp_trace_store.emit(TraceEvent(
            flow_id="flow-2",
            level=TraceLevel.FLOW,
            step_type=StepType.CODE_EXECUTION,
            notebook_id="nb",
            cell_id="cell-456",
        ))
        
        results = temp_trace_store.query(cell_id="cell-123")
        assert len(results) == 1
        assert results[0].cell_id == "cell-123"
    
    def test_get_flow(self, temp_trace_store):
        """get_flow returns all events for a flow in order."""
        flow_id = "test-flow-hierarchy"
        
        # Emit flow, task, and step events
        temp_trace_store.emit(TraceEvent(
            step_id="step-1",
            flow_id=flow_id,
            level=TraceLevel.FLOW,
            step_type=StepType.CODE_EXECUTION,
        ))
        temp_trace_store.emit(TraceEvent(
            step_id="step-2",
            flow_id=flow_id,
            task_id="task-1",
            parent_step_id="step-1",
            level=TraceLevel.TASK,
            step_type=StepType.LLM_CODE_GENERATION,
        ))
        temp_trace_store.emit(TraceEvent(
            step_id="step-3",
            flow_id=flow_id,
            task_id="task-1",
            parent_step_id="step-2",
            level=TraceLevel.STEP,
            step_type=StepType.LLM_CODE_GENERATION,
        ))
        
        events = temp_trace_store.get_flow(flow_id)
        assert len(events) == 3
        # Should be sorted by time
        assert events[0].step_id == "step-1"
        assert events[1].step_id == "step-2"
        assert events[2].step_id == "step-3"
    
    def test_redaction_on_emit(self, temp_trace_store):
        """Secrets are redacted when traces are emitted."""
        event = TraceEvent(
            flow_id="secret-test",
            level=TraceLevel.STEP,
            step_type=StepType.LLM_CODE_GENERATION,
            llm_prompt="Use API key sk-super_secret_key_12345678901234567890",
            llm_system_prompt="Password: mysecretpassword123",
        )
        temp_trace_store.emit(event)
        
        # Read the trace file directly
        trace_file = temp_trace_store._current_file
        with open(trace_file, "r") as f:
            line = f.readline()
            data = json.loads(line)
        
        # Secrets should be redacted
        assert "sk-super_secret" not in data.get("llm_prompt", "")
        assert "[REDACTED" in data.get("llm_prompt", "")
    
    def test_persistence_survives_restart(self, tmp_path):
        """Traces persist and can be queried after 'restart' (new instance)."""
        # First "session"
        TraceStore._instance = None
        with patch("backend.app.services.trace_store.config") as mock_config:
            mock_config.get_workspace_root.return_value = str(tmp_path)
            store1 = TraceStore()
            store1.emit(TraceEvent(
                flow_id="persistent-flow",
                level=TraceLevel.FLOW,
                step_type=StepType.CODE_EXECUTION,
            ))
        
        # "Restart" - new instance
        TraceStore._instance = None
        with patch("backend.app.services.trace_store.config") as mock_config:
            mock_config.get_workspace_root.return_value = str(tmp_path)
            store2 = TraceStore()
            results = store2.query(flow_id="persistent-flow")
        
        assert len(results) == 1
        assert results[0].flow_id == "persistent-flow"
        
        # Clean up
        TraceStore._instance = None
