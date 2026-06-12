"""Compatibility wrapper for the LumiTrace vector bootstrapper.

The old entry point still works:

    python ai_engine/generate_vectors.py --preset small

The implementation lives in `tools/bootstrap_recommender.py` so the same
interactive setup can be used by both maintainers and new users.
"""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.bootstrap_recommender import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
