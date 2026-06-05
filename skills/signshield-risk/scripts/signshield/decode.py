from __future__ import annotations

from typing import Any

from .types import CalldataResolver
from .utils import normalize_address

LOCAL_SELECTORS = {
    "0x095ea7b3": "approve(address,uint256)",
    "0xa9059cbb": "transfer(address,uint256)",
    "0x23b872dd": "transferFrom(address,address,uint256)",
    "0xa22cb465": "setApprovalForAll(address,bool)",
    "0xd505accf": "permit(address,address,uint256,uint256,uint8,bytes32,bytes32)",
    "0x5ae401dc": "multicall(uint256,bytes[])",
    "0xac9650d8": "multicall(bytes[])",
    "0x3593564c": "execute(bytes,bytes[],uint256)",
}


def word_at(data: str, index: int) -> str:
    start = 10 + index * 64
    return data[start : start + 64]


def decode_word_int(data: str, index: int) -> int:
    word = word_at(data, index)
    if len(word) != 64:
        return 0
    return int(word, 16)


def decode_word_address(data: str, index: int) -> str | None:
    word = word_at(data, index)
    if len(word) != 64:
        return None
    return normalize_address("0x" + word[-40:])


def decode_calldata(data: str | None, resolver: CalldataResolver | None = None) -> dict[str, Any]:
    if not data or data == "0x":
        return {"isEmpty": True, "selector": None, "function": None, "parameters": {}, "resolver": "empty"}
    clean = data.lower()
    selector = clean[:10] if len(clean) >= 10 else clean
    fn = LOCAL_SELECTORS.get(selector)
    resolver_result: dict[str, Any] | None = None
    if fn is None and resolver is not None and len(selector) == 10:
        resolver_result = resolver.resolve(selector)
        if resolver_result:
            fn = resolver_result.get("signature")

    params: dict[str, Any] = {}
    if fn == "approve(address,uint256)":
        params = {"spender": decode_word_address(clean, 0), "amountRaw": decode_word_int(clean, 1)}
    elif fn == "transfer(address,uint256)":
        params = {"to": decode_word_address(clean, 0), "amountRaw": decode_word_int(clean, 1)}
    elif fn == "transferFrom(address,address,uint256)":
        params = {
            "from": decode_word_address(clean, 0),
            "to": decode_word_address(clean, 1),
            "amountRaw": decode_word_int(clean, 2),
        }
    elif fn == "setApprovalForAll(address,bool)":
        params = {"operator": decode_word_address(clean, 0), "approved": bool(decode_word_int(clean, 1))}
    elif fn == "permit(address,address,uint256,uint256,uint8,bytes32,bytes32)":
        params = {
            "owner": decode_word_address(clean, 0),
            "spender": decode_word_address(clean, 1),
            "amountRaw": decode_word_int(clean, 2),
            "deadline": decode_word_int(clean, 3),
            "v": decode_word_int(clean, 4),
            "r": "0x" + word_at(clean, 5),
            "s": "0x" + word_at(clean, 6),
        }
    elif fn:
        params = {"rawArgs": clean[10:]}

    return {
        "isEmpty": False,
        "selector": selector,
        "function": fn,
        "parameters": params,
        "resolver": resolver_result or {"source": "local_selector_table" if selector in LOCAL_SELECTORS else "unresolved"},
    }
