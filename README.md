# Digital Article

A novel analytics notebook where biologists interact with natural language prompts instead of code. The system generates Python code from prompts and displays results while keeping the technical complexity hidden.

## Quick Start

### Installation
Install the Digital Article CLI package to get the `da-backend` and `da-frontend` commands:

```bash
# Install in development mode (from project root)
pip install -e .

# Or install from PyPI (when published)
pip install digital-article-cli
```

### Usage
After installation, you can use these commands from anywhere:

```bash
# Start backend server (kills any existing process on port 8000)
da-backend

# Start frontend server (kills any existing process on port 5173)  
da-frontend
```

The commands will automatically:
- 🔍 Find your Digital Article project directory
- 🧹 Kill any existing processes on the required ports
- 📦 Install missing dependencies (uvicorn for backend, npm packages for frontend)
- 🚀 Start the servers with auto-reload enabled

### Manual Setup (Alternative)
#### Backend (FastAPI)
```bash
# Kill any existing process on port 8000
lsof -ti:8000 | xargs kill -9 2>/dev/null || true

# Start backend
cd backend
python -m uvicorn app.main:app --reload --port 8000
```

#### Frontend (React)
```bash
# Kill any existing process on port 5173
lsof -ti:5173 | xargs kill -9 2>/dev/null || true

# Start frontend
cd frontend
npm run dev
```

## Access
- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## Usage
1. Create a new notebook
2. Enter natural language prompts (e.g., "analyze gene_expression.csv and show distribution")
3. Execute cells to generate Python code and view results
4. Toggle between prompt and code view using the switch icon

## Sample Data
The system includes sample biological datasets:
- `gene_expression.csv` - Gene expression data
- `patient_data.csv` - Patient clinical data
- `protein_levels.csv` - Protein level measurements
- `drug_response.csv` - Drug response data