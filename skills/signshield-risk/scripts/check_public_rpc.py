#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from signshield.rpc import check_public_rpc_endpoints  # noqa: E402


def main() -> int:
    results = check_public_rpc_endpoints()
    print(json.dumps({"schemaVersion": "signshield-public-rpc-check/v0.1", "results": results}, ensure_ascii=False, indent=2))
    return 0 if any(result.get("status") == "ok" for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
