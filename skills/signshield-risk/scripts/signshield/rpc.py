from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Any
from urllib.parse import urlparse

from .adapters.http import HttpClient


@dataclass(frozen=True)
class RpcEndpoint:
    chain_id: int
    chain_name: str
    url: str
    protocol: str = "http"


PUBLIC_RPC_ENDPOINTS: tuple[RpcEndpoint, ...] = (
    RpcEndpoint(1, "Ethereum", "https://ethereum-rpc.publicnode.com"),
    RpcEndpoint(1, "Ethereum", "https://1rpc.io/eth"),
    RpcEndpoint(42161, "Arbitrum One", "https://arb1.arbitrum.io/rpc"),
    RpcEndpoint(10, "Optimism / OP Mainnet", "https://mainnet.optimism.io"),
    RpcEndpoint(8453, "Base", "https://mainnet.base.org"),
    RpcEndpoint(137, "Polygon PoS", "https://polygon.drpc.org"),
    RpcEndpoint(137, "Polygon PoS", "https://polygon.publicnode.com"),
    RpcEndpoint(137, "Polygon PoS", "https://1rpc.io/matic"),
    RpcEndpoint(56, "BNB Smart Chain", "https://bsc-dataseed.bnbchain.org"),
    RpcEndpoint(56, "BNB Smart Chain", "https://bsc-dataseed-public.bnbchain.org"),
    RpcEndpoint(56, "BNB Smart Chain", "https://bsc-dataseed.defibit.io"),
    RpcEndpoint(43114, "Avalanche C-Chain", "https://api.avax.network/ext/bc/C/rpc"),
    RpcEndpoint(43114, "Avalanche C-Chain WS", "wss://api.avax.network/ext/bc/C/ws", "ws"),
)


class PublicRpcResolver:
    def __init__(
        self,
        explicit_url: str | None = None,
        *,
        client: HttpClient | None = None,
        endpoints: tuple[RpcEndpoint, ...] = PUBLIC_RPC_ENDPOINTS,
    ) -> None:
        self.explicit_url = explicit_url
        self.client = client or HttpClient(timeout=4.0)
        self.endpoints = endpoints
        self._cache: dict[int, dict[str, Any]] = {}

    def resolve(self, chain_id: int) -> dict[str, Any]:
        if self.explicit_url:
            return {
                "status": "ok",
                "source": "explicit",
                "chainId": chain_id,
                "url": self.explicit_url,
                "attempts": [],
            }
        if chain_id in self._cache:
            return self._cache[chain_id]

        candidates = [endpoint for endpoint in self.endpoints if endpoint.chain_id == chain_id]
        if not candidates:
            result = {"status": "no_public_endpoint", "source": "public_fallback", "chainId": chain_id, "attempts": []}
            self._cache[chain_id] = result
            return result

        attempts = []
        for endpoint in candidates:
            attempt = self.probe(endpoint)
            attempts.append(attempt)
            if attempt.get("status") == "ok":
                result = {
                    "status": "ok",
                    "source": "public_fallback",
                    "chainId": chain_id,
                    "url": endpoint.url,
                    "attempts": attempts,
                }
                self._cache[chain_id] = result
                return result

        result = {"status": "unavailable", "source": "public_fallback", "chainId": chain_id, "attempts": attempts}
        self._cache[chain_id] = result
        return result

    def probe(self, endpoint: RpcEndpoint) -> dict[str, Any]:
        parsed = urlparse(endpoint.url)
        protocol = endpoint.protocol or parsed.scheme
        base = {"url": endpoint.url, "chainId": endpoint.chain_id, "chainName": endpoint.chain_name, "protocol": protocol}
        if protocol not in {"http", "https"} and parsed.scheme not in {"http", "https"}:
            return {**base, "status": "unsupported_protocol"}

        started = perf_counter()
        try:
            response = self.client.post_json(
                endpoint.url,
                payload={"jsonrpc": "2.0", "id": 1, "method": "eth_chainId", "params": []},
            )
        except Exception as exc:
            return {**base, "status": "error", "error": str(exc)}

        elapsed_ms = round((perf_counter() - started) * 1000)
        if response.get("error"):
            return {**base, "status": "error", "error": response["error"], "latencyMs": elapsed_ms}
        observed = _parse_chain_id(response.get("result"))
        if observed != endpoint.chain_id:
            return {**base, "status": "chain_mismatch", "observedChainId": observed, "latencyMs": elapsed_ms}
        return {**base, "status": "ok", "observedChainId": observed, "latencyMs": elapsed_ms}


def check_public_rpc_endpoints(*, client: HttpClient | None = None) -> list[dict[str, Any]]:
    resolver = PublicRpcResolver(client=client)
    return [resolver.probe(endpoint) for endpoint in PUBLIC_RPC_ENDPOINTS]


def _parse_chain_id(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    if not isinstance(value, str):
        return None
    try:
        if value.startswith(("0x", "0X")):
            return int(value, 16)
        return int(value)
    except ValueError:
        return None
