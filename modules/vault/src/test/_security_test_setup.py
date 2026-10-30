"""Use repository sources for security tests and their child processes."""

import sys
from pathlib import Path


def setup_sources():
    modules = Path(__file__).resolve().parents[3]
    for module in ("vault", "datasource", "clitt", "hspylib"):
        source = str(modules / module / "src" / "main")
        if source not in sys.path:
            sys.path.insert(0, source)
