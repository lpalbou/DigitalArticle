"""
LLM Service for converting natural language prompts to Python code.

This service uses AbstractCore to interface with LLM providers (specifically LMStudio)
and generates appropriate Python code for data analysis tasks.

Token Tracking:
    Uses ONLY AbstractCore's response.usage for actual token counts.
    NO custom estimation - only real data from LLM provider.
"""

import logging
from typing import Optional, Dict, Any
from abstractcore import create_llm, ProviderAPIError, ModelNotFoundError, AuthenticationError
from .token_tracker import TokenTracker

# Create a general LLMError that encompasses all AbstractCore errors
class LLMError(Exception):
    """General LLM error for the digital article application."""
    pass

logger = logging.getLogger(__name__)


class LLMService:
    """Service for LLM-powered prompt to code conversion with token tracking."""

    def __init__(self, provider: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize the LLM service with token tracker.

        If provider/model not specified, will load from project config.

        Args:
            provider: LLM provider name (optional, will load from config if not provided)
            model: Model name (optional, will load from config if not provided)
        """
        # Load from config if not provided
        if provider is None or model is None:
            from ..config import config
            self.provider = provider or config.get_llm_provider()
            self.model = model or config.get_llm_model()
            logger.info(f"Loaded LLM config from file: {self.provider}/{self.model}")
        else:
            self.provider = provider
            self.model = model

        self.llm = None
        self.token_tracker = TokenTracker()  # NEW: Track actual token usage from AbstractCore
        self._initialize_llm()
    
    def _initialize_llm(self):
        """Initialize the LLM client."""
        try:
            self.llm = create_llm(self.provider, model=self.model)
            logger.info(f"✅ Initialized LLM: {self.provider}/{self.model}")
        except (ProviderAPIError, ModelNotFoundError, AuthenticationError) as e:
            logger.error(f"❌ Failed to initialize LLM: {e}")
            self.llm = None  # Keep service alive but mark LLM as unavailable
            # Don't raise - allow service to exist in degraded state
        except Exception as e:
            logger.error(f"❌ Unexpected error initializing LLM: {e}")
            self.llm = None  # Keep service alive but mark LLM as unavailable
    
    def check_provider_health(self) -> Dict[str, Any]:
        """
        Check provider health using AbstractCore 2.4.6's provider.health() method.
        
        Returns:
            Dict with health status information
        """
        if not self.llm:
            return {
                "status": "error",
                "message": "LLM not initialized",
                "healthy": False
            }
        
        try:
            # Use AbstractCore 2.4.6's provider.health() method
            if hasattr(self.llm, 'provider') and hasattr(self.llm.provider, 'health'):
                health_result = self.llm.provider.health()
                logger.info(f"🏥 Provider health check: {health_result}")
                return {
                    "status": "healthy" if health_result.get("healthy", False) else "unhealthy",
                    "message": health_result.get("message", "Unknown status"),
                    "healthy": health_result.get("healthy", False),
                    "details": health_result
                }
            else:
                # Fallback for older AbstractCore versions
                return {
                    "status": "connected",
                    "message": "Provider health check not available",
                    "healthy": True
                }
        except Exception as e:
            logger.error(f"❌ Provider health check failed: {e}")
            return {
                "status": "error",
                "message": f"Health check failed: {str(e)}",
                "healthy": False
            }
    
    def _get_notebook_seed(self, notebook_id: str) -> int:
        """
        Generate a consistent seed for a notebook based on its ID.
        
        Checks for custom seeds first, then falls back to notebook ID hash.
        
        Args:
            notebook_id: Notebook identifier
            
        Returns:
            Consistent integer seed for the notebook
        """
        # Check for custom seed first
        if hasattr(self, '_custom_seeds') and notebook_id in self._custom_seeds:
            return self._custom_seeds[notebook_id]
        
        # Fall back to notebook ID hash
        import hashlib
        seed = int(hashlib.md5(notebook_id.encode()).hexdigest()[:8], 16) % (2**31)
        return seed
    
    def generate_code_from_prompt(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> tuple[str, Optional[float]]:
        """
        Convert a natural language prompt to Python code.

        Args:
            prompt: Natural language description of the desired analysis
            context: Additional context information (variables, data info, etc.)

        Returns:
            Tuple of (generated Python code as string, generation time in milliseconds)

        Raises:
            LLMError: If code generation fails
        """
        if not self.llm:
            raise LLMError(f"LLM provider '{self.provider}' is not available. Please check that {self.provider} is running and accessible.")
        
        # Build the system prompt for code generation
        system_prompt = self._build_system_prompt(context)
        
        # Construct the user prompt
        user_prompt = self._build_user_prompt(prompt, context)
        
        try:
            logger.info(f"🚨 CALLING LLM with prompt: {prompt[:100]}...")
            logger.info(f"🚨 System prompt length: {len(system_prompt)}")
            
            # Debug: Log available variables
            if context and 'available_variables' in context:
                logger.info(f"🚨 Available variables: {context['available_variables']}")
            else:
                logger.info("🚨 No available variables in context")
            
            # Get notebook-specific seed for LLM generation reproducibility
            # Note: This seed affects LLM code generation consistency, while execution 
            # environment seeds (in ExecutionService) ensure consistent random data results
            notebook_seed = None
            if context and 'notebook_id' in context:
                notebook_seed = self._get_notebook_seed(context['notebook_id'])
            
            # Prepare generation parameters
            generation_params = {
                "max_tokens": 2000,
                "temperature": 0.1  # Low temperature for consistent code generation
            }
            
            # Add seed parameter if provider supports it (all except Anthropic in AbstractCore 2.4.6)
            if notebook_seed is not None and self.provider != 'anthropic':
                generation_params["seed"] = notebook_seed
                logger.info(f"🎲 Using LLM generation seed {notebook_seed} for {self.provider}")
            
            response = self.llm.generate(
                user_prompt,
                system_prompt=system_prompt,
                **generation_params
            )

            logger.info(f"🚨 LLM RAW RESPONSE: {response.content[:200]}...")

            # Debug: Check what's in the response object
            logger.info(f"🔍 Response attributes: {dir(response)}")
            logger.info(f"🔍 response.usage type: {type(response.usage) if hasattr(response, 'usage') else 'NO USAGE ATTR'}")
            logger.info(f"🔍 response.usage value: {response.usage if hasattr(response, 'usage') else 'NO USAGE'}")

            # Track actual token usage and generation time from AbstractCore response
            if context and 'notebook_id' in context and 'cell_id' in context:
                logger.info(f"📝 Context has notebook_id={context['notebook_id']}, cell_id={context['cell_id']}")

                usage_data = getattr(response, 'usage', None)
                generation_time = getattr(response, 'gen_time', None)  # AbstractCore 2.4.8+ provides gen_time in ms
                
                logger.info(f"📊 About to track generation with usage_data: {usage_data}")
                logger.info(f"⏱️ Generation time: {generation_time}ms" if generation_time else "⏱️ No generation time available")

                self.token_tracker.track_generation(
                    notebook_id=context['notebook_id'],
                    cell_id=context['cell_id'],
                    usage_data=usage_data,  # AbstractCore provides: {input_tokens, output_tokens, total_tokens} or legacy names
                    generation_time_ms=generation_time
                )

                if usage_data:
                    # Support both new and legacy field names
                    input_tokens = usage_data.get('input_tokens') or usage_data.get('prompt_tokens', 'N/A')
                    output_tokens = usage_data.get('output_tokens') or usage_data.get('completion_tokens', 'N/A')
                    total_tokens = usage_data.get('total_tokens', 'N/A')
                    
                    logger.info(
                        f"✅ Token usage - input: {input_tokens}, "
                        f"output: {output_tokens}, total: {total_tokens}"
                        f"{f', time: {generation_time}ms' if generation_time else ''}"
                    )
                else:
                    logger.warning(f"⚠️ NO USAGE DATA in response!")

            # Extract code from the response
            code = self._extract_code_from_response(response.content)
            generation_time = getattr(response, 'gen_time', None)

            logger.info(f"🚨 EXTRACTED CODE: {code}")
            logger.info(f"Generated code for prompt: {prompt[:50]}...")
            return code, generation_time
            
        except (ProviderAPIError, ModelNotFoundError, AuthenticationError) as e:
            logger.error(f"LLM API error during code generation: {e}")
            raise LLMError(f"LLM API error: {e}")
        except Exception as e:
            logger.error(f"Code generation failed: {e}")
            raise LLMError(f"Failed to generate code: {e}")
    
    def _build_system_prompt(self, context: Optional[Dict[str, Any]] = None) -> str:
        """Build the system prompt for code generation."""
        
        base_prompt = """You are a data analysis assistant that converts natural language requests into Python code.

CRITICAL DATA PATH INFORMATION:
- ALL data files are located in the 'data/' directory (relative to working directory)
- ALWAYS use paths like: 'data/filename.csv' 
- NEVER use bare filenames like 'filename.csv'
- The working directory contains a 'data/' subdirectory with all datasets
- Files are managed by the data manager and guaranteed to be accessible

RULES:
1. Generate ONLY executable Python code - no explanations or markdown
2. Always import required libraries at the start
3. Use common data science libraries: pandas, numpy, matplotlib, plotly, seaborn, scipy, sklearn
4. For data files, ALWAYS use 'data/filename.csv' format
5. For plots, always use matplotlib.pyplot or plotly and ensure plots are displayed
6. For tables, use pandas DataFrame.to_html() or print formatted output
7. Handle errors gracefully with try/except blocks
8. Keep code concise but complete
9. Always end plotting code with plt.show() or fig.show()
10. Use descriptive variable names
11. RANDOM DATA: Generate random data without setting seeds - the system handles reproducibility automatically

AVAILABLE LIBRARIES:
- pandas as pd (data manipulation)
- numpy as np (numerical computing)
- matplotlib.pyplot as plt (plotting)
- plotly.express as px (interactive plots)
- plotly.graph_objects as go (advanced plots)
- seaborn as sns (statistical visualization)
- scipy.stats as stats (statistical functions)
- sklearn (scikit-learn - machine learning)
- scanpy as sc (single-cell analysis)
- umap (UMAP dimensionality reduction)
- PIL (pillow - image manipulation)
- requests (HTTP requests)
- openpyxl (Excel files)
- datetime, timedelta, date (from datetime module)

TYPE SAFETY HELPERS (automatically available):
- safe_timedelta(days=value) - Creates timedelta with automatic numpy type conversion
- to_python_type(value) - Converts numpy/pandas types to Python native types
- safe_int(value) - Converts to int, handling numpy types
- safe_float(value) - Converts to float, handling numpy types

IMPORTANT - NumPy Type Conversion:
When using numpy or pandas operations that return numeric types (np.random.randint, series.sum(), etc.),
these return numpy types (numpy.int64, numpy.float64) which are NOT compatible with Python built-ins like timedelta, range, etc.

SOLUTION:
- Use safe_timedelta() instead of timedelta() when value comes from numpy/pandas
- Use int()/float() conversion: timedelta(days=int(np_value))
- Use pandas vectorized methods: pd.to_timedelta() instead of loops with timedelta()

EXAMPLES:
```python
# WRONG - Will fail with numpy types
days = np.random.randint(1, 30)
td = timedelta(days=days)  # TypeError!

# RIGHT - Convert numpy type
days = int(np.random.randint(1, 30))
td = timedelta(days=days)

# BETTER - Use helper
days = np.random.randint(1, 30)
td = safe_timedelta(days=days)  # Automatically converts

# BEST - Use pandas vectorized operations
df['timedelta_col'] = pd.to_timedelta(df['days'], unit='D')
```

DATA FILE EXAMPLES:
```python
# CORRECT - Use data/ directory
df = pd.read_csv('data/gene_expression.csv')
patients = pd.read_csv('data/patient_data.csv')

# WRONG - Don't use bare filenames
df = pd.read_csv('gene_expression.csv')  # This will fail!
```

ADDITIONAL LIBRARY EXAMPLES:
```python
# Image handling with PIL
from PIL import Image
img = Image.open('data/image.jpg')
img_resized = img.resize((100, 100))

# Excel file handling
df = pd.read_excel('data/file.xlsx', sheet_name='Sheet1')
# OR for advanced Excel operations:
import openpyxl
wb = openpyxl.load_workbook('data/file.xlsx')

# Web requests
import requests
response = requests.get('https://api.example.com/data')
data = response.json()

# UMAP dimensionality reduction
from umap import UMAP
reducer = UMAP(n_neighbors=15, min_dist=0.1, n_components=2)
embedding = reducer.fit_transform(data)

# Scanpy single-cell analysis
import scanpy as sc
sc.pp.filter_cells(adata, min_genes=200)
sc.pp.filter_genes(adata, min_cells=3)
```

COMPLETE EXAMPLE:
```python
import pandas as pd
import matplotlib.pyplot as plt

# Load data from data directory
data = pd.read_csv('data/gene_expression.csv')
print("Shape:", data.shape)
print("Columns:", data.columns.tolist())

# Create visualization
plt.figure(figsize=(10, 6))
plt.hist(data['Sample_1'])
plt.title('Gene Expression Distribution')
plt.show()
```"""

        # Add context-specific information
        if context:
            if 'available_variables' in context:
                base_prompt += f"\n\nAVAILABLE VARIABLES:\n{context['available_variables']}"
            if 'data_info' in context:
                base_prompt += f"\n\nDATA INFO:\n{context['data_info']}"
        
        return base_prompt
    
    def _build_user_prompt(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Build the user prompt for code generation with context awareness."""

        user_prompt = ""

        # FIRST: Show available variables prominently for maximum visibility
        if context and 'available_variables' in context:
            variables = context['available_variables']
            if variables:
                user_prompt += "=" * 70 + "\n"
                user_prompt += "AVAILABLE VARIABLES IN CURRENT EXECUTION CONTEXT\n"
                user_prompt += "=" * 70 + "\n\n"

                # Separate DataFrames from other variables for emphasis
                dataframes = {}
                other_vars = {}

                for name, info in variables.items():
                    var_type = info.get('type', 'unknown') if isinstance(info, dict) else str(info)
                    if 'DataFrame' in var_type:
                        dataframes[name] = info
                    else:
                        other_vars[name] = info

                # Show DataFrames FIRST (most important for reuse)
                if dataframes:
                    user_prompt += "DATAFRAMES (REUSE THESE - DO NOT RECREATE):\n"
                    user_prompt += "-" * 70 + "\n"
                    for name, info in dataframes.items():
                        if isinstance(info, dict):
                            shape = info.get('shape', 'unknown')
                            columns = info.get('columns', [])
                            user_prompt += f"  Variable: '{name}'\n"
                            user_prompt += f"  Type: DataFrame\n"
                            user_prompt += f"  Shape: {shape}\n"
                            if columns:
                                cols_preview = ', '.join(str(c) for c in columns[:8])
                                if len(columns) > 8:
                                    cols_preview += f", ... ({len(columns)} total columns)"
                                user_prompt += f"  Columns: {cols_preview}\n"
                            user_prompt += "\n"
                        else:
                            user_prompt += f"  '{name}': {info}\n\n"

                # Show other variables
                if other_vars:
                    user_prompt += "OTHER VARIABLES:\n"
                    user_prompt += "-" * 70 + "\n"
                    for name, info in other_vars.items():
                        if isinstance(info, dict):
                            var_type = info.get('type', 'unknown')
                            extra = info.get('shape') or info.get('length') or ''
                            user_prompt += f"  '{name}': {var_type} {extra}\n"
                        else:
                            user_prompt += f"  '{name}': {info}\n"
                    user_prompt += "\n"

                user_prompt += "=" * 70 + "\n\n"

        # SECOND: Add previous cells context for awareness
        if context and 'previous_cells' in context:
            previous_cells = context['previous_cells']
            if previous_cells:
                user_prompt += "PREVIOUS CELLS IN THIS NOTEBOOK:\n"
                user_prompt += "=" * 60 + "\n"
                for idx, cell in enumerate(previous_cells, 1):
                    user_prompt += f"\nCell {idx} ({'✓' if cell.get('success') else '✗'}):\n"
                    if cell.get('prompt'):
                        user_prompt += f"  Prompt: {cell['prompt'][:200]}...\n" if len(cell.get('prompt', '')) > 200 else f"  Prompt: {cell['prompt']}\n"
                    user_prompt += f"  Code: {cell['code']}\n"
                    if cell.get('has_dataframes'):
                        user_prompt += f"  ✓ This cell created/modified DataFrames\n"
                user_prompt += "=" * 60 + "\n\n"

                user_prompt += "CRITICAL INSTRUCTIONS FOR CODE REUSE:\n"
                user_prompt += "=" * 60 + "\n"
                user_prompt += "1. CHECK THE 'AVAILABLE VARIABLES' SECTION ABOVE FIRST!\n"
                user_prompt += "2. If a DataFrame exists (e.g., 'sdtm_dataset'), REUSE IT by its exact name\n"
                user_prompt += "3. DO NOT create new DataFrames from the same source with different names\n"
                user_prompt += "4. DO NOT use pd.DataFrame(data) if a DataFrame already exists\n"
                user_prompt += "5. DO NOT use pd.read_csv() if the data is already loaded in memory\n"
                user_prompt += "6. When asked to 'display', 'show', or 'print' variables, ALWAYS use print() function\n"
                user_prompt += "7. For random data generation, do not set seeds - the system manages reproducibility\n"
                user_prompt += "\n"
                user_prompt += "BAD Example (DO NOT DO THIS):\n"
                user_prompt += "  df = pd.DataFrame(data)  # ❌ WRONG if 'sdtm_dataset' already exists\n"
                user_prompt += "\n"
                user_prompt += "GOOD Example (DO THIS):\n"
                user_prompt += "  # Use existing 'sdtm_dataset' directly\n"
                user_prompt += "  fig, axes = plt.subplots(2, 3)\n"
                user_prompt += "  sns.countplot(data=sdtm_dataset, x='ARM', ax=axes[0,0])\n"
                user_prompt += "\n"
                user_prompt += "DISPLAY VARIABLES Example:\n"
                user_prompt += "  # If asked to 'display them' and x_values, y_values exist:\n"
                user_prompt += "  print('x_values:', x_values)\n"
                user_prompt += "  print('y_values:', y_values)\n"
                user_prompt += "\n"
                user_prompt += "RANDOM DATA Example:\n"
                user_prompt += "  # Generate random data (system handles reproducibility):\n"
                user_prompt += "  x = np.random.randn(20)  # ✅ GOOD - clean code\n"
                user_prompt += "  # NOT: np.random.seed(42); x = np.random.randn(20)  # ❌ BAD - system handles seeds\n"
                user_prompt += "=" * 60 + "\n\n"

        # THIRD: Add available files information
        if context and 'files_in_context' in context:
            files = context['files_in_context']
            if files:
                user_prompt += "AVAILABLE DATA FILES:\n"
                user_prompt += "=" * 60 + "\n"
                for file_info in files:
                    user_prompt += f"📄 {file_info['name']}\n"
                    user_prompt += f"   Path: {file_info['path']}\n"
                    user_prompt += f"   Type: {file_info['type']}\n"
                    user_prompt += f"   Size: {self._format_file_size(file_info['size'])}\n"
                    
                    # Add preview information for structured data
                    if 'preview' in file_info and file_info['preview']:
                        preview = file_info['preview']
                        if 'error' not in preview:
                            if file_info['type'] == 'csv':
                                user_prompt += f"   Shape: {preview['shape'][0]} rows × {preview['shape'][1]} columns\n"
                                columns = preview['columns'][:5]  # Show first 5 columns
                                cols_str = ', '.join(columns)
                                if len(preview['columns']) > 5:
                                    cols_str += f", ... ({len(preview['columns'])} total)"
                                user_prompt += f"   Columns: {cols_str}\n"
                            elif file_info['type'] == 'json':
                                if preview.get('type') == 'array':
                                    user_prompt += f"   JSON array with {preview['length']} items\n"
                                    if 'schema' in preview and preview['schema']:
                                        user_prompt += f"   Item structure: {self._format_json_schema(preview['schema'])}\n"
                                elif preview.get('type') == 'object':
                                    user_prompt += f"   JSON object with {preview.get('total_keys', len(preview.get('keys', [])))} properties\n"
                                    if preview.get('keys'):
                                        keys_str = ', '.join(preview['keys'][:5])
                                        if len(preview['keys']) > 5:
                                            keys_str += f", ... ({len(preview['keys'])} total)"
                                        user_prompt += f"   Keys: {keys_str}\n"
                            elif file_info['type'] in ['xlsx', 'xls']:
                                if 'sheets' in preview:
                                    sheets_str = ', '.join(preview['sheets'][:3])
                                    if len(preview['sheets']) > 3:
                                        sheets_str += f", ... ({len(preview['sheets'])} total)"
                                    user_prompt += f"   Excel sheets: {sheets_str}\n"
                            elif file_info['type'] == 'txt':
                                if 'first_lines' in preview and preview['first_lines']:
                                    user_prompt += f"   Text preview: {preview['first_lines'][0][:50]}...\n"
                    user_prompt += "\n"
                
                user_prompt += "IMPORTANT: Use 'data/filename.csv' format to access these files!\n"
                user_prompt += "=" * 60 + "\n\n"

        user_prompt += f"CURRENT REQUEST:\n{prompt}\n\n"
        user_prompt += "Generate the Python code (no explanations, just code):"

        return user_prompt
    
    def _format_file_size(self, bytes_size: int) -> str:
        """Format file size in human-readable format."""
        if bytes_size == 0:
            return "0 B"
        
        units = ['B', 'KB', 'MB', 'GB']
        size = float(bytes_size)
        unit_index = 0
        
        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1
        
        if unit_index == 0:
            return f"{int(size)} {units[unit_index]}"
        else:
            return f"{size:.1f} {units[unit_index]}"
    
    def _format_json_schema(self, schema: Dict[str, Any]) -> str:
        """Format JSON schema information for LLM prompt."""
        if schema.get('type') == 'object' and 'properties' in schema:
            props = []
            for key, value in list(schema['properties'].items())[:3]:  # Show first 3 properties
                prop_type = value.get('type', 'unknown')
                props.append(f"{key}: {prop_type}")
            result = "{" + ", ".join(props)
            if len(schema['properties']) > 3:
                result += f", ... ({len(schema['properties'])} total)"
            result += "}"
            return result
        elif schema.get('type') == 'array':
            item_type = schema.get('items', {}).get('type', 'unknown')
            return f"[{item_type}]"
        else:
            return schema.get('type', 'unknown')
    
    def _extract_code_from_response(self, response: str) -> str:
        """
        Extract Python code from LLM response.
        
        Handles various response formats including code blocks and plain text.
        """
        # Remove common prefixes/suffixes
        response = response.strip()
        
        # Look for code blocks
        if "```python" in response:
            # Extract from ```python block
            start = response.find("```python") + 9
            end = response.find("```", start)
            if end != -1:
                code = response[start:end].strip()
            else:
                code = response[start:].strip()
        elif "```" in response:
            # Extract from generic ``` block
            start = response.find("```") + 3
            end = response.find("```", start)
            if end != -1:
                code = response[start:end].strip()
            else:
                code = response[start:].strip()
        else:
            # Assume entire response is code
            code = response
        
        # Clean up the code
        code = self._clean_code(code)
        
        return code
    
    def _clean_code(self, code: str) -> str:
        """Clean and validate the generated code."""
        lines = code.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # Skip empty lines at start and end
            if line.strip() or cleaned_lines:
                # Remove common explanation prefixes
                if line.strip().startswith(('Here', 'This', 'The code', '```')):
                    continue
                cleaned_lines.append(line)
        
        # Remove trailing empty lines
        while cleaned_lines and not cleaned_lines[-1].strip():
            cleaned_lines.pop()
        
        return '\n'.join(cleaned_lines)
    
    def explain_code(self, code: str) -> str:
        """
        Generate a natural language explanation of Python code.
        
        Args:
            code: Python code to explain
            
        Returns:
            Natural language explanation
        """
        if not self.llm:
            raise LLMError("LLM not initialized")
        
        prompt = f"""Explain this Python code in simple terms for non-technical users:

```python
{code}
```

Provide a clear, concise explanation focusing on:
1. What the code does (purpose)
2. What data it works with
3. What results it produces
4. Any visualizations created

Keep the explanation accessible to biologists, clinicians, and other domain experts."""

        try:
            response = self.llm.generate(
                prompt,
                max_tokens=500,
                temperature=0.3
            )
            return response.content.strip()
            
        except (ProviderAPIError, ModelNotFoundError, AuthenticationError) as e:
            logger.error(f"LLM API error during code explanation: {e}")
            raise LLMError(f"LLM API error: {e}")
        except Exception as e:
            logger.error(f"Code explanation failed: {e}")
            raise LLMError(f"Failed to explain code: {e}")
    
    def suggest_improvements(
        self,
        prompt: str,
        code: str,
        error_message: Optional[str] = None,
        error_type: Optional[str] = None,
        traceback: Optional[str] = None
    ) -> str:
        """
        Suggest improvements or fixes for generated code.

        Args:
            prompt: Original natural language prompt
            code: Generated code that needs improvement
            error_message: Error message if code failed to execute
            error_type: Exception type (e.g., "ValueError")
            traceback: Full Python traceback

        Returns:
            Improved Python code
        """
        if not self.llm:
            raise LLMError("LLM not initialized")

        improvement_prompt = f"""The following code was generated for this request: "{prompt}"

```python
{code}
```"""

        if error_message:
            # Use error analyzer to provide enhanced context
            enhanced_error = self._enhance_error_context(
                error_message,
                error_type or "Unknown",
                traceback or "",
                code
            )

            improvement_prompt += f"\n\nBut it failed with this error:\n\n{enhanced_error}\n\nFix the code to resolve this error."

            logger.info("Enhanced error context provided to LLM for auto-retry")
        else:
            improvement_prompt += "\n\nImprove this code to be more robust, efficient, and user-friendly."

        improvement_prompt += "\n\nGenerate the improved Python code:"

        try:
            response = self.llm.generate(
                improvement_prompt,
                system_prompt=self._build_system_prompt(),
                max_tokens=2000,
                temperature=0.1
            )

            return self._extract_code_from_response(response.content)

        except (ProviderAPIError, ModelNotFoundError, AuthenticationError) as e:
            logger.error(f"LLM API error during code improvement: {e}")
            raise LLMError(f"LLM API error: {e}")
        except Exception as e:
            logger.error(f"Code improvement failed: {e}")
            raise LLMError(f"Failed to improve code: {e}")

    def _enhance_error_context(
        self,
        error_message: str,
        error_type: str,
        traceback: str,
        code: str
    ) -> str:
        """
        Enhance error message with domain-specific guidance.

        Uses ErrorAnalyzer to provide targeted, helpful context that helps
        the LLM fix errors more effectively during auto-retry cycles.

        Args:
            error_message: Original error message
            error_type: Exception type
            traceback: Full Python traceback
            code: Code that caused the error

        Returns:
            Enhanced error message with guidance
        """
        try:
            from .error_analyzer import ErrorAnalyzer

            analyzer = ErrorAnalyzer()
            context = analyzer.analyze_error(error_message, error_type, traceback, code)
            formatted = analyzer.format_for_llm(context, traceback)

            logger.info(f"Error enhanced with {len(context.suggestions)} suggestions")

            return formatted

        except Exception as e:
            logger.warning(f"Error analysis failed, using original error: {e}")
            # Fallback to original error message if analysis fails
            return f"{error_type}: {error_message}\n\nTraceback:\n{traceback}"
    
    def generate_scientific_explanation(self, prompt: str, code: str, execution_result: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> tuple[str, Optional[float]]:
        """
        Generate a scientific article-style explanation of what was done and why.
        
        Args:
            prompt: The original natural language prompt
            code: The generated Python code
            execution_result: The result of code execution (stdout, plots, etc.)
            
        Returns:
            Scientific article-style explanation text
            
        Raises:
            LLMError: If explanation generation fails
        """
        if not self.llm:
            raise LLMError("LLM not initialized")
        
        # Build the system prompt for scientific writing
        system_prompt = """You are a scientific writing assistant that creates high-impact scientific article sections.

TASK: Write a clear, professional scientific explanation of a data analysis step.

STYLE REQUIREMENTS:
- Write in the style of a high-impact scientific journal (Nature, Science, Cell)
- Use present tense for describing what is being done
- Use past tense for describing results obtained
- Be concise but comprehensive
- Use technical language appropriately
- Focus on methodology and findings
- Avoid first person (I, we) - use passive voice or third person

STRUCTURE:
1. Brief context of what analysis is being performed and why
2. Methodology: Describe the approach taken
3. Results: Summarize key findings from the execution

EXAMPLE OUTPUT:
"To assess the distribution of gene expression levels across samples, a comprehensive statistical analysis was performed. The dataset containing 20 genes across 6 experimental conditions was loaded and examined for basic descriptive statistics. The analysis revealed a mean expression level of 15.3 ± 4.2 across all genes, with significant variability observed between experimental conditions (CV = 28%). These findings suggest heterogeneous expression patterns that warrant further investigation through differential expression analysis."

GUIDELINES:
- Keep paragraphs focused and coherent
- Use quantitative results when available
- Mention statistical measures and sample sizes
- Connect findings to broader scientific context
- Maintain objective, analytical tone
- Length: 2-4 sentences, maximum 150 words"""

        # Build the user prompt with all context
        user_prompt = f"""Generate a scientific article-style explanation for this analysis:

ORIGINAL REQUEST: {prompt}

CODE EXECUTED:
```python
{code}
```

EXECUTION RESULTS:
- Status: {'Success' if execution_result.get('status') == 'success' else 'Error'}
- Output: {execution_result.get('stdout', 'No output')}
- Plots generated: {'Yes' if execution_result.get('plots') else 'No'}
- Tables generated: {'Yes' if execution_result.get('tables') else 'No'}

Write a scientific explanation of what was done and the results obtained:"""

        try:
            print("🔬 LLM SERVICE: Starting scientific explanation generation...")
            logger.info("Generating scientific explanation...")
            
            print("🔬 LLM SERVICE: About to call self.llm.generate...")
            import time
            start_time = time.time()
            # Get notebook-specific seed for LLM generation reproducibility
            notebook_seed = None
            if context and 'notebook_id' in context:
                notebook_seed = self._get_notebook_seed(context['notebook_id'])
            
            # Prepare generation parameters
            generation_params = {
                "max_tokens": 300,  # Shorter for concise explanations
                "temperature": 0.2  # Slightly higher for more natural writing
            }
            
            # Add seed parameter if provider supports it (all except Anthropic in AbstractCore 2.4.6)
            if notebook_seed is not None and self.provider != 'anthropic':
                generation_params["seed"] = notebook_seed
                logger.info(f"🎲 Using LLM generation seed {notebook_seed} for scientific explanation with {self.provider}")
            
            response = self.llm.generate(
                user_prompt,
                system_prompt=system_prompt,
                **generation_params
            )
            elapsed_time = time.time() - start_time
            print(f"🔬 LLM SERVICE: LLM call took {elapsed_time:.1f} seconds")
            print(f"🔬 LLM SERVICE: Got response: {type(response)}")
            print(f"🔬 LLM SERVICE: Response content: {response.content[:100]}...")
            
            explanation = response.content.strip()
            generation_time = getattr(response, 'gen_time', None)
            print(f"🔬 LLM SERVICE: Final explanation: {len(explanation)} characters")
            logger.info(f"Generated scientific explanation: {len(explanation)} characters")
            return explanation, generation_time
            
        except (ProviderAPIError, ModelNotFoundError, AuthenticationError) as e:
            print(f"🔬 LLM SERVICE: API error: {e}")
            logger.error(f"LLM API error during explanation generation: {e}")
            raise LLMError(f"LLM API error: {e}")
        except Exception as e:
            print(f"🔬 LLM SERVICE: Exception: {e}")
            import traceback
            print(f"🔬 LLM SERVICE: Traceback: {traceback.format_exc()}")
            logger.error(f"Scientific explanation generation failed: {e}")
            raise LLMError(f"Failed to generate scientific explanation: {e}")

    def generate_abstract(self, notebook_data: Dict[str, Any]) -> str:
        """
        Generate a scientific abstract for the entire digital article.
        
        Args:
            notebook_data: Complete notebook data including all cells with prompts, code, results, and methodologies
            
        Returns:
            Generated abstract as a string
        """
        try:
            # Get notebook seed for consistent generation
            notebook_id = notebook_data.get('id', 'unknown')
            seed = self._get_notebook_seed(notebook_id)
            
            # Build comprehensive context from all cells
            cells_summary = []
            for i, cell in enumerate(notebook_data.get('cells', []), 1):
                cell_summary = f"Cell {i}:"
                
                if cell.get('prompt'):
                    cell_summary += f"\n  Objective: {cell['prompt']}"
                
                if cell.get('code'):
                    cell_summary += f"\n  Implementation: {cell['code'][:200]}{'...' if len(cell['code']) > 200 else ''}"
                
                if cell.get('last_result') and cell['last_result'].get('output'):
                    output = cell['last_result']['output']
                    cell_summary += f"\n  Results: {output[:300]}{'...' if len(output) > 300 else ''}"
                
                if cell.get('scientific_explanation'):
                    explanation = cell['scientific_explanation']
                    cell_summary += f"\n  Analysis: {explanation[:400]}{'...' if len(explanation) > 400 else ''}"
                
                cells_summary.append(cell_summary)
            
            cells_content = "\n\n".join(cells_summary)
            
            # Create system prompt for abstract generation
            system_prompt = """You are a scientific writing expert specializing in creating high-quality abstracts for data analysis articles.

Your task is to generate a concise, professional abstract that follows scientific writing standards.

CRITICAL REQUIREMENTS:
1. EMPIRICAL GROUNDING: Base ALL claims on the actual data, code, and results provided. Never invent or assume information.
2. STRUCTURE: Follow standard scientific abstract format (Background/Objective, Methods, Results, Conclusions)
3. CONCISENESS: Keep it between 150-250 words
4. PRECISION: Use specific numbers, metrics, and findings from the actual results
5. OBJECTIVITY: Present findings objectively without speculation beyond what the data shows
6. TECHNICAL ACCURACY: Ensure all technical details are correct based on the provided code and outputs

ABSTRACT STRUCTURE:
- Background/Objective (1-2 sentences): What problem is being addressed and why
- Methods (2-3 sentences): What approaches/techniques were used (based on actual code)
- Results (2-4 sentences): Key findings with specific numbers/metrics from actual outputs
- Conclusions/Implications (1-2 sentences): What the results mean, with brief perspectives on future directions

STYLE GUIDELINES:
- Use past tense for completed work
- Be specific with numbers and metrics
- Avoid vague terms like "significant" without quantification
- Use active voice where appropriate
- Maintain professional, academic tone
- Do NOT include any headers, titles, or formatting like "**Abstract**" - provide only the abstract text"""

            user_prompt = f"""Generate a scientific abstract for this digital article based on the following comprehensive analysis:

ARTICLE METADATA:
Title: {notebook_data.get('title', 'Untitled Digital Article')}
Description: {notebook_data.get('description', 'A data analysis article')}
Author: {notebook_data.get('author', 'Unknown')}

COMPLETE ANALYSIS CONTENT:
{cells_content}

INSTRUCTIONS:
1. Analyze ALL the provided content (objectives, code implementations, actual results, and scientific explanations)
2. Create an abstract that accurately reflects what was actually done and found
3. Ground every statement in the empirical evidence provided
4. Include specific metrics, numbers, and findings from the actual outputs
5. End with brief perspectives on implications or future directions based on the analysis
6. IMPORTANT: Provide ONLY the abstract text - no headers, no "**Abstract**", no formatting

Generate a professional scientific abstract now:"""

            print(f"🎯 ABSTRACT GENERATION: Generating abstract for notebook {notebook_id}")
            logger.info(f"Generating abstract for notebook {notebook_id}")
            
            response = self.llm.generate(
                user_prompt,
                system_prompt=system_prompt,
                seed=seed  # Use AbstractCore's native SEED parameter
            )
            
            # Track token usage
            if hasattr(response, 'usage') and response.usage:
                # Handle both dict and object formats
                if isinstance(response.usage, dict):
                    usage_data = response.usage
                    prompt_tokens = response.usage.get('prompt_tokens', 0)
                    completion_tokens = response.usage.get('completion_tokens', 0)
                else:
                    usage_data = {
                        'prompt_tokens': response.usage.prompt_tokens,
                        'completion_tokens': response.usage.completion_tokens,
                        'total_tokens': getattr(response.usage, 'total_tokens', response.usage.prompt_tokens + response.usage.completion_tokens)
                    }
                    prompt_tokens = response.usage.prompt_tokens
                    completion_tokens = response.usage.completion_tokens
                
                self.token_tracker.track_generation(
                    notebook_id=notebook_id,
                    cell_id='abstract',  # Use 'abstract' as placeholder cell_id
                    usage_data=usage_data
                )
                print(f"🎯 ABSTRACT GENERATION: Used {prompt_tokens} input + {completion_tokens} output tokens")
            
            abstract = response.content.strip()
            print(f"🎯 ABSTRACT GENERATION: Generated {len(abstract)} character abstract")
            logger.info(f"Abstract generation successful for notebook {notebook_id}")
            
            return abstract
            
        except (ProviderAPIError, ModelNotFoundError, AuthenticationError) as e:
            print(f"🎯 ABSTRACT GENERATION: API error: {e}")
            logger.error(f"LLM API error during abstract generation: {e}")
            raise LLMError(f"LLM API error: {e}")
        except Exception as e:
            print(f"🎯 ABSTRACT GENERATION: Exception: {e}")
            import traceback
            print(f"🎯 ABSTRACT GENERATION: Traceback: {traceback.format_exc()}")
            logger.error(f"Abstract generation failed: {e}")
            raise LLMError(f"Failed to generate abstract: {e}")

    def generate_article_plan(self, notebook_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a comprehensive article plan/outline for the digital article.
        
        Args:
            notebook_data: Complete notebook data including all cells with prompts, code, results, and methodologies
            
        Returns:
            Dictionary with article structure and section plans
        """
        try:
            # Get notebook seed for consistent generation
            notebook_id = notebook_data.get('id', 'unknown')
            seed = self._get_notebook_seed(notebook_id)
            
            # Build comprehensive context from all cells
            cells_summary = []
            for i, cell in enumerate(notebook_data.get('cells', []), 1):
                cell_summary = f"Cell {i}:"
                
                if cell.get('prompt'):
                    cell_summary += f"\n  Research Question/Objective: {cell['prompt']}"
                
                if cell.get('code'):
                    cell_summary += f"\n  Implementation: {cell['code'][:300]}{'...' if len(cell['code']) > 300 else ''}"
                
                if cell.get('last_result') and cell['last_result'].get('output'):
                    output = cell['last_result']['output']
                    cell_summary += f"\n  Results: {output[:400]}{'...' if len(output) > 400 else ''}"
                
                if cell.get('scientific_explanation'):
                    explanation = cell['scientific_explanation']
                    cell_summary += f"\n  Analysis: {explanation[:500]}{'...' if len(explanation) > 500 else ''}"
                
                cells_summary.append(cell_summary)
            
            cells_content = "\n\n".join(cells_summary)
            
            # Create system prompt for article planning
            system_prompt = """You are a scientific writing expert specializing in creating comprehensive article outlines for data analysis research.

Your task is to analyze the provided research work and create a detailed article plan that will guide the writing of a complete scientific article.

CRITICAL REQUIREMENTS:
1. COMPREHENSIVE ANALYSIS: Analyze ALL provided content to understand the complete research story
2. LOGICAL STRUCTURE: Create a coherent narrative flow from research questions to conclusions
3. SECTION PLANNING: Plan each section with specific content focus and key points
4. EMPIRICAL GROUNDING: Ensure each section is supported by actual data and results
5. SCIENTIFIC RIGOR: Follow standard scientific article structure and conventions

ARTICLE STRUCTURE TO PLAN:
1. Introduction - Context, motivation, research questions, objectives
2. Methodology - Approaches, techniques, implementation details
3. Results - Findings, data analysis, key discoveries
4. Discussion - Interpretation, implications, limitations
5. Conclusions - Summary, contributions, future work

OUTPUT FORMAT:
Return a JSON structure with:
{
  "title": "Compelling article title based on the research",
  "sections": {
    "introduction": {
      "focus": "Main focus of this section",
      "key_points": ["Point 1", "Point 2", "Point 3"],
      "empirical_support": "What data/results support this section"
    },
    "methodology": { ... },
    "results": { ... },
    "discussion": { ... },
    "conclusions": { ... }
  },
  "narrative_flow": "Brief description of how the story flows from section to section"
}"""

            user_prompt = f"""Create a comprehensive article plan for this digital article based on the following research work:

ARTICLE METADATA:
Title: {notebook_data.get('title', 'Untitled Digital Article')}
Description: {notebook_data.get('description', 'A data analysis article')}
Author: {notebook_data.get('author', 'Unknown')}
Abstract: {notebook_data.get('abstract', 'No abstract available')}

COMPLETE RESEARCH CONTENT:
{cells_content}

INSTRUCTIONS:
1. Analyze the entire research work to understand the story being told
2. Create a compelling article title that reflects the actual research conducted
3. Plan each section with specific focus, key points, and empirical support
4. Ensure the narrative flows logically from research questions to conclusions
5. Ground every section in the actual data, code, and results provided
6. Make the plan detailed enough to guide comprehensive article writing

Create the article plan now:"""

            print(f"🎯 ARTICLE PLANNING: Generating article plan for notebook {notebook_id}")
            logger.info(f"Generating article plan for notebook {notebook_id}")
            
            response = self.llm.generate(
                user_prompt,
                system_prompt=system_prompt,
                seed=seed
            )
            
            # Track token usage
            if hasattr(response, 'usage') and response.usage:
                # Handle both dict and object formats
                if isinstance(response.usage, dict):
                    usage_data = response.usage
                    prompt_tokens = response.usage.get('prompt_tokens', 0)
                    completion_tokens = response.usage.get('completion_tokens', 0)
                else:
                    usage_data = {
                        'prompt_tokens': response.usage.prompt_tokens,
                        'completion_tokens': response.usage.completion_tokens,
                        'total_tokens': getattr(response.usage, 'total_tokens', response.usage.prompt_tokens + response.usage.completion_tokens)
                    }
                    prompt_tokens = response.usage.prompt_tokens
                    completion_tokens = response.usage.completion_tokens
                
                self.token_tracker.track_generation(
                    notebook_id=notebook_id,
                    cell_id='article_plan',
                    usage_data=usage_data
                )
                print(f"🎯 ARTICLE PLANNING: Used {prompt_tokens} input + {completion_tokens} output tokens")
            
            plan_text = response.content.strip()
            
            # Try to parse as JSON, fallback to text if needed
            try:
                import json
                article_plan = json.loads(plan_text)
            except json.JSONDecodeError:
                # If JSON parsing fails, create a basic structure
                article_plan = {
                    "title": notebook_data.get('title', 'Data Analysis Study'),
                    "sections": {
                        "introduction": {"focus": "Research context and objectives", "key_points": [], "empirical_support": ""},
                        "methodology": {"focus": "Analysis approach", "key_points": [], "empirical_support": ""},
                        "results": {"focus": "Key findings", "key_points": [], "empirical_support": ""},
                        "discussion": {"focus": "Interpretation", "key_points": [], "empirical_support": ""},
                        "conclusions": {"focus": "Summary and implications", "key_points": [], "empirical_support": ""}
                    },
                    "narrative_flow": plan_text
                }
            
            print(f"🎯 ARTICLE PLANNING: Generated plan with {len(article_plan.get('sections', {}))} sections")
            logger.info(f"Article plan generation successful for notebook {notebook_id}")
            
            return article_plan
            
        except (ProviderAPIError, ModelNotFoundError, AuthenticationError) as e:
            print(f"🎯 ARTICLE PLANNING: API error: {e}")
            logger.error(f"LLM API error during article planning: {e}")
            raise LLMError(f"LLM API error: {e}")
        except Exception as e:
            print(f"🎯 ARTICLE PLANNING: Exception: {e}")
            import traceback
            print(f"🎯 ARTICLE PLANNING: Traceback: {traceback.format_exc()}")
            logger.error(f"Article planning failed: {e}")
            raise LLMError(f"Failed to generate article plan: {e}")

    def generate_article_section(self, section_name: str, section_plan: Dict[str, Any], 
                                notebook_data: Dict[str, Any], article_plan: Dict[str, Any]) -> str:
        """
        Generate a specific section of the scientific article.
        
        Args:
            section_name: Name of the section (introduction, methodology, results, discussion, conclusions)
            section_plan: Plan for this specific section
            notebook_data: Complete notebook data
            article_plan: Complete article plan for context
            
        Returns:
            Generated section content as a string
        """
        try:
            # Get notebook seed for consistent generation
            notebook_id = notebook_data.get('id', 'unknown')
            seed = self._get_notebook_seed(notebook_id)
            
            # Build comprehensive context from all cells
            cells_summary = []
            for i, cell in enumerate(notebook_data.get('cells', []), 1):
                cell_summary = f"Cell {i}:"
                
                if cell.get('prompt'):
                    cell_summary += f"\n  Research Question/Objective: {cell['prompt']}"
                
                if cell.get('code'):
                    cell_summary += f"\n  Implementation: {cell['code']}"
                
                if cell.get('last_result') and cell['last_result'].get('output'):
                    output = cell['last_result']['output']
                    cell_summary += f"\n  Results: {output}"
                
                # Check for figures/plots
                if cell.get('last_result') and cell['last_result'].get('plots'):
                    plots = cell['last_result']['plots']
                    if plots:
                        cell_summary += f"\n  Figures: {len(plots)} plot(s) generated"
                        for j, plot in enumerate(plots):
                            figure_num = sum(len(c.get('last_result', {}).get('plots', [])) for c in notebook_data.get('cells', [])[:i-1]) + j + 1
                            cell_summary += f"\n    - Figure {figure_num}: Available for referencing in text"
                
                if cell.get('scientific_explanation'):
                    explanation = cell['scientific_explanation']
                    cell_summary += f"\n  Analysis: {explanation}"
                
                cells_summary.append(cell_summary)
            
            cells_content = "\n\n".join(cells_summary)
            
            # Create section-specific system prompt
            system_prompt = f"""You are a scientific writing expert specializing in writing high-quality {section_name} sections for data analysis research articles.

Your task is to write a comprehensive, engaging, and scientifically rigorous {section_name} section based on the provided research work and article plan.

CRITICAL REQUIREMENTS:
1. EMPIRICAL GROUNDING: Base ALL statements on the actual data, code, and results provided
2. SCIENTIFIC RIGOR: Use appropriate scientific language and methodology
3. NARRATIVE COHERENCE: Write in a flowing, human-readable style that tells a compelling story
4. EVIDENCE-BASED: Reference specific findings, numbers, and results from the research
5. PROFESSIONAL TONE: Maintain academic writing standards while being accessible
6. LOGICAL FLOW: Ensure the section flows logically and connects to the overall article narrative

SECTION-SPECIFIC GUIDELINES:
{self._get_section_guidelines(section_name)}

WRITING STYLE:
- Use past tense for completed work
- Be specific with numbers, metrics, and findings
- Avoid speculation beyond what the data shows
- Use active voice where appropriate
- Write for a scientific audience but keep it engaging
- Include specific references to the empirical evidence (code outputs, data results, etc.)
- CRITICAL: When figures/plots are available, you MUST reference them explicitly in the text
- Use natural integration: "Figure 1 demonstrates...", "As shown in Figure 2...", "The visualization in Figure 3 reveals..."
- NEVER mention a figure exists without referencing it in your text
- Explain what each figure shows and its significance to your analysis

OUTPUT REQUIREMENTS:
- Write ONLY the section content - no headers, no section titles
- Make it substantial and comprehensive (aim for 2-4 paragraphs depending on section)
- Ensure it reads like professional scientific writing
- Ground every claim in the actual research conducted"""

            user_prompt = f"""Write the {section_name} section for this scientific article based on the following information:

ARTICLE PLAN CONTEXT:
Title: {article_plan.get('title', 'Research Study')}
Overall Narrative: {article_plan.get('narrative_flow', 'Data analysis study')}

SECTION PLAN:
Focus: {section_plan.get('focus', 'Section content')}
Key Points: {', '.join(section_plan.get('key_points', []))}
Empirical Support: {section_plan.get('empirical_support', 'Research data')}

ARTICLE METADATA:
Title: {notebook_data.get('title', 'Untitled Digital Article')}
Description: {notebook_data.get('description', 'A data analysis article')}
Author: {notebook_data.get('author', 'Unknown')}
Abstract: {notebook_data.get('abstract', 'No abstract available')}

COMPLETE RESEARCH CONTENT:
{cells_content}

AVAILABLE FIGURES FOR REFERENCING:
{self._get_figure_list(notebook_data)}

INSTRUCTIONS:
1. Write a comprehensive {section_name} section that follows the section plan
2. Ground every statement in the actual research data and results provided
3. MANDATORY: Reference ALL available figures naturally in your text
4. Use specific numbers, findings, and evidence from the cell outputs
5. Write in a flowing, engaging scientific style
6. Ensure the section contributes to the overall article narrative
7. Make it substantial and informative while being concise

Write the {section_name} section now:"""

            print(f"🎯 SECTION WRITING: Generating {section_name} section for notebook {notebook_id}")
            logger.info(f"Generating {section_name} section for notebook {notebook_id}")
            
            response = self.llm.generate(
                user_prompt,
                system_prompt=system_prompt,
                seed=seed
            )
            
            # Track token usage
            if hasattr(response, 'usage') and response.usage:
                # Handle both dict and object formats
                if isinstance(response.usage, dict):
                    usage_data = response.usage
                    prompt_tokens = response.usage.get('prompt_tokens', 0)
                    completion_tokens = response.usage.get('completion_tokens', 0)
                else:
                    usage_data = {
                        'prompt_tokens': response.usage.prompt_tokens,
                        'completion_tokens': response.usage.completion_tokens,
                        'total_tokens': getattr(response.usage, 'total_tokens', response.usage.prompt_tokens + response.usage.completion_tokens)
                    }
                    prompt_tokens = response.usage.prompt_tokens
                    completion_tokens = response.usage.completion_tokens
                
                self.token_tracker.track_generation(
                    notebook_id=notebook_id,
                    cell_id=f'article_{section_name}',
                    usage_data=usage_data
                )
                print(f"🎯 SECTION WRITING: Used {prompt_tokens} input + {completion_tokens} output tokens for {section_name}")
            
            section_content = response.content.strip()
            print(f"🎯 SECTION WRITING: Generated {len(section_content)} character {section_name} section")
            logger.info(f"{section_name} section generation successful for notebook {notebook_id}")
            
            return section_content
            
        except (ProviderAPIError, ModelNotFoundError, AuthenticationError) as e:
            print(f"🎯 SECTION WRITING: API error: {e}")
            logger.error(f"LLM API error during {section_name} section generation: {e}")
            raise LLMError(f"LLM API error: {e}")
        except Exception as e:
            print(f"🎯 SECTION WRITING: Exception: {e}")
            import traceback
            print(f"🎯 SECTION WRITING: Traceback: {traceback.format_exc()}")
            logger.error(f"{section_name} section generation failed: {e}")
            raise LLMError(f"Failed to generate {section_name} section: {e}")
    
    def _get_figure_list(self, notebook_data: Dict[str, Any]) -> str:
        """Generate a list of available figures for LLM reference."""
        figure_list = []
        figure_counter = 1
        
        for i, cell in enumerate(notebook_data.get('cells', []), 1):
            if cell.get('last_result') and cell['last_result'].get('plots'):
                plots = cell['last_result']['plots']
                for plot in plots:
                    figure_list.append(f"Figure {figure_counter}: Generated from Cell {i} - {cell.get('prompt', 'Data visualization')}")
                    figure_counter += 1
        
        if not figure_list:
            return "No figures available in this research."
        
        return "\n".join(figure_list)

    def _get_section_guidelines(self, section_name: str) -> str:
        """Get specific guidelines for each section type."""
        guidelines = {
            'introduction': """
- Provide context and background for the research
- Clearly state the research questions and objectives
- Explain the motivation and importance of the study
- Set up the reader for what follows in the article""",
            
            'methodology': """
- Describe the analytical approaches and techniques used
- Explain the implementation details and tools
- Justify the methodological choices made
- Provide enough detail for reproducibility""",
            
            'results': """
- Present the key findings and discoveries
- Include specific numbers, statistics, and measurements
- Describe patterns, trends, and relationships found in the data
- Use empirical evidence to support all claims""",
            
            'discussion': """
- Interpret the results and their implications
- Discuss the significance of the findings
- Address limitations and potential sources of error
- Connect findings to broader scientific context""",
            
            'conclusions': """
- Summarize the main contributions and findings
- Highlight the key insights and their importance
- Suggest future research directions and applications
- Provide a strong closing that ties everything together"""
        }
        
        return guidelines.get(section_name, "Write a comprehensive and well-structured section.")