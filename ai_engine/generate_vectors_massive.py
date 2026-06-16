"""Large-index compatibility entry point for LumiTrace.

This legacy script now forwards to the maintained bootstrapper with a large
preset. Use it when you want a wider TMDB candidate pool and are willing to
wait longer for downloads and BERT embedding.
"""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.bootstrap_recommender import main  # noqa: E402


if __name__ == "__main__":
    if "--preset" not in sys.argv:
        sys.argv.extend(["--preset", "large"])
    raise SystemExit(main())
