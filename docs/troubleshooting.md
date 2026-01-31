# Troubleshooting

This page is a **practical checklist** for diagnosing the most common failures in Digital Article. When in doubt, remember the architecture:

- Frontend (Vite / Nginx) talks to Backend (FastAPI) via `/api/*`
- Backend talks to your LLM provider via AbstractCore ([`backend/app/services/llm_service.py`](../backend/app/services/llm_service.py))
- Long-running operations (model downloads, PDF export, semantic export, article review) use **SSE streams**

If you are new, start from [`docs/getting-started.md`](getting-started.md) and come back here only when something fails.

## “LLM not initialized” / provider unavailable

**What it means (code-as-truth)**: `LLMService` failed to create an AbstractCore client, so `self.llm` is `None` and code generation will raise an error.

- Source: [`backend/app/services/llm_service.py::LLMService._initialize_llm()`](../backend/app/services/llm_service.py) and `LLMService.agenerate_code_from_prompt()`

**Checklist**

- **Is your provider running?**
  - Ollama: `OLLAMA_BASE_URL` (default `http://localhost:11434`)
  - LMStudio: `LMSTUDIO_BASE_URL` (default `http://localhost:1234/v1`)
  - OpenAI-compatible: `OPENAI_COMPATIBLE_BASE_URL` (default `http://localhost:8080/v1`)
- **Does the backend think it is connected?**
  - Call `GET /api/llm/status` (served by [`backend/app/api/llm.py`](../backend/app/api/llm.py))
- **If using Ollama**, run the backend debug endpoint:
  - `GET /api/llm/debug/connection?base_url=http://...:11434`
  - Source: [`backend/app/api/llm.py::debug_ollama_connection()`](../backend/app/api/llm.py)

**Common root causes**

- **Wrong base URL** saved in per-user settings:
  - Settings storage: [`backend/app/services/user_settings_service.py`](../backend/app/services/user_settings_service.py) (`{WORKSPACE_DIR}/user_settings/{username}.json`)
  - UI: [`frontend/src/components/SettingsModal.tsx`](../frontend/src/components/SettingsModal.tsx)
- **Docker “localhost” trap**: inside containers, `localhost` is *the container*, not your host.
  - Prefer `http://host.docker.internal:PORT` on Docker Desktop, or see Linux section below.

## “I changed Settings but execution still uses the old provider/model”

**What’s happening**

- Per-user settings are saved via `PUT /api/settings` ([`backend/app/api/settings.py`](../backend/app/api/settings.py))
- Provider/model selection for the backend LLM is applied via `POST /api/llm/providers/select` ([`backend/app/api/llm.py`](../backend/app/api/llm.py)) which updates [`config.json`](../config.json) ([`backend/app/config.py`](../backend/app/config.py)) and reinitializes the in-process `LLMService`
- The UI currently calls **both** when you click Save ([`frontend/src/components/SettingsModal.tsx`](../frontend/src/components/SettingsModal.tsx))

**Checklist**

- **Did Save succeed** (no toast error)?
- **Is the footer updated** (it polls `GET /api/llm/status`)?
- **If needed, refresh the page** to force a clean state in the browser.

## Docker can’t reach host LLM (`host.docker.internal` not working)

On Linux without Docker Desktop, `host.docker.internal` may not resolve.

**Fix**

- Run with:

```bash
docker run --add-host=host.docker.internal:host-gateway \
  -p 80:80 -v da-data:/app/data digital-article
```

See also: [`docker/README.md`](../docker/README.md) and [`docker/2-tiers/README.md`](../docker/2-tiers/README.md).

## Model download stuck / no progress in UI

Model downloads are streamed via SSE:

- Endpoint: `POST /api/models/pull` ([`backend/app/api/models.py`](../backend/app/api/models.py))
- UI: [`frontend/src/contexts/ModelDownloadContext.tsx`](../frontend/src/contexts/ModelDownloadContext.tsx)

**Checklist**

- **Provider supports pulling**: only `ollama`, `huggingface`, `mlx` (see [`backend/app/api/models.py`](../backend/app/api/models.py))
- **If provider is Ollama**, ensure `OLLAMA_BASE_URL` points to the actual Ollama server.
- **If using docker-compose (3-tier)**: Ollama may be downloading a model on first boot; the compose healthcheck uses a long `start_period` (see [`docker-compose.yml`](../docker-compose.yml)).

## SSE streams don’t work behind a proxy (exports/review/models)

Streaming endpoints rely on `text/event-stream` and require buffering to be disabled.

In code we set:

- Header: `X-Accel-Buffering: no`
- Used by: review streaming ([`backend/app/api/review.py`](../backend/app/api/review.py)), model pull ([`backend/app/api/models.py`](../backend/app/api/models.py)), notebook export streams ([`backend/app/api/notebooks.py`](../backend/app/api/notebooks.py))

If you deploy behind Nginx/Cloudflare/etc, verify that:

- The proxy supports SSE
- Response buffering is disabled for these endpoints

## PDF export fails (WeasyPrint / fonts / rendering)

PDF export is initiated from:

- Backend: [`backend/app/api/notebooks.py`](../backend/app/api/notebooks.py) (`/api/notebooks/{id}/export` and `/export/pdf/stream`)

**Checklist**

- If running locally on macOS/Linux: ensure system dependencies required by WeasyPrint are installed (this varies by OS).
- If running in Docker: prefer the provided Docker images (they bake dependencies).

## Execution state persistence surprises

There are **two** relevant persistence systems:

- **Workspace files (uploads, previews, user settings)**: `config.json.paths.workspace_dir` (default [`data/workspace`](../data/workspace))
  - Implemented by: [`backend/app/services/data_manager_clean.py`](../backend/app/services/data_manager_clean.py)
  - Settings stored by: [`backend/app/services/user_settings_service.py`](../backend/app/services/user_settings_service.py)
- **Execution state snapshots (pickle)**: stored under `backend/notebook_workspace/{notebook_id}/state/` by default
  - Implemented by: [`backend/app/services/state_persistence_service.py`](../backend/app/services/state_persistence_service.py)
  - Triggered by: [`backend/app/services/execution_service.py`](../backend/app/services/execution_service.py)

If you expected state snapshots under [`data/workspace`](../data/workspace), that is a known mismatch to address (see [`docs/architecture.md`](architecture.md) for the current persistence map).

## Still stuck?

Collect these before asking for help:

- Backend logs (FastAPI + stack trace; see global exception handler in [`backend/app/main.py`](../backend/app/main.py))
- Your [`config.json`](../config.json)
- Your `/api/llm/status` output
- If relevant: the provider base URL you configured in Settings

