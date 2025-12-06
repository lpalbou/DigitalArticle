# Changelog

All notable changes to the Digital Article project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## [0.3.1] - 2025-12-05

### Added

- **🗑️ Ollama Model Deletion**: Delete models to free disk space
  - Trash icon in model dropdown for Ollama models
  - Confirmation dialog before deletion
  - Refreshes model list after deletion
  - Toast notifications for success/error

### Fixed

- **💾 Model Selection Persistence**: Settings now persist across notebooks
  - Fixed: New notebook creation now reads from user settings (`/api/settings`)
  - Previously: Used global config which didn't persist user preferences
  - Model selection now persists across new notebooks, page refresh, and browser sessions

- **🔧 httpx DELETE API Fix**: Fixed model deletion endpoint
  - Changed from `client.delete(json=...)` to `client.request("DELETE", json=...)`
  - Resolves: "AsyncClient.delete() got an unexpected keyword argument"


## [0.3.0] - 2025-12-05

### Fixed

- **🔧 Docker Deployment**: Fixed missing personas in Docker containers
  - Added `COPY data/personas/system/` to all 4 Dockerfiles (monolithic, NVIDIA, 3-tier backend, root)
  - Added `libgomp1` runtime dependency for llama-cpp-python (AbstractCore HuggingFace provider)
  - Personas now properly included in Docker images, available in Settings UI
  - Backend no longer crashes with "libgomp.so.1: cannot open shared object file" error

- **🌐 Base URL Settings**: Fixed Ollama/LMStudio base URL not applied to LLM calls
  - LLM service now loads saved base URLs from `user_settings.json`
  - Priority: saved settings > environment variable > default
  - Provider discovery and LLM calls now use consistent base URL configuration
  - Docker deployments can still override via environment variables

- **📦 Docker Registry**: Switched 3-tier backend to AWS ECR Public
  - Eliminated Docker Hub rate limit warnings for Python base images
  - Consistent with monolithic Dockerfile (all use AWS ECR except Ollama)

### Changed

- **🎨 PDF Export**: Enhanced with Plotly figure support (from 0.2.5)
  - Added `kaleido==0.2.1` for Plotly → PNG conversion
  - Scientific PDFs now include all interactive visualizations as high-quality static images


## [0.2.5] - 2025-12-04

### Added

- **🎭 Persona System**: Domain-expert personas that shape article generation
  - **5 Built-in Personas**: Generic, Clinical, Genomics, RWD (Real-World Data), Medical Imaging
  - **Per-Notebook Selection**: Each notebook can have its own persona (stored in notebook metadata)
  - **Domain-Specific Guidance**: Personas inject expertise into code generation, methodology writing, and terminology
  - **Custom Personas**: Users can create and manage their own domain-specific personas
  - **Scope-Aware Prompts**: Different guidance for code generation, methodology, chat, abstract, and review
  - Files: `backend/app/models/persona.py`, `backend/app/services/persona_service.py`, `backend/app/api/personas.py`
  - UI: `PersonaTab.tsx`, `PersonaCard.tsx`, `PersonaEditor.tsx`

- **📝 Article Review System**: Automated peer-review quality control
  - **Dimensional Assessment**: Structured evaluation across 5 scientific dimensions
    - Research Question (relevance, clarity, scope)
    - Methodology (appropriateness, implementation, statistical rigor)
    - Results (accuracy, completeness, presentation)
    - Reproducibility (documentation, data access, code quality)
    - Communication (structure, language, visualization)
  - **3-Phase Review**: Intent review, Implementation review, Results review
  - **Severity Levels**: Info, Warning, Critical findings with actionable suggestions
  - **Article-Level Synthesis**: Overall assessment with key strengths and areas for improvement
  - Files: `backend/app/models/review.py`, `backend/app/services/review_service.py`, `backend/app/api/review.py`
  - UI: `ArticleReviewModal.tsx`, `ReviewPanel.tsx`, `ReviewSettingsTab.tsx`

- **📖 Architecture Documentation**: Comprehensive documentation of the Persona and Review systems
  - File: `docs/persona-and-review-architecture.md`

### Changed

- **💬 Enhanced Chat Service**: Chat now supports mode-based operation (standard, review)
- **⚙️ Settings Modal**: New tabs for Persona selection and Review configuration
- **🔧 LLM Service**: Enhanced to support persona context injection

## [0.2.3] - 2025-12-02

### Changed

- **🔧 Centralized Version Management**: Single source of truth (`digitalarticle/_version.py`)
  - Backend imports version directly; Docker copies `digitalarticle/` folder
  - Frontend footer fetches version from `/api/system/version` endpoint
  - No more hardcoded versions across codebase


## [0.2.2] - 2025-11-27

### Added

- **🔧 Multi-Provider Docker Support**: Environment variable-driven LLM configuration for all AbstractCore providers
  - **Provider Selection**: `LLM_PROVIDER` env var supports `ollama`, `openai`, `anthropic`, `lmstudio`, `huggingface`
  - **Model Configuration**: `LLM_MODEL` env var to specify model name for any provider
  - **API Key Support**: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `HUGGINGFACE_TOKEN` env vars for external providers
  - **Smart Startup**: Ollama server only starts when `LLM_PROVIDER=ollama`, saving resources for external providers
  - Files: `docker/monolithic/entrypoint.sh`, `docker/monolithic/supervisord.conf`, `docker/monolithic/Dockerfile`, `docker/monolithic/Dockerfile.nvidia`

### Enhanced

- **⚙️ Configuration Priority**: ENV > config.json > defaults (follows Docker/12-Factor conventions)
  - **Environment First**: Environment variables take precedence for container deployments
  - **Config File Second**: `config.json` used for local development when env vars not set
  - **Sensible Defaults**: Built-in defaults (`ollama`/`gemma3n:e2b`) when neither env nor config specified
  - Files: `backend/app/config.py`

- **📁 Local Development Paths**: Updated `config.json` to use relative paths for local development
  - **Before**: `/app/data/notebooks` (Docker absolute paths)
  - **After**: `data/notebooks` (relative paths for local dev)
  - **Rationale**: `config.json` is for local development; Docker uses env vars
  - Files: `config.json`

- **📖 Docker Documentation**: Comprehensive provider configuration documentation
  - **Provider Examples**: Usage examples for all supported providers (OpenAI, Anthropic, LMStudio, HuggingFace)
  - **Environment Reference**: Complete table of all configuration environment variables
  - **External Ollama**: Updated docs for using native Ollama on host machine
  - Files: `docker/monolithic/README.md`, `docker/README.md`

### Technical Details

**Configuration Priority Chain**:
```
1. Environment variables (LLM_PROVIDER, LLM_MODEL, etc.)
2. config.json file 
3. Built-in defaults (ollama, gemma3n:e2b)
```

**Provider-Aware Startup**:
- If `LLM_PROVIDER=ollama`: Start Ollama, wait for health, pull model
- If `LLM_PROVIDER=openai|anthropic|lmstudio|huggingface`: Skip Ollama entirely

**Example Usage**:
```bash
# OpenAI (no Ollama started)
docker run -p 80:80 \
    -e LLM_PROVIDER=openai \
    -e LLM_MODEL=gpt-4o \
    -e OPENAI_API_KEY=sk-... \
    digital-article:unified

# Ollama (default, with bundled server)
docker run -p 80:80 \
    -e LLM_MODEL=llama3.2:7b \
    digital-article:unified
```

## [0.2.1] - 2025-11-25

### Added

- **🐳 Unified Docker Image**: Single-container deployment consolidating all services
  - **All-in-One Container**: Backend (FastAPI) + Frontend (Nginx) + Ollama (LLM) in one image
  - **Supervisord Process Management**: Coordinated multi-service startup with health checks
  - **Smart Model Caching**: Models downloaded once at first run, persisted in named volume for subsequent starts
  - **Configurable Paths**: Environment variables override config.json for notebooks, workspace, and model storage
  - **Official Ollama Binary**: Uses binary from `ollama/ollama:latest` official Docker image for reliability
  - **Orchestrated Startup**: 9-step entrypoint sequence ensures services start in correct order with health verification
  - **Simplified Deployment**: Single `docker run` command vs 3-service docker-compose
  - **Production Ready**: Complete with health checks, resource limits, and comprehensive logging
  - Files: `docker/Dockerfile.unified`, `docker/entrypoint-unified.sh`, `docker/supervisord.conf`, `docker/nginx-unified.conf`

- **📦 Dual Deployment Options**: Flexibility to choose between unified or multi-container setup
  - **Unified Image** (recommended): Simplified deployment for most use cases with `digitalarticle:unified`
  - **Multi-Container**: Original 3-service architecture still available for advanced scenarios
  - **Named Volumes**: Both strategies use persistent volumes for notebooks and models
  - **Comprehensive Guides**: Separate documentation for each deployment approach
  - Files: `docker/monolithic/README.md`, `docker/3-tiers/README.md`

- **⚙️ Backend Path Configuration**: Dynamic path configuration with ENV > config.json > default cascade
  - **Configurable Notebooks Directory**: `NOTEBOOKS_DIR` env var or `paths.notebooks_dir` in config.json
  - **Configurable Workspace Root**: `WORKSPACE_DIR` env var or `paths.workspace_dir` in config.json
  - **Programmatic API**: `config.get_notebooks_dir()`, `config.get_workspace_root()`, `config.set_paths()`
  - **Docker Integration**: Backend automatically uses paths from environment variables in containers
  - Files: `backend/app/config.py`, `backend/app/services/shared.py`, `backend/app/services/data_manager_clean.py`

### Enhanced

- **📖 Comprehensive Deployment Documentation**
  - **Main Docs**: `docker/README.md` - Overview and decision tree
  - **Monolithic Guide**: `docker/monolithic/README.md` - Single container deployment
  - **3-Tier Guide**: `docker/3-tiers/README.md` - Multi-container deployment
  - **Technical Report**: `docs/devnotes/docker-one-image.md` - Implementation details

### Technical Details

**Unified Container Architecture**:
- **Multi-stage Build**: Frontend (Node 20 Alpine) → Backend (Python 3.12 Slim) → Runtime
- **Process Management**: Supervisord coordinates 3 services (Ollama priority 10, Backend priority 20, Nginx priority 30)
- **Service Communication**: Localhost networking (nginx → backend:8000, backend → ollama:11434)
- **Volume Strategy**: Two named volumes (notebooks/workspace data, Ollama models)
- **Startup Sequence**:
  1. Initialize directories from ENV vars
  2. Start supervisord
  3. Wait for Ollama readiness (30 retries × 2s)
  4. Check/download model (skip if cached in volume)
  5. Start backend via supervisorctl
  6. Wait for backend health (30 retries × 2s)
  7. Start nginx
  8. Display configuration summary
  9. Hand off to supervisord foreground mode

**Image Size & Performance**:
- **Base Image**: ~2.3-2.5GB (no models included)
- **First Startup**: 10-30 minutes (model download)
- **Subsequent Startups**: 90-120 seconds (models cached)
- **Resource Requirements**: 8GB RAM minimum, 32GB+ recommended for 30B models

**Deployment Comparison**:
```
Multi-Container (0.2.0):
  docker-compose up -d  # 3 containers

Unified Image (0.2.1):
  docker run -d -p 80:80 \
    -v digitalarticle-data:/app/data \
    -v digitalarticle-models:/models \
    digitalarticle:unified
```

## [0.2.0] - 2025-11-21

### Added

- **🐳 Docker Containerization**: Complete production-ready Docker deployment with 3-service architecture
  - **Backend Container**: FastAPI application with automatic health checks and fail-safe startup
  - **Frontend Container**: Nginx-served React application with optimized production build
  - **Ollama Container**: Dedicated LLM service with automatic model download and GPU support
  - **Named Volumes**: Zero-setup deployment with automatic directory creation for notebooks, data, and logs
  - **Resource Management**: Configurable memory limits and CPU allocation for each service
  - **Comprehensive Documentation**: 593-line deployment guide covering all scenarios from quick test to production
  - Files: `docker/Dockerfile.backend`, `docker/Dockerfile.frontend`, `docker-compose.yml`, `docker-compose.dev.yml`, `docker/entrypoint.sh`, `docker/ollama-entrypoint.sh`, `docker/nginx.conf`, `docker/README.md`

- **🚀 Automatic Model Setup**: Intelligent model management with zero manual intervention
  - **Config-Driven**: Reads model name from `config.json` for consistent deployment
  - **Automatic Download**: Ollama container downloads models during startup if not present
  - **Health Checks**: Extended health check periods (40 minutes) to accommodate large model downloads
  - **Graceful Startup**: Backend waits for Ollama to be ready before serving requests
  - **Progress Tracking**: Model download progress visible in container logs
  - Files: `docker/ollama-entrypoint.sh`, `docker/entrypoint.sh`, `config.json`

- **📦 Dependency Management**: Unified dependency management using `pyproject.toml` as single source of truth
  - **SOTA Best Practice**: Eliminated duplicate dependency definitions in `requirements.txt`
  - **Consistent Versions**: All dependencies defined once in `pyproject.toml`
  - **Docker Integration**: Dockerfile installs directly from `pyproject.toml`
  - **Missing Dependencies**: Added `python-multipart` for file upload support
  - Files: `pyproject.toml`, `docker/Dockerfile.backend`

### Enhanced

- **🔧 Robust Entrypoint Scripts**: Production-grade startup scripts with comprehensive error handling
  - **Fail-Safe Backend**: Waits for Ollama health before starting, with timeout and retry logic
  - **Clean Separation**: Each container manages its own concerns (backend=API, ollama=models, frontend=UI)
  - **Logging**: Detailed startup logs for debugging and monitoring
  - **Non-Blocking**: Services start independently without blocking each other
  - Files: `docker/entrypoint.sh`, `docker/ollama-entrypoint.sh`

- **⚙️ Configuration Management**: Versioned configuration with sensible defaults
  - **Default Ollama Settings**: Pre-configured for `ollama` provider with `qwen3-coder:30b` model
  - **No Setup Required**: Works out-of-the-box with `docker-compose up`
  - **Customizable**: Easy to modify provider, model, and connection settings
  - Files: `config.json`

### Changed

- **📁 Data Management**: Removed automatic sample data copying for cleaner deployments
  - **User Responsibility**: Users must upload their own data or manually copy sample data
  - **Cleaner Builds**: Reduced image size and deployment complexity
  - **Clear Documentation**: Instructions for data management in Docker guide
  - Files: `docker/Dockerfile.backend`, `docker/README.md`

### Fixed

- **🔌 Ollama Connection**: Corrected AbstractCore parameter from `api_base` to `base_url`
  - **Root Cause**: AbstractCore uses `base_url` parameter, not `api_base`
  - **Impact**: Ollama provider now connects correctly in Docker environment
  - Files: `backend/app/services/llm_service.py`

- **🏗️ Docker Build**: Fixed build order to copy application code before pip install
  - **Root Cause**: Dockerfile tried to install package before copying source code
  - **Solution**: Reorganized Dockerfile to copy `app/` directory before running `pip install`
  - Files: `docker/Dockerfile.backend`

- **🏥 Health Checks**: Removed blocking model downloads from backend health checks
  - **Problem**: Backend downloaded 17GB models before passing health checks (15-30 min timeout)
  - **Solution**: Moved model downloads to Ollama container startup
  - **Result**: Backend starts in ~15 seconds, health checks pass immediately
  - Files: `docker/entrypoint.sh`, `docker/ollama-entrypoint.sh`

### Technical Details

**Docker Architecture**:
- **3-Service Design**: Frontend (Nginx) → Backend (FastAPI) → Ollama (LLM)
- **Port Mapping**: Frontend (80), Backend (8000), Ollama (11434)
- **Network**: Custom bridge network for inter-container communication
- **Volumes**: Named volumes for persistence (notebooks, data, logs, ollama-models)
- **Resource Limits**: Ollama (32GB/8 cores), Backend (4GB/2 cores), Frontend (unlimited)

**Deployment Options**:
1. **Quick Test**: Frontend + Backend only (~2 minutes, no LLM)
2. **Full Deployment**: All services with automatic model download (~20-40 minutes first time)
3. **Development Mode**: Hot-reload enabled with `docker-compose.dev.yml`
4. **Production**: Optimized builds with health checks and resource limits

**System Requirements**:
- Memory: 16-32GB RAM for qwen3-coder:30b (or 8GB for qwen3-coder:4b)
- Disk: 25GB minimum (images + models)
- Docker: Version 20.10+ with Compose v2

## [0.0.8] - 2025-10-28

### Added

- **🧬 State-of-the-Art H5 File Support**: Comprehensive support for HDF5 files with interactive visualization
  - **H5/HDF5 Files**: Full support for standard HDF5 files with hierarchical structure analysis
  - **H5AD (AnnData) Files**: Specialized support for single-cell genomics data with scanpy integration
  - **Interactive Preview**: Tree-based file structure browser with metadata and sample data display
  - **Memory Efficient Processing**: Smart sampling for large datasets to provide previews without memory issues
  - **Robust Error Handling**: Graceful fallbacks and comprehensive error reporting
  - **Dependencies**: Added h5py>=3.10.0, anndata>=0.10.0, and tables>=3.9.0 to requirements
  - Files: `backend/app/services/h5_service.py`, `frontend/src/components/H5FileViewer.tsx`, `backend/app/services/data_manager_clean.py`, `frontend/src/components/FileViewerModal.tsx`, `frontend/src/components/FileContextPanel.tsx`, `requirements.txt`, `docs/getting-started.md`

## [0.0.7] - 2025-10-26

### Updated

- **AbstractCore 2.5.2 Integration**: Updated to AbstractCore version 2.5.2 for improved stability and performance
  - **Version Consistency**: Updated all version references from 2.4.6/2.4.8 to 2.5.2 across codebase
  - **Dependency Updates**: Updated `requirements.txt` and `pyproject.toml` to require `abstractcore[all]>=2.5.2`
  - **Comment Updates**: Updated all AbstractCore version references in code comments to reflect current version
  - Files: `requirements.txt`, `pyproject.toml`, `backend/app/services/llm_service.py`, `backend/app/api/llm.py`, `backend/app/services/token_tracker.py`, `backend/app/models/notebook.py`, `frontend/src/types/index.ts`

## [0.0.6] - 2025-10-22

### Fixed

- **Files in Context UI**: Removed redundant eye button from Files in Context section since it's already a collapsible section
- **Enhanced File Awareness**: Significantly improved LLM awareness of available files with comprehensive metadata and previews
  - **Rich File Previews**: Added detailed previews for CSV (columns, shape, sample data), JSON (schema analysis), Excel (sheet names), and text files
  - **Smart JSON Schema Analysis**: Automatically analyzes JSON structure to provide object/array type information and property schemas
  - **LLM Context Integration**: Files are now prominently displayed in LLM prompts with full metadata, making the LLM aware of available data
  - **File Size Formatting**: Human-readable file sizes (B, KB, MB, GB) in both UI and LLM context
  - **Structured Information**: LLM receives file paths, types, sizes, and content previews for better code generation
  - Files: `frontend/src/components/FileContextPanel.tsx`, `backend/app/services/llm_service.py`, `backend/app/services/data_manager_clean.py`


## [0.0.5] - 2025-10-22

### Enhanced

- **AbstractCore 2.4.8 Integration**: Updated to latest AbstractCore version with improved token counting and generation time tracking
  - **Accurate Token Counts**: Now uses proper `input_tokens`, `output_tokens`, `total_tokens` from AbstractCore 2.4.8+ (with backward compatibility for legacy field names)
  - **Generation Time Display**: Added discrete generation time display for each cell in iPhone message style (e.g., "14:32 | 1.2s")
  - **Timestamp Tracking**: Added execution timestamps to cells showing when each cell was last executed
  - **Fixed Footer Token Display**: Resolved issue where footer showed "0 / 262.1k" instead of actual tokens used in methodology generation
  - Files: `backend/app/services/token_tracker.py`, `backend/app/services/llm_service.py`, `backend/app/services/notebook_service.py`, `frontend/src/components/PromptEditor.tsx`, `frontend/src/types/index.ts`

- **Enhanced Library Support & Error Handling**: Comprehensive improvements to library management and auto-retry system
  - **Essential Libraries Added**: Added `umap-learn`, `scanpy`, and `openpyxl` for bioinformatics and data parsing (removed over-engineered libraries like opencv, xgboost, biopython)
  - **Smart Import Error Detection**: Added intelligent error analyzer that suggests alternatives when users try unavailable libraries (e.g., suggests sklearn for tensorflow, PIL for opencv)
  - **Matplotlib Color Error Fix**: Added specific error analyzer for categorical data color mapping issues with targeted solutions (color_map, seaborn, factorize)
  - **Enhanced Auto-Retry System**: Increased max retries from 3 to 5 attempts with improved visual progress indicators showing "correcting code x/5"
  - **Complete Error Context**: LLM now receives full error details including original message, stack trace, and domain-specific guidance for better auto-fixes
  - **Simplified Architecture**: Replaced complex import interception system with elegant keyword-based suggestions for maintainability

### Changed

- **Data Management**: Removed automatic sample data copying; users must now upload their own data or manually copy sample data


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
