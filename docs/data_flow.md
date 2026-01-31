# Data Flow (call graphs and key sequences)

This document captures the **actual runtime call flows** of Digital Article, grounded in the current codebase.

For the high-level map, see [`docs/architecture.md`](architecture.md).

## Flow 1: Execute a prompt cell (prompt → code → exec → retry → methodology)

Source code:

- API: [`backend/app/api/cells.py`](../backend/app/api/cells.py) (`POST /api/cells/execute`)
- Orchestrator: [`backend/app/services/notebook_service.py::NotebookService.execute_cell()`](../backend/app/services/notebook_service.py)
- LLM integration: [`backend/app/services/llm_service.py`](../backend/app/services/llm_service.py)
- Execution: [`backend/app/services/execution_service.py`](../backend/app/services/execution_service.py)

```mermaid
sequenceDiagram
  participant FE as Frontend
  participant API as POST /api/cells/execute
  participant NS as NotebookService.execute_cell()
  participant LLM as LLMService
  participant EX as ExecutionService

  FE->>API: CellExecuteRequest
  API->>NS: execute_cell()

  NS->>NS: _build_execution_context()
  NS->>LLM: agenerate_code_from_prompt()
  LLM-->>NS: code + trace

  NS->>EX: execute_code()
  EX-->>NS: ExecutionResult

  alt error and retries remain (max 5)
    loop retry
      NS->>LLM: asuggest_improvements()
      LLM-->>NS: fixed_code + trace
      NS->>EX: execute_code(fixed_code)
      EX-->>NS: ExecutionResult
    end
  end

  alt success (prompt + code)
    NS->>LLM: agenerate_scientific_explanation()
    LLM-->>NS: methodology + trace
  end

  NS-->>API: updated cell + result
  API-->>FE: CellExecuteResponse
```

## Flow 2: Article review (SSE streaming)

Source code:

- API: [`backend/app/api/review.py`](../backend/app/api/review.py) (`POST /api/review/article/{id}/stream`)
- Service: [`backend/app/services/review_service.py::ReviewService.review_article_streaming()`](../backend/app/services/review_service.py)

```mermaid
sequenceDiagram
  participant FE as Frontend
  participant API as POST /api/review/article/{id}/stream
  participant RS as ReviewService.review_article_streaming()
  participant LLM as AbstractCore LLM

  FE->>API: start SSE
  API->>RS: build full article context
  RS->>LLM: agenerate(stream=True)
  loop chunks
    LLM-->>RS: chunk
    RS-->>API: progress update
    API-->>FE: SSE event
  end
  RS-->>API: complete (review + trace)
  API-->>FE: SSE complete
```

## Flow 3: Model download (SSE streaming)

Source code:

- API: [`backend/app/api/models.py`](../backend/app/api/models.py) (`POST /api/models/pull`)
- UI: [`frontend/src/contexts/ModelDownloadContext.tsx`](../frontend/src/contexts/ModelDownloadContext.tsx)

```mermaid
sequenceDiagram
  participant FE as Frontend
  participant API as POST /api/models/pull
  participant AC as AbstractCore download_model()

  FE->>API: start SSE (provider + model)
  API->>AC: download_model(provider, model)
  loop progress
    AC-->>API: DownloadProgress
    API-->>FE: SSE event
  end
```

## Flow 4: Export (non-streaming vs streaming)

Source code:

- Non-streaming export: `GET /api/notebooks/{id}/export` ([`backend/app/api/notebooks.py`](../backend/app/api/notebooks.py))
- Streaming export:
  - `POST /api/notebooks/{id}/export/semantic/stream`
  - `POST /api/notebooks/{id}/export/pdf/stream`

```mermaid
flowchart TB
  FE["Frontend"] -->|"GET /export?format=..."| API["backend/app/api/notebooks.py"]
  API -->|"NotebookService.export_notebook(...)"| NS["backend/app/services/notebook_service.py"]

  FE -->|"POST /export/*/stream (SSE)"| SSE["StreamingResponse\n(text/event-stream)"]
  SSE --> NS
```

