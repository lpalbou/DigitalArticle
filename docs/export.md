# Export System Documentation

Digital Article provides multiple export formats to support different use cases, from data archival to scientific publication. This document details the export system architecture and formats.

## Overview

The export system is designed with the following principles:
- **Clean Structure**: Focus on essential content, removing internal application state
- **Actionable Data**: Structured for easy parsing and processing by external tools
- **Version Tracking**: Include export metadata for compatibility and debugging
- **Format Flexibility**: Support multiple output formats for different audiences

## Export Formats

### JSON Export

The JSON export is the primary format for data interchange, backup, and version control. It provides a complete representation of the digital article in a clean, structured format.

#### Structure Overview

```json
{
  "digital_article": {
    "version": "0.0.3",
    "export_timestamp": "2025-10-21T07:53:25.083962"
  },
  "metadata": { ... },
  "configuration": { ... },
  "cells": [ ... ]
}
```

#### Detailed Schema

##### Root Level

| Field | Type | Description |
|-------|------|-------------|
| `digital_article` | Object | Export metadata and version information |
| `metadata` | Object | Article metadata (title, author, dates, etc.) |
| `configuration` | Object | LLM and system configuration used |
| `cells` | Array | Array of cell objects containing the article content |

##### Digital Article Section

```json
{
  "digital_article": {
    "version": "0.0.3",           // Digital Article version that created this export
    "export_timestamp": "..."     // ISO 8601 timestamp of export
  }
}
```

##### Metadata Section

```json
{
  "metadata": {
    "id": "uuid-string",          // Unique notebook identifier
    "title": "Article Title",     // Article title (editable by user)
    "description": "...",         // Article description/subtitle (editable by user)
    "author": "Author Name",      // Author name
    "created_at": "...",          // ISO 8601 creation timestamp
    "updated_at": "...",          // ISO 8601 last update timestamp
    "version": "1.0.0",           // Article version (user-defined)
    "tags": ["tag1", "tag2"]      // User-defined tags
  }
}
```

##### Configuration Section

```json
{
  "configuration": {
    "llm_provider": "lmstudio",           // LLM provider used
    "llm_model": "qwen/qwen3-next-80b"    // LLM model used
  }
}
```

##### Cells Array

Each cell in the `cells` array has the following structure:

```json
{
  "id": "uuid-string",           // Unique cell identifier
  "type": "prompt",              // Cell type: "prompt", "code", "markdown", "methodology"
  "created_at": "...",           // ISO 8601 creation timestamp
  "updated_at": "...",           // ISO 8601 last update timestamp
  "content": { ... },            // Cell content (varies by type)
  "execution": { ... },          // Execution status and summary
  "tags": ["tag1"],              // Optional: user-defined tags
  "metadata": { ... }            // Optional: additional metadata
}
```

##### Cell Content by Type

**Prompt Cells** (most common):
```json
{
  "content": {
    "prompt": "Natural language description of analysis",
    "code": "Generated Python code",
    "methodology": "AI-generated scientific explanation"
  }
}
```

**Code Cells**:
```json
{
  "content": {
    "code": "Python code",
    "methodology": "Optional scientific explanation"
  }
}
```

**Markdown Cells**:
```json
{
  "content": {
    "markdown": "Markdown content for documentation"
  }
}
```

**Methodology Cells**:
```json
{
  "content": {
    "prompt": "Original prompt",
    "code": "Generated code", 
    "methodology": "Scientific methodology explanation"
  }
}
```

##### Execution Summary

The execution section provides a lightweight summary without heavy data:

```json
{
  "execution": {
    "status": "success",                    // "success", "error", "not_executed"
    "execution_count": 3,                   // Number of times executed
    "last_executed": "2025-10-21T...",      // ISO 8601 timestamp of last execution
    "execution_time": 0.007,                // Execution time in seconds
    "has_output": true,                     // Boolean: has text output
    "has_plots": false,                     // Boolean: has matplotlib plots
    "has_tables": true,                     // Boolean: has pandas tables
    "has_interactive_plots": false,         // Boolean: has plotly charts
    "error_type": "ValueError",             // Only present if status is "error"
    "error_message": "Error description"    // Only present if status is "error"
  }
}
```

### PDF Export

PDF export generates publication-ready scientific articles with two variants:

1. **Article PDF**: Includes prompts, methodology, and results (no code)
2. **Article + Code PDF**: Same as above plus generated code in appendix

The PDF export uses professional typography and scientific article formatting suitable for academic publication.

### HTML Export

HTML export creates standalone web pages with:
- Interactive Plotly charts (if present)
- Formatted code blocks with syntax highlighting
- Responsive design for web viewing
- Self-contained (no external dependencies)

### Markdown Export

Markdown export provides:
- Version control friendly format
- Human-readable structure
- Compatible with documentation systems
- Suitable for GitHub, GitLab, etc.

## Usage Examples

### Programmatic Access

```python
import requests
import json

# Export as JSON
response = requests.get(f"http://localhost:8000/api/notebooks/{notebook_id}/export?format=json")
article_data = response.json()

# Access article metadata
print(f"Title: {article_data['metadata']['title']}")
print(f"Author: {article_data['metadata']['author']}")

# Process cells
for cell in article_data['cells']:
    if cell['type'] == 'prompt':
        print(f"Prompt: {cell['content']['prompt']}")
        print(f"Code: {cell['content']['code']}")
        print(f"Methodology: {cell['content']['methodology']}")
```

### Command Line Export

```bash
# Export as JSON
curl "http://localhost:8000/api/notebooks/{id}/export?format=json" > article.json

# Export as PDF
curl "http://localhost:8000/api/notebooks/{id}/export?format=pdf" > article.pdf

# Export as PDF with code
curl "http://localhost:8000/api/notebooks/{id}/export?format=pdf&include_code=true" > article_with_code.pdf
```

### Frontend Export

The frontend provides export buttons in the header:
- **Export as JSON**: Downloads clean JSON file
- **Export as PDF**: Downloads scientific article PDF
- **Export PDF with Code**: Downloads PDF including code appendix

## Import Considerations

While Digital Article currently focuses on export, the clean JSON structure is designed to support future import functionality:

- **Unique IDs**: All cells and notebooks have UUIDs for reference integrity
- **Timestamps**: Creation and update times preserved
- **Version Tracking**: Export version allows for format migration
- **Metadata Preservation**: All user-defined content is maintained

## Best Practices

### For Archival
- Use JSON export for complete data preservation
- Include export in version control systems
- Regular exports for backup purposes

### For Sharing
- Use PDF export for scientific communication
- Use HTML export for web sharing with interactive elements
- Use Markdown export for documentation systems

### For Processing
- Parse JSON exports for automated analysis
- Use execution summaries to identify successful analyses
- Filter cells by type for specific content extraction

## Technical Implementation

The export system is implemented in:
- **Backend**: `backend/app/services/notebook_service.py` - `_create_clean_export_structure()`
- **Frontend**: `frontend/src/services/api.ts` - `notebookAPI.export()`
- **API**: `backend/app/api/notebooks.py` - `/export` endpoint

### Key Design Decisions

1. **Separation of Concerns**: Export structure differs from internal storage to optimize for different use cases
2. **Lightweight Execution Data**: Execution results summarized as boolean flags to reduce file size
3. **Version Tracking**: Export format versioning enables future compatibility
4. **Content Focus**: Internal application state removed to focus on user content

## Future Enhancements

Planned improvements to the export system:

- **Import Functionality**: Ability to import JSON exports back into Digital Article
- **Selective Export**: Export specific cells or date ranges
- **Template Export**: Export as templates for reuse
- **Batch Export**: Export multiple articles at once
- **Custom Formats**: Plugin system for custom export formats

## Troubleshooting

### Common Issues

**Empty JSON Export**: 
- Check that the notebook exists and has content
- Verify API endpoint is accessible

**Large File Sizes**:
- JSON exports exclude heavy execution data (plots, tables)
- Use execution summary flags to identify content without downloading full data

**Format Errors**:
- Ensure proper URL encoding for special characters
- Check API response status codes for error details

### API Response Codes

- `200`: Successful export
- `404`: Notebook not found
- `400`: Invalid format parameter
- `500`: Server error during export generation

For additional support, see the main [Architecture Documentation](architecture.md) or [Getting Started Guide](getting-started.md).
