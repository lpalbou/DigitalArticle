# Digital Article

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![React 18](https://img.shields.io/badge/react-18.2-blue.svg)](https://reactjs.org/)
[![FastAPI](https://img.shields.io/badge/fastapi-0.104+-green.svg)](https://fastapi.tiangolo.com/)

> Transform computational notebooks from code-first to article-first. Write what you want to analyze in natural language; let AI generate the code.

## What is Digital Article?

Digital Article inverts the traditional computational notebook paradigm. Instead of writing code to perform analysis, you describe your analysis in natural language, and the system generates, executes, and documents the code for you—automatically creating publication-ready scientific methodology text.

![Digital Article](assets/da-illustration.jpg)

### Traditional Notebook
```
[Code: Data loading, cleaning, analysis]
[Output: Plots and tables]
```

### Digital Article
```
[Prompt: "Analyze gene expression distribution across experimental conditions"]
[Generated Methodology: "To assess gene expression patterns, data from 6 samples..."]
[Results: Plots and tables]
[Code: Available for inspection and editing]
```

## Key Features

- **Natural Language Analysis**: Write prompts like "create a heatmap of gene correlations" instead of Python code
- **Intelligent Code Generation**: LLM-powered code generation using AbstractCore (supports LMStudio, Ollama, OpenAI, and more)
- **Auto-Retry Error Fixing**: System automatically debugs and fixes generated code (up to 3 attempts)
- **Scientific Methodology Generation**: Automatically creates article-style explanations of your analysis
- **Rich Output Capture**: Matplotlib plots, Plotly interactive charts, Pandas tables, and text output
- **Publication-Ready PDF Export**: Generate scientific article PDFs with methodology, results, and optional code
- **Transparent Code Access**: View, edit, and understand all generated code
- **Persistent Execution Context**: Variables and DataFrames persist across cells (like Jupyter)
- **Workspace Isolation**: Each notebook has its own data workspace

## Who Is This For?

- **Domain Experts** (biologists, clinicians, social scientists): Perform sophisticated analyses without programming expertise
- **Data Scientists**: Accelerate exploratory analysis and documentation
- **Researchers**: Create reproducible analyses with built-in methodology text
- **Educators**: Teach data analysis concepts without syntax barriers
- **Anyone** who wants to think in terms of *what* to analyze rather than *how* to code it

## Quick Start

### Prerequisites

- Python 3.8+
- Node.js 16+
- LMStudio or Ollama (for local LLM) OR OpenAI API key

### Installation

```bash
# Clone repository
git clone https://github.com/lpalbou/digitalarticle.git
cd digitalarticle

# Set up Python environment
python -m venv .venv
source .venv/bin/activate  # On macOS/Linux
pip install -r requirements.txt
pip install -e .

# Set up frontend
cd frontend
npm install
cd ..
```

### Start the Application

```bash
# Terminal 1: Backend
da-backend

# Terminal 2: Frontend
da-frontend
```

Then open [http://localhost:3000](http://localhost:3000)

**Full setup guide**: See [Getting Started](docs/getting-started.md)

## LLM Configuration

Digital Article requires an LLM provider to generate code from prompts. The system provides flexible configuration options:

### Global Configuration
- Click the **Settings** button in the header to select your provider and model
- Changes persist across sessions and apply to all new notebooks
- Configuration is saved to `config.json` in the project root

### Per-Notebook Configuration
- Each notebook can use a different provider/model if needed
- New notebooks automatically inherit the global configuration
- Notebook-specific settings override global defaults during execution

### Visual Feedback
- The **status footer** at the bottom shows the current provider, model, and context size
- Real-time updates when configuration changes
- Click the footer's **Settings** button for quick access to configuration

### Remote Access
All configuration works seamlessly when accessing Digital Article from remote machines (e.g., `http://server-ip:3000`). The settings modal and status footer use relative API paths for proper remote connectivity.

## Example Usage

### Simple Analysis

**Prompt:**
```
Load gene_expression.csv and show the distribution of expression values
```

**Generated Code:**
```python
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

df = pd.read_csv('data/gene_expression.csv')

plt.figure(figsize=(10, 6))
sns.histplot(df.values.flatten(), bins=50, kde=True)
plt.title('Distribution of Gene Expression Values')
plt.xlabel('Expression Level')
plt.ylabel('Frequency')
plt.show()

print(f"Dataset shape: {df.shape}")
print(f"Mean expression: {df.values.mean():.2f}")
print(f"Std expression: {df.values.std():.2f}")
```

**Generated Methodology:**
```
To assess the overall distribution of gene expression levels, the dataset
containing 20 genes across 6 experimental conditions was examined. The
analysis revealed a mean expression level of 15.3 ± 4.2 across all genes,
with a right-skewed distribution indicative of heterogeneous expression
patterns.
```

### Progressive Analysis

```
Cell 1: "Load patient_data.csv and show basic statistics"
Cell 2: "Create a scatter plot of age vs blood_pressure colored by gender"
Cell 3: "Perform t-test comparing blood pressure between genders"
Cell 4: "Generate a summary table with mean values by gender"
```

Each cell builds on the previous context, with variables persisting across cells.

## Architecture Overview

```
Frontend (React + TypeScript)
    ↓ HTTP/REST
Backend (FastAPI)
    ↓
Services Layer
    ├─ LLMService (AbstractCore → LMStudio/Ollama/OpenAI)
    ├─ ExecutionService (Python code execution sandbox)
    ├─ NotebookService (orchestration)
    └─ PDFService (scientific article generation)
    ↓
Data Layer
    ├─ Notebooks (JSON files)
    └─ Workspaces (isolated data directories)
```

**Detailed architecture**: See [Architecture Documentation](docs/architecture.md)

## Technology Stack

### Backend
- **FastAPI** - Modern Python web framework
- **AbstractCore** - LLM provider abstraction
- **Pandas, NumPy, Matplotlib, Plotly** - Data analysis and visualization
- **Pydantic** - Data validation and serialization
- **ReportLab/WeasyPrint** - PDF generation

### Frontend
- **React 18 + TypeScript** - UI framework with type safety
- **Vite** - Lightning-fast dev server and build tool (runs on port 3000)
- **Tailwind CSS** - Utility-first styling
- **Monaco Editor** - Code viewing
- **Plotly.js** - Interactive visualizations
- **Axios** - HTTP client

## Project Philosophy

Digital Article is built on the belief that **analytical tools should adapt to how scientists think, not the other way around**. Key principles:

1. **Article-First**: The narrative is primary; code is a derived implementation
2. **Transparent Generation**: All code is inspectable and editable
3. **Scientific Rigor**: Auto-generate methodology text suitable for publications
4. **Progressive Disclosure**: Show complexity only when needed
5. **Intelligent Recovery**: Auto-fix errors before asking for user intervention

**Full philosophy**: See [Philosophy Documentation](docs/philosophy.md)

## Documentation

- [Getting Started Guide](docs/getting-started.md) - Installation and first analysis
- [Architecture Documentation](docs/architecture.md) - System design and component breakdown
- [Philosophy](docs/philosophy.md) - Design principles and motivation
- [Roadmap](ROADMAP.md) - Planned features and development timeline

## Current Status

**Version**: 0.1.0 (Alpha)

**Working Features**:
- ✅ Natural language to code generation
- ✅ Code execution with rich output capture
- ✅ Auto-retry error correction (up to 3 attempts)
- ✅ Scientific methodology generation
- ✅ Matplotlib and Plotly visualization support
- ✅ Pandas DataFrame capture and display
- ✅ Multi-format export (JSON, HTML, Markdown)
- ✅ Scientific PDF export
- ✅ File upload and workspace management
- ✅ Persistent execution context across cells

**Known Limitations**:
- ⚠️ Single-user deployment only (no multi-user authentication)
- ⚠️ Code execution in same process as server (not production-safe)
- ⚠️ JSON file storage (not scalable to many notebooks)
- ⚠️ No real-time collaboration
- ⚠️ LLM latency makes it unsuitable for real-time applications

**Production Readiness**: This is a research prototype suitable for single-user or small team deployment. Production use requires:
- Containerized code execution
- Database storage (PostgreSQL)
- Authentication and authorization
- Job queue for LLM requests
- See [Architecture - Deployment Considerations](docs/architecture.md#deployment-considerations)

## Example Use Cases

### Bioinformatics
```
"Load RNA-seq counts and perform differential expression analysis between treatment and control"
"Create a volcano plot highlighting significantly differentially expressed genes"
"Generate a heatmap of top 50 DE genes with hierarchical clustering"
```

### Clinical Research
```
"Analyze patient outcomes by treatment group with survival curves"
"Test for significant differences in biomarkers across cohorts"
"Create a forest plot of hazard ratios for different risk factors"
```

### Data Exploration
```
"Load the dataset and identify missing values and outliers"
"Perform PCA and visualize the first two principal components"
"Fit a linear model predicting outcome from predictors and show coefficients"
```

## Comparison to Alternatives

| Feature | Digital Article | Jupyter | ChatGPT Code Interpreter | Observable |
|---------|----------------|---------|--------------------------|------------|
| Natural language prompts | ✅ Primary | ❌ | ✅ | ❌ |
| Code transparency | ✅ Always visible | ✅ | ⚠️ Limited | ⚠️ Limited |
| Local LLM support | ✅ | ❌ | ❌ | ❌ |
| Auto-error correction | ✅ 3 retries | ❌ | ⚠️ Manual | ❌ |
| Scientific methodology | ✅ Auto-generated | ❌ | ❌ | ❌ |
| Publication PDF export | ✅ | ⚠️ Via nbconvert | ❌ | ❌ |
| Persistent context | ✅ | ✅ | ⚠️ Session-based | ✅ |
| Self-hosted | ✅ | ✅ | ❌ | ❌ |

## Roadmap Highlights

**Near Term (Q2 2025)**:
- Enhanced LLM prompt templates for specific domains
- Version control integration (git-style cell history)
- Improved error diagnostics and suggestions
- Additional export formats (LaTeX, Quarto)

**Medium Term (Q3-Q4 2025)**:
- Collaborative editing (real-time multi-user)
- Database backend (PostgreSQL)
- Containerized code execution (Docker)
- Template library (common analysis workflows)

**Long Term (2026+)**:
- LLM-suggested analysis strategies
- Active learning from user corrections
- Integration with laboratory information systems
- Plugin architecture for domain-specific extensions

**Full roadmap**: See [ROADMAP.md](ROADMAP.md)

## Contributing

We welcome contributions! Areas where help is needed:

- **Testing**: Try the system with your data and report issues
- **Documentation**: Improve guides, add examples
- **LLM Prompts**: Enhance code generation quality
- **UI/UX**: Improve the interface
- **Domain Templates**: Add analysis workflows for specific fields

See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines.

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Citation

If you use Digital Article in your research, please cite:

```bibtex
@software{digital_article_2025,
  title = {Digital Article: Natural Language Computational Notebooks},
  author = {Laurent-Philippe Albou},
  year = {2025},
  url = {https://github.com/lpalbou/digitalarticle}
}
```

## Acknowledgments

- **AbstractCore** for LLM provider abstraction
- **LMStudio** and **Ollama** for local LLM serving
- **FastAPI** and **React** communities for excellent frameworks
- Inspired by literate programming (Knuth), computational essays (Wolfram), and Jupyter notebooks

## Support and Contact

- **Issues**: [GitHub Issues](https://github.com/lpalbou/digitalarticle/issues)
- **Discussions**: [GitHub Discussions](https://github.com/lpalbou/digitalarticle/discussions)
- **Email**: contact@abstractcore.ai

---

**We're not building a better notebook. We're building a different kind of thinking tool—one that speaks the language of science, not just the language of code.**
