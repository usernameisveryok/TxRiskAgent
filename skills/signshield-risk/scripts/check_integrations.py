#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from signshield.adapters.contract_reputation import CompositeContractReputationAdapter  # noqa: E402
from signshield.adapters.threat_intel import CompositeThreatIntelAdapter  # noqa: E402
from signshield.rpc import check_public_rpc_endpoints  # noqa: E402


def main() -> int:
    etherscan_key = os.getenv("ETHERSCAN_API_KEY")
    contract_adapter = CompositeContractReputationAdapter(etherscan_key, os.getenv("BLOCKSCOUT_BASE_URL"))
    threat_adapter = CompositeThreatIntelAdapter()
    checks = {
        "publicRpc": check_public_rpc_endpoints(),
        "etherscan": contract_adapter.inspect(1, "0xdac17f958d2ee523a2206206994597c13d831ec7").get("etherscan", {}),
        "goplusMetamask": threat_adapter.inspect(1, ["0xdac17f958d2ee523a2206206994597c13d831ec7"], "https://app.uniswap.org"),
    }
    print(json.dumps(redact(checks), ensure_ascii=False, indent=2))
    return 0


def redact(value):
    if isinstance(value, dict):
        return {key: redact(item) for key, item in value.items() if key not in {"SourceCode", "apikey"}}
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value


if __name__ == "__main__":
    raise SystemExit(main())
