from __future__ import annotations

from typing import Any


def recommended_action(level: str, factors: list[dict[str, Any]]) -> str:
    factor_ids = {factor["id"] for factor in factors}
    if level == "CRITICAL":
        return "REJECT"
    if "known_malicious_spender" in factor_ids:
        return "REJECT"
    if "erc20_approval" in factor_ids or "large_or_unbounded_allowance" in factor_ids:
        return "REDUCE_ALLOWANCE"
    if level == "HIGH":
        return "REJECT"
    if level == "MEDIUM":
        return "CONTINUE_WITH_CAUTION"
    return "CONTINUE"
