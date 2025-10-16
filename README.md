# Reverse Analytics Notebook

A revolutionary analytics notebook where users interact with natural language prompts instead of code, powered by LLM code generation and live Python execution.

## Overview

This application transforms data analysis by allowing users to write natural language prompts that automatically generate and execute Python code. Perfect for biologists, clinicians, and other domain experts who want to focus on questions and results rather than implementation details.

## Features

- **Natural Language Interface**: Write prompts instead of code
- **Prompt-Code Bijection**: Each prompt maps to exactly one code implementation
- **Dual View Mode**: Toggle between prompt and generated code views
- **Rich Visualization**: Support for matplotlib, plotly, pandas tables, and images
- **Live Execution**: Immediate code execution with rich result display
- **Notebook Persistence**: Save/load functionality with JSON serialization
- **Advanced Result Panels**: Display plots, tables, interactive charts, and error messages
- **Auto-save Functionality**: Automatic saving of notebook changes
- **Export Capabilities**: Export notebooks in JSON, HTML, or Markdown formats

## Prerequisites

Before running the application, ensure you have:

1. **Python 3.9+** installed
2. **Node.js 16+** installed
3. **LMStudio** running locally with the `qwen/qwen3-next-80b` model
   - Download and install LMStudio from [lmstudio.ai](https://lmstudio.ai)
   - Load the `qwen/qwen3-next-80b` model in LMStudio
   - Start the local server in LMStudio (usually on port 1234)

## Quick Start

### Option 1: Using the Startup Scripts (Recommended)

1. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Start the backend**:
   ```bash
   python start_backend.py
   ```
   The backend will be available at `http://localhost:8000`

3. **Start the frontend** (in a new terminal):
   ```bash
   node start_frontend.js
   ```
   The frontend will be available at `http://localhost:3000`

### Option 2: Manual Setup

#### Backend Setup
```bash
# Install Python dependencies
pip install -r requirements.txt

# Start the FastAPI server
cd backend
uvicorn app.main:app --reload --port 8000 --host 0.0.0.0
```

#### Frontend Setup
```bash
# Install Node.js dependencies
cd frontend
npm install

# Start the React development server
npm run dev
```

## Architecture

- **Frontend**: React SPA with TypeScript and Tailwind CSS
- **Backend**: FastAPI server with AbstractCore LLM integration
- **LLM Provider**: LMStudio with qwen/qwen3-next-80b model
- **Execution**: Local Python execution with full data science stack
- **Visualization**: Advanced result panels supporting multiple output types
- **Storage**: JSON-based notebook persistence with auto-save

## Usage

1. **Create a New Notebook**: The application starts with a new notebook automatically
2. **Add a Cell**: Click "Add Cell" to create a new prompt cell
3. **Write a Prompt**: Describe your analysis in natural language, e.g.:
   - "Load the sales data and show me the first 5 rows"
   - "Create a bar chart of revenue by product category"
   - "Calculate the correlation between age and income"
4. **Execute**: Click the "Run" button or press Ctrl+Enter
5. **View Results**: See the generated code and execution results below
6. **Toggle Views**: Use the eye icon to switch between prompt and code views
7. **Save**: The notebook auto-saves, or click "Save" manually

## Sample Data

The `sample_data/` directory includes:
- `sales_data.csv`: Sample sales data with products, categories, prices, and revenue
- `customer_demographics.csv`: Customer demographic data with age, income, and education

## Example Prompts

### Basic Data Exploration
- "Load the sales data from sample_data/sales_data.csv and show me the first few rows"
- "Calculate summary statistics for all numeric columns"
- "Show me the data types and shape of the dataset"

### Visualizations
- "Create a bar chart showing total revenue by product"
- "Make a scatter plot of age vs income from the customer demographics"
- "Generate a pie chart of customer distribution by region"

### Advanced Analytics
- "Calculate the correlation matrix for numeric variables and create a heatmap"
- "Perform a time series analysis of daily revenue trends"
- "Create an interactive plotly visualization of the sales data"

### Statistical Analysis
- "Compare the average revenue between different customer segments"
- "Analyze the relationship between education level and purchase frequency"
- "Find the top 5 best-selling products by quantity"

See `test_examples.md` for comprehensive examples and expected outputs.

## API Documentation

When the backend is running, visit `http://localhost:8000/docs` for interactive API documentation.

## File Structure

```
reverse-notebook/
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── main.py         # FastAPI application
│   │   ├── models/         # Pydantic data models
│   │   ├── services/       # Business logic services
│   │   └── api/            # API endpoint routers
├── frontend/               # React frontend
│   ├── src/
│   │   ├── components/     # React components
│   │   ├── services/       # API client
│   │   └── types/          # TypeScript definitions
├── sample_data/           # Sample datasets
├── notebooks/             # Saved notebooks (created at runtime)
├── requirements.txt       # Python dependencies
├── package.json          # Node.js dependencies
└── start_*.py/js         # Startup scripts
```

## Troubleshooting

### Backend Issues
- **LLM Connection Errors**: Ensure LMStudio is running with the correct model
- **Import Errors**: Make sure all Python dependencies are installed (`pip install -r requirements.txt`)
- **Port Conflicts**: Check if port 8000 is available

### Frontend Issues
- **Build Errors**: Run `npm install` in the frontend directory
- **API Connection**: Ensure the backend is running on port 8000
- **Browser Issues**: Try clearing cache or using a different browser

### Common Problems
- **Code Generation Fails**: Check LMStudio connection and model availability
- **Execution Errors**: Verify sample data files exist in `sample_data/` directory
- **Plots Not Displaying**: Ensure matplotlib and plotly are properly installed

## Development

### Adding New Features
1. Backend changes go in `backend/app/`
2. Frontend changes go in `frontend/src/`
3. Update type definitions in `frontend/src/types/`
4. Add tests and examples in `test_examples.md`

### Contributing
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
