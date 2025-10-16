# Reverse Analytics Notebook

A novel analytics notebook where biologists interact with natural language prompts instead of code. The system generates Python code from prompts and displays results while keeping the technical complexity hidden.

## Quick Start

### Backend (FastAPI)
```bash
# Kill any existing process on port 8000
lsof -ti:8000 | xargs kill -9 2>/dev/null || true

# Start backend
cd backend
python -m uvicorn app.main:app --reload --port 8000 --log-level debug
```

### Frontend (React)
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