"""
Pytest configuration for Digital Article.

Why this exists:
- A portion of the test suite imports backend modules using `backend.app.*`.
- Depending on pytest import mode / environment, the repository root may not be on `sys.path`,
  which makes `import backend...` fail during collection.

This file ensures the repo root is available on `sys.path` for all tests in a deterministic way.
"""

from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Ensure the repository root is importable (so `import backend.app...` works).
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

