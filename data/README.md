# `data/` (versioned resources + runtime directories)

This folder contains **two different kinds of things**:

## 1) Versioned resources (committed to git)

- **Personas**: [`data/personas/`](personas/)
  - System personas: `data/personas/system/*.json`
  - Custom personas: `data/personas/custom/{username}/*.json`

These are part of the product behavior (LLM guidance) and are used by the backend (see [`backend/app/services/persona_service.py`](../backend/app/services/persona_service.py)).

## 2) Runtime data (NOT committed to git)

The repository `.gitignore` ignores runtime directories like:

- `data/workspace/` (notebook workspaces, file uploads, per-user settings)
- `data/notebooks/` (notebook JSON storage, depending on config)

These are **runtime outputs** and should be treated like application state (backups, volumes), not source code.

