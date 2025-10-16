"""
LLM Service for converting natural language prompts to Python code.

This service uses AbstractCore to interface with LLM providers (specifically LMStudio)
and generates appropriate Python code for data analysis tasks.
"""

import logging
from typing import Optional, Dict, Any
from abstractcore import create_llm, ProviderAPIError, ModelNotFoundError, AuthenticationError

# Create a general LLMError that encompasses all AbstractCore errors
class LLMError(Exception):
    """General LLM error for the reverse notebook application."""
    pass

logger = logging.getLogger(__name__)


class LLMService:
    """Service for LLM-powered prompt to code conversion."""
    
    def __init__(self, provider: str = "lmstudio", model: str = "qwen/qwen3-next-80b"):
        """
        Initialize the LLM service.
        
        Args:
            provider: LLM provider name (default: lmstudio)
            model: Model name (default: qwen/qwen3-next-80b)
        """
        self.provider = provider
        self.model = model
        self.llm = None
        self._initialize_llm()
    
    def _initialize_llm(self):
        """Initialize the LLM client."""
        try:
            self.llm = create_llm(self.provider, model=self.model)
            logger.info(f"Initialized LLM: {self.provider}/{self.model}")
        except (ProviderAPIError, ModelNotFoundError, AuthenticationError) as e:
            logger.error(f"Failed to initialize LLM: {e}")
            raise LLMError(f"LLM initialization failed: {e}")
        except Exception as e:
            logger.error(f"Unexpected error initializing LLM: {e}")
            raise LLMError(f"Unexpected LLM initialization error: {e}")
    
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
            raise LLMError("LLM not initialized")
        
        # Build the system prompt for code generation
        system_prompt = self._build_system_prompt(context)
        
        # Construct the user prompt
        user_prompt = self._build_user_prompt(prompt, context)
        
        try:
            response = self.llm.generate(
                user_prompt,
                system_prompt=system_prompt,
                max_tokens=2000,
                temperature=0.1  # Low temperature for consistent code generation
            )
            
            # Extract code from the response
            code = self._extract_code_from_response(response.content)
            
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
- ALL data files are located in the 'data/' directory
- ALWAYS use paths like: 'data/filename.csv' 
- NEVER use bare filenames like 'filename.csv'
- The working directory is set to the project root where 'data/' exists

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

AVAILABLE LIBRARIES:
- pandas as pd
- numpy as np
- matplotlib.pyplot as plt
- plotly.express as px
- plotly.graph_objects as go
- seaborn as sns
- scipy.stats as stats
- sklearn (all modules)

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
        """Build the user prompt for code generation."""
        
        user_prompt = f"Convert this request to Python code:\n\n{prompt}\n\n"
        
        # Add context information if available
        if context:
            if 'previous_cells' in context:
                user_prompt += f"PREVIOUS CELLS CONTEXT:\n{context['previous_cells']}\n\n"
        
        user_prompt += "Generate the Python code:"
        
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
    
    def suggest_improvements(self, prompt: str, code: str, error_message: Optional[str] = None) -> str:
        """
        Suggest improvements or fixes for generated code.
        
        Args:
            prompt: Original natural language prompt
            code: Generated code that needs improvement
            error_message: Error message if code failed to execute
            
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
            improvement_prompt += f"\n\nBut it failed with this error:\n{error_message}\n\nFix the code to resolve this error."
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
