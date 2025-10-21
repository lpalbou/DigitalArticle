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
    Track actual token usage from AbstractCore GenerateResponse.usage.

    This service relies ENTIRELY on AbstractCore providing:
    - prompt_tokens: Input tokens (context + user prompt)
    - completion_tokens: Output tokens (generated code)
    - total_tokens: Sum of both

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
        usage_data: Optional[Dict[str, int]]
    ) -> None:
        """
        Track token usage from an AbstractCore response.

        Args:
            notebook_id: ID of the notebook
            cell_id: ID of the cell
            usage_data: The response.usage dict from AbstractCore
                       Expected: {'prompt_tokens': int, 'completion_tokens': int, 'total_tokens': int}

        Note:
            If usage_data is None or missing required fields, logs warning but doesn't fail.
            This handles cases where providers don't return usage data.
        """
        if not usage_data:
            logger.warning(f"⚠️ No usage data provided for cell {cell_id} - LLM provider may not support token counting")
            return

        # Validate required fields
        required_fields = ['prompt_tokens', 'completion_tokens', 'total_tokens']
        missing_fields = [f for f in required_fields if f not in usage_data]

        if missing_fields:
            logger.warning(
                f"⚠️ Usage data missing fields {missing_fields} for cell {cell_id}. "
                f"Got: {list(usage_data.keys())}"
            )
            return

        prompt_tokens = usage_data['prompt_tokens']
        completion_tokens = usage_data['completion_tokens']
        total_tokens = usage_data['total_tokens']

        # Track by notebook (cumulative)
        if notebook_id not in self._notebook_usage:
            self._notebook_usage[notebook_id] = {
                'prompt_tokens': 0,
                'completion_tokens': 0,
                'total_tokens': 0,
                'generations': 0,
                'cells': set(),
                'last_updated': None
            }

        nb_usage = self._notebook_usage[notebook_id]
        nb_usage['prompt_tokens'] += prompt_tokens
        nb_usage['completion_tokens'] += completion_tokens
        nb_usage['total_tokens'] += total_tokens
        nb_usage['generations'] += 1
        nb_usage['cells'].add(cell_id)
        nb_usage['last_updated'] = datetime.now()

        # Track by cell (latest generation)
        self._cell_usage[cell_id] = {
            'prompt_tokens': prompt_tokens,
            'completion_tokens': completion_tokens,
            'total_tokens': total_tokens,
            'timestamp': datetime.now(),
            'notebook_id': notebook_id
        }

        logger.info(
            f"📊 Tracked generation for cell {cell_id}: "
            f"prompt={prompt_tokens}, completion={completion_tokens}, total={total_tokens}"
        )

    def get_notebook_usage(self, notebook_id: str) -> Dict[str, Any]:
        """
        Get cumulative token usage for a notebook.

        Args:
            notebook_id: ID of the notebook

        Returns:
            Dict with:
            - prompt_tokens: Total input tokens across all generations
            - completion_tokens: Total output tokens
            - total_tokens: Sum of both
            - generations: Number of LLM calls
            - cells_with_generations: Number of cells with tracked generations
            - last_updated: Timestamp of last generation

        Note:
            Returns zero usage if notebook has no tracked generations.
        """
        usage = self._notebook_usage.get(notebook_id)

        if not usage:
            return {
                'prompt_tokens': 0,
                'completion_tokens': 0,
                'total_tokens': 0,
                'generations': 0,
                'cells_with_generations': 0,
                'last_updated': None
            }

        # Convert set to count for JSON serialization
        return {
            'prompt_tokens': usage['prompt_tokens'],
            'completion_tokens': usage['completion_tokens'],
            'total_tokens': usage['total_tokens'],
            'generations': usage['generations'],
            'cells_with_generations': len(usage['cells']),
            'last_updated': usage['last_updated'].isoformat() if usage['last_updated'] else None
        }

    def get_cell_usage(self, cell_id: str) -> Optional[Dict[str, Any]]:
        """
        Get token usage for a specific cell's latest generation.

        Args:
            cell_id: ID of the cell

        Returns:
            Dict with usage data or None if cell has no tracked generation
        """
        usage = self._cell_usage.get(cell_id)

        if not usage:
            return None

        return {
            'prompt_tokens': usage['prompt_tokens'],
            'completion_tokens': usage['completion_tokens'],
            'total_tokens': usage['total_tokens'],
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
            logger.info(f"✅ Returning {recent_cell['prompt_tokens']} tokens from most recent cell")
            return recent_cell['prompt_tokens']

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
        Get summary of token usage across all notebooks in this session.

        Returns:
            Dict with total usage stats and per-notebook breakdown
        """
        total_prompt = sum(nb['prompt_tokens'] for nb in self._notebook_usage.values())
        total_completion = sum(nb['completion_tokens'] for nb in self._notebook_usage.values())
        total_tokens = sum(nb['total_tokens'] for nb in self._notebook_usage.values())
        total_generations = sum(nb['generations'] for nb in self._notebook_usage.values())

        return {
            'session_start': self._session_start.isoformat(),
            'total_prompt_tokens': total_prompt,
            'total_completion_tokens': total_completion,
            'total_tokens': total_tokens,
            'total_generations': total_generations,
            'notebooks_tracked': len(self._notebook_usage),
            'cells_tracked': len(self._cell_usage)
        }
