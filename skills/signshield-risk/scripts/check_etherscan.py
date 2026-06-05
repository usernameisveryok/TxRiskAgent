#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from signshield.adapters.contract_reputation import CompositeContractReputationAdapter  # noqa: E402


def main() -> int:
    api_key = os.getenv("ETHERSCAN_API_KEY")
    if not api_key:
        print(json.dumps({"status": "config_missing", "message": "Set ETHERSCAN_API_KEY in the environment."}, indent=2))
        return 2

    adapter = CompositeContractReputationAdapter(api_key)
    usage = adapter._etherscan_request(None, "getapilimit", "getapilimit")  # Script-level key smoke check.
    report = adapter.inspect(1, "0xdAC17F958D2ee523a2206206994597C13D831ec7")
    etherscan = report.get("etherscan", {})
    summary = {
        "schemaVersion": "signshield-etherscan-check/v0.1",
        "status": etherscan.get("status"),
        "sourceVerified": etherscan.get("sourceVerified"),
        "contractName": etherscan.get("contractName"),
        "deployerPresent": bool(etherscan.get("deployer")),
        "deployedAtPresent": bool(etherscan.get("deployedAt")),
        "abiFunctionCount": etherscan.get("abiSummary", {}).get("functionCount"),
        "securitySignalsPresent": sorted(
            key
            for key, value in etherscan.get("securitySignals", {}).items()
            if isinstance(value, dict) and value.get("present")
        ),
        "tokenStatus": etherscan.get("token", {}).get("status"),
        "usageStatus": usage.get("status"),
        "usage": usage.get("result") if isinstance(usage.get("result"), dict) else None,
        "providerLimitations": etherscan.get("providerLimitations", []),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["status"] == "ok" and summary["sourceVerified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
