"""
LLM Service for converting natural language prompts to Python code.

This service uses AbstractCore to interface with LLM providers (specifically LMStudio)
and generates appropriate Python code for data analysis tasks.

Token Tracking:
    Uses ONLY AbstractCore's response.usage for actual token counts.
    NO custom estimation - only real data from LLM provider.
"""

import logging
import os
from typing import Optional, Dict, Any, Tuple, List
from datetime import datetime
from abstractcore import create_llm, ProviderAPIError, ModelNotFoundError, AuthenticationError
from .token_tracker import TokenTracker
from .execution_insights_extractor import ExecutionInsightsExtractor

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
        """Initialize the LLM client with tracing enabled for observability."""
        try:
            kwargs = {
                "enable_tracing": True,  # Enable full interaction tracing
                "max_traces": 100  # Ring buffer for last 100 interactions
            }

            # Load user settings for base URLs (with env var fallback for Docker)
            base_url = None
            try:
                from .user_settings_service import get_user_settings_service
                settings_service = get_user_settings_service()
                settings = settings_service.get_settings()
                base_urls = settings.llm.base_urls
            except Exception as e:
                logger.warning(f"Could not load user settings, using env vars: {e}")
                base_urls = {}

            if self.provider.lower() == "ollama":
                # Priority: saved settings > env var > default
                base_url = base_urls.get('ollama') or os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
                kwargs["base_url"] = base_url
                logger.info(f"🐳 Using Ollama at: {base_url}")
            elif self.provider.lower() == "lmstudio":
                # Priority: saved settings > env var > default
                base_url = base_urls.get('lmstudio') or os.getenv('LMSTUDIO_BASE_URL', 'http://localhost:1234/v1')
                kwargs["base_url"] = base_url
                logger.info(f"🖥️ Using LMStudio at: {base_url}")
            elif self.provider.lower() == "vllm":
                # Priority: saved settings > env var > default
                base_url = base_urls.get('vllm') or os.getenv('VLLM_BASE_URL', 'http://localhost:8000/v1')
                kwargs["base_url"] = base_url
                logger.info(f"🚀 Using vLLM at: {base_url}")
            elif self.provider.lower() == "openai-compatible":
                # Priority: saved settings > env var > default
                base_url = base_urls.get('openai-compatible') or os.getenv('OPENAI_COMPATIBLE_BASE_URL', 'http://localhost:8080/v1')
                kwargs["base_url"] = base_url
                logger.info(f"🔗 Using OpenAI-compatible server at: {base_url}")

            # Configure AbstractCore provider before creating LLM (ensures consistent base_url usage)
            if base_url:
                from abstractcore.config import configure_provider
                configure_provider(self.provider.lower(), base_url=base_url)

            self.llm = create_llm(
                self.provider,
                model=self.model,
                **kwargs
            )
            logger.info(f"✅ Initialized LLM with tracing: {self.provider}/{self.model}")
        except (ProviderAPIError, ModelNotFoundError, AuthenticationError) as e:
            logger.error(f"❌ Failed to initialize LLM: {e}")
            self.llm = None  # Keep service alive but mark LLM as unavailable
            # Don't raise - allow service to exist in degraded state
        except Exception as e:
            logger.error(f"❌ Unexpected error initializing LLM: {e}")
            self.llm = None  # Keep service alive but mark LLM as unavailable
    
    def check_provider_health(self) -> Dict[str, Any]:
        """
        Check provider health using AbstractCore 2.5.2's provider.health() method.
        
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
            # Use AbstractCore 2.5.2's provider.health() method
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
    
    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        return datetime.now().isoformat()

    def generate_code_from_prompt(self, prompt: str, context: Optional[Dict[str, Any]] = None,
                                  step_type: str = 'code_generation', attempt_number: int = 1) -> Tuple[str, Optional[float], Optional[str], Optional[Dict[str, Any]]]:
        """
        Convert a natural language prompt to Python code with full tracing.

        Args:
            prompt: Natural language description of the desired analysis
            context: Additional context information (variables, data info, etc.)
            step_type: Type of step for tracing (e.g., 'code_generation', 'code_fix')
            attempt_number: Attempt number for tracing (1-based)

        Returns:
            Tuple of (generated Python code, generation time in ms, trace_id or None, full_trace or None)

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
            # max_tokens = FULL ACTIVE CONTEXT (input + output)
            # max_output_tokens = OUTPUT LIMIT (includes thinking tokens for models like o1/o3)
            generation_params = {
                "max_tokens": 32000,  # Full active context size
                "max_output_tokens": 8192,  # 8k output limit (includes thinking tokens)
                "temperature": 0.1  # Low temperature for consistent code generation
            }
            
            # Add seed parameter if provider supports it (all except Anthropic in AbstractCore 2.5.2)
            if notebook_seed is not None and self.provider != 'anthropic':
                generation_params["seed"] = notebook_seed
                logger.info(f"🎲 Using LLM generation seed {notebook_seed} for {self.provider}")

            #  Call LLM with trace metadata for full observability
            response = self.llm.generate(
                user_prompt,
                system_prompt=system_prompt,
                trace_metadata={
                    'step_type': step_type,
                    'attempt_number': attempt_number,
                    'notebook_id': context.get('notebook_id') if context else None,
                    'cell_id': context.get('cell_id') if context else None
                },
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
                generation_time = getattr(response, 'gen_time', None)  # AbstractCore 2.5.2+ provides gen_time in ms
                
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

            # Get trace_id and full trace from AbstractCore's tracing system
            trace_id = None
            full_trace = None
            if hasattr(response, 'metadata') and response.metadata:
                trace_id = response.metadata.get('trace_id')
                logger.info(f"📝 Trace ID: {trace_id}")

                # Fetch full trace for persistent storage
                if trace_id and self.llm:
                    try:
                        traces = self.llm.get_traces(trace_id=trace_id)
                        if traces:
                            full_trace = traces if isinstance(traces, dict) else traces[0] if isinstance(traces, list) else None
                            logger.info(f"✅ Retrieved full trace for {trace_id}")
                    except Exception as e:
                        logger.warning(f"⚠️ Could not retrieve full trace: {e}")

            logger.info(f"🚨 EXTRACTED CODE: {code}")
            logger.info(f"Generated code for prompt: {prompt[:50]}...")

            return code, generation_time, trace_id, full_trace
            
        except (ProviderAPIError, ModelNotFoundError, AuthenticationError) as e:
            logger.error(f"LLM API error during code generation: {e}")
            raise LLMError(f"LLM API error: {e}")
        except Exception as e:
            logger.error(f"Code generation failed: {e}")
            raise LLMError(f"Failed to generate code: {e}")
    
    def _build_system_prompt(self, context: Optional[Dict[str, Any]] = None) -> str:
        """Build the system prompt for code generation.

        Args:
            context: Optional context including:
                - persona_combination: PersonaCombination for specialized guidance
                - available_variables: Dict of variables in namespace
                - data_info: Information about data files
        """

        # Extract persona combination if present
        persona_guidance = ""
        if context and 'persona_combination' in context:
            from ..services.persona_service import PersonaService
            from ..models.persona import PersonaScope

            persona_service = PersonaService()
            persona_combination = context['persona_combination']
            persona_guidance = persona_service.build_system_prompt_addition(
                persona_combination,
                PersonaScope.CODE_GENERATION
            )

        # OPTIMIZED PROMPT (2025-12-07): Sandwich architecture with few-shot examples
        # Reduces token count from ~2000 to ~950 (53% reduction)
        # Addresses position bias: critical instructions at START and END
        # Research: https://dl.acm.org/doi/10.1145/3715275.3732038 (Position is Power)
        #           https://www.promptingguide.ai/techniques/fewshot (Few-Shot > Instructions)

        base_prompt = """🎯 CRITICAL OUTPUT REQUIREMENT (READ FIRST)
================================================================================
You generate Python code from natural language.
ALL final results MUST use display() with descriptive labels:
  display(dataframe, "Table 1: Description")
  display(figure, "Figure 1: Description")
================================================================================

📊 EXAMPLES (FOLLOW THESE PATTERNS)
--------------------------------------------------------------------------------
Example 1 - Creating data:
```python
import pandas as pd
import numpy as np
df = pd.DataFrame({'age': np.random.randint(20, 80, 50)})
df.to_csv('data/output.csv', index=False)
display(df.head(20), "Table 1: Patient Dataset")  # ← REQUIRED
```

Example 2 - Matplotlib plot:
```python
import matplotlib.pyplot as plt
fig, ax = plt.subplots()
ax.hist(df['age'], bins=10)
ax.set_xlabel('Age')
display(fig, "Figure 1: Age Distribution")  # ← REQUIRED, NOT plt.show()
```

Example 3 - Plotly interactive plot (2D - only use 3D if explicitly requested):
```python
import plotly.express as px
fig = px.scatter(df, x='age', y='value', color='category', title='Interactive Scatter')
display(fig, "Figure 1: Interactive Plot")  # ← Plotly figs are interactive
```

Example 4 - Cross-validation results (display PRIMARY results):
```python
from sklearn.model_selection import cross_val_score
# When user asks for model validation, display the validation metrics FIRST
results = {}
for name, model in models.items():
    scores = cross_val_score(model, X, y, cv=10)
    results[name] = scores
    print(f"{name}: {scores.mean():.3f} ± {scores.std():.3f}")  # Console info

# Display PRIMARY result (what user asked for)
results_df = pd.DataFrame({
    'Model': list(results.keys()),
    'Mean Accuracy': [s.mean() for s in results.values()],
    'Std': [s.std() for s in results.values()]
})
display(results_df, "Table 1: 10-Fold Cross-Validation Results")  # ← PRIMARY

# THEN display secondary/supporting results
display(feature_importance, "Table 2: Feature Importance")  # ← SECONDARY
```

📁 DATA FILES
--------------------------------------------------------------------------------
All files in 'data/' directory. Use: pd.read_csv('data/filename.csv')

🚨 ANALYTICAL FLAGS (Stop if you detect these)
--------------------------------------------------------------------------------
• PRIMARY RESULT: The MAIN result answering the user's request must be display()'ed FIRST
• CIRCULAR REASONING: Don't predict X from variables derived from X
• DATA MISMATCH: Check df.columns.tolist() before accessing columns
• MISSING display(): Every DataFrame/figure must be displayed

⚠️ COMMON MISTAKES
--------------------------------------------------------------------------------
❌ WRONG: df.to_csv('data/file.csv')  # Missing display()
✅ RIGHT: df.to_csv('data/file.csv'); display(df.head(), "Table 1: Data")

❌ WRONG: plt.show()
✅ RIGHT: display(fig, "Figure 1: Title")

❌ WRONG: print(df)  OR  df['nonexistent_col']
✅ RIGHT: display(df, "Table 1: Results")  AND check columns first

❌ WRONG: from scipy.integrate import trapz  # REMOVED in SciPy 1.14+
✅ RIGHT: from scipy.integrate import trapezoid  # Use trapezoid for AUC

❌ WRONG: matplotlib for "interactive" plots
✅ RIGHT: Use plotly.graph_objects for INTERACTIVE visualizations

❌ WRONG: from sklearn.manifold import UMAP  # UMAP not in sklearn!
✅ RIGHT: from umap import UMAP  # Separate package

📚 AVAILABLE
--------------------------------------------------------------------------------
Libraries: pandas, numpy, matplotlib, plotly, seaborn, scipy, sklearn, lmfit, scanpy, umap, PIL, requests, openpyxl, lifelines, tableone
Helpers: display(obj, label), safe_timedelta(), safe_int(), safe_float()

✅ FINAL CHECKLIST (VERIFY BEFORE SUBMITTING)
================================================================================
□ Did you call display() for EVERY DataFrame you created?
□ Did you call display() for EVERY figure you created?
□ Did you use descriptive labels like "Table 1: Description"?
□ Did you verify column names exist before using them?
================================================================================"""

        # OLD PROMPT (kept for rollback if needed):
        # """You are a data analysis assistant that converts natural language requests into Python code.
        #
        # DATA FILES:
        # All data files are in the 'data/' directory. Always use 'data/filename.csv' format, never bare filenames.
        #
        # RULES:
        # 1. DISPLAY RESULTS using the display() function for article outputs:
        #    - For tables/DataFrames: display(df, "Table 1: Summary Statistics")
        #    - For matplotlib plots: fig, ax = plt.subplots(); ...; display(fig, "Figure 1: Age Distribution")
        #    - For plotly plots: fig = go.Figure(...); display(fig, "Figure 2: Interactive Chart")
        #    - The display() function auto-labels if you omit the label (Table 1, Table 2, etc.)
        #    - DO NOT use print() for final results - use display() to mark them for the article
        #    - DO NOT use plt.show() - it's not needed, use display(fig) instead
        #    - You can print() intermediate values for debugging, but final results must use display()
        #
        # 2. Generate executable Python code only - no explanations or markdown
        #
        # 3. Import required libraries at the start (pandas, numpy, matplotlib, plotly, seaborn, scipy, sklearn)
        #
        # 4. Use descriptive variable names
        #
        # 5. Handle errors with try/except blocks
        #
        # 6. Generate random data without seeds - reproducibility is handled automatically
        #
        # COMMON MISTAKES TO AVOID:
        #
        # 1. Function calls need parentheses
        #    WRONG: random.choice['A', 'B']
        #    RIGHT: random.choice(['A', 'B'])
        #
        # 2. NumPy types incompatible with Python built-ins
        #    WRONG: timedelta(days=np.random.randint(1, 30))
        #    RIGHT: timedelta(days=int(np.random.randint(1, 30)))
        #    OR USE: safe_timedelta(days=np.random.randint(1, 30))
        #
        # 3. File paths need 'data/' prefix
        #    WRONG: pd.read_csv('patients.csv')
        #    RIGHT: pd.read_csv('data/patients.csv')
        #
        # 4. CRITICAL - DataFrame columns: ALWAYS use exact column names as shown in DataFrame info
        #    WRONG: df['visit_date'] when DataFrame has 'VISIT_DATE'
        #    RIGHT: df['VISIT_DATE'] - use exact case and naming
        #    VERIFY: If unsure, check with df.columns.tolist() first
        #
        # ANALYTICAL REASONING FRAMEWORK (Think Before Coding):
        #
        # BEFORE WRITING CODE - REASON ABOUT THE ANALYSIS:
        #
        # 1. CLARIFY INTENT:
        #    - What question is the user trying to answer?
        #    - What is the goal: explore, predict, compare, test, quantify?
        #    - What would constitute a successful answer?
        #
        # 2. IDENTIFY KEY VARIABLES:
        #    - What is the TARGET/OUTCOME (what we're trying to explain/understand)?
        #    - What are the PREDICTORS/INPUTS (what might influence the outcome)?
        #    - CRITICAL: Target should be something we want to UNDERSTAND, not something already known/fixed
        #
        # 3. CHECK LOGICAL COHERENCE:
        #    - Does it make sense to analyze this relationship?
        #    - Watch for CIRCULAR REASONING:
        #      * Don't predict a variable from itself or its derivatives
        #      * Don't predict an assignment/grouping variable from characteristics it was used to create
        #      * Don't predict cause from effect (respect temporal logic: predictors must come BEFORE outcome)
        #
        # 4. VALIDATE DATA AVAILABILITY:
        #    - Do the required variables exist in the data?
        #    - Check column names carefully against available variables
        #    - If column missing: either derive it from existing data or adapt approach
        #
        # 5. ASSESS METHOD APPROPRIATENESS:
        #    - Does the statistical/ML method match the data type and question?
        #    - Are there obvious violations of assumptions?
        #    - What are alternative approaches?
        #
        # 6. IDENTIFY LIMITATIONS:
        #    - Is sample size adequate for this analysis?
        #    - Are there potential confounding factors?
        #    - What assumptions am I making?
        #
        # CRITICAL FLAGS (Stop and reconsider if you detect these):
        #
        # 🚨 CIRCULAR REASONING:
        #    - Predicting a grouping/assignment variable (like experimental condition, group label) from characteristics
        #    - Using outcome to predict itself or variables derived from it
        #    - Predicting X from variables that were created using X
        #
        # 🚨 DATA MISMATCH:
        #    - Using columns that don't exist in available variables
        #    - Requesting variables without checking they're available first
        #    - Assuming data structure without validation
        #
        # ⚠️ ANALYTICAL CONCERNS:
        #    - Very small sample size (n < 30) for statistical inference
        #    - Potential confounders not being considered
        #    - Method assumptions not being checked (normality, independence, etc.)
        #    - No validation strategy (train/test split, cross-validation)
        #
        # CONSTRUCTIVE APPROACH:
        # If you detect issues above:
        # 1. First check if variables exist using available_variables
        # 2. If analysis seems problematic, adapt to a more appropriate approach
        # 3. If unsure about column names, check df.columns.tolist() first
        # 4. Document assumptions and limitations in comments
        #
        # AVAILABLE LIBRARIES:
        # pandas, numpy, matplotlib, plotly, seaborn, scipy, sklearn, scanpy, umap, PIL, requests, openpyxl
        #
        # HELPERS (pre-loaded):
        # - Type conversion: safe_timedelta(), safe_int(), safe_float(), to_python_type()
        # - Article display: display(obj, label=None) - marks results for article with auto-labeling"""

        # Inject persona-specific guidance
        if persona_guidance:
            base_prompt += "\n\n" + "="*80 + "\n"
            base_prompt += "SPECIALIZED PERSONA GUIDANCE:\n"
            base_prompt += "="*80 + "\n"
            base_prompt += persona_guidance

        # Add context-specific information
        if context:
            if 'available_variables' in context:
                base_prompt += "\n\nAVAILABLE VARIABLES:\n"
                base_prompt += "Note: Use these variable names directly in your code.\n"
                vars_info = context['available_variables']

                # Check if categorized structure
                is_categorized = any(k in vars_info for k in ['dataframes', 'modules', 'numbers', 'arrays', 'dicts', 'other'])

                if is_categorized:
                    # Format categorized structure - just list the variable names
                    if vars_info.get('dataframes'):
                        base_prompt += "DataFrames: " + ", ".join(vars_info['dataframes'].keys()) + "\n"
                    if vars_info.get('arrays'):
                        base_prompt += "Arrays: " + ", ".join(vars_info['arrays'].keys()) + "\n"
                    if vars_info.get('modules'):
                        base_prompt += "Modules: " + ", ".join(vars_info['modules'].keys()) + "\n"
                    if vars_info.get('dicts'):
                        base_prompt += "Dicts: " + ", ".join(vars_info['dicts'].keys()) + "\n"
                    if vars_info.get('numbers'):
                        if len(vars_info['numbers']) <= 10:
                            base_prompt += "Numbers: " + ", ".join(vars_info['numbers'].keys()) + "\n"
                    if vars_info.get('other'):
                        if len(vars_info['other']) <= 5:
                            base_prompt += "Other: " + ", ".join(vars_info['other'].keys()) + "\n"
                else:
                    # Format flat structure
                    base_prompt += ", ".join(vars_info.keys())

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
                user_prompt += "\n" + "=" * 80 + "\n"
                user_prompt += "⚠️  CRITICAL: EXISTING VARIABLES YOU MUST REUSE  ⚠️\n"
                user_prompt += "=" * 80 + "\n\n"
                user_prompt += "These variables already exist in memory. DO NOT recreate them!\n"
                user_prompt += "REUSE them by their exact variable names shown below.\n\n"

                # Check if variables are categorized (from get_variable_info)
                is_categorized = 'dataframes' in variables or 'modules' in variables

                if is_categorized:
                    # Handle categorized structure from get_variable_info()
                    # Show DataFrames FIRST (most important for reuse)
                    if variables.get('dataframes'):
                        user_prompt += "🔹 DATAFRAMES AVAILABLE (REUSE THESE - NEVER RECREATE!):\n"
                        user_prompt += "-" * 80 + "\n"
                        for name, info in variables['dataframes'].items():
                            shape = info.get('shape', 'unknown')
                            columns = info.get('columns', [])
                            user_prompt += f"  ▶ Variable name: '{name}'\n"
                            user_prompt += f"    Type: DataFrame\n"
                            user_prompt += f"    Shape: {shape}\n"
                            if columns:
                                cols_preview = ', '.join(str(c) for c in columns)  # Show ALL columns
                                user_prompt += f"    Columns: {cols_preview}\n"
                            user_prompt += f"    ⚠️  USE THIS: {name}[column_name] or {name}.method()\n"
                            user_prompt += "\n"

                    # Show other variable categories
                    for category in ['arrays', 'dicts', 'numbers', 'modules', 'other']:
                        if variables.get(category):
                            category_name = category.upper().replace('_', ' ')
                            user_prompt += f"🔹 {category_name} AVAILABLE:\n"
                            user_prompt += "-" * 80 + "\n"
                            for name, info in variables[category].items():
                                var_type = info.get('type', 'unknown') if isinstance(info, dict) else 'unknown'
                                if isinstance(info, dict):
                                    # Show detailed info for structured types
                                    if 'shape' in info:
                                        user_prompt += f"  ▶ '{name}': {var_type} {info['shape']}\n"
                                    elif 'size' in info:
                                        user_prompt += f"  ▶ '{name}': {var_type} (size: {info['size']})\n"
                                    elif 'value' in info:
                                        user_prompt += f"  ▶ '{name}': {var_type} = {info['value']}\n"
                                    else:
                                        user_prompt += f"  ▶ '{name}': {var_type}\n"
                                else:
                                    user_prompt += f"  ▶ '{name}': {info}\n"
                            user_prompt += "\n"

                else:
                    # Handle flat structure (legacy or simple case)
                    user_prompt += "🔹 VARIABLES AVAILABLE:\n"
                    user_prompt += "-" * 80 + "\n"
                    for name, info in variables.items():
                        if isinstance(info, dict):
                            var_type = info.get('type', 'unknown')
                            user_prompt += f"  ▶ '{name}': {var_type}\n"
                        else:
                            user_prompt += f"  ▶ '{name}': {info}\n"
                    user_prompt += "\n"

                user_prompt += "\n⚠️  REMINDER: Use existing variable names EXACTLY as shown above!\n"
                user_prompt += "=" * 80 + "\n\n"

        # ANALYSIS PLAN GUIDANCE: Show planning results to guide code generation
        if context and 'analysis_plan' in context:
            plan = context['analysis_plan']
            user_prompt += "=" * 80 + "\n"
            user_prompt += "📋 ANALYSIS PLAN GUIDANCE (AI Pre-Analysis)\n"
            user_prompt += "=" * 80 + "\n\n"
            user_prompt += "Before generating code, AI analyzed your request:\n\n"

            if plan.get('research_question'):
                user_prompt += f"Research Question: {plan['research_question']}\n"

            if plan.get('suggested_method'):
                user_prompt += f"\n✅ Recommended Method: {plan['suggested_method']}\n"

            if plan.get('method_rationale'):
                user_prompt += f"   Rationale: {plan['method_rationale']}\n"

            if plan.get('target_variable'):
                user_prompt += f"\n🎯 Target Variable: {plan['target_variable']}\n"

            if plan.get('predictor_variables'):
                predictors = ', '.join(plan['predictor_variables'])
                user_prompt += f"📊 Predictor Variables: {predictors}\n"

            if plan.get('assumptions') and len(plan['assumptions']) > 0:
                user_prompt += f"\n⚙️  Assumptions to Consider:\n"
                for assumption in plan['assumptions']:  # Show all assumptions - no truncation
                    user_prompt += f"   - {assumption}\n"

            if plan.get('validation_issues') and len(plan['validation_issues']) > 0:
                # Show non-critical warnings (critical already blocked execution)
                warnings = [issue for issue in plan['validation_issues']
                          if issue.get('severity') != 'critical']
                if warnings:
                    user_prompt += f"\n⚠️  VALIDATION WARNINGS ({len(warnings)}):\n"
                    for issue in warnings:  # Show all warnings - no truncation
                        user_prompt += f"   - {issue.get('message', 'Unknown issue')}\n"
                        if issue.get('suggestion'):
                            user_prompt += f"     Suggestion: {issue['suggestion']}\n"

            user_prompt += "\n💡 IMPORTANT: Follow the recommended method and consider the assumptions above.\n"
            user_prompt += "=" * 80 + "\n\n"

        # SECOND: Add previous cells context for awareness
        if context and 'previous_cells' in context:
            previous_cells = context['previous_cells']
            if previous_cells:
                user_prompt += "PREVIOUS CELLS IN THIS NOTEBOOK:\n"
                user_prompt += "=" * 60 + "\n"
                for idx, cell in enumerate(previous_cells, 1):
                    user_prompt += f"\nCell {idx} ({'✓' if cell.get('success') else '✗'}):\n"
                    if cell.get('prompt'):
                        user_prompt += f"  Prompt: {cell['prompt']}\n"  # Full prompt - no truncation
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

        # THIRD: Add available files information with full preview data
        if context and 'files_in_context' in context:
            files = context['files_in_context']
            if files:
                user_prompt += "AVAILABLE DATA FILES:\n"
                user_prompt += "=" * 60 + "\n"
                user_prompt += "NOTE: Below is METADATA + PREVIEW DATA (first 20 rows) for each file.\n"
                user_prompt += "Use this to understand the data structure and write appropriate analysis code.\n"
                user_prompt += "The full dataset is available at the specified path.\n"
                user_prompt += "=" * 60 + "\n\n"
                
                for file_info in files:
                    user_prompt += f"📄 {file_info['name']}\n"
                    user_prompt += f"   Path: {file_info['path']}\n"
                    user_prompt += f"   Type: {file_info['type']}\n"
                    user_prompt += f"   Size: {self._format_file_size(file_info['size'])}\n"
                    
                    # Add preview information for structured data
                    if 'preview' in file_info and file_info['preview']:
                        preview = file_info['preview']
                        if 'error' not in preview:
                            # CSV and TSV files - full preview with column stats and sample data
                            if file_info['type'] in ['csv', 'tsv']:
                                user_prompt += f"   Shape: {preview['shape'][0]} rows × {preview['shape'][1]} columns\n\n"
                                
                                # Columns with rich stats (type, missing, range/values)
                                column_stats = preview.get('column_stats', {})
                                if column_stats:
                                    user_prompt += f"   COLUMN ANALYSIS:\n"
                                    for col in preview.get('columns', []):
                                        stats = column_stats.get(col, {})
                                        col_type = stats.get('type', 'unknown')
                                        missing = stats.get('missing', '0')
                                        
                                        # Build compact stats string
                                        stats_parts = [col_type]
                                        if missing != '0':
                                            stats_parts.append(f"missing: {missing}")
                                        if 'range' in stats:
                                            stats_parts.append(f"range: {stats['range']}")
                                        if 'mean' in stats:
                                            stats_parts.append(f"mean: {stats['mean']}")
                                        if 'unique' in stats:
                                            stats_parts.append(f"{stats['unique']} unique")
                                        if 'values' in stats:
                                            stats_parts.append(f"values: {stats['values']}")
                                        elif 'top_values' in stats:
                                            stats_parts.append(f"top: {stats['top_values']}")
                                        
                                        user_prompt += f"      - {col}: {' | '.join(stats_parts)}\n"
                                else:
                                    # Fallback to old dtypes format
                                    user_prompt += f"   Columns and Types:\n"
                                    for col in preview.get('columns', []):
                                        dtype = preview.get('dtypes', {}).get(col, 'unknown')
                                        user_prompt += f"      - {col}: {dtype}\n"
                                
                                # Sample data table (or full data for dictionaries)
                                sample_data = preview.get('sample_data', [])
                                is_dictionary = preview.get('is_dictionary', False)
                                if sample_data:
                                    if is_dictionary:
                                        user_prompt += f"\n   📖 DATA DICTIONARY (COMPLETE - ALL {len(sample_data)} rows):\n"
                                        user_prompt += "   This is a data dictionary describing variables/columns. Use this to understand the data.\n"
                                    else:
                                        user_prompt += f"\n   SAMPLE DATA (first {len(sample_data)} rows of {preview['shape'][0]} total):\n"
                                    user_prompt += self._format_sample_data_table(
                                        preview.get('columns', []),
                                        sample_data,
                                        column_stats if column_stats else preview.get('dtypes', {})
                                    )
                            
                            # Excel files - full preview for each sheet
                            elif file_info['type'] in ['xlsx', 'xls', 'excel']:
                                sheets = preview.get('sheets', [])
                                if isinstance(sheets, list) and len(sheets) > 0 and isinstance(sheets[0], dict):
                                    # New format with full sheet details
                                    user_prompt += f"   Excel file with {len(sheets)} sheet(s)\n\n"
                                    for sheet in sheets:
                                        if 'error' in sheet:
                                            user_prompt += f"   SHEET: {sheet['name']} (Error: {sheet['error']})\n\n"
                                            continue
                                        
                                        user_prompt += f"   SHEET: {sheet['name']}\n"
                                        user_prompt += f"   Shape: {sheet.get('rows', 0)} rows × {len(sheet.get('columns', []))} columns\n\n"
                                        
                                        # Columns with rich stats (type, missing, range/values)
                                        column_stats = sheet.get('column_stats', {})
                                        if column_stats:
                                            user_prompt += f"   COLUMN ANALYSIS:\n"
                                            for col in sheet.get('columns', []):
                                                stats = column_stats.get(col, {})
                                                col_type = stats.get('type', 'unknown')
                                                missing = stats.get('missing', '0')
                                                
                                                # Build compact stats string
                                                stats_parts = [col_type]
                                                if missing != '0':
                                                    stats_parts.append(f"missing: {missing}")
                                                if 'range' in stats:
                                                    stats_parts.append(f"range: {stats['range']}")
                                                if 'mean' in stats:
                                                    stats_parts.append(f"mean: {stats['mean']}")
                                                if 'unique' in stats:
                                                    stats_parts.append(f"{stats['unique']} unique")
                                                if 'values' in stats:
                                                    stats_parts.append(f"values: {stats['values']}")
                                                elif 'top_values' in stats:
                                                    stats_parts.append(f"top: {stats['top_values']}")
                                                
                                                user_prompt += f"      - {col}: {' | '.join(stats_parts)}\n"
                                        else:
                                            # Fallback to old dtypes format
                                            user_prompt += f"   Columns and Types:\n"
                                            for col in sheet.get('columns', []):
                                                dtype = sheet.get('dtypes', {}).get(col, 'unknown')
                                                user_prompt += f"      - {col}: {dtype}\n"
                                        
                                        # Sample data table (or full data for dictionary sheets)
                                        sample_data = sheet.get('sample_data', [])
                                        is_dictionary = sheet.get('is_dictionary', False)
                                        if sample_data:
                                            if is_dictionary:
                                                user_prompt += f"\n   📖 DATA DICTIONARY SHEET (COMPLETE - ALL {len(sample_data)} rows):\n"
                                                user_prompt += "   This sheet is a data dictionary describing variables/columns. Use this to understand the data.\n"
                                            else:
                                                user_prompt += f"\n   SAMPLE DATA (first {len(sample_data)} rows of {sheet.get('rows', 0)} total):\n"
                                            user_prompt += self._format_sample_data_table(
                                                sheet.get('columns', []),
                                                sample_data,
                                                column_stats if column_stats else sheet.get('dtypes', {})
                                            )
                                        user_prompt += "\n"
                                else:
                                    # Legacy format - just sheet names
                                    sheets_str = ', '.join(str(s) for s in sheets[:5])
                                    if len(sheets) > 5:
                                        sheets_str += f", ... ({len(sheets)} total)"
                                    user_prompt += f"   Excel sheets: {sheets_str}\n"
                            
                            # JSON files - send FULL content
                            elif file_info['type'] == 'json':
                                if 'full_content' in preview:
                                    # New format: full content
                                    is_large = preview.get('is_large_file', False)
                                    token_est = preview.get('estimated_tokens', 0)
                                    if is_large:
                                        user_prompt += f"   ⚠️ LARGE FILE ({token_est:,} tokens estimated)\n"
                                    user_prompt += f"   Structure: {preview.get('structure_type', 'unknown')}\n"
                                    user_prompt += f"   Lines: {preview.get('line_count', 0)}\n\n"
                                    user_prompt += f"   FULL CONTENT:\n```json\n{preview['full_content']}\n```\n"
                                else:
                                    # Legacy format
                                    if preview.get('type') == 'array':
                                        user_prompt += f"   JSON array with {preview['length']} items\n"
                                        if 'schema' in preview and preview['schema']:
                                            user_prompt += f"   Item structure: {self._format_json_schema(preview['schema'])}\n"
                                    elif preview.get('type') == 'object':
                                        user_prompt += f"   JSON object with {preview.get('total_keys', len(preview.get('keys', [])))} properties\n"
                                        if preview.get('keys'):
                                            keys_str = ', '.join(preview['keys'])
                                            user_prompt += f"   Keys: {keys_str}\n"
                            
                            # Text files - send FULL content
                            elif file_info['type'] == 'txt':
                                if 'full_content' in preview:
                                    # New format: full content
                                    is_large = preview.get('is_large_file', False)
                                    token_est = preview.get('estimated_tokens', 0)
                                    if is_large:
                                        user_prompt += f"   ⚠️ LARGE FILE ({token_est:,} tokens estimated)\n"
                                    user_prompt += f"   Lines: {preview.get('line_count', 0)}\n\n"
                                    user_prompt += f"   FULL CONTENT:\n```\n{preview['full_content']}\n```\n"
                                elif 'first_lines' in preview and preview['first_lines']:
                                    # Legacy format
                                    user_prompt += f"   Text preview:\n"
                                    for line in preview['first_lines'][:5]:
                                        user_prompt += f"      {line}\n"
                            
                            # Markdown files - send FULL content
                            elif file_info['type'] == 'md':
                                if 'full_content' in preview:
                                    is_large = preview.get('is_large_file', False)
                                    token_est = preview.get('estimated_tokens', 0)
                                    if is_large:
                                        user_prompt += f"   ⚠️ LARGE FILE ({token_est:,} tokens estimated)\n"
                                    user_prompt += f"   Lines: {preview.get('line_count', 0)}\n\n"
                                    user_prompt += f"   FULL CONTENT:\n```markdown\n{preview['full_content']}\n```\n"
                            
                            # YAML files - send FULL content
                            elif file_info['type'] in ['yaml', 'yml']:
                                if 'full_content' in preview:
                                    is_large = preview.get('is_large_file', False)
                                    token_est = preview.get('estimated_tokens', 0)
                                    if is_large:
                                        user_prompt += f"   ⚠️ LARGE FILE ({token_est:,} tokens estimated)\n"
                                    user_prompt += f"   Structure: {preview.get('structure_type', 'unknown')}\n"
                                    user_prompt += f"   Lines: {preview.get('line_count', 0)}\n\n"
                                    user_prompt += f"   FULL CONTENT:\n```yaml\n{preview['full_content']}\n```\n"
                    
                    user_prompt += "\n"
                
                user_prompt += "IMPORTANT: Use 'data/filename.ext' format to access these files!\n"
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
    
    def _format_sample_data_table(self, columns: List[str], sample_data: List[dict], dtypes: dict = None) -> str:
        """
        Format sample data as a readable table for LLM context.
        
        Args:
            columns: List of column names
            sample_data: List of row dictionaries
            dtypes: Optional dict of column data types
            
        Returns:
            Formatted table string
        """
        if not columns or not sample_data:
            return "   (No sample data available)\n"
        
        result = ""
        
        # Build header row
        header = " | ".join(str(col) for col in columns)
        result += f"   | {header} |\n"
        
        # Build separator
        separator = " | ".join("-" * min(len(str(col)), 15) for col in columns)
        result += f"   | {separator} |\n"
        
        # Build data rows
        for row in sample_data:
            values = []
            for col in columns:
                val = row.get(col, "")
                if val is None:
                    val_str = ""
                else:
                    val_str = str(val)
                    # Truncate very long values in table display only
                    if len(val_str) > 30:
                        val_str = val_str[:27] + "..."
                values.append(val_str)
            row_str = " | ".join(values)
            result += f"   | {row_str} |\n"
        
        return result
    
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
    
    def explain_code(
        self,
        code: str,
        step_type: str = 'methodology_generation',
        attempt_number: int = 1,
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, Optional[str]]:
        """
        Generate a natural language explanation of Python code with full tracing.

        Args:
            code: Python code to explain
            step_type: Type of step for tracing (e.g., 'methodology_generation')
            attempt_number: Attempt number for tracing
            context: Additional context for tracing (notebook_id, cell_id)

        Returns:
            Tuple of (natural language explanation, trace_id or None)
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
                trace_metadata={
                    'step_type': step_type,
                    'attempt_number': attempt_number,
                    'notebook_id': context.get('notebook_id') if context else None,
                    'cell_id': context.get('cell_id') if context else None
                },
                max_tokens=32000,  # Full active context
                max_output_tokens=8192,  # 8k output limit
                temperature=0.3
            )

            # Extract trace_id from AbstractCore's tracing system
            trace_id = None
            if hasattr(response, 'metadata') and response.metadata:
                trace_id = response.metadata.get('trace_id')
                logger.info(f"📝 Methodology trace ID: {trace_id}")

            explanation = response.content.strip()
            return explanation, trace_id

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
        traceback: Optional[str] = None,
        step_type: str = 'code_fix',
        attempt_number: int = 2,
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, Optional[str], Optional[Dict[str, Any]]]:
        """
        Suggest improvements or fixes for generated code with full tracing.

        Args:
            prompt: Original natural language prompt
            code: Generated code that needs improvement
            error_message: Error message if code failed to execute
            error_type: Exception type (e.g., "ValueError")
            traceback: Full Python traceback
            step_type: Type of step for tracing (e.g., 'code_fix')
            attempt_number: Attempt number for tracing (typically 2+)
            context: Additional context for tracing (notebook_id, cell_id)

        Returns:
            Tuple of (improved Python code, trace_id or None, full_trace or None)
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
                code,
                context  # Pass context to error analyzer for DataFrame column info
            )

            improvement_prompt += f"\n\nBut it failed with this error:\n\n{enhanced_error}\n\nRegenerate the COMPLETE working Python code that fixes this error. Output the FULL code, not just the fixed line."

            logger.info("Enhanced error context provided to LLM for auto-retry")
        else:
            improvement_prompt += "\n\nImprove this code to be more robust, efficient, and user-friendly."

        improvement_prompt += "\n\nGenerate the improved Python code:"

        try:
            response = self.llm.generate(
                improvement_prompt,
                system_prompt=self._build_system_prompt(context),  # Pass context for available variables
                trace_metadata={
                    'step_type': step_type,
                    'attempt_number': attempt_number,
                    'notebook_id': context.get('notebook_id') if context else None,
                    'cell_id': context.get('cell_id') if context else None
                },
                max_tokens=32000,  # Full active context
                max_output_tokens=8192,  # 8k output limit
                temperature=0.1
            )

            # Extract trace_id and full trace from AbstractCore's tracing system
            trace_id = None
            full_trace = None
            if hasattr(response, 'metadata') and response.metadata:
                trace_id = response.metadata.get('trace_id')
                logger.info(f"📝 Code fix trace ID: {trace_id}")

                # Fetch full trace for persistent storage
                if trace_id and self.llm:
                    try:
                        traces = self.llm.get_traces(trace_id=trace_id)
                        if traces:
                            full_trace = traces if isinstance(traces, dict) else traces[0] if isinstance(traces, list) else None
                            logger.info(f"✅ Retrieved full trace for code fix {trace_id}")
                    except Exception as e:
                        logger.warning(f"⚠️ Could not retrieve full trace: {e}")

            improved_code = self._extract_code_from_response(response.content)
            return improved_code, trace_id, full_trace

        except (ProviderAPIError, ModelNotFoundError, AuthenticationError) as e:
            logger.error(f"LLM API error during code improvement: {e}")
            raise LLMError(f"LLM API error: {e}")
        except Exception as e:
            logger.error(f"Code improvement failed: {e}")
            raise LLMError(f"Failed to improve code: {e}")

    def _enhance_traceback_with_code(self, traceback: str, code: str) -> str:
        """
        Enhance traceback by showing actual code lines from generated code.

        Python's exec() with '<string>' source doesn't provide source code context
        in tracebacks. This method extracts line numbers and shows the actual code.

        When the error line is just a closing bracket (}, ], )), shows context
        lines to reveal the actual expression that caused the error (Python reports
        errors at closing brackets for multi-line expressions).

        Transforms:
          File "<string>", line 37, in <module>

        Into:
          File "<string>", line 37, in <module>
        >>> 37:     response.append(np.random.choice(['CR', 'PR'], p=[0.5, 0.4]))

        Or for closing brackets:
          File "<string>", line 19, in <module>
        >>> Context around line 19:
            15:     "key": f"{df.loc[condition].values[0]}"
        >>> 19: }

        Args:
            traceback: Original Python traceback
            code: The generated code that was executed

        Returns:
            Enhanced traceback with actual code lines and context shown
        """
        import re

        # Extract all line numbers from traceback that reference generated code
        pattern = r'File "<string>", line (\d+)'
        matches = list(re.finditer(pattern, traceback))

        if not matches:
            return traceback  # No <string> references, return as-is

        code_lines = code.split('\n')
        enhanced_lines = []

        for line in traceback.split('\n'):
            enhanced_lines.append(line)

            # Check if this line references generated code
            match = re.search(pattern, line)
            if match:
                line_num = int(match.group(1))
                if 1 <= line_num <= len(code_lines):
                    actual_code = code_lines[line_num - 1].strip()

                    # Check if line is just a closing bracket (likely end of multi-line expression)
                    # Python reports errors at closing brackets for dict/list literals
                    if actual_code in ['}', ']', ')', '},', '],', '),', '})', '})']:
                        # Show context: 5 lines before and the bracket line
                        enhanced_lines.append(f">>> Context around line {line_num} (error in multi-line expression):")
                        start = max(0, line_num - 6)  # 5 lines before
                        for i in range(start, line_num):
                            ctx_line = code_lines[i]
                            marker = ">>>" if i == line_num - 1 else "   "
                            enhanced_lines.append(f"{marker} {i + 1}: {ctx_line}")
                    else:
                        # Normal case: show just the error line
                        enhanced_lines.append(f">>> {line_num}: {code_lines[line_num - 1]}")

        return '\n'.join(enhanced_lines)

    def _enhance_error_context(
        self,
        error_message: str,
        error_type: str,
        traceback: str,
        code: str,
        context: Optional[Dict[str, Any]] = None
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
            context: Optional execution context with available variables

        Returns:
            Enhanced error message with guidance
        """
        # First, enhance traceback to show actual code lines
        enhanced_traceback = self._enhance_traceback_with_code(traceback, code)

        try:
            from .error_analyzer import ErrorAnalyzer

            analyzer = ErrorAnalyzer()
            error_context = analyzer.analyze_error(error_message, error_type, enhanced_traceback, code, context)
            formatted = analyzer.format_for_llm(error_context, enhanced_traceback)

            logger.info(f"Error enhanced with {len(error_context.suggestions)} suggestions")

            return formatted

        except Exception as e:
            logger.warning(f"Error analysis failed, using original error: {e}")
            # Fallback to original error message if analysis fails
            return f"{error_type}: {error_message}\n\nTraceback:\n{enhanced_traceback}"
    
    def generate_scientific_explanation(
        self,
        prompt: str,
        code: str,
        execution_result: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
        step_type: str = 'methodology_generation',
        attempt_number: int = 1,
        previous_methodologies: Optional[List[str]] = None
    ) -> Tuple[str, Optional[float], Optional[str], Optional[Dict[str, Any]]]:
        """
        Generate a scientific article-style explanation of what was done and why with full tracing.

        Args:
            prompt: The original natural language prompt
            code: The generated Python code
            execution_result: The result of code execution (stdout, plots, etc.)
            context: Additional context for tracing (notebook_id, cell_id, available_variables)
            step_type: Type of step for tracing (e.g., 'methodology_generation')
            attempt_number: Attempt number for tracing
            previous_methodologies: List of previous cells' methodologies for narrative continuity

        Returns:
            Tuple of (scientific explanation text, generation time in ms, trace_id or None, full_trace or None)

        Raises:
            LLMError: If explanation generation fails
        """
        if not self.llm:
            raise LLMError("LLM not initialized")

        # Extract rich insights from execution results
        from .execution_service import ExecutionResult

        # Convert execution_result dict to ExecutionResult object if needed
        if isinstance(execution_result, dict):
            # Create a simple object to hold the data
            class ResultObj:
                def __init__(self, data):
                    for key, value in data.items():
                        setattr(self, key, value)
            result_obj = ResultObj(execution_result)
        else:
            result_obj = execution_result

        # Extract insights
        insights = ExecutionInsightsExtractor.extract_insights(result_obj, code, context)
        formatted_insights = ExecutionInsightsExtractor.format_for_methodology_prompt(insights)

        # Build the system prompt for scientific writing
        system_prompt = """You are a scientific writing assistant that creates high-impact scientific article sections.

TASK: Write a clear, professional scientific explanation of a data analysis step that reads like a Nature/Science article.

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
2. Methodology: Describe the approach taken with specific details
3. Results: Summarize key findings from the execution with ACTUAL QUANTITATIVE DATA

CRITICAL REQUIREMENT - ASSET REFERENCING:
When tables or figures are generated, you MUST reference them by their labels:
- Use "Table 1", "Table 2", "Figure 1", "Figure 2" etc. in your text
- Include actual quantitative results from the tables/figures
- Format: "As shown in Table 1, the cohort comprised 50 patients with mean age 52.3 ± 8.7 years..."
- Format: "The dashboard visualization (Figure 1) revealed..."

EXAMPLE OUTPUT WITH ASSET REFERENCES:
"To assess the distribution of gene expression levels across samples, a comprehensive statistical analysis was performed on the normalized expression matrix (Table 1; 20 genes × 6 conditions). The analysis revealed a mean expression level of 15.3 ± 4.2 across all genes, with significant variability observed between experimental conditions (CV = 28%). Visualization of the expression patterns (Figure 1) demonstrated clear clustering of samples by treatment condition, with treated samples showing 2.5-fold higher expression of key marker genes (p < 0.001)."

EXAMPLE OUTPUT FOR DASHBOARD:
"A comprehensive clinical trial dashboard (Figure 1) was constructed to visualize key metrics and trends from the SDTM dataset of 50 TNBC patients. The dashboard revealed a cohort with mean age of 52.3 ± 8.7 years, predominantly female (95%), and mean tumor size of 4.2 ± 1.8 mm. Treatment response analysis showed complete response (CR) in 20% of patients, partial response (PR) in 30%, with the remaining showing stable disease (30%) or progression (20%). Correlation analysis revealed a positive association between tumor size and treatment duration (Spearman ρ = 0.45, p < 0.01)."

GUIDELINES:
- ALWAYS reference tables and figures by their labels when they exist
- Include ACTUAL quantitative results (means, percentages, p-values, counts)
- Use specific numbers from the execution results provided
- Mention statistical measures and sample sizes
- Connect findings to the analysis objective
- Maintain objective, analytical tone
- VERIFY claims against data: If console output shows specific results, use EXACT values from the output
- Never invent or guess values - only report what is explicitly shown in the data
- When multiple models are compared, report results for EACH model accurately
- Length: 3-5 sentences, maximum 200 words for complex analyses"""

        # Inject persona guidance for methodology if available
        if context and 'persona_combination' in context:
            from ..services.persona_service import PersonaService
            from ..models.persona import PersonaScope

            persona_service = PersonaService()
            persona_combination = context['persona_combination']
            methodology_guidance = persona_service.build_system_prompt_addition(
                persona_combination,
                PersonaScope.METHODOLOGY
            )
            if methodology_guidance:
                system_prompt += "\n\n" + "="*60 + "\n"
                system_prompt += "METHODOLOGY WRITING GUIDANCE (from active personas):\n"
                system_prompt += "="*60 + "\n"
                system_prompt += methodology_guidance

        # Build context section for previous methodologies
        previous_context = ""
        if previous_methodologies and len(previous_methodologies) > 0:
            previous_context = "\n## PREVIOUS ANALYSIS STEPS (for narrative continuity):\n"
            for i, prev_method in enumerate(previous_methodologies, 1):
                previous_context += f"\nStep {i}: {prev_method}\n"

        # Build the user prompt with rich context
        user_prompt = f"""Generate a scientific article-style explanation for this analysis:

ORIGINAL REQUEST: {prompt}

CODE EXECUTED:
```python
{code}
```

{formatted_insights}

## CONSOLE OUTPUT (full context for statistical results):
```
{execution_result.get('stdout', '')}
```

EXECUTION STATUS: {'Success' if execution_result.get('status') == 'success' else 'Error'}
{previous_context}

CRITICAL INSTRUCTIONS:
1. Reference specific tables/figures by their labels (e.g., "Table 1", "Figure 1")
2. Include ACTUAL quantitative results from the data above (means, counts, percentages, statistics)
3. Connect this analysis to any previous steps if context is provided
4. Write in publication-ready scientific prose

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
            # max_tokens = FULL ACTIVE CONTEXT (input + output)
            # max_output_tokens = OUTPUT LIMIT (includes thinking tokens for models like o1/o3)
            generation_params = {
                "max_tokens": 32000,  # Full active context size
                "max_output_tokens": 8192,  # 8k output limit
                "temperature": 0.2  # Slightly higher for more natural writing
            }
            
            # Add seed parameter if provider supports it (all except Anthropic in AbstractCore 2.5.2)
            if notebook_seed is not None and self.provider != 'anthropic':
                generation_params["seed"] = notebook_seed
                logger.info(f"🎲 Using LLM generation seed {notebook_seed} for scientific explanation with {self.provider}")
            
            response = self.llm.generate(
                user_prompt,
                system_prompt=system_prompt,
                trace_metadata={
                    'step_type': step_type,
                    'attempt_number': attempt_number,
                    'notebook_id': context.get('notebook_id') if context else None,
                    'cell_id': context.get('cell_id') if context else None
                },
                **generation_params
            )
            elapsed_time = time.time() - start_time
            print(f"🔬 LLM SERVICE: LLM call took {elapsed_time:.1f} seconds")
            print(f"🔬 LLM SERVICE: Got response: {type(response)}")
            print(f"🔬 LLM SERVICE: Response content: {response.content[:100]}...")

            # Extract trace_id and full trace from AbstractCore's tracing system
            trace_id = None
            full_trace = None
            if hasattr(response, 'metadata') and response.metadata:
                trace_id = response.metadata.get('trace_id')
                logger.info(f"📝 Methodology trace ID: {trace_id}")

                # Fetch full trace for persistent storage
                if trace_id and self.llm:
                    try:
                        traces = self.llm.get_traces(trace_id=trace_id)
                        if traces:
                            full_trace = traces if isinstance(traces, dict) else traces[0] if isinstance(traces, list) else None
                            logger.info(f"✅ Retrieved full trace for methodology {trace_id}")
                    except Exception as e:
                        logger.warning(f"⚠️ Could not retrieve full trace: {e}")

            explanation = response.content.strip()
            generation_time = getattr(response, 'gen_time', None)
            print(f"🔬 LLM SERVICE: Final explanation: {len(explanation)} characters")
            logger.info(f"Generated scientific explanation: {len(explanation)} characters")
            return explanation, generation_time, trace_id, full_trace
            
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
            
            # Build comprehensive context from all cells - NO TRUNCATION
            # The abstract needs complete information to avoid hallucinations
            cells_summary = []
            for i, cell in enumerate(notebook_data.get('cells', []), 1):
                cell_summary = f"Cell {i}:"
                
                # Full prompt (the intent)
                if cell.get('prompt'):
                    cell_summary += f"\n  Objective: {cell['prompt']}"
                
                # Full code (the implementation)
                if cell.get('code'):
                    cell_summary += f"\n  Implementation:\n{cell['code']}"
                
                # Full results from execution
                last_result = cell.get('last_result')
                if last_result:
                    # Stdout output
                    if last_result.get('output'):
                        cell_summary += f"\n  Output:\n{last_result['output']}"
                    
                    # Table metadata + 20-row preview (same format as cell code generation)
                    if last_result.get('tables'):
                        for j, table in enumerate(last_result['tables'], 1):
                            cell_summary += f"\n  Table {j}:"
                            if isinstance(table, dict):
                                # Table identification
                                if table.get('label'):
                                    cell_summary += f" {table['label']}"
                                if table.get('name'):
                                    cell_summary += f" ({table['name']})"
                                
                                # Shape
                                shape = table.get('shape', [0, 0])
                                cell_summary += f"\n    Shape: {shape[0]} rows × {shape[1]} columns"
                                
                                # Columns with data types (same format as cell code generation)
                                columns = table.get('columns', [])
                                info = table.get('info', {})
                                dtypes = info.get('dtypes', {})
                                
                                if columns:
                                    cell_summary += f"\n    COLUMNS:"
                                    for col in columns:
                                        dtype = dtypes.get(col, 'unknown')
                                        cell_summary += f"\n      - {col}: {dtype}"
                                
                                # Sample data table (first 20 rows, same format as cell code generation)
                                data = table.get('data', [])
                                if data and columns:
                                    sample_data = data[:20]
                                    cell_summary += f"\n    SAMPLE DATA (first {len(sample_data)} rows of {shape[0]} total):\n"
                                    cell_summary += self._format_sample_data_table(columns, sample_data, dtypes)
                    
                    # Interactive plot METADATA only (titles, axes - not data arrays)
                    if last_result.get('interactive_plots'):
                        for j, plot in enumerate(last_result['interactive_plots'], 1):
                            cell_summary += f"\n  Figure {j}:"
                            if isinstance(plot, dict):
                                # Get layout from nested 'figure' or direct
                                figure = plot.get('figure', plot)
                                layout = figure.get('layout', {})
                                
                                if layout.get('title'):
                                    title = layout['title']
                                    if isinstance(title, dict):
                                        cell_summary += f" {title.get('text', '')}"
                                    else:
                                        cell_summary += f" {title}"
                                if layout.get('xaxis', {}).get('title'):
                                    xaxis = layout['xaxis']['title']
                                    if isinstance(xaxis, dict):
                                        cell_summary += f"\n    X-axis: {xaxis.get('text', '')}"
                                    else:
                                        cell_summary += f"\n    X-axis: {xaxis}"
                                if layout.get('yaxis', {}).get('title'):
                                    yaxis = layout['yaxis']['title']
                                    if isinstance(yaxis, dict):
                                        cell_summary += f"\n    Y-axis: {yaxis.get('text', '')}"
                                    else:
                                        cell_summary += f"\n    Y-axis: {yaxis}"
                                        
                                # Include trace names/types ONLY (not data arrays)
                                data = figure.get('data', [])
                                if data:
                                    trace_info = []
                                    for trace in data[:5]:  # Limit to first 5 traces
                                        trace_type = trace.get('type', 'unknown')
                                        trace_name = trace.get('name', '')
                                        if trace_name:
                                            trace_info.append(f"{trace_type}: {trace_name}")
                                        else:
                                            trace_info.append(trace_type)
                                    if trace_info:
                                        cell_summary += f"\n    Plot elements: {', '.join(trace_info)}"
                                    if len(data) > 5:
                                        cell_summary += f" (+{len(data) - 5} more)"
                    
                    # Static plot descriptions (labels only, not image data)
                    if last_result.get('plots'):
                        plot_count = len(last_result['plots'])
                        cell_summary += f"\n  Static visualizations: {plot_count} plot(s) generated"
                        for j, plot in enumerate(last_result['plots'], 1):
                            if isinstance(plot, dict) and plot.get('label'):
                                cell_summary += f"\n    Plot {j}: {plot['label']}"
                    
                    # Warnings (statistical/analytical context)
                    if last_result.get('warnings'):
                        cell_summary += f"\n  Warnings:"
                        for warning in last_result['warnings']:
                            cell_summary += f"\n    - {warning}"
                
                # Full scientific explanation (the methodology)
                if cell.get('scientific_explanation'):
                    cell_summary += f"\n  Methodology:\n{cell['scientific_explanation']}"
                
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
                max_tokens=32000,  # Full active context
                max_output_tokens=8192,  # 8k output limit
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
                max_tokens=32000,  # Full active context
                max_output_tokens=8192,  # 8k output limit
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
                max_tokens=32000,  # Full active context
                max_output_tokens=8192,  # 8k output limit
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