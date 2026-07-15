import os
import sys

# Make the repo root importable so `from src.scraper_facade import ...` works when
# the backend is launched from the backend/ directory (uvicorn) as well as in tests.
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
