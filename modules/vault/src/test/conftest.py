"""Load repository sources rather than installed hspylib distributions."""

import sys
from pathlib import Path

MODULES = Path(__file__).resolve().parents[3]
for module in ("vault", "datasource", "clitt", "hspylib"):
    sys.path.insert(0, str(MODULES / module / "src" / "main"))
