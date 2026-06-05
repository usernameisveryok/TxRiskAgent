from __future__ import annotations

from typing import Any

from .fixtures import BYTECODE_FIXTURES


SELECTOR_HINTS = {
    "mintable": ["40c10f19", "1249c58b"],
    "blacklistEnabled": ["f9f92be4", "8f005b1d", "0e4c29f2"],
    "whitelistEnabled": ["a8f9e2d0", "9b19251a"],
    "taxMutable": ["f2fde38b", "3a7b36f4", "4f1ef286"],
    "transferPausable": ["8456cb59", "3f4ba83a"],
    "antiWhaleEnabled": ["a2e62045", "c21f1e5c"],
    "antiWhaleMutable": ["a2e62045", "c21f1e5c"],
    "withdrawFunction": ["3ccfd60b", "51cff8d9", "f3fef3a3"],
    "balanceMutable": ["27e235e3", "a9059cbb"],
    "transferCooldown": ["ce4b2f7b", "6d7f6f9a"],
    "canRegainOwnership": ["f2fde38b"],
}


def scan_contract_bytecode(chain_id: int, address: str | None, contract_reputation: dict[str, Any] | None = None) -> dict[str, Any]:
    bytecode = None
    if address:
        bytecode = BYTECODE_FIXTURES.get((chain_id, address.lower()))
    if bytecode is None and isinstance(contract_reputation, dict):
        bytecode = contract_reputation.get("bytecode")
    if not bytecode:
        return {"status": "not_available", "source": None, "signals": {}}

    clean = bytecode.lower().removeprefix("0x")
    signals: dict[str, Any] = {
        "selfdestructPresent": "ff" in clean,
        "delegatecallPresent": "f4" in clean,
        "externalCallPresent": any(op in clean for op in ("f1", "f2", "f4", "fa")),
    }
    for field, selectors in SELECTOR_HINTS.items():
        signals[field] = any(selector.lower() in clean for selector in selectors)
    return {"status": "ok", "source": "local_fixture" if address and (chain_id, address.lower()) in BYTECODE_FIXTURES else "contract_reputation", "signals": signals}
