from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "skills" / "signshield-risk" / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))
