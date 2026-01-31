# Backlog Item (Historical; migrated from legacy planning)

## Title
Digital Article Implementation Plan

## Backlog ID
0031

## Priority
- **P2 (historical)**: migrated record from the legacy `docs/planning/` folder to keep governance artifacts in one system.

## Date / Time
Unknown (historical; migrated 2026-01-31)

## Short Summary
This file preserves a historical planning/proposal document that previously lived under `docs/backlog/completed/0031_digital_article_implementation_plan.md`. It has been migrated to `docs/backlog/completed/` so older design artifacts live under the backlog governance system.

## Key Goals
- Preserve historical context without losing information.
- Reduce confusion by removing `docs/planning/` from the active doc graph.
- Keep references navigable.

## Scope

### To do
- Preserve the original planning content under **Full Report** (verbatim aside from link-path adjustments due to relocation).
- Update references elsewhere in the docs to point to this new location.

### NOT to do
- Do not claim the underlying plan is current or implemented.

## Dependencies

### Backlog dependencies (ordering)
- **None**

### ADR dependencies (must comply)
- **All ADRs are mandatory**: [`docs/adr/README.md`](../../adr/README.md)

### Points of vigilance (during execution)
- Keep the historical record intact.
- Ensure any updated links remain valid (run `python tools/validate_markdown_links.py`).

## References (source of truth)
- Legacy source: `docs/backlog/completed/0031_digital_article_implementation_plan.md` (removed after migration)
- Canonical docs: [`docs/overview.md`](../../overview.md), [`docs/architecture.md`](../../architecture.md)

## Full Report (legacy planning content)

# Digital Article Implementation Plan

> **Historical planning document.** This file captures early design intent and may not match the current codebase (e.g., the project uses `pyproject.toml`, not `requirements.txt`).  
> For the canonical architecture map, see `docs/architecture.md`.

## Architecture Overview

- **Frontend**: React SPA with cell-based interface and result visualization
- **Backend**: FastAPI server handling LLM integration, code execution, and notebook persistence
- **LLM**: AbstractCore with LMStudio provider using qwen/qwen3-next-80b model
- **Execution**: Direct local Python execution with full data science stack
- **Visualization**: Advanced panel supporting plots, tables, images, and interactive charts

## Project Structure

```
digitalarticle/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI application
│   │   ├── models/              # Pydantic models
│   │   ├── services/            # Business logic services
│   │   └── api/                 # API endpoints
├── frontend/
│   ├── src/
│   │   ├── components/          # React components
│   │   ├── services/            # API client
│   │   └── types/               # TypeScript interfaces
├── requirements.txt             # Python dependencies
├── package.json                 # Node.js dependencies
└── README.md                    # Project documentation
```

## Core Components

### Backend Services

1. **LLM Service**: AbstractCore integration for prompt-to-code conversion
2. **Execution Service**: Safe Python code execution with output capture
3. **Digital Article Service**: Serialization/deserialization of digital article files
4. **Visualization Service**: Processing various output types (plots, tables, etc.)

### Frontend Components

1. **NotebookCell**: Toggle between prompt/code view with execution controls
2. **ResultPanel**: Advanced visualization of execution outputs
3. **NotebookContainer**: Overall digital article management and file operations
4. **PromptEditor**: Rich text editor for natural language prompts

### Data Models

- **Digital Article**: Contains metadata and list of cells
- **Cell**: Stores prompt, generated code, execution state, and results
- **ExecutionResult**: Captures stdout, stderr, plots, and rich outputs

## Implementation Flow

1. User enters natural language prompt in cell
2. LLM converts prompt to Python code via AbstractCore
3. Code executes locally with output capture
4. Results display in visualization panel below cell
5. User can toggle cell to view/edit generated code
6. Digital Article serializes to JSON for persistence

## Key Features

- **Prompt-Code Bijection**: Each prompt maps to exactly one code implementation
- **Live Execution**: Immediate code execution with rich result display
- **Dual View Mode**: Toggle between prompt and code views per cell
- **Rich Visualization**: Support for matplotlib, plotly, pandas tables, images
- **Digital Article Persistence**: Save/load functionality with JSON serialization
- **Error Handling**: Graceful handling of execution errors and LLM failures
