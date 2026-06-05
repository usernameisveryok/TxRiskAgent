from __future__ import annotations

from typing import Any

from .adapters.http import HttpClient
from .fixtures import TOKEN_FIXTURES
from .rpc import PublicRpcResolver
from .utils import normalize_address


ERC20_NAME_SELECTOR = "0x06fdde03"
ERC20_SYMBOL_SELECTOR = "0x95d89b41"
ERC20_DECIMALS_SELECTOR = "0x313ce567"
ERC20_TOTAL_SUPPLY_SELECTOR = "0x18160ddd"


class TokenMetadataResolver:
    def __init__(
        self,
        rpc_url: str | None = None,
        client: HttpClient | None = None,
        *,
        public_fallback: bool = False,
        rpc_resolver: PublicRpcResolver | None = None,
    ) -> None:
        self.rpc_url = rpc_url
        self.client = client or HttpClient()
        self.public_fallback = public_fallback
        self.rpc_resolver = rpc_resolver or (PublicRpcResolver(client=self.client) if public_fallback and not rpc_url else None)

    def metadata(self, chain_id: int, address: str | None, contract_reputation: dict[str, Any] | None = None) -> dict[str, Any]:
        normalized = normalize_address(address)
        base = {"chainId": f"eip155:{chain_id}", "address": normalized, "symbol": "UNKNOWN_ERC20", "decimals": 18, "sources": []}
        if not normalized:
            return {**base, "symbol": "UNKNOWN", "sources": ["invalid_address"]}

        fixture = TOKEN_FIXTURES.get((chain_id, normalized))
        if fixture:
            base.update(fixture)
            base["sources"].append("local_fixture")

        rpc = self._rpc_metadata(chain_id, normalized)
        if rpc.get("status") == "ok":
            for key in ("name", "symbol", "decimals", "totalSupplyRaw"):
                if rpc.get(key) is not None:
                    base[key] = rpc[key]
            base["sources"].append("rpc")
            base["rpcStatus"] = _rpc_status_summary(rpc)
        elif rpc.get("status") not in {None, "config_missing"}:
            base["rpcStatus"] = _rpc_status_summary(rpc)

        explorer = self._explorer_metadata(contract_reputation)
        if explorer:
            for key, value in explorer.items():
                if value is not None and base.get(key) in {None, "UNKNOWN_ERC20", "UNKNOWN"}:
                    base[key] = value
            base["sources"].append("explorer")

        if not base["sources"]:
            base["sources"].append("default")
        return base

    def _rpc_metadata(self, chain_id: int, address: str) -> dict[str, Any]:
        rpc = self._resolve_rpc(chain_id)
        rpc_url = rpc.get("url")
        if not rpc_url:
            if rpc.get("status") not in {"config_missing"}:
                return rpc
            return {"status": "config_missing"}
        result: dict[str, Any] = {
            "status": "ok",
            "rpc": {key: rpc.get(key) for key in ("source", "chainId", "url", "attempts") if rpc.get(key) is not None},
        }
        calls = {
            "name": ERC20_NAME_SELECTOR,
            "symbol": ERC20_SYMBOL_SELECTOR,
            "decimals": ERC20_DECIMALS_SELECTOR,
            "totalSupplyRaw": ERC20_TOTAL_SUPPLY_SELECTOR,
        }
        for field, selector in calls.items():
            value = self._eth_call(rpc_url, address, selector)
            if value.get("status") != "ok":
                result.setdefault("errors", {})[field] = value
                continue
            raw = value.get("result")
            if field in {"name", "symbol"}:
                result[field] = _decode_abi_string(raw)
            else:
                result[field] = _decode_uint(raw)
        return result

    def _resolve_rpc(self, chain_id: int) -> dict[str, Any]:
        if self.rpc_url:
            return {"status": "ok", "source": "explicit", "chainId": chain_id, "url": self.rpc_url, "attempts": []}
        if not self.public_fallback:
            return {"status": "config_missing"}
        if not self.rpc_resolver:
            return {"status": "config_missing"}
        return self.rpc_resolver.resolve(chain_id)

    def _eth_call(self, rpc_url: str, to: str, data: str) -> dict[str, Any]:
        try:
            response = self.client.post_json(
                rpc_url,
                payload={"jsonrpc": "2.0", "id": 1, "method": "eth_call", "params": [{"to": to, "data": data}, "latest"]},
            )
        except Exception as exc:
            return {"status": "error", "error": str(exc)}
        if response.get("error"):
            return {"status": "error", "error": response["error"]}
        return {"status": "ok", "result": response.get("result")}

    def _explorer_metadata(self, contract_reputation: dict[str, Any] | None) -> dict[str, Any]:
        if not isinstance(contract_reputation, dict):
            return {}
        for key in ("etherscan", "blockscout"):
            source = contract_reputation.get(key)
            if isinstance(source, dict) and source.get("status") == "ok":
                token_info = source.get("token", {}).get("info") if isinstance(source.get("token"), dict) else None
                if isinstance(token_info, dict):
                    return {
                        "name": token_info.get("tokenName") or source.get("contractName"),
                        "symbol": token_info.get("symbol"),
                        "decimals": _decode_uint(token_info.get("divisor")),
                        "totalSupplyRaw": _decode_uint(token_info.get("totalSupply")),
                    }
                return {"name": source.get("contractName")}
        return {}


def _decode_uint(raw: Any) -> int | None:
    if isinstance(raw, int):
        return raw
    if not isinstance(raw, str):
        return None
    try:
        if raw.startswith("0x"):
            return int(raw, 16)
        return int(raw)
    except ValueError:
        return None


def _decode_abi_string(raw: Any) -> str | None:
    if not isinstance(raw, str) or not raw.startswith("0x"):
        return None
    data = raw[2:]
    try:
        if len(data) == 64:
            return bytes.fromhex(data).rstrip(b"\x00").decode("utf-8") or None
        if len(data) >= 128:
            offset = int(data[:64], 16) * 2
            length = int(data[offset : offset + 64], 16) * 2
            return bytes.fromhex(data[offset + 64 : offset + 64 + length]).decode("utf-8") or None
    except Exception:
        return None
    return None


def _rpc_status_summary(rpc: dict[str, Any]) -> dict[str, Any]:
    summary = {key: rpc.get(key) for key in ("status", "source", "chainId", "url", "attempts", "errors") if rpc.get(key) is not None}
    nested = rpc.get("rpc")
    if isinstance(nested, dict):
        summary.update({key: nested.get(key) for key in ("source", "chainId", "url", "attempts") if nested.get(key) is not None})
    return summary
