"""
Scientific Analysis Service for generating publication-quality content.

This service analyzes notebook content and generates proper scientific article
sections including abstract, introduction, findings, and conclusions using LLM.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from ..models.notebook import Notebook, Cell, CellType
from .llm_service import LLMService

logger = logging.getLogger(__name__)


class ScientificAnalysisService:
    """Service for generating scientific article content from notebook analysis."""
    
    def __init__(self):
        self.llm_service = LLMService()
    
    def generate_scientific_content(self, notebook: Notebook) -> Dict[str, str]:
        """
        Generate comprehensive scientific content for a notebook.
        
        Args:
            notebook: The notebook to analyze
            
        Returns:
            Dictionary containing generated scientific sections
        """
        logger.info(f"Generating scientific content for notebook: {notebook.title}")
        
        # Analyze notebook content
        analysis = self._analyze_notebook_content(notebook)
        
        # Generate scientific sections using LLM
        scientific_content = self._generate_scientific_sections(notebook, analysis)
        
        logger.info("Scientific content generation completed")
        return scientific_content
    
    def _analyze_notebook_content(self, notebook: Notebook) -> Dict[str, Any]:
        """Analyze notebook content to extract COMPLETE information including all prompts, codes, and results."""
        analysis = {
            'cells_analysis': [],
            'total_cells': len(notebook.cells),
            'has_plots': False,
            'has_tables': False,
            'has_methodologies': False,
            'data_sources': set(),
            'analysis_types': set(),
            'analysis_sections': []  # For structured analysis plan
        }
        
        for i, cell in enumerate(notebook.cells, 1):
            cell_analysis = {
                'cell_number': i,
                'intent': cell.prompt or f"Cell {i} analysis",
                'full_prompt': cell.prompt or "",  # Complete prompt text
                'full_code': cell.code or "",      # Complete code
                'code_summary': self._summarize_code(cell.code) if cell.code else None,
                'has_results': bool(cell.last_result),
                'has_methodology': bool(cell.scientific_explanation),
                'methodology': cell.scientific_explanation or "",
                'full_observations': self._extract_full_observations(cell),  # Complete results
                'plots_count': len(cell.last_result.plots) if cell.last_result else 0,
                'tables_count': len(cell.last_result.tables) if cell.last_result else 0,
                'interactive_plots_count': len(cell.last_result.interactive_plots) if cell.last_result else 0,
                'stdout_output': cell.last_result.stdout if cell.last_result else "",
                'stderr_output': cell.last_result.stderr if cell.last_result else "",
                'execution_status': cell.last_result.status.value if cell.last_result else "not_executed"
            }
            
            # Update global analysis
            if cell_analysis['plots_count'] > 0 or cell_analysis['interactive_plots_count'] > 0:
                analysis['has_plots'] = True
            if cell_analysis['tables_count'] > 0:
                analysis['has_tables'] = True
            if cell_analysis['has_methodology']:
                analysis['has_methodologies'] = True
            
            # Extract data sources and analysis types from code
            if cell.code:
                self._extract_analysis_patterns(cell.code, analysis)
            
            # Identify analysis sections based on prompts
            if cell.prompt:
                section_type = self._identify_analysis_section(cell.prompt, cell.code)
                if section_type:
                    analysis['analysis_sections'].append({
                        'cell_number': i,
                        'section_type': section_type,
                        'title': self._generate_section_title(cell.prompt),
                        'prompt': cell.prompt
                    })
            
            analysis['cells_analysis'].append(cell_analysis)
        
        return analysis
    
    def _summarize_code(self, code: str) -> str:
        """Summarize what the code does."""
        if not code:
            return ""
        
        # Simple code analysis
        lines = code.lower().split('\n')
        operations = []
        
        for line in lines:
            line = line.strip()
            if 'read_csv' in line or 'load' in line:
                operations.append("data loading")
            elif 'plot' in line or 'figure' in line or 'chart' in line:
                operations.append("visualization")
            elif 'groupby' in line or 'aggregate' in line or 'sum(' in line or 'mean(' in line:
                operations.append("data aggregation")
            elif 'merge' in line or 'join' in line:
                operations.append("data joining")
            elif 'filter' in line or 'query' in line or '[' in line:
                operations.append("data filtering")
            elif 'model' in line or 'fit' in line or 'predict' in line:
                operations.append("statistical modeling")
            elif 'correlation' in line or 'corr(' in line:
                operations.append("correlation analysis")
        
        return ", ".join(set(operations)) if operations else "data processing"
    
    def _extract_observations(self, cell: Cell) -> str:
        """Extract key observations from cell results."""
        if not cell.last_result:
            return ""
        
        observations = []
        
        # Text output observations
        if cell.last_result.stdout:
            stdout_lines = cell.last_result.stdout.strip().split('\n')
            if len(stdout_lines) > 0:
                # Take first few lines as key observations
                key_output = ' '.join(stdout_lines[:3])
                if len(key_output) > 200:
                    key_output = key_output[:200] + "..."
                observations.append(f"Output: {key_output}")
        
        # Visual observations
        if cell.last_result.plots:
            observations.append(f"{len(cell.last_result.plots)} visualization(s) generated")
        
        if cell.last_result.interactive_plots:
            observations.append(f"{len(cell.last_result.interactive_plots)} interactive plot(s) created")
        
        if cell.last_result.tables:
            for table in cell.last_result.tables:
                shape = table.get('shape', [0, 0])
                observations.append(f"Table with {shape[0]} rows and {shape[1]} columns")
        
        return "; ".join(observations)
    
    def _extract_full_observations(self, cell: Cell) -> str:
        """Extract COMPLETE observations from cell results including full outputs."""
        if not cell.last_result:
            return "No execution results available"
        
        observations = []
        
        # Complete text output
        if cell.last_result.stdout:
            observations.append(f"STDOUT OUTPUT:\n{cell.last_result.stdout}")
        
        if cell.last_result.stderr:
            observations.append(f"STDERR OUTPUT:\n{cell.last_result.stderr}")
        
        # Visual elements details
        if cell.last_result.plots:
            observations.append(f"GENERATED {len(cell.last_result.plots)} STATIC PLOT(S)")
        
        if cell.last_result.interactive_plots:
            observations.append(f"GENERATED {len(cell.last_result.interactive_plots)} INTERACTIVE PLOT(S)")
        
        if cell.last_result.tables:
            for i, table in enumerate(cell.last_result.tables, 1):
                shape = table.get('shape', [0, 0])
                observations.append(f"TABLE {i}: {shape[0]} rows × {shape[1]} columns")
                # Include table data if available and not too large
                if 'data' in table and shape[0] <= 20:
                    observations.append(f"TABLE {i} DATA:\n{table['data']}")
        
        return "\n\n".join(observations) if observations else "No observable outputs"
    
    def _extract_analysis_patterns(self, code: str, analysis: Dict[str, Any]):
        """Extract analysis patterns from code."""
        code_lower = code.lower()
        
        # Data sources
        if 'csv' in code_lower:
            analysis['data_sources'].add('CSV files')
        if 'json' in code_lower:
            analysis['data_sources'].add('JSON data')
        if 'database' in code_lower or 'sql' in code_lower:
            analysis['data_sources'].add('Database')
        
        # Analysis types
        if 'correlation' in code_lower:
            analysis['analysis_types'].add('correlation analysis')
        if 'regression' in code_lower:
            analysis['analysis_types'].add('regression analysis')
        if 'cluster' in code_lower:
            analysis['analysis_types'].add('clustering')
        if 'classification' in code_lower:
            analysis['analysis_types'].add('classification')
        if 'plot' in code_lower or 'chart' in code_lower:
            analysis['analysis_types'].add('data visualization')
        if 'statistics' in code_lower or 'describe' in code_lower:
            analysis['analysis_types'].add('descriptive statistics')
    
    def _identify_analysis_section(self, prompt: str, code: str) -> Optional[str]:
        """Identify the type of analysis section based on prompt and code."""
        prompt_lower = prompt.lower()
        code_lower = code.lower() if code else ""
        
        # Data loading/preparation
        if any(keyword in prompt_lower for keyword in ['load', 'import', 'read', 'data']):
            if any(keyword in code_lower for keyword in ['read_csv', 'load', 'import']):
                return "data_preparation"
        
        # Exploratory analysis
        if any(keyword in prompt_lower for keyword in ['explore', 'summary', 'describe', 'overview']):
            return "exploratory_analysis"
        
        # Statistical analysis
        if any(keyword in prompt_lower for keyword in ['correlation', 'regression', 'test', 'statistical']):
            return "statistical_analysis"
        
        # Visualization
        if any(keyword in prompt_lower for keyword in ['plot', 'chart', 'visualize', 'graph']):
            return "visualization"
        
        # Modeling
        if any(keyword in prompt_lower for keyword in ['model', 'predict', 'machine learning', 'classification']):
            return "modeling"
        
        # Results/conclusions
        if any(keyword in prompt_lower for keyword in ['result', 'conclusion', 'finding', 'summary']):
            return "results"
        
        return "general_analysis"
    
    def _generate_section_title(self, prompt: str) -> str:
        """Generate a scientific section title from a prompt."""
        # Simple title generation - could be enhanced with LLM
        prompt_clean = prompt.strip().capitalize()
        if len(prompt_clean) > 60:
            prompt_clean = prompt_clean[:60] + "..."
        return prompt_clean
    
    def _generate_scientific_sections(self, notebook: Notebook, analysis: Dict[str, Any]) -> Dict[str, str]:
        """Generate scientific sections using LLM."""
        
        # Prepare context for LLM
        context = self._build_llm_context(notebook, analysis)
        
        # Generate each section
        sections = {}
        
        # Generate global findings and conclusions
        sections['findings_conclusions'] = self._generate_findings_conclusions(context)
        
        # Generate abstract
        sections['abstract'] = self._generate_abstract(context, sections['findings_conclusions'])
        
        # Generate introduction
        sections['introduction'] = self._generate_introduction(context)
        
        # Generate analysis plan
        sections['analysis_plan'] = self.generate_analysis_plan(notebook)
        
        return sections
    
    def generate_scientific_methodology_sections(self, notebook: Notebook) -> List[Dict[str, str]]:
        """Generate scientific methodology sections for each cell/prompt."""
        analysis = self._analyze_notebook_content(notebook)
        sections = []
        
        for cell_analysis in analysis['cells_analysis']:
            if cell_analysis['full_prompt']:  # Only process cells with prompts
                section_content = self._generate_cell_scientific_section(cell_analysis, notebook.title)
                sections.append({
                    'cell_number': cell_analysis['cell_number'],
                    'title': self._generate_scientific_section_title(cell_analysis['full_prompt']),
                    'content': section_content,
                    'has_methodology': cell_analysis['has_methodology'],
                    'original_methodology': cell_analysis['methodology']
                })
        
        return sections
    
    def _generate_cell_scientific_section(self, cell_analysis: Dict[str, Any], notebook_title: str) -> str:
        """Generate scientific section content for a single cell."""
        prompt = f"""You are writing a methodology section for a scientific paper titled "{notebook_title}".

Transform the following computational analysis cell into a professional scientific methodology section:

ORIGINAL USER PROMPT: "{cell_analysis['full_prompt']}"

EXECUTED CODE:
```python
{cell_analysis['full_code']}
```

EXECUTION RESULTS:
{cell_analysis['full_observations']}

EXISTING METHODOLOGY (if any):
{cell_analysis['methodology']}

Write a scientific methodology section that:
1. **DESCRIBES THE APPROACH**: Explain what analytical approach was taken and why
2. **DETAILS THE METHODS**: Describe the computational methods, statistical techniques, or analytical procedures used
3. **EXPLAINS THE IMPLEMENTATION**: Discuss how the analysis was implemented (tools, libraries, parameters)
4. **JUSTIFIES THE APPROACH**: Explain why this method was appropriate for addressing the research question
5. **REFERENCES OUTPUTS**: Mention the types of outputs generated (visualizations, tables, statistical measures)

REQUIREMENTS:
- Write in third person, past tense
- Use scientific language appropriate for a methodology section
- Be specific about the computational approaches used
- Integrate any existing methodology content
- Focus on the "how" and "why" of the analysis
- Avoid repeating results - focus on methods

Write 1-2 paragraphs in professional scientific style."""

        try:
            response = self.llm_service.generate_text(prompt)
            return response.strip() if response else f"Computational analysis was performed to address the research objective: {cell_analysis['intent']}"
        except Exception as e:
            logger.error(f"Failed to generate scientific section for cell {cell_analysis['cell_number']}: {e}")
            return f"Computational analysis was performed using Python-based methods to {cell_analysis['intent'].lower()}. The implementation involved data processing and analytical techniques appropriate for the research objectives."
    
    def _generate_scientific_section_title(self, prompt: str) -> str:
        """Generate a scientific section title from a user prompt."""
        title_prompt = f"""Convert this user prompt into a professional scientific section title (2-8 words):

User Prompt: "{prompt}"

Generate a concise, professional section title that would be appropriate for a scientific methodology section. Examples:
- "Data Preparation and Cleaning"
- "Statistical Analysis of Correlations" 
- "Visualization of Temporal Patterns"
- "Regression Model Development"

Return only the title, no explanation."""

        try:
            response = self.llm_service.generate_text(title_prompt)
            title = response.strip() if response else self._generate_section_title(prompt)
            # Clean up the title
            title = title.replace('"', '').replace("'", '').strip()
            return title
        except Exception as e:
            logger.error(f"Failed to generate scientific section title: {e}")
            return self._generate_section_title(prompt)
    
    def _build_llm_context(self, notebook: Notebook, analysis: Dict[str, Any]) -> str:
        """Build COMPREHENSIVE context for LLM with ALL prompts, codes, and results."""
        context_parts = [
            "=" * 80,
            "COMPLETE DIGITAL ARTICLE CONTEXT FOR SCIENTIFIC ANALYSIS",
            "=" * 80,
            f"Title: {notebook.title}",
            f"Description: {notebook.description}",
            f"Author: {notebook.author}",
            f"Total Cells: {analysis['total_cells']}",
            f"Created: {notebook.created_at}",
            f"Last Updated: {notebook.updated_at}",
            ""
        ]
        
        # Analysis overview
        if analysis['data_sources']:
            context_parts.append(f"Data Sources Identified: {', '.join(analysis['data_sources'])}")
        
        if analysis['analysis_types']:
            context_parts.append(f"Analysis Types: {', '.join(analysis['analysis_types'])}")
        
        if analysis['analysis_sections']:
            context_parts.append(f"Analysis Sections Identified: {len(analysis['analysis_sections'])}")
            for section in analysis['analysis_sections']:
                context_parts.append(f"  - {section['section_type']}: {section['title']}")
        
        context_parts.extend([
            "",
            "=" * 80,
            "COMPLETE CELL-BY-CELL ANALYSIS WITH FULL CONTEXT",
            "=" * 80
        ])
        
        for cell_analysis in analysis['cells_analysis']:
            context_parts.extend([
                "",
                f"{'=' * 20} CELL {cell_analysis['cell_number']} {'=' * 20}",
                ""
            ])
            
            # Full prompt
            if cell_analysis['full_prompt']:
                context_parts.extend([
                    "ORIGINAL PROMPT (User Intent):",
                    f'"{cell_analysis["full_prompt"]}"',
                    ""
                ])
            
            # Full code
            if cell_analysis['full_code']:
                context_parts.extend([
                    "GENERATED/EXECUTED CODE:",
                    "```python",
                    cell_analysis['full_code'],
                    "```",
                    ""
                ])
            
            # Execution status
            context_parts.append(f"EXECUTION STATUS: {cell_analysis['execution_status']}")
            
            # Complete results
            if cell_analysis['full_observations']:
                context_parts.extend([
                    "",
                    "COMPLETE EXECUTION RESULTS:",
                    cell_analysis['full_observations'],
                    ""
                ])
            
            # Scientific methodology if available
            if cell_analysis['methodology']:
                context_parts.extend([
                    "SCIENTIFIC METHODOLOGY/EXPLANATION:",
                    cell_analysis['methodology'],
                    ""
                ])
            
            # Visual elements summary
            visual_summary = []
            if cell_analysis['plots_count'] > 0:
                visual_summary.append(f"{cell_analysis['plots_count']} static plot(s)")
            if cell_analysis['interactive_plots_count'] > 0:
                visual_summary.append(f"{cell_analysis['interactive_plots_count']} interactive plot(s)")
            if cell_analysis['tables_count'] > 0:
                visual_summary.append(f"{cell_analysis['tables_count']} data table(s)")
            
            if visual_summary:
                context_parts.extend([
                    f"VISUAL OUTPUTS: {', '.join(visual_summary)}",
                    ""
                ])
        
        context_parts.extend([
            "",
            "=" * 80,
            "END OF COMPLETE CONTEXT",
            "=" * 80
        ])
        
        return '\n'.join(context_parts)
    
    def _generate_findings_conclusions(self, context: str) -> str:
        """Generate global findings and conclusions based on complete context."""
        prompt = f"""You are a scientific researcher writing the findings and conclusions section of a research article. 

You have been provided with COMPLETE CONTEXT including all user prompts, generated code, execution results, and outputs from a computational analysis study.

{context}

Based on this COMPLETE ANALYSIS, write a comprehensive "Findings and Conclusions" section that:

1. **SYNTHESIZES KEY FINDINGS**: Identify and synthesize the most important discoveries from across ALL cells, referencing specific results, numbers, patterns, and visualizations that were actually generated.

2. **DRAWS MEANINGFUL CONCLUSIONS**: Connect the findings to broader implications, explaining what these results mean in the context of the research domain.

3. **REFERENCES SPECIFIC EVIDENCE**: Cite specific outputs, numerical results, visualizations, and tables that support your conclusions. Use phrases like "As shown in the analysis..." or "The generated visualization revealed..."

4. **ADDRESSES LIMITATIONS**: Acknowledge any limitations in the methodology, data, or analysis approach that were evident from the execution results.

5. **SUGGESTS IMPLICATIONS**: Discuss what these findings mean for the field, future research, or practical applications.

CRITICAL REQUIREMENTS:
- Base your analysis ONLY on what was actually executed and observed in the cells
- Reference specific numerical results, patterns, and visualizations that were generated
- Write in past tense using scientific language
- Be specific rather than generic - avoid statements that could apply to any study
- Ensure conclusions are supported by the actual evidence from the analysis

Write 3-5 paragraphs in professional scientific style."""

        try:
            response = self.llm_service.generate_text(prompt)
            return response.strip() if response else "Comprehensive analysis of findings and conclusions from the digital article investigation."
        except Exception as e:
            logger.error(f"Failed to generate findings and conclusions: {e}")
            return "Comprehensive analysis of findings and conclusions from the digital article investigation."
    
    def _generate_abstract(self, context: str, findings: str) -> str:
        """Generate scientific abstract based on complete context and findings."""
        prompt = f"""You are writing a scientific abstract for a computational research study. You have access to the COMPLETE CONTEXT of the analysis and the synthesized findings.

COMPLETE ANALYSIS CONTEXT:
{context}

SYNTHESIZED FINDINGS AND CONCLUSIONS:
{findings}

Write a scientific abstract (150-250 words) that follows standard academic format and includes:

1. **BACKGROUND/OBJECTIVE**: What specific problem or research question was addressed? (Based on the actual prompts and analysis performed)

2. **METHODS**: What computational methods, data sources, and analytical approaches were actually used? (Reference the specific techniques from the executed code)

3. **RESULTS**: What were the key quantitative and qualitative findings? (Reference specific numbers, patterns, visualizations that were generated)

4. **CONCLUSIONS**: What are the main implications and significance of these results?

CRITICAL REQUIREMENTS:
- Write in third person, past tense
- Be SPECIFIC to this analysis - reference actual data sources, methods, and results
- Avoid generic statements that could apply to any study
- Include specific domain context inferred from the analysis
- Reference concrete findings (numbers, patterns, relationships) that were discovered
- Use precise scientific language
- Ensure the abstract accurately reflects what was actually done and found

The abstract should read like it's for a real scientific paper, not a generic template."""

        try:
            response = self.llm_service.generate_text(prompt)
            return response.strip() if response else "This digital article presents a comprehensive computational analysis with data-driven insights and methodological approaches to address key research questions in the domain."
        except Exception as e:
            logger.error(f"Failed to generate abstract: {e}")
            return "This digital article presents a comprehensive computational analysis with data-driven insights and methodological approaches to address key research questions in the domain."
    
    def _generate_introduction(self, context: str) -> str:
        """Generate scientific introduction with analysis plan based on complete context."""
        prompt = f"""You are writing the introduction section for a scientific research article. You have access to the COMPLETE CONTEXT of a computational analysis study.

COMPLETE ANALYSIS CONTEXT:
{context}

Write a comprehensive introduction (3-5 paragraphs) that:

1. **ESTABLISHES THE RESEARCH DOMAIN**: Based on the actual data sources, analysis types, and prompts, identify and introduce the specific research domain/field this work addresses.

2. **DEFINES THE PROBLEM**: Articulate the specific research problem or questions that motivated this analysis, inferred from the user prompts and analytical approach.

3. **PROVIDES CONTEXT AND BACKGROUND**: Discuss why this type of analysis is important in the identified domain, referencing the complexity or challenges that computational approaches can address.

4. **DESCRIBES THE ANALYTICAL APPROACH**: Outline the systematic approach taken in this study, creating a clear analysis plan with sections based on the actual cell progression:
   - Data preparation and exploration phases
   - Statistical analysis components  
   - Visualization and interpretation methods
   - Any modeling or advanced analytical techniques used

5. **SETS EXPECTATIONS**: Explain what insights the reader can expect to gain and how the analysis contributes to understanding in this domain.

CRITICAL REQUIREMENTS:
- Infer the specific research domain from the actual data and analysis performed
- Create a logical analysis plan that reflects the actual sequence and types of analyses conducted
- Reference the specific methodological approaches that were actually used
- Write in scholarly, scientific language appropriate for the inferred domain
- Ensure the introduction logically leads to the methodology section
- Be specific to this analysis rather than generic

The introduction should read like it's from a real research paper in the appropriate scientific domain."""

        try:
            response = self.llm_service.generate_text(prompt)
            return response.strip() if response else "This investigation addresses important questions through computational analysis and data-driven methodologies, providing insights into complex patterns and relationships within the studied domain."
        except Exception as e:
            logger.error(f"Failed to generate introduction: {e}")
            return "This investigation addresses important questions through computational analysis and data-driven methodologies, providing insights into complex patterns and relationships within the studied domain."
    
    def generate_analysis_plan(self, notebook: Notebook) -> Dict[str, Any]:
        """Generate a structured analysis plan based on the notebook content."""
        analysis = self._analyze_notebook_content(notebook)
        context = self._build_llm_context(notebook, analysis)
        
        plan_prompt = f"""Based on the complete analysis context, create a structured analysis plan that organizes the work into logical scientific sections.

{context}

Create a structured analysis plan with:
1. Section titles that reflect the actual analytical progression
2. Brief descriptions of what each section accomplishes
3. Mapping of cells to appropriate sections

Return the plan as a structured format suitable for a scientific methodology section."""

        try:
            plan_response = self.llm_service.generate_text(plan_prompt)
            return {
                'analysis_plan': plan_response.strip() if plan_response else "Systematic computational analysis approach",
                'sections': analysis.get('analysis_sections', [])
            }
        except Exception as e:
            logger.error(f"Failed to generate analysis plan: {e}")
            return {
                'analysis_plan': "Systematic computational analysis approach with data exploration, statistical analysis, and visualization components.",
                'sections': analysis.get('analysis_sections', [])
            }
