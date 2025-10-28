"""
Token Tracker Service - Uses ONLY AbstractCore's actual token counts.

This service tracks real token usage from AbstractCore's response.usage field.
NO estimation or guessing - only real data from the LLM provider.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
from collections import defaultdict

logger = logging.getLogger(__name__)


class TokenTracker:
    """
    Track actual token usage and generation time from AbstractCore GenerateResponse.

    This service relies ENTIRELY on AbstractCore providing:
    - input_tokens/prompt_tokens: Input tokens (context + user prompt)
    - output_tokens/completion_tokens: Output tokens (generated code)
    - total_tokens: Sum of both
    - gen_time: Generation time in milliseconds (AbstractCore 2.5.2+)

    NO custom estimation logic - only real counts from LLM.
    """

    def __init__(self):
        """Initialize token tracker with empty state."""
        # Notebook-level tracking: notebook_id -> usage stats
        self._notebook_usage: Dict[str, Dict[str, Any]] = {}

        # Cell-level tracking: cell_id -> usage stats
        self._cell_usage: Dict[str, Dict[str, Any]] = {}

        # Session start time
        self._session_start = datetime.now()

        logger.info("✅ TokenTracker initialized (using AbstractCore response.usage only)")

    def track_generation(
        self,
        notebook_id: str,
        cell_id: str,
        usage_data: Optional[Dict[str, int]],
        generation_time_ms: Optional[float] = None
    ) -> None:
        """
        Track token usage and generation time from an AbstractCore response.

        Args:
            notebook_id: ID of the notebook
            cell_id: ID of the cell
            usage_data: The response.usage dict from AbstractCore
                       Expected: {'input_tokens': int, 'output_tokens': int, 'total_tokens': int}
                       Or legacy: {'prompt_tokens': int, 'completion_tokens': int, 'total_tokens': int}
            generation_time_ms: Generation time in milliseconds (from response.gen_time)

        Note:
            If usage_data is None or missing required fields, logs warning but doesn't fail.
            This handles cases where providers don't return usage data.
        """
        if not usage_data:
            logger.warning(f"⚠️ No usage data provided for cell {cell_id} - LLM provider may not support token counting")
            return

        # Support both new and legacy field names from AbstractCore 2.5.2+
        # New format: input_tokens, output_tokens, total_tokens
        # Legacy format: prompt_tokens, completion_tokens, total_tokens
        input_tokens = usage_data.get('input_tokens') or usage_data.get('prompt_tokens')
        output_tokens = usage_data.get('output_tokens') or usage_data.get('completion_tokens')
        total_tokens = usage_data.get('total_tokens')

        if input_tokens is None or output_tokens is None or total_tokens is None:
            logger.warning(
                f"⚠️ Usage data missing required token fields for cell {cell_id}. "
                f"Got: {list(usage_data.keys())}"
            )
            return

        # Track by notebook (cumulative)
        if notebook_id not in self._notebook_usage:
            self._notebook_usage[notebook_id] = {
                'input_tokens': 0,
                'output_tokens': 0,
                'total_tokens': 0,
                'total_generation_time_ms': 0.0,
                'generations': 0,
                'cells': set(),
                'last_updated': None
            }

        nb_usage = self._notebook_usage[notebook_id]
        nb_usage['input_tokens'] += input_tokens
        nb_usage['output_tokens'] += output_tokens
        nb_usage['total_tokens'] += total_tokens
        nb_usage['generations'] += 1
        nb_usage['cells'].add(cell_id)
        nb_usage['last_updated'] = datetime.now()
        
        # Add generation time if provided
        if generation_time_ms is not None:
            nb_usage['total_generation_time_ms'] += generation_time_ms

        # Track by cell (latest generation)
        self._cell_usage[cell_id] = {
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
            'total_tokens': total_tokens,
            'generation_time_ms': generation_time_ms,
            'timestamp': datetime.now(),
            'notebook_id': notebook_id
        }

        logger.info(
            f"📊 Tracked generation for cell {cell_id}: "
            f"input={input_tokens}, output={output_tokens}, total={total_tokens}"
            f"{f', time={generation_time_ms}ms' if generation_time_ms else ''}"
        )

    def get_notebook_usage(self, notebook_id: str) -> Dict[str, Any]:
        """
        Get cumulative token usage and generation time for a notebook.

        Args:
            notebook_id: ID of the notebook

        Returns:
            Dict with:
            - input_tokens: Total input tokens across all generations
            - output_tokens: Total output tokens
            - total_tokens: Sum of both
            - total_generation_time_ms: Total generation time in milliseconds
            - avg_generation_time_ms: Average generation time per call
            - generations: Number of LLM calls
            - cells_with_generations: Number of cells with tracked generations
            - last_updated: Timestamp of last generation

        Note:
            Returns zero usage if notebook has no tracked generations.
        """
        usage = self._notebook_usage.get(notebook_id)

        if not usage:
            return {
                'input_tokens': 0,
                'output_tokens': 0,
                'total_tokens': 0,
                'total_generation_time_ms': 0.0,
                'avg_generation_time_ms': 0.0,
                'generations': 0,
                'cells_with_generations': 0,
                'last_updated': None
            }

        # Calculate average generation time
        avg_time = (usage['total_generation_time_ms'] / usage['generations']) if usage['generations'] > 0 else 0.0

        # Convert set to count for JSON serialization
        return {
            'input_tokens': usage['input_tokens'],
            'output_tokens': usage['output_tokens'],
            'total_tokens': usage['total_tokens'],
            'total_generation_time_ms': usage['total_generation_time_ms'],
            'avg_generation_time_ms': round(avg_time, 1),
            'generations': usage['generations'],
            'cells_with_generations': len(usage['cells']),
            'last_updated': usage['last_updated'].isoformat() if usage['last_updated'] else None
        }

    def get_cell_usage(self, cell_id: str) -> Optional[Dict[str, Any]]:
        """
        Get token usage and generation time for a specific cell's latest generation.

        Args:
            cell_id: ID of the cell

        Returns:
            Dict with usage data or None if cell has no tracked generation
        """
        usage = self._cell_usage.get(cell_id)

        if not usage:
            return None

        return {
            'input_tokens': usage['input_tokens'],
            'output_tokens': usage['output_tokens'],
            'total_tokens': usage['total_tokens'],
            'generation_time_ms': usage['generation_time_ms'],
            'timestamp': usage['timestamp'].isoformat(),
            'notebook_id': usage['notebook_id']
        }

    def get_current_context_tokens(self, notebook_id: str) -> int:
        """
        Get the ACTUAL context tokens used in the last generation.

        This returns the prompt_tokens from the most recent generation,
        which represents the actual context size that was sent to the LLM.

        Args:
            notebook_id: ID of the notebook

        Returns:
            Number of prompt tokens from last generation, or 0 if no generations yet

        Note:
            This is the REAL context size as measured by the LLM provider,
            not an estimate. It includes system prompt + previous cells + current prompt.
        """
        logger.info(f"🔍 get_current_context_tokens called for notebook {notebook_id}")
        logger.info(f"🔍 Available notebook_ids in tracker: {list(self._notebook_usage.keys())}")
        logger.info(f"🔍 Available cell_ids in tracker: {list(self._cell_usage.keys())}")

        usage = self._notebook_usage.get(notebook_id)
        logger.info(f"🔍 Notebook usage: {usage}")

        if not usage or not usage.get('last_updated'):
            logger.warning(f"⚠️ No usage data for notebook {notebook_id}")
            return 0

        # Find the most recent cell for this notebook
        recent_cell = None
        recent_time = None

        for cell_id, cell_usage in self._cell_usage.items():
            if cell_usage['notebook_id'] == notebook_id:
                logger.info(f"🔍 Found cell {cell_id} for notebook {notebook_id}: {cell_usage}")
                if recent_time is None or cell_usage['timestamp'] > recent_time:
                    recent_time = cell_usage['timestamp']
                    recent_cell = cell_usage

        if recent_cell:
            logger.info(f"✅ Returning {recent_cell['input_tokens']} tokens from most recent cell")
            return recent_cell['input_tokens']

        logger.warning(f"⚠️ No cells found for notebook {notebook_id}")
        return 0

    def reset_notebook(self, notebook_id: str) -> None:
        """
        Reset token tracking for a notebook.

        Args:
            notebook_id: ID of the notebook to reset

        Note:
            Cell-level usage is preserved for history.
        """
        if notebook_id in self._notebook_usage:
            logger.info(f"♻️ Resetting token tracking for notebook {notebook_id}")
            del self._notebook_usage[notebook_id]

    def get_session_summary(self) -> Dict[str, Any]:
        """
        Get summary of token usage and generation time across all notebooks in this session.

        Returns:
            Dict with total usage stats and per-notebook breakdown
        """
        total_input = sum(nb['input_tokens'] for nb in self._notebook_usage.values())
        total_output = sum(nb['output_tokens'] for nb in self._notebook_usage.values())
        total_tokens = sum(nb['total_tokens'] for nb in self._notebook_usage.values())
        total_time = sum(nb['total_generation_time_ms'] for nb in self._notebook_usage.values())
        total_generations = sum(nb['generations'] for nb in self._notebook_usage.values())

        return {
            'session_start': self._session_start.isoformat(),
            'total_input_tokens': total_input,
            'total_output_tokens': total_output,
            'total_tokens': total_tokens,
            'total_generation_time_ms': total_time,
            'avg_generation_time_ms': round(total_time / total_generations, 1) if total_generations > 0 else 0.0,
            'total_generations': total_generations,
            'notebooks_tracked': len(self._notebook_usage),
            'cells_tracked': len(self._cell_usage)
        }
