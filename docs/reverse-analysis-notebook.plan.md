# Reverse Analytics Notebook Implementation Plan

## Architecture Overview

- **Frontend**: React SPA with cell-based interface and result visualization
- **Backend**: FastAPI server handling LLM integration, code execution, and notebook persistence
- **LLM**: AbstractCore with LMStudio provider using qwen/qwen3-next-80b model
- **Execution**: Direct local Python execution with full data science stack
- **Visualization**: Advanced panel supporting plots, tables, images, and interactive charts

## Project Structure

```
reverse-notebook/
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
3. **Notebook Service**: Serialization/deserialization of notebook files
4. **Visualization Service**: Processing various output types (plots, tables, etc.)

### Frontend Components

1. **NotebookCell**: Toggle between prompt/code view with execution controls
2. **ResultPanel**: Advanced visualization of execution outputs
3. **NotebookContainer**: Overall notebook management and file operations
4. **PromptEditor**: Rich text editor for natural language prompts

### Data Models

- **Notebook**: Contains metadata and list of cells
- **Cell**: Stores prompt, generated code, execution state, and results
- **ExecutionResult**: Captures stdout, stderr, plots, and rich outputs

## Implementation Flow

1. User enters natural language prompt in cell
2. LLM converts prompt to Python code via AbstractCore
3. Code executes locally with output capture
4. Results display in visualization panel below cell
5. User can toggle cell to view/edit generated code
6. Notebook serializes to JSON for persistence

## Key Features

- **Prompt-Code Bijection**: Each prompt maps to exactly one code implementation
- **Live Execution**: Immediate code execution with rich result display
- **Dual View Mode**: Toggle between prompt and code views per cell
- **Rich Visualization**: Support for matplotlib, plotly, pandas tables, images
- **Notebook Persistence**: Save/load functionality with JSON serialization
- **Error Handling**: Graceful handling of execution errors and LLM failures