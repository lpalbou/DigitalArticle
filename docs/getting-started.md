# Getting Started with Digital Article

> **Status (2026-01-31):** This page starts with a **current quick-start** grounded in the code. Everything under **“Legacy guide (historical)”** is kept for historical context and may drift from the current implementation.

## Quick start (current)

### What you will run
- **Backend**: FastAPI on `http://localhost:8000` (API prefix: `/api`)  
  - Entry point: [`backend/app/main.py`](../backend/app/main.py)
  - Primary orchestration: [`backend/app/services/notebook_service.py::NotebookService`](../backend/app/services/notebook_service.py)
- **Frontend**: Vite dev server on `http://localhost:3000`  
  - Dev proxy: [`frontend/vite.config.ts`](../frontend/vite.config.ts) proxies `/api/*` → `http://localhost:8000/api/*`
- **LLM provider**: local server (LMStudio/Ollama/vLLM/OpenAI-compatible) or a cloud API (OpenAI/Anthropic)

### 1) Install (local dev)

```bash
git clone https://github.com/lpalbou/digitalarticle.git
cd digitalarticle

python -m venv .venv
source .venv/bin/activate  # macOS/Linux

# Install Python deps + CLI tools (da-backend, da-frontend) from pyproject.toml
pip install -e ".[dev]"

# Install frontend deps
cd frontend
npm install
cd ..
```

### 2) Run locally

```bash
# Terminal 1
da-backend

# Terminal 2
da-frontend
```

Open `http://localhost:3000`.

### 3) Configure your LLM (how it works in the code)

- **UI Settings**: [`frontend/src/components/SettingsModal.tsx`](../frontend/src/components/SettingsModal.tsx) persists settings via:
  - `GET/PUT /api/settings` ([`backend/app/api/settings.py`](../backend/app/api/settings.py)) → per-user settings file under `{WORKSPACE_DIR}/user_settings/{username}.json` ([`backend/app/services/user_settings_service.py`](../backend/app/services/user_settings_service.py))
  - `POST /api/llm/providers/select` ([`backend/app/api/llm.py`](../backend/app/api/llm.py)) → updates [`config.json`](../config.json) ([`backend/app/config.py`](../backend/app/config.py)) and reinitializes the in-process `LLMService`
- **Config precedence (project-level)**: ENV > [`config.json`](../config.json) > defaults ([`backend/app/config.py`](../backend/app/config.py))
- **Docker note**: at startup we apply Docker base-URL env overrides to user settings *before* creating `NotebookService` ([`backend/app/services/shared.py`](../backend/app/services/shared.py))

Common local base URLs:
- **LMStudio**: `http://localhost:1234/v1` (provider: `lmstudio` or `openai-compatible`)
- **Ollama**: `http://localhost:11434` (provider: `ollama`)
- **OpenAI-compatible** (llama.cpp/vLLM/LocalAI): usually `http://localhost:PORT/v1` (provider: `openai-compatible`)

### 4) First analysis (recommended workflow)

1. Create a notebook
2. Upload a dataset in the **Files** panel  
   - Backend endpoints: [`backend/app/api/files.py`](../backend/app/api/files.py) (`/api/files/{notebook_id}/upload`, `/api/files/{notebook_id}`, ...)
3. Write a prompt and execute the cell  
   - Backend endpoint: `POST /api/cells/execute` ([`backend/app/api/cells.py`](../backend/app/api/cells.py))
   - Orchestration: [`backend/app/services/notebook_service.py::NotebookService.execute_cell()`](../backend/app/services/notebook_service.py)

### 5) Where your data is stored (paths)

- **Notebooks**: `config.json.paths.notebooks_dir` (default in repo: `data/notebooks`) → [`backend/app/config.py::Config.get_notebooks_dir()`](../backend/app/config.py)
- **Workspace files (uploads, previews, user settings)**: `config.json.paths.workspace_dir` (default in repo: [`data/workspace`](../data/workspace)) → [`backend/app/config.py::Config.get_workspace_root()`](../backend/app/config.py)
- **Execution state snapshots (pickle)**: currently stored under `backend/notebook_workspace/{notebook_id}/state/` by [`backend/app/services/state_persistence_service.py::StatePersistenceService`](../backend/app/services/state_persistence_service.py) (independent of `paths.workspace_dir`)

### 6) Next docs

- [`README.md`](../README.md) (main entry point)
- [`docs/overview.md`](overview.md) (documentation index)
- [`docs/architecture.md`](architecture.md) (canonical system map + diagrams + links to dive-ins)
- [`docs/limitations.md`](limitations.md) (known limitations + production readiness expectations)
- [`docs/data_flow.md`](data_flow.md) (sequence diagrams for key flows)
- [`docs/knowledge_base.md`](knowledge_base.md) (accumulated “do not forget” insights)
- [`docs/troubleshooting.md`](troubleshooting.md) (common failures: LLM connectivity, Docker networking, model downloads, exports)

## Legacy guide (historical)

## Overview

Digital Article is a computational notebook application where you write what you want to analyze in natural language, and the system generates and executes Python code for you. This guide will walk you through installation, setup, and your first analysis.

## Prerequisites

### Required
- **Python 3.11+**
- **Node.js 18+** and npm (for frontend)
- **Git** (for cloning the repository)

### Recommended
- **LMStudio** (for local LLM hosting) - [Download here](https://lmstudio.ai/)
  - Or **Ollama** as an alternative - [Install here](https://ollama.ai/)
- **8GB+ RAM** (16GB+ recommended for running local LLMs)
- **Modern browser** (Chrome, Firefox, Safari, Edge - latest versions)

### For M4 Max Mac Users
- Ensure you're using Apple Silicon native Python (`arch -arm64 python3`)
- LMStudio or Ollama will leverage your Metal GPU acceleration
- Install Xcode Command Line Tools: `xcode-select --install`

## Installation

### Step 1: Clone the Repository

```bash
git clone https://github.com/lpalbou/digitalarticle.git
cd digitalarticle
```

### Step 2: Set Up Python Environment

We recommend using a virtual environment:

```bash
# Create virtual environment
python3 -m venv .venv

# Activate it
source .venv/bin/activate  # On macOS/Linux
# OR
.venv\Scripts\activate  # On Windows

# Install dependencies
pip install -r requirements.txt

# Install the CLI package in development mode
pip install -e .
```

**Dependencies installed** (from `requirements.txt`):
- `fastapi` - Backend web framework
- `uvicorn` - ASGI server
- `abstractcore[all]` **>= 2.6.9** - LLM provider abstraction (supports LMStudio, Ollama, OpenAI, etc.)
  - **Note**: Version 2.6.9 or higher is required for reliable async trace capture
- `pandas`, `numpy`, `matplotlib`, `plotly`, `seaborn` - Data analysis and visualization
- `scikit-learn`, `scipy` - Machine learning and scientific computing
- `reportlab`, `weasyprint` - PDF generation
- `pydantic` - Data validation

### Step 3: Set Up Frontend

```bash
cd frontend
npm install
cd ..
```

**Dependencies installed** (from `package.json`):
- `react`, `react-dom` - UI framework
- `typescript` - Type safety
- `vite` - Modern build tool and dev server (much faster than webpack)
- `tailwindcss` - Styling
- `axios` - HTTP client
- `@monaco-editor/react` - Code viewer
- `plotly.js`, `react-plotly.js` - Interactive visualizations
- `marked` - Markdown rendering

**Note on Vite**: The frontend uses Vite as the development server and build tool. Vite provides:
- Lightning-fast hot module replacement (HMR)
- Instant server startup
- Optimized production builds
- Configured to run on port 3000 (see [`frontend/vite.config.ts`](../frontend/vite.config.ts))

### Step 4: Set Up LLM Provider

Digital Article requires an LLM to generate code from prompts. You have several options:

#### Option A: LMStudio (Recommended for Local)

1. Download and install [LMStudio](https://lmstudio.ai/)
2. Download a code-capable model (recommended: **Qwen/Qwen3-next-80b** or **DeepSeek-Coder-33B**)
3. Start the local server:
   - Open LMStudio
   - Go to "Local Server" tab
   - Click "Start Server"
   - Note the port (default: 1234)

The default configuration in Digital Article already points to LMStudio:
```python
# backend/app/services/llm_service.py
provider = "lmstudio"
model = "qwen/qwen3-next-80b"
```

#### Option B: Ollama (Alternative Local Option)

```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Pull a model
ollama pull qwen2.5-coder:32b

# Start the server (runs automatically after install)
ollama serve
```

Update the configuration:
```python
# backend/app/services/llm_service.py
provider = "ollama"
model = "qwen2.5-coder:32b"
```

#### Option C: OpenAI API (Cloud Option)

```bash
# Set your API key
export OPENAI_API_KEY="sk-..."
```

Update the configuration:
```python
# backend/app/services/llm_service.py
provider = "openai"
model = "gpt-4"
```

**Note**: AbstractCore supports many other providers (Anthropic, Cohere, HuggingFace, etc.). See [AbstractCore docs](https://docs.abstractcore.dev/) for full list.

### Step 5: Verify Installation

Run a quick test to ensure everything is set up:

```bash
# Verify Python packages
python -c "import fastapi, pandas, abstractcore; print('✓ Backend dependencies OK')"

# Verify CLI commands are installed
which da-backend
which da-frontend

# If these commands are not found, reinstall the package
pip install -e . --force-reinstall
```

## Running the Application

### Quick Start (Recommended)

Use the CLI commands from anywhere:

```bash
# Terminal 1: Start backend
da-backend

# Terminal 2: Start frontend
da-frontend
```

**What the CLI commands do** (provided by `digitalarticle` package):

**`da-backend`**:
- Auto-discovers project root (searches for [`backend/`](../backend) directory)
- Kills any existing process on port 8000
- Checks for uvicorn, installs if missing
- Starts FastAPI server with auto-reload: `uvicorn app.main:app --reload --port 8000`

**`da-frontend`**:
- Auto-discovers project root (searches for [`frontend/`](../frontend) directory)
- Kills any existing process on port 3000
- Checks for Node.js and npm
- Installs npm dependencies if `node_modules/` doesn't exist
- Starts Vite dev server: `npm run dev` (configured for port 3000)

These commands are installed when you run `pip install -e .` and registered in [`pyproject.toml`](../pyproject.toml).

### Manual Start (Alternative)

If you prefer manual control:

```bash
# Terminal 1: Backend
cd backend
python -m uvicorn app.main:app --reload --port 8000

# Terminal 2: Frontend
cd frontend
npm run dev
```

### Access the Application

Once both servers are running:

- **Frontend**: [http://localhost:3000](http://localhost:3000) (Vite dev server)
- **Backend API**: [http://localhost:8000](http://localhost:8000) (FastAPI)
- **API Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs) (OpenAPI/Swagger UI)

You should see the Digital Article interface with a new empty notebook.

**Port Configuration**:
- Frontend uses port 3000 (configured in [`frontend/vite.config.ts`](../frontend/vite.config.ts))
- Backend uses port 8000 (standard for FastAPI)
- Vite proxies API requests from `/api/*` to `http://localhost:8000/api/*`

## Configuring Your LLM Provider

Before creating your first analysis, you should configure your LLM provider. Digital Article provides flexible configuration with visual feedback.

### Global LLM Configuration

1. Click the **Settings** button in the top header (or the **Settings** link in the status footer at the bottom)
2. The settings modal will show all available providers (LMStudio, Ollama, Anthropic, OpenAI, etc.)
3. Select your preferred provider and model
4. Click **Save Settings**

**What happens when you save:**
- Configuration is saved to [`config.json`](../config.json) in the project root
- The global LLMService is reinitialized with your selection
- All new notebooks will use this provider/model by default
- The status footer immediately updates to show the new configuration

### LLM Status Footer

At the bottom of every page, you'll see a status footer showing:
- **Connection status**: Connected, Error, or Loading
- **Provider**: The currently active LLM provider (e.g., "LM Studio", "Ollama")
- **Model**: The current model name (e.g., "qwen3-next-80b")
- **Context size**: Total context window (e.g., "32k context")
- **Output tokens**: Maximum output allocation (e.g., "out: 8k")

Click anywhere on the footer to quickly open the settings modal.

### Per-Notebook Configuration

Each notebook stores its own LLM configuration, which it inherits from the global config when created:
- When you create a new notebook, it automatically uses the current global provider/model
- If you change the global config later, existing notebooks keep their original settings
- This allows different analyses to use different models if needed

**Why this matters**: You can run heavy analyses with a powerful model, then create new notebooks with a faster model for simpler tasks.

### Downloading Models

Digital Article v2.6.0+ includes a unified model download system that works with Ollama, HuggingFace, and MLX providers directly from the settings UI.

#### How model downloads work

The download system uses AbstractCore 2.6.0's `download_model()` API to provide:
- **Non-blocking downloads**: Downloads run in background, UI remains responsive
- **Real-time progress**: See download status, percent complete, and bytes transferred
- **Persistent tracking**: Close the settings modal anytime - download continues
- **Toast notifications**: Get notified when download completes
- **Cancel anytime**: Stop downloads with one click

#### Downloading Ollama models

1. Open **Settings → Provider & Model**
2. Select **Ollama** provider
3. In the "Download Ollama Model" section:
   - Enter model name (e.g., `llama3.2`, `qwen3:4b`, `gemma3:1b`)
   - Click **Download**
4. The "Active Download" section appears at top showing progress
5. **You can now close the settings modal** - download continues in background
6. When complete, you'll see a toast notification: "Model X is ready to use"

**Example models**:
- `llama3.2` - Meta's Llama 3.2 (various sizes)
- `qwen3:4b` - Qwen 3 4B (fast, good for testing)
- `gemma3:1b` - Google Gemma 3 1B (very fast)
- `deepseek-coder:6.7b` - DeepSeek Coder (excellent for code generation)

#### Downloading HuggingFace models

1. Open **Settings → Provider & Model**
2. Select **HuggingFace** provider
3. In the "Download HuggingFace Model" section:
   - Enter model path (e.g., `meta-llama/Llama-2-7b-hf`)
   - For gated models, enter your HuggingFace auth token
   - Click **Download**
4. Progress tracked in "Active Download" section at top
5. Downloads are cached in persistent volume

**Note**: HuggingFace models are cached in `~/.cache/huggingface/` and shared with MLX.

#### Downloading MLX models (Apple Silicon only)

1. Open **Settings → Provider & Model**
2. Select **MLX** provider
3. In the "Download MLX Model" section:
   - Enter model path (e.g., `mlx-community/Qwen3-4B-4bit`)
   - Click **Download**
4. Progress tracked in "Active Download" section at top

**Note**: MLX models are optimized for Apple Silicon and not available in Docker deployments.

#### Download progress visibility

The "Active Download" section at the top of settings shows:
- **Provider and model name**: e.g., "ollama: llama3:8b"
- **Status message**: Current operation (e.g., "pulling manifest", "downloading layer")
- **Progress bar**: Visual progress with percentage
- **Download size**: Bytes downloaded / total size (when available)
- **Cancel button**: Stop the download anytime

**Key feature**: The download status is **always visible** regardless of which provider or tab you're viewing. Start an Ollama download, switch to HuggingFace to browse models, and you'll still see the Ollama progress at the top.

#### Checking downloaded models

After downloading, the model **automatically appears** in the model dropdown:
1. The provider list refreshes automatically when download completes
2. Select the provider (e.g., Ollama)
3. Open the **Model** dropdown
4. Your downloaded model will be listed
5. Select it and click **Save Settings**

**Auto-refresh**: The settings modal automatically refreshes the provider list when a download completes, so your new model appears immediately without needing to close and reopen settings.

**Note for LMStudio**: LMStudio does not have a REST API for downloading models. You must download models using the LMStudio GUI or the `lms get` CLI command on your host machine.

### Remote Access Configuration

Digital Article fully supports remote access. When accessing from a remote machine (e.g., `http://192.168.1.100:3000`):
- All configuration works seamlessly
- Settings modal uses relative API paths (no hardcoded localhost)
- Status footer updates in real-time
- Provider detection works from the server, not the client

**Important for Remote LLM Providers**: If you're using a local provider (LMStudio, Ollama) on the server, configure the server IP/hostname in the backend's LLM service settings.

## Your First Analysis

Let's perform a simple gene expression analysis using the included sample data.

### Step 1: Create a New Notebook

1. The application automatically creates a new notebook on first load
2. You'll see "Untitled Digital Article" at the top
3. Click to edit the title (e.g., "Gene Expression Analysis")
4. Click to edit the description (e.g., "Exploratory analysis of sample gene expression data")

### Step 2: View Available Data

At the top of the page, you'll see the "Files in Context" panel listing available data files:
- `gene_expression.csv` - Gene expression data
- `patient_data.csv` - Patient clinical data
- `protein_levels.csv` - Protein measurements
- `drug_response.csv` - Drug response data

### Step 3: Write Your First Prompt

In the empty cell, write a natural language prompt:

```
Load the gene expression data and show me basic information about the dataset
```

### Step 4: Execute the Cell

Click the **"Run"** button (play icon) or press `Ctrl+Enter` (Cmd+Enter on Mac).

**What happens**:
1. The prompt is sent to the LLM
2. The LLM generates Python code (takes 2-5 seconds)
3. The code is automatically executed
4. Results appear below the cell
5. A scientific methodology description is generated

You'll see:
- **Results Tab**: Output (dataset shape, columns, preview)
- **Code Tab**: Generated Python code (you can view and edit it)
- **Methodology Tab**: Scientific article-style description of what was done

### Step 5: Continue Your Analysis

Add another cell by clicking the **"+ Add Cell"** button at the bottom.

Try progressively more complex prompts:

```
Cell 2: "Create a heatmap showing the correlation between genes"

Cell 3: "Plot the distribution of expression values for the first 5 genes"

Cell 4: "Calculate and display descriptive statistics for all genes"

Cell 5: "Perform hierarchical clustering and show a dendrogram"
```

### Step 6: View Generated Code

For any cell, click the **"Code"** tab to see the Python code that was generated.

Example generated code (from "Load and show basic info" prompt):
```python
import pandas as pd
import matplotlib.pyplot as plt

# Load data from data directory
df = pd.read_csv('data/gene_expression.csv')

# Display basic information
print("Dataset shape:", df.shape)
print("\nColumn names:", df.columns.tolist())
print("\nFirst 5 rows:")
print(df.head())
print("\nBasic statistics:")
print(df.describe())
```

**You can edit this code directly** if needed, then re-run the cell.

### Step 7: Handle Errors Gracefully

If a prompt generates incorrect code, the system will:
1. Execute the code
2. Detect the error
3. Automatically ask the LLM to fix it (up to 3 retries)
4. Show the corrected result

You can also click **"Regenerate"** to ask the LLM to generate new code from the original prompt.

### Step 8: Export Your Analysis

When you're done, you have several export options in the header menu:

1. **Save** (💾): Saves the notebook (also auto-saves every 2 seconds)
2. **Export JSON**: Download full notebook as JSON
3. **Export PDF**:
   - **Article PDF**: Professional scientific article format (prompts + methodology + results, no code)
   - **Article + Code**: Same as above but includes generated code in appendix

The PDF export creates a publication-ready document that looks like a scientific paper.

## Understanding the Interface

### Cell Structure

Each cell has several components:

```
┌─────────────────────────────────────────────────┐
│ Cell Header                                      │
│ [▶ Run] [↻ Regenerate] [⚙ Settings] [🗑 Delete] │
├─────────────────────────────────────────────────┤
│ Prompt Input Area                                │
│ "Your natural language prompt here..."           │
├─────────────────────────────────────────────────┤
│ [Results] [Code] [Methodology]  ← Tabs           │
├─────────────────────────────────────────────────┤
│ Output Area (plots, tables, text, errors)        │
└─────────────────────────────────────────────────┘
```

### Cell Types

- **Prompt Cell** (default): Natural language → code generation → execution
- **Code Cell**: Direct Python code (for advanced users)
- **Markdown Cell**: Documentation and notes
- **Methodology Cell**: Scientific explanation (auto-generated after successful execution)

### Output Types

Digital Article captures and displays multiple output types:

1. **Text Output**: `print()` statements, warnings, errors
2. **Static Plots**: Matplotlib/Seaborn plots (rendered as PNG images)
3. **Interactive Plots**: Plotly charts (fully interactive in browser)
4. **Tables**: Pandas DataFrames (rendered as HTML tables)
5. **Errors**: Full Python tracebacks with highlighting

### Execution Context

Variables persist across cells (like Jupyter):

```
Cell 1: df = pd.read_csv('data/gene_expression.csv')
Cell 2: print(df.shape)  # Works! df is available
```

## Working with Data Files

### Uploading Your Own Data

1. Click "Files in Context" panel at the top
2. Click "Upload" button
3. Select your file - supported formats include:
   - **CSV/TSV**: Tabular data with automatic preview
   - **Excel (.xlsx/.xls)**: Spreadsheet files with sheet detection
   - **JSON**: Structured data with schema analysis
   - **H5/HDF5**: Scientific data containers with hierarchical structure
   - **H5AD**: Single-cell genomics data (AnnData format) with metadata
   - **Text files**: Plain text, markdown, etc.
4. File is copied to the notebook's workspace
5. Reference it in prompts: `"Load my_data.csv and analyze it"`

#### H5 File Support (NEW!)

Digital Article now provides state-of-the-art support for HDF5 files:

- **Standard H5/HDF5**: Hierarchical data with groups, datasets, and attributes
- **H5AD (AnnData)**: Single-cell genomics data with observations, variables, and embeddings
- **Interactive Preview**: Browse file structure, view metadata, and sample data
- **Scanpy Integration**: Automatic detection and processing of single-cell data
- **Memory Efficient**: Large files are processed with smart sampling for previews

Example prompts for H5 files:
```
Load the single-cell data from experiment.h5ad and show me the cell types
Analyze the gene expression matrix in data.h5 and find highly variable genes
Show me the structure of the HDF5 file and preview the main datasets
```

### Data File Paths

**Important**: Always reference files with the [`data/`](../data) prefix:

```python
# ✓ CORRECT
df = pd.read_csv('data/gene_expression.csv')

# ✗ WRONG (will fail)
df = pd.read_csv('gene_expression.csv')
```

This is automatically handled in generated code, but important if you're writing code directly.

### Deleting Files

Click the trash icon next to any uploaded file in the "Files in Context" panel.

**Note**: Sample data files cannot be deleted (they're shared across notebooks).

## Tips and Best Practices

### Writing Effective Prompts

**Good Prompts** (specific, clear intent):
```
"Load patient_data.csv and create a scatter plot of age vs blood_pressure"
"Calculate the mean and standard deviation for each gene in gene_expression.csv"
"Perform a t-test comparing treatment and control groups"
```

**Poor Prompts** (vague, ambiguous):
```
"Analyze the data"  # What data? What analysis?
"Make a plot"  # Plot of what?
"Do statistics"  # Which statistics?
```

### Iterative Refinement

You can refine prompts by re-running with more specific instructions:

```
Attempt 1: "Plot gene expression"
Results:   [Simple line plot]

Attempt 2: "Plot gene expression as a heatmap with hierarchical clustering"
Results:   [Clustered heatmap]

Attempt 3: "Plot gene expression as a heatmap with hierarchical clustering and color-coded by patient groups"
Results:   [Annotated clustered heatmap]
```

### Using Previous Results

Reference previous cells in later prompts:

```
Cell 1: "Load gene_expression.csv and assign it to variable df"

Cell 2: "Using df, filter for genes with mean expression > 10"

Cell 3: "Using the filtered data, create a PCA plot"
```

### Editing Generated Code

You can always switch to the "Code" tab and edit the Python code directly:

1. Click "Code" tab
2. Make your changes
3. Click "Run" to execute the modified code
4. The system remembers your edit (won't regenerate from prompt)

### Keyboard Shortcuts

- `Ctrl+Enter` / `Cmd+Enter`: Execute current cell
- `Shift+Enter`: Execute current cell and create new cell below
- `Ctrl+S` / `Cmd+S`: Save notebook
- `Escape`: Cancel editing

## Common Issues and Solutions

### Issue: "LLM service not available"

**Symptoms**: Errors about LLM connection failures

**Solutions**:
1. Ensure LMStudio/Ollama is running
2. Check the port (default: 1234 for LMStudio, 11434 for Ollama)
3. Verify the model is loaded in LMStudio
4. Check backend logs for connection errors

### Issue: "Module not found" errors in generated code

**Symptoms**: `ModuleNotFoundError: No module named 'some_package'`

**Solutions**:
1. Install the missing package: `pip install some_package`
2. Add it to `requirements.txt`
3. Restart the backend server
4. Click "Regenerate" to get updated code

### Issue: "File not found" errors

**Symptoms**: `FileNotFoundError: data/myfile.csv`

**Solutions**:
1. Ensure the file is uploaded (check "Files in Context" panel)
2. Use the correct path: `data/myfile.csv` (not just `myfile.csv`)
3. Check file name spelling and capitalization

### Issue: Generated code doesn't do what I want

**Solutions**:
1. **Refine the prompt**: Be more specific about what you want
2. **Click "Regenerate"**: LLM might produce better code on second try
3. **Edit the code manually**: Switch to "Code" tab and fix it yourself
4. **Check methodology**: The "Methodology" tab explains what the LLM understood

### Issue: Notebook not saving

**Symptoms**: Changes don't persist after refresh

**Solutions**:
1. Check browser console for errors
2. Verify backend is running (`http://localhost:8000/health`)
3. Check file permissions in [`notebooks/`](../notebooks) directory
4. Manually click "Save" button
5. Check backend logs for write errors

### Issue: Frontend shows blank page

**Solutions**:
1. Check browser console (F12) for JavaScript errors
2. Ensure backend is running and accessible
3. Check CORS configuration in [`backend/app/main.py`](../backend/app/main.py)
4. Try clearing browser cache
5. Verify Vite dev server is running on port 3000
6. Check that the Vite proxy is working (`/api` requests go to port 8000)

## Next Steps

### Learn More

- Read [Architecture Documentation](./architecture.md) to understand how the system works
- Read [Philosophy](./philosophy.md) to understand the design principles
- Check [Backlog](backlog/README.md) to see planned features

### Advanced Usage

Once comfortable with basics, explore:

1. **Custom LLM Providers**: Configure different models for different notebooks
2. **Direct Code Writing**: Use Code cells for complex logic
3. **Markdown Documentation**: Add context and explanations
4. **Version Control**: Export notebooks as JSON and track in git
5. **Scientific Publishing**: Use PDF export for papers and presentations

### Example Notebooks

Check the [`notebooks/`](../notebooks) directory for example analyses:
- Gene expression analysis
- Patient cohort analysis
- Time series analysis
- Machine learning workflows

### Community and Support

- **Issues**: Report bugs on GitHub
- **Discussions**: Ask questions in GitHub Discussions
- **Contributions**: See CONTRIBUTING.md for development guidelines

## Troubleshooting Checklist

If things aren't working, check this list:

- [ ] Python 3.8+ installed (`python --version`)
- [ ] Virtual environment activated (should see `(.venv)` in terminal)
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] CLI package installed (`pip install -e .`)
- [ ] Node.js 16+ installed (`node --version`)
- [ ] Frontend dependencies installed (`cd frontend && npm install`)
- [ ] LMStudio/Ollama running with a model loaded
- [ ] Backend server running on port 8000 (`curl http://localhost:8000/health`)
- [ ] Frontend server running on port 3000 (visit `http://localhost:3000`)
- [ ] No firewall blocking local ports
- [ ] Browser console shows no errors (F12 → Console tab)

## Getting Help

If you're still stuck:

1. Check backend logs in terminal where `da-backend` is running
2. Check browser console (F12) for frontend errors
3. Visit the API docs: `http://localhost:8000/docs`
4. Check GitHub Issues for similar problems
5. Create a new issue with:
   - Error messages
   - Steps to reproduce
   - System info (OS, Python version, Node version)
   - Backend and frontend logs

Welcome to Digital Article! We hope this tool makes your data analysis more accessible and your scientific communication more effective.
