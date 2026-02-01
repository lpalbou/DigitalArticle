"""
Version information for Digital Article package.

This module provides the single source of truth for version information.
Update both __version__ and __release_date__ when releasing new versions.
"""

__version__ = "0.3.2"
__version_info__ = tuple(map(int, __version__.split(".")))
__release_date__ = "Feb 01, 2026"

# Additional version metadata
__author__ = "Laurent-Philippe Albou"
__author_email__ = "contact@abstractcore.ai"
__description__ = "Command-line tools for Digital Article notebook application"
__url__ = "https://github.com/lpalbou/digitalarticle"
