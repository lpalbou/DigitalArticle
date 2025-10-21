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
    
    def generate_code_from_prompt(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Convert a natural language prompt to Python code.

        Args:
            prompt: Natural language description of the desired analysis
            context: Additional context information (variables, data info, etc.)

        Returns:
            Generated Python code as a string

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

            # Track actual token usage from AbstractCore response.usage
            if context and 'notebook_id' in context and 'cell_id' in context:
                logger.info(f"📝 Context has notebook_id={context['notebook_id']}, cell_id={context['cell_id']}")

                usage_data = getattr(response, 'usage', None)
                logger.info(f"📊 About to track generation with usage_data: {usage_data}")

                self.token_tracker.track_generation(
                    notebook_id=context['notebook_id'],
                    cell_id=context['cell_id'],
                    usage_data=usage_data  # AbstractCore provides: {prompt_tokens, completion_tokens, total_tokens}
                )

                if usage_data:
                    logger.info(
                        f"✅ Token usage - prompt: {usage_data.get('prompt_tokens') if isinstance(usage_data, dict) else getattr(usage_data, 'prompt_tokens', 'N/A')}, "
                        f"completion: {usage_data.get('completion_tokens') if isinstance(usage_data, dict) else getattr(usage_data, 'completion_tokens', 'N/A')}, "
                        f"total: {usage_data.get('total_tokens') if isinstance(usage_data, dict) else getattr(usage_data, 'total_tokens', 'N/A')}"
                    )
                else:
                    logger.warning(f"⚠️ NO USAGE DATA in response!")

            # Extract code from the response
            code = self._extract_code_from_response(response.content)

            logger.info(f"🚨 EXTRACTED CODE: {code}")
            logger.info(f"Generated code for prompt: {prompt[:50]}...")
            return code
            
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
- pandas as pd
- numpy as np
- matplotlib.pyplot as plt
- plotly.express as px
- plotly.graph_objects as go
- seaborn as sns
- scipy.stats as stats
- sklearn (all modules)
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

        user_prompt += f"CURRENT REQUEST:\n{prompt}\n\n"
        user_prompt += "Generate the Python code (no explanations, just code):"

        return user_prompt
    
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
            formatted = analyzer.format_for_llm(context)

            logger.info(f"Error enhanced with {len(context.suggestions)} suggestions")

            return formatted

        except Exception as e:
            logger.warning(f"Error analysis failed, using original error: {e}")
            # Fallback to original error message if analysis fails
            return f"{error_type}: {error_message}\n\nTraceback:\n{traceback}"
    
    def generate_scientific_explanation(self, prompt: str, code: str, execution_result: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> str:
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
            print(f"🔬 LLM SERVICE: Final explanation: {len(explanation)} characters")
            logger.info(f"Generated scientific explanation: {len(explanation)} characters")
            return explanation
            
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