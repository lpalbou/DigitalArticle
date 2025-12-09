"""
Execution Insights Extractor Service

Extracts rich insights from execution results to enable publication-quality
methodology generation. Analyzes tables, plots, statistical outputs, and code
to provide comprehensive context for scientific narrative generation.
"""

import re
import ast
import logging
from typing import Dict, List, Any, Optional
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class ExecutionInsightsExtractor:
    """
    Extracts rich insights from execution results including:
    - Table statistics and summaries
    - Plot metadata and descriptions
    - Statistical findings from stdout
    - Code analysis for methods used
    """

    # Statistical patterns for stdout mining
    STAT_PATTERNS = {
        'p_value': r'p[-\s]*(?:value)?[:\s=]+\s*([<>]?\s*[\d.e-]+)',
        'mean': r'(?:mean|average)[:\s=]+\s*([\d.]+)',
        'std': r'(?:std|standard deviation)[:\s=]+\s*([\d.]+)',
        'correlation': r'(?:correlation|corr|r)[:\s=]+\s*([-]?[\d.]+)',
        'r_squared': r'(?:r[²2]|r-squared)[:\s=]+\s*([\d.]+)',
        'accuracy': r'accuracy[:\s=]+\s*([\d.]+)',
        'precision': r'precision[:\s=]+\s*([\d.]+)',
        'recall': r'recall[:\s=]+\s*([\d.]+)',
        'f1_score': r'f1[-\s]score[:\s=]+\s*([\d.]+)',
    }

    @classmethod
    def extract_insights(cls, execution_result: Any, code: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Extract comprehensive insights from execution results.

        Args:
            execution_result: ExecutionResult object with tables, plots, stdout, etc.
            code: The executed Python code
            context: Optional context with available variables

        Returns:
            Dictionary with structured insights for methodology generation
        """
        insights = {
            'tables': [],
            'plots': [],
            'statistical_findings': [],
            'code_insights': {},
            'summary': ''
        }

        try:
            # Extract table insights
            if hasattr(execution_result, 'tables') and execution_result.tables:
                insights['tables'] = cls._extract_table_insights(execution_result.tables)
                logger.info(f"📊 Extracted insights from {len(insights['tables'])} table(s)")

            # Extract plot metadata
            if hasattr(execution_result, 'plots') and execution_result.plots:
                insights['plots'] = cls._extract_plot_metadata(execution_result.plots)
                logger.info(f"📈 Extracted metadata from {len(insights['plots'])} plot(s)")

            # Extract statistical findings from stdout
            if hasattr(execution_result, 'stdout') and execution_result.stdout:
                insights['statistical_findings'] = cls._extract_statistical_findings(execution_result.stdout)
                if insights['statistical_findings']:
                    logger.info(f"🔢 Found {len(insights['statistical_findings'])} statistical finding(s)")

            # Extract code insights (libraries, methods used)
            insights['code_insights'] = cls._extract_code_insights(code)

            # Build summary
            insights['summary'] = cls._build_insights_summary(insights)

        except Exception as e:
            logger.error(f"Error extracting insights: {e}")
            # Return partial insights if extraction fails
            pass

        return insights

    @classmethod
    def _extract_table_insights(cls, tables: List[Dict]) -> List[Dict]:
        """
        Extract insights from tables including shape, columns, statistics.
        """
        table_insights = []

        for table in tables:
            try:
                insight = {
                    'label': table.get('label', 'Unlabeled Table'),
                    'source': table.get('source', 'unknown'),
                    'shape': table.get('shape', [0, 0]),
                    'columns': table.get('columns', []),
                    'statistics': {},
                    'sample_data': None
                }

                # Calculate basic statistics if data is available
                if 'data' in table and table['data']:
                    try:
                        # Convert to DataFrame for analysis
                        df = pd.DataFrame(table['data'])

                        # Get numeric columns statistics
                        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
                        if numeric_cols:
                            stats = {}
                            for col in numeric_cols[:5]:  # Limit to first 5 numeric columns
                                col_stats = {
                                    'mean': round(df[col].mean(), 2) if not pd.isna(df[col].mean()) else None,
                                    'std': round(df[col].std(), 2) if not pd.isna(df[col].std()) else None,
                                    'min': round(df[col].min(), 2) if not pd.isna(df[col].min()) else None,
                                    'max': round(df[col].max(), 2) if not pd.isna(df[col].max()) else None,
                                }
                                stats[col] = {k: v for k, v in col_stats.items() if v is not None}
                            insight['statistics'] = stats

                        # Get categorical columns distributions
                        categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
                        if categorical_cols:
                            insight['categorical_distributions'] = {}
                            for col in categorical_cols[:3]:  # Limit to first 3 categorical columns
                                value_counts = df[col].value_counts().head(5).to_dict()
                                insight['categorical_distributions'][col] = value_counts

                        # Sample data (first 3 rows)
                        insight['sample_data'] = df.head(3).to_dict(orient='records')

                    except Exception as e:
                        logger.warning(f"Could not calculate statistics for table: {e}")

                table_insights.append(insight)

            except Exception as e:
                logger.warning(f"Error extracting insights from table: {e}")
                continue

        return table_insights

    @classmethod
    def _extract_plot_metadata(cls, plots: List[Any]) -> List[Dict]:
        """
        Extract metadata from plots including labels and types.
        """
        plot_metadata = []

        for idx, plot in enumerate(plots):
            try:
                metadata = {
                    'index': idx + 1,
                    'label': 'Unlabeled Plot',
                    'source': 'unknown',
                    'type': 'unknown'
                }

                # Handle both old format (string) and new format (dict)
                if isinstance(plot, dict):
                    metadata['label'] = plot.get('label', f'Figure {idx + 1}')
                    metadata['source'] = plot.get('source', 'unknown')
                elif isinstance(plot, str):
                    metadata['label'] = f'Figure {idx + 1}'

                plot_metadata.append(metadata)

            except Exception as e:
                logger.warning(f"Error extracting plot metadata: {e}")
                continue

        return plot_metadata

    @classmethod
    def _extract_statistical_findings(cls, stdout: str) -> List[Dict]:
        """
        Mine statistical findings from stdout using regex patterns.
        """
        findings = []

        for stat_type, pattern in cls.STAT_PATTERNS.items():
            matches = re.finditer(pattern, stdout, re.IGNORECASE)
            for match in matches:
                try:
                    value = match.group(1).strip()
                    findings.append({
                        'type': stat_type,
                        'value': value,
                        'context': match.group(0)
                    })
                except Exception:
                    continue

        return findings

    @classmethod
    def _extract_code_insights(cls, code: str) -> Dict[str, Any]:
        """
        Extract insights from code using AST parsing.
        """
        insights = {
            'libraries_imported': [],
            'methods_called': [],
            'plot_types': []
        }

        try:
            tree = ast.parse(code)

            # Extract imports
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        insights['libraries_imported'].append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        insights['libraries_imported'].append(node.module)

            # Extract method calls (limited to common analysis methods)
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Attribute):
                        method_name = node.func.attr
                        # Track common statistical/plotting methods
                        if method_name in ['hist', 'scatter', 'plot', 'bar', 'boxplot', 'heatmap',
                                          'mean', 'std', 'describe', 'groupby', 'pivot_table',
                                          'corr', 'ttest_ind', 'linregress', 'pca']:
                            insights['methods_called'].append(method_name)

            # Deduplicate
            insights['libraries_imported'] = list(set(insights['libraries_imported']))
            insights['methods_called'] = list(set(insights['methods_called']))

        except Exception as e:
            logger.warning(f"Could not parse code for insights: {e}")

        return insights

    @classmethod
    def _build_insights_summary(cls, insights: Dict) -> str:
        """
        Build a human-readable summary of extracted insights.
        """
        summary_parts = []

        # Tables summary
        if insights['tables']:
            table_count = len(insights['tables'])
            table_labels = [t['label'] for t in insights['tables']]
            summary_parts.append(f"{table_count} table(s) generated: {', '.join(table_labels)}")

        # Plots summary
        if insights['plots']:
            plot_count = len(insights['plots'])
            plot_labels = [p['label'] for p in insights['plots']]
            summary_parts.append(f"{plot_count} figure(s) generated: {', '.join(plot_labels)}")

        # Statistical findings summary
        if insights['statistical_findings']:
            stat_types = list(set(f['type'] for f in insights['statistical_findings']))
            summary_parts.append(f"Statistical measures computed: {', '.join(stat_types)}")

        # Methods summary
        if insights['code_insights']['methods_called']:
            methods = insights['code_insights']['methods_called'][:5]
            summary_parts.append(f"Analysis methods: {', '.join(methods)}")

        return "; ".join(summary_parts) if summary_parts else "Analysis completed"

    @classmethod
    def format_for_methodology_prompt(cls, insights: Dict) -> str:
        """
        Format extracted insights for inclusion in methodology generation prompt.

        CRITICAL: This method must NEVER raise exceptions - methodology generation
        depends on it. All formatting operations are wrapped in defensive try-except.
        """
        sections = []

        try:
            # Table details - wrap entire section for safety
            if insights.get('tables'):
                sections.append("## TABLES GENERATED:")
                for table in insights['tables']:
                    try:
                        # Defensive extraction with fallbacks
                        shape = table.get('shape', ['?', '?'])
                        cols = table.get('columns', [])[:10]  # First 10 columns
                        label = table.get('label', 'Unnamed Table')

                        table_desc = f"\n- **{label}**"
                        table_desc += f"\n  - Shape: {shape[0]} rows × {shape[1]} columns"

                        # Robust column formatting: handle any type
                        if cols:
                            try:
                                # Convert all to strings safely
                                col_strs = [str(c) if c is not None else 'None' for c in cols]
                                table_desc += f"\n  - Columns: {', '.join(col_strs)}"
                            except Exception as col_err:
                                table_desc += f"\n  - Columns: [formatting error: {type(cols).__name__}]"

                        # Statistics - defensive extraction
                        if table.get('statistics'):
                            try:
                                table_desc += "\n  - Key Statistics:"
                                for col, stats in list(table['statistics'].items())[:3]:
                                    try:
                                        # Safely format each statistic
                                        stat_pairs = []
                                        for k, v in stats.items():
                                            try:
                                                stat_pairs.append(f"{k}={v:.2f}" if isinstance(v, float) else f"{k}={v}")
                                            except:
                                                stat_pairs.append(f"{k}={v}")
                                        stat_str = ", ".join(stat_pairs)
                                        table_desc += f"\n    - {col}: {stat_str}"
                                    except Exception:
                                        continue  # Skip malformed statistics
                            except Exception:
                                pass  # Skip statistics section if corrupted

                        # Categorical distributions - defensive extraction
                        if table.get('categorical_distributions'):
                            try:
                                table_desc += "\n  - Categorical Distributions:"
                                for col, dist in table.get('categorical_distributions', {}).items():
                                    try:
                                        dist_pairs = [f"{k}: {v}" for k, v in list(dist.items())[:3]]
                                        dist_str = ", ".join(dist_pairs)
                                        table_desc += f"\n    - {col}: {dist_str}"
                                    except Exception:
                                        continue  # Skip malformed distributions
                            except Exception:
                                pass  # Skip distributions section if corrupted

                        sections.append(table_desc)

                    except Exception as table_err:
                        # Log error but continue - don't let one bad table break everything
                        sections.append(f"\n- [Table formatting error: {str(table_err)[:50]}]")

        except Exception as tables_err:
            # Even if entire tables section fails, continue with other sections
            sections.append(f"## TABLES: [Section error: {str(tables_err)[:50]}]")

        try:
            # Plot details - robust formatting
            if insights.get('plots'):
                sections.append("\n## FIGURES GENERATED:")
                for plot in insights['plots']:
                    try:
                        label = plot.get('label', 'Unnamed Figure')
                        source = plot.get('source', 'unknown')
                        plot_desc = f"\n- **{label}** (from {source})"
                        sections.append(plot_desc)
                    except Exception:
                        sections.append(f"\n- [Figure formatting error]")
        except Exception:
            sections.append("\n## FIGURES: [Section error]")

        try:
            # Statistical findings - include full context from stdout
            if insights.get('statistical_findings'):
                sections.append("\n## STATISTICAL FINDINGS:")
                for finding in insights['statistical_findings']:
                    try:
                        finding_type = finding.get('type', 'unknown')
                        finding_value = finding.get('value', 'N/A')
                        finding_context = finding.get('context', '')  # Full line context from regex match

                        # If we have rich context and it's not just the value, show the full line
                        if finding_context and finding_context != finding_value:
                            sections.append(f"\n- {finding_context}")
                        else:
                            # Fallback to type: value format
                            sections.append(f"\n- {finding_type}: {finding_value}")
                    except Exception:
                        continue  # Skip malformed findings
        except Exception:
            pass  # Statistical findings are optional

        try:
            # Code insights - libraries
            if insights.get('code_insights', {}).get('libraries_imported'):
                libs = insights['code_insights']['libraries_imported']
                if libs:
                    # Ensure all are strings
                    lib_strs = [str(lib) for lib in libs]
                    sections.append(f"\n## LIBRARIES USED: {', '.join(lib_strs)}")
        except Exception:
            pass  # Libraries are nice-to-have

        try:
            # Code insights - methods
            if insights.get('code_insights', {}).get('methods_called'):
                methods = insights['code_insights']['methods_called']
                if methods:
                    # Ensure all are strings
                    method_strs = [str(m) for m in methods]
                    sections.append(f"\n## ANALYSIS METHODS: {', '.join(method_strs)}")
        except Exception:
            pass  # Methods are nice-to-have

        # GUARANTEE: Always return a string, even if empty
        result = "\n".join(sections) if sections else "## EXECUTION COMPLETED\nCode executed successfully."
        return result
