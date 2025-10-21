# Changelog

All notable changes to the Digital Article project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.0.4] - 2025-10-21

### Enhanced
- **Provider Health Check**: Upgraded to use AbstractCore 2.4.6's native `provider.health()` method
  - **Real Health Status**: Now uses actual provider health checks instead of basic initialization checks
  - **Better Error Messages**: More detailed health status information from AbstractCore
  - **Automatic Updates**: Health status refreshes every 60 seconds in the UI (reasonable frequency)
  - Files: `backend/app/services/llm_service.py`, `backend/app/api/llm.py`, `frontend/src/components/LLMStatusFooter.tsx`

- **Dual Seed Management**: Implemented comprehensive seed management using both AbstractCore and execution environment
  - **LLM Generation Seeds**: Uses AbstractCore's native SEED parameter for consistent code generation
  - **Execution Environment Seeds**: Maintains global random state management for consistent code execution results
  - **Provider Support**: AbstractCore SEED works with all providers except Anthropic (as per AbstractCore 2.4.6 spec)
  - **Consistent Results**: Each notebook gets deterministic seeds based on notebook ID hash for both LLM and execution
  - **Clean Code Generation**: LLM no longer generates `np.random.seed(42)` in code - system handles all reproducibility
  - **Two-Layer Approach**: LLM seed ensures consistent code generation, execution seed ensures consistent random data
  - Files: `backend/app/services/llm_service.py`, `backend/app/services/execution_service.py`

- **User-Controlled Seed UI**: Added intuitive seed control interface for reproducibility management
  - **LLM Settings Integration**: Seed control integrated into LLM Settings modal (gear icon)
  - **Educational Tooltip**: Comprehensive tooltip explaining seeds and reproducibility for non-technical users
  - **Smart Defaults**: Automatic seed generation based on notebook ID, with option for custom seeds
  - **Random Generation**: One-click random seed generation with shuffle button
  - **Dual Application**: Custom seeds affect both LLM generation and execution environment
  - **Validation**: Input validation ensures seeds are within valid range (0-2,147,483,647)
  - **Persistent Storage**: Custom seeds are saved with notebook metadata
  - Files: `frontend/src/components/LLMSettingsModal.tsx`, `frontend/src/components/Header.tsx`, `backend/app/api/notebooks.py`, `backend/app/services/notebook_service.py`

### Removed
- **Redundant Seed Methods**: Eliminated some custom seed management methods in favor of cleaner dual approach
  - Removed: `reset_random_state()`, `execute_code_with_fresh_random()` methods (complex state switching)
  - Simplified: Cleaner separation between LLM seeds (AbstractCore) and execution seeds (environment)
  - Cleaner: LLM prompts no longer need to instruct against seed usage

## [0.0.3] - 2025-10-21

### Fixed
- **JSON Export Bug**: Fixed critical issue where JSON export was downloading `"[object Object]"` instead of proper JSON content
  - Root cause: Axios was auto-parsing JSON responses, then the parsed object was being incorrectly converted to string
  - Solution: Enhanced frontend API client to detect auto-parsed JSON responses and re-stringify them properly
  - File: `frontend/src/services/api.ts`

### Enhanced
- **JSON Export Structure**: Completely redesigned JSON export format for better usability and actionability
  - **Clean Structure**: Removed internal application state (execution flags, retry counters, etc.)
  - **Organized Sections**: Clear separation between metadata, configuration, and content
  - **Cell Content Focus**: Each cell now has a clean `content` object with `prompt`, `code`, and `methodology`
  - **Execution Summary**: Lightweight execution status without heavy data (plots, tables stored as boolean flags)
  - **Export Metadata**: Added export timestamp and version tracking
  - **Improved Readability**: Structured for easy parsing and human readability

### Added
- **Export Documentation**: New `docs/export.md` documenting the export system and JSON structure
- **Version Tracking**: Export files now include Digital Article version and export timestamp

### Technical Details

**New JSON Export Structure**:
```json
{
  "digital_article": {
    "version": "0.0.3",
    "export_timestamp": "2025-10-21T07:53:25.083962"
  },
  "metadata": {
    "title": "Article Title",
    "description": "Article Description", 
    "author": "Author Name",
    "created_at": "...",
    "updated_at": "..."
  },
  "configuration": {
    "llm_provider": "lmstudio",
    "llm_model": "qwen/qwen3-next-80b"
  },
  "cells": [
    {
      "type": "prompt",
      "content": {
        "prompt": "Natural language prompt",
        "code": "Generated Python code",
        "methodology": "Scientific explanation"
      },
      "execution": {
        "status": "success",
        "has_plots": true,
        "has_tables": false
      }
    }
  ]
}
```

## [0.0.2] - 2025-10-20

### Documentation
- **Added** comprehensive documentation suite:
  - `docs/architecture.md` - Complete system architecture documentation with diagrams
  - `docs/philosophy.md` - Design principles and philosophical foundations
  - `docs/getting-started.md` - Step-by-step installation and tutorial guide
  - `ROADMAP.md` - Detailed development roadmap through 2027
  - Updated `README.md` - Comprehensive project overview with feature comparison

### Summary

This release represents the first stable beta version of Digital Article with complete documentation. The system is functional for single-user or small team deployment, featuring natural language to code generation, automatic scientific methodology writing, and rich output capture.

**Current Capabilities**:
- Natural language prompts → Python code generation via LLM
- Automatic code execution with matplotlib/plotly/pandas output capture
- Auto-retry error correction (up to 3 attempts with LLM self-debugging)
- Scientific article-style methodology generation
- Multi-format export (JSON, HTML, Markdown, PDF)
- Workspace isolation with file management
- Persistent execution context across cells

**Known Limitations**:
- Single-user deployment only (no authentication)
- Code executes in same process as server (not production-safe)
- JSON file storage (not scalable)
- No real-time collaboration
- See ROADMAP.md for planned improvements

## [0.1.0] - 2025-10-16

### Changed
- Renamed project from "Reverse Analytics Notebook" to "Digital Article"
- Updated all references, documentation, and UI elements to reflect new name

### Fixed
- Save and export functionality now working
- Improved error handling and logging

### Known Issues
- PDF export has occasional rendering issues with complex plots
- Auto-retry may fail on certain syntax errors
- File upload limited to 100MB

## [0.0.0] - 2025-10-15

### Added - Initial Implementation

#### Core Architecture
- **Backend**: FastAPI + Python with AbstractCore LLM integration
- **Frontend**: React + TypeScript with Vite build system
- **LLM Integration**: AbstractCore with LMStudio provider using qwen/qwen3-next-80b model

#### Natural Language Interface
- Prompt-based cell system for natural language analysis requests
- Automatic Python code generation from prompts
- Dual view mode (toggle between prompt and generated code)
- Real-time code execution with comprehensive output capture

#### Visualization & Output Capture
- Matplotlib static plots (PNG export via base64)
- Plotly interactive visualizations (JSON serialization)
- Pandas DataFrame rendering (HTML tables + JSON data)
- Image display capabilities
- Full Python stdout/stderr capture
- Complete error tracebacks with type information

#### Cell & Notebook Management
- Complete CRUD operations for notebooks and cells
- Multiple cell types:
  - **Prompt cells**: Natural language → code
  - **Code cells**: Direct Python coding
  - **Markdown cells**: Documentation
  - **Methodology cells**: Scientific explanations
- Cell execution tracking (execution count, status, timing)
- Auto-save functionality (2-second debounce)

#### Export Capabilities
- **JSON export**: Full notebook with all data
- **HTML export**: Standalone web page with interactive plots
- **Markdown export**: Plain text format for version control
- **PDF export**: Scientific article style with methodology sections

#### Data Management
- Sample datasets included (gene_expression, patient_data, protein_levels, drug_response)
- File upload and management system
- Notebook-specific workspaces (isolated data directories)
- Data file context panel with previews

#### Error Handling & Recovery
- Comprehensive error capture with full tracebacks
- Auto-retry mechanism with LLM-based error fixing (up to 3 attempts)
- Detailed error logging for debugging
- User-friendly error messages in UI

#### Developer Tools
- CLI commands: `da-backend` and `da-frontend` for easy startup
- Automatic port management (kills existing processes)
- Development mode with hot reload
- OpenAPI documentation at `/docs` endpoint

#### Technical Components

**Backend Services** (`backend/app/services/`):
- `llm_service.py` - LLM code generation and explanation
- `execution_service.py` - Python code execution sandbox
- `notebook_service.py` - Notebook orchestration and persistence
- `data_manager_clean.py` - Workspace and file management
- `pdf_service_scientific.py` - Scientific PDF generation

**Frontend Components** (`frontend/src/components/`):
- `NotebookContainer.tsx` - Main notebook orchestration
- `NotebookCell.tsx` - Individual cell rendering
- `ResultPanel.tsx` - Rich output display
- `FileContextPanel.tsx` - Data file management
- `PDFGenerationModal.tsx` - Export progress UI

**API Endpoints**:
- `/api/notebooks/` - Notebook CRUD operations
- `/api/cells/` - Cell CRUD and execution
- `/api/llm/` - Direct LLM interactions
- `/api/files/` - File upload/download/management
- `/api/system/` - System information and health

#### Key Features

**Prompt-Code Mapping**:
- Every prompt generates exactly one code implementation
- Code is always visible and editable
- Context-aware generation (considers previous cells, available variables, data files)

**Intelligent Code Generation**:
- System prompts enforce data path conventions (`data/` directory)
- Automatic library imports
- Error handling with try/except blocks
- Variable and data context injection

**Multi-Format Output Support**:
- Text: stdout/stderr streams
- Static plots: matplotlib/seaborn (base64 PNG)
- Interactive plots: Plotly (JSON with full interactivity)
- Tables: Pandas DataFrames (HTML + JSON)
- Errors: Full Python tracebacks with syntax highlighting

**Scientific Methodology Generation**:
- LLM generates article-style explanations after successful execution
- High-impact journal writing style (Nature/Science/Cell)
- Includes quantitative results and statistical measures
- 2-4 sentence concise paragraphs

**Production Ready Features**:
- Comprehensive error handling throughout stack
- Structured logging for debugging
- Type safety with Pydantic models (backend) and TypeScript (frontend)
- Modular architecture for extensibility

### Dependencies

**Python** (`requirements.txt`):
- abstractcore[all]>=2.4.1 - LLM provider abstraction
- fastapi>=0.104.1 - Web framework
- uvicorn[standard]>=0.24.0 - ASGI server
- pandas>=2.1.4, numpy>=1.26.0 - Data analysis
- matplotlib>=3.8.2, plotly>=5.17.0, seaborn>=0.13.0 - Visualization
- scikit-learn>=1.3.2, scipy>=1.11.4 - Machine learning and stats
- reportlab>=4.0.7, weasyprint>=60.0 - PDF generation
- pydantic>=2.5.2 - Data validation

**Node.js** (`frontend/package.json`):
- react@18.2.0, react-dom@18.2.0 - UI framework
- typescript@5.2.2 - Type safety
- vite@4.5.0 - Build tool
- tailwindcss@3.3.6 - Styling
- axios@1.6.2 - HTTP client
- @monaco-editor/react@4.6.0 - Code viewer
- plotly.js@2.27.1, react-plotly.js@2.6.0 - Interactive plots
- marked@16.4.0 - Markdown rendering

### Architecture Highlights
- **Modular design**: Clear separation between services, components, and data models
- **Scalable structure**: Easily extensible for new features and providers
- **Security conscious**: Safe code execution with error boundaries
- **Performance optimized**: Efficient rendering and state management
- **User experience focused**: Intuitive interface for non-technical users

### Files Added

**Backend**:
- Complete FastAPI application in `backend/app/`
- Service layer with LLM, execution, and notebook services
- Pydantic data models for type safety
- API routers for all endpoints
- Data manager for workspace isolation

**Frontend**:
- React application with TypeScript in `frontend/src/`
- Component-based architecture
- API client with error handling
- Rich output display components
- File management UI

**Configuration**:
- `pyproject.toml` - Python package configuration
- `requirements.txt` - Python dependencies
- `frontend/package.json` - Node.js dependencies
- `frontend/tsconfig.json` - TypeScript configuration
- `frontend/tailwind.config.js` - Tailwind CSS configuration

**Data & Scripts**:
- Sample datasets in `sample_data/`
- CLI scripts in `digitalarticle/`
- Build and dist directories for package distribution

### Initial Release Notes

This initial release (v0.0.0) provided a complete, working implementation of the revolutionary Digital Article concept, enabling domain experts to perform sophisticated data analysis through natural language interaction. The system successfully demonstrates the "article-first" paradigm where narrative descriptions generate executable code and scientific methodology text.

**Target Users**: Researchers, biologists, clinicians, data scientists who want to focus on analysis rather than coding.

**Deployment**: Suitable for single-user local deployment or small team shared server. Not yet ready for production multi-user environments.

---

## Future Plans

See [ROADMAP.md](ROADMAP.md) for detailed development plans through 2027.

**Near-term priorities**:
- Enhanced error diagnostics
- Domain-specific prompt templates
- Version control for cells
- Improved scientific methodology generation
- Comprehensive test coverage

**Medium-term goals**:
- Multi-user authentication
- Database storage (PostgreSQL)
- Real-time collaboration
- Containerized code execution

**Long-term vision**:
- LLM-suggested analysis strategies
- Active learning from user corrections
- Plugin architecture
- Enterprise features (SSO, compliance, HA)

---

## Notes

- This project follows semantic versioning
- Breaking changes will be clearly documented
- Beta versions (1.x) may have breaking changes between minor versions
- Stable versions (2.x+) will maintain backward compatibility within major versions

For detailed change history, see git commit log.
For bug reports and feature requests, see GitHub Issues.
