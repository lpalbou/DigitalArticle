# Contributing to Digital Article

Thank you for your interest in contributing to Digital Article! This document provides guidelines for contributing to the project.

## Project Author

**Laurent-Philippe Albou** (lpalbou@gmail.com)
- Lead developer and architect
- Responsible for core design and implementation
- Research scientist specializing in bioinformatics and computational analysis tools

## Acknowledgments

The **[AbstractCore](https://www.abstractcore.ai/)** project for their LLM provider abstraction library and support in adapting the framework for Digital Article's specific needs.

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- Git
- Docker (for containerized deployment)
- LLM provider (Ollama, LMStudio, or API keys for cloud providers)

### Development Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/lpalbou/digitalarticle.git
   cd digitalarticle
   ```

2. **Set up Python environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   # .venv\Scripts\activate   # Windows
   pip install -e .
   ```

3. **Set up frontend**:
   ```bash
   cd frontend
   npm install
   cd ..
   ```

4. **Start development servers**:
   ```bash
   # Terminal 1: Backend
   da-backend

   # Terminal 2: Frontend
   da-frontend
   ```

### Project Structure

```
digital-article/
├── backend/           # FastAPI backend
│   ├── app/
│   │   ├── api/       # REST API endpoints
│   │   ├── models/    # Pydantic data models
│   │   └── services/  # Business logic
│   └── pyproject.toml
├── frontend/          # React TypeScript frontend
│   ├── src/
│   │   ├── components/
│   │   ├── services/  # API client
│   │   └── types/
│   └── package.json
├── docker/            # Docker deployment files
├── docs/              # Documentation
├── notebooks/         # Notebook storage (JSON)
└── tests/             # Test suites
```

## Development Guidelines

### Code Style

**Python (Backend)**:
- Follow PEP 8
- Use type hints for all functions
- Document functions with docstrings
- Use meaningful variable names
- Keep functions focused and small

**TypeScript (Frontend)**:
- Follow Airbnb style guide
- Use interfaces for all data structures
- Prefer functional components with hooks
- Use meaningful component and variable names

### Testing

**Testing Philosophy**:
- All tests use **real implementations**, never mocked
- Tests should cover edge cases and error handling
- Test suite must pass before declaring features complete

**Running Tests**:
```bash
# Backend tests
python -m pytest tests/ -v

# Frontend tests (when available)
cd frontend
npm test
```

### Commit Messages

Use clear, descriptive commit messages:
```
feat: Add semantic knowledge graph extraction
fix: Resolve variable leakage between notebooks
docs: Update Docker deployment guide
refactor: Simplify execution context management
test: Add comprehensive table parsing tests
```

## Contributing Process

### Reporting Issues

When reporting issues, please include:
- Clear description of the problem
- Steps to reproduce
- Expected vs actual behavior
- Environment details (OS, Python version, Node version)
- Relevant logs or screenshots

### Submitting Pull Requests

1. **Fork the repository** and create a feature branch
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** following the guidelines above

3. **Test thoroughly**:
   - Ensure all existing tests pass
   - Add new tests for your changes
   - Test both backend and frontend functionality

4. **Document your changes**:
   - Update relevant documentation
   - Add comments for complex logic
   - Update CLAUDE.md with completed task details

5. **Submit the pull request**:
   - Provide clear description of changes
   - Reference any related issues
   - Explain design decisions if applicable

### Code Review Process

- All pull requests require review before merging
- Address review feedback promptly
- Keep pull requests focused and atomic
- Ensure CI checks pass

## Areas for Contribution

We welcome contributions in these areas:

### High Priority
- **Testing**: Expand test coverage (target: 80%)
- **Documentation**: Improve guides, add examples
- **LLM Prompts**: Enhance code generation quality
- **UI/UX**: Improve interface usability
- **Error Handling**: Better error messages and recovery

### Medium Priority
- **Domain Templates**: Add analysis workflows for specific fields (bioinformatics, clinical research, etc.)
- **Export Formats**: Add LaTeX, Quarto, Word export
- **Performance**: Optimize LLM response time
- **Accessibility**: ARIA labels, keyboard navigation

### Future Enhancements
- **Multi-user Support**: Authentication, authorization
- **Collaboration**: Real-time editing
- **Database Backend**: PostgreSQL migration
- **Containerized Execution**: Docker-based code sandboxing

## Development Philosophy

**Article-First Paradigm**: Digital Article inverts traditional computational notebooks - users describe analysis in natural language, and the system generates, executes, and documents code automatically. When contributing, keep this philosophy in mind:

1. **User Experience**: Prioritize simplicity for domain experts
2. **Transparency**: All code must be inspectable and editable
3. **Scientific Rigor**: Methodology text should be publication-ready
4. **Progressive Disclosure**: Hide complexity, show on demand
5. **Intelligent Recovery**: Auto-fix errors before asking for user intervention

## Questions and Support

- **GitHub Issues**: For bug reports and feature requests
- **GitHub Discussions**: For questions and general discussion
- **Email**: lpalbou@gmail.com for direct contact

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Thank You!

Your contributions help make Digital Article better for researchers and domain experts worldwide. We appreciate your time and effort!

---

**Remember**: Code is the source of truth. When in doubt, consult the codebase and existing patterns.
