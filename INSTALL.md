# Digital Article CLI Installation Guide

## Quick Installation

### From Source (Development)
```bash
# Clone the repository
git clone <repository-url>
cd reverse-notebook

# Install in development mode
pip install -e .
```

### From PyPI (When Published)
```bash
pip install digital-article-cli
```

## Verification

After installation, verify the commands are available:

```bash
# Check if commands are installed
which da-backend
which da-frontend

# Test the commands (from any directory)
da-backend --help   # Should show usage information
da-frontend --help  # Should show usage information
```

## Usage

### Starting the Backend
```bash
da-backend
```
This will:
- Find your Digital Article project directory automatically
- Kill any existing process on port 8000
- Install uvicorn if not present
- Start the FastAPI backend server on http://localhost:8000
- Enable auto-reload for development

### Starting the Frontend
```bash
da-frontend
```
This will:
- Find your Digital Article project directory automatically
- Kill any existing process on port 5173
- Check for Node.js and npm
- Install npm dependencies if needed
- Start the Vite development server on http://localhost:5173
- Enable hot module replacement

## Troubleshooting

### Command Not Found
If you get "command not found" errors:
```bash
# Reinstall the package
pip install -e . --force-reinstall

# Check your Python environment
which python
which pip
```

### Permission Errors
If you get permission errors during installation:
```bash
# Use user installation
pip install -e . --user

# Or use virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -e .
```

### Port Already in Use
The commands automatically kill existing processes on the required ports, but if you encounter issues:
```bash
# Manually kill processes
lsof -ti:8000 | xargs kill -9  # Backend port
lsof -ti:5173 | xargs kill -9  # Frontend port
```

### Missing Dependencies
If you encounter missing dependency errors:
```bash
# For backend issues
pip install uvicorn[standard] fastapi

# For frontend issues (in frontend directory)
cd frontend
npm install
```

## Development

### Building the Package
```bash
# Install build dependencies
pip install build

# Build wheel
python -m build --wheel

# The wheel will be in dist/
```

### Running Tests
```bash
# Install test dependencies
pip install -e .[dev]

# Run tests
pytest
```

## Uninstallation

```bash
pip uninstall digital-article-cli
```
