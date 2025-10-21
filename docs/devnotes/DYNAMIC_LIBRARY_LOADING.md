# Dynamic Library Loading Enhancement Proposal

## Current State

The Digital Article system currently uses a **static library approach** where supported libraries are:

1. **Pre-installed** in requirements.txt
2. **Pre-configured** in ExecutionService._initialize_globals()
3. **Hard-coded** in LLMService system prompts
4. **Manually handled** in code preprocessing

### Current Library Support Architecture

```python
# In ExecutionService._initialize_globals()
globals_dict = {
    'pd': pd,           # Pre-imported
    'np': np,           # Pre-imported
    'plt': plt,         # Pre-imported
    'px': None,         # Lazy-loaded
    'go': None,         # Lazy-loaded
    'sns': None,        # Lazy-loaded
    'stats': None,      # Lazy-loaded
    'sc': None,         # Lazy-loaded (scanpy)
    'umap': None,       # Lazy-loaded
}

# In _preprocess_code()
if 'import seaborn as sns' in line:
    processed_lines.append("sns = _lazy_import('seaborn', 'sns')")
elif 'import scanpy as sc' in line:
    processed_lines.append("sc = _lazy_import('scanpy', 'sc')")
# ... manual handling for each library
```

## Problems with Current Approach

1. **Manual Configuration**: Each new library requires code changes in multiple places
2. **Static Dependencies**: All libraries must be pre-installed, even if unused
3. **Limited Extensibility**: Users cannot add domain-specific libraries
4. **Maintenance Overhead**: Adding libraries requires developer intervention

## Dynamic Library Loading Vision

### Goals

1. **User-Driven Installation**: Allow users to install libraries on-demand
2. **Automatic Discovery**: System detects and configures new libraries
3. **Safe Execution**: Maintain security while allowing flexibility
4. **Intelligent Prompting**: LLM knows about available libraries dynamically

### Proposed Architecture

#### 1. Library Registry System

```python
class LibraryRegistry:
    """Central registry for managing available libraries."""
    
    def __init__(self):
        self.installed_libraries = {}
        self.library_metadata = {}
        self.import_patterns = {}
    
    def scan_environment(self):
        """Scan Python environment for installed packages."""
        import pkg_resources
        for dist in pkg_resources.working_set:
            self.register_library(dist.project_name, dist.version)
    
    def register_library(self, name: str, version: str, metadata: dict = None):
        """Register a library with optional metadata."""
        self.installed_libraries[name] = version
        if metadata:
            self.library_metadata[name] = metadata
    
    def get_import_suggestions(self, library_name: str) -> List[str]:
        """Get common import patterns for a library."""
        return self.import_patterns.get(library_name, [])
    
    def is_available(self, library_name: str) -> bool:
        """Check if library is available."""
        return library_name in self.installed_libraries
```

#### 2. Dynamic Import Handler

```python
class DynamicImportHandler:
    """Handles dynamic imports with safety checks."""
    
    def __init__(self, registry: LibraryRegistry):
        self.registry = registry
        self.import_cache = {}
        self.security_whitelist = set()  # Approved libraries
    
    def safe_import(self, module_path: str, alias: str = None) -> Any:
        """Safely import a module with caching."""
        if module_path in self.import_cache:
            return self.import_cache[module_path]
        
        # Security check
        if not self._is_safe_import(module_path):
            raise SecurityError(f"Import of {module_path} not allowed")
        
        try:
            module = importlib.import_module(module_path)
            self.import_cache[module_path] = module
            return module
        except ImportError as e:
            # Suggest installation or alternatives
            suggestions = self._get_import_suggestions(module_path)
            raise ImportError(f"Cannot import {module_path}. {suggestions}")
    
    def _is_safe_import(self, module_path: str) -> bool:
        """Check if import is safe (security whitelist)."""
        # Check against whitelist of approved libraries
        base_module = module_path.split('.')[0]
        return base_module in self.security_whitelist
```

#### 3. Smart Code Preprocessing

```python
class SmartCodePreprocessor:
    """Intelligently preprocess code based on available libraries."""
    
    def __init__(self, registry: LibraryRegistry, import_handler: DynamicImportHandler):
        self.registry = registry
        self.import_handler = import_handler
    
    def preprocess_code(self, code: str) -> str:
        """Preprocess code with dynamic library handling."""
        lines = code.split('\n')
        processed_lines = []
        
        for line in lines:
            if self._is_import_line(line):
                processed_line = self._handle_import_line(line)
                processed_lines.append(processed_line)
            else:
                processed_lines.append(line)
        
        return '\n'.join(processed_lines)
    
    def _handle_import_line(self, line: str) -> str:
        """Handle import lines dynamically."""
        import_info = self._parse_import(line)
        
        if import_info['module'] in self.registry.installed_libraries:
            # Generate lazy import for known libraries
            return f"{import_info['alias']} = _dynamic_import('{import_info['module']}', '{import_info['alias']}')"
        else:
            # Suggest installation or alternatives
            return f"# {line}  # Library not available - install with: pip install {import_info['module']}"
```

#### 4. Enhanced LLM System Prompt

```python
def build_dynamic_system_prompt(self, registry: LibraryRegistry) -> str:
    """Build system prompt with dynamically available libraries."""
    
    base_prompt = """..."""
    
    # Add available libraries dynamically
    available_libs = []
    for lib_name, version in registry.installed_libraries.items():
        metadata = registry.library_metadata.get(lib_name, {})
        description = metadata.get('description', '')
        common_alias = metadata.get('common_alias', lib_name)
        
        available_libs.append(f"- {lib_name} as {common_alias} (v{version}) - {description}")
    
    dynamic_section = f"""
DYNAMICALLY AVAILABLE LIBRARIES:
{chr(10).join(available_libs)}

LIBRARY INSTALLATION:
If you need a library that's not available, mention it in a comment:
# pip install library_name
The system will suggest installation to the user.
"""
    
    return base_prompt + dynamic_section
```

### Implementation Phases

#### Phase 1: Library Discovery (Low Risk)
- Implement LibraryRegistry to scan environment
- Update system prompts with discovered libraries
- No changes to execution - just better awareness

#### Phase 2: Dynamic Import Handling (Medium Risk)
- Replace manual import preprocessing with smart handler
- Implement security whitelist
- Add import suggestion system

#### Phase 3: User-Driven Installation (High Risk)
- Allow users to install libraries through UI
- Implement sandboxed pip install
- Add library approval workflow

#### Phase 4: Advanced Features (Future)
- Library recommendation based on prompts
- Automatic dependency resolution
- Version conflict detection

### Security Considerations

1. **Whitelist Approach**: Only allow approved libraries
2. **Sandboxed Installation**: Isolate pip install operations
3. **Code Review**: Flag unusual imports for review
4. **Resource Limits**: Prevent resource exhaustion attacks

### Benefits

1. **User Flexibility**: Domain experts can use specialized libraries
2. **Reduced Maintenance**: No manual library configuration
3. **Better LLM Awareness**: System knows what's actually available
4. **Scalability**: Supports diverse use cases without code changes

### Risks

1. **Security**: Arbitrary code execution through imports
2. **Stability**: Untested libraries may cause crashes
3. **Complexity**: More moving parts to maintain
4. **Performance**: Dynamic discovery overhead

## Recommendation

**Start with Phase 1** - implement library discovery and dynamic system prompts. This provides immediate value with minimal risk.

The current static approach works well for the core use cases, but dynamic loading would enable Digital Article to become a true platform for domain-specific analysis.
