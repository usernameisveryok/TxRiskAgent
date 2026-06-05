from __future__ import annotations

from typing import Any

from .http import HttpClient


class SourcifyOpenChainResolver:
    """Resolve 4-byte selectors through Sourcify's OpenChain-compatible API."""

    def __init__(self, client: HttpClient | None = None, base_url: str = "https://api.4byte.sourcify.dev") -> None:
        self.client = client or HttpClient()
        self.base_url = base_url.rstrip("/")

    def resolve(self, selector: str) -> dict[str, Any] | None:
        if not selector.startswith("0x") or len(selector) != 10:
            return None
        try:
            data = self.client.get_json(
                f"{self.base_url}/signature-database/v1/lookup",
                params={"function": selector},
            )
        except Exception as exc:
            return {"source": "sourcify_openchain", "status": "error", "selector": selector, "error": str(exc)}

        result = data.get("result") if isinstance(data.get("result"), dict) else data
        functions = result.get("function") or result.get("functions") or {}
        candidates = _extract_candidates(functions, selector)
        if not candidates:
            return {"source": "sourcify_openchain", "status": "not_found", "selector": selector}
        return {
            "source": "sourcify_openchain",
            "status": "resolved",
            "selector": selector,
            "signature": candidates[0],
            "candidates": candidates[:10],
        }


class FourByteDirectoryResolver:
    """Resolve selectors through the legacy 4byte.directory REST API."""

    def __init__(self, client: HttpClient | None = None, base_url: str = "https://www.4byte.directory") -> None:
        self.client = client or HttpClient()
        self.base_url = base_url.rstrip("/")

    def resolve(self, selector: str) -> dict[str, Any] | None:
        if not selector.startswith("0x") or len(selector) != 10:
            return None
        try:
            data = self.client.get_json(
                f"{self.base_url}/api/v1/signatures/",
                params={"hex_signature": selector, "ordering": "created_at"},
            )
        except Exception as exc:
            return {"source": "4byte_directory", "status": "error", "selector": selector, "error": str(exc)}
        results = data.get("results") if isinstance(data.get("results"), list) else []
        candidates = [item.get("text_signature") for item in results if isinstance(item, dict) and item.get("text_signature")]
        if not candidates:
            return {"source": "4byte_directory", "status": "not_found", "selector": selector}
        return {
            "source": "4byte_directory",
            "status": "resolved",
            "selector": selector,
            "signature": candidates[0],
            "candidates": candidates[:10],
        }


class CombinedCalldataResolver:
    def __init__(self, resolvers: list[Any]) -> None:
        self.resolvers = resolvers

    def resolve(self, selector: str) -> dict[str, Any] | None:
        attempts: list[dict[str, Any]] = []
        for resolver in self.resolvers:
            result = resolver.resolve(selector)
            if not result:
                continue
            attempts.append(result)
            if result.get("status") == "resolved" and result.get("signature"):
                if attempts[:-1]:
                    result = {**result, "attempts": attempts}
                return result
        if attempts:
            return {"source": "combined_calldata_resolver", "status": "not_found", "selector": selector, "attempts": attempts}
        return None


def _extract_candidates(functions: Any, selector: str) -> list[str]:
    if isinstance(functions, dict):
        raw = functions.get(selector) or functions.get(selector.lower()) or functions.get(selector[2:]) or []
        if isinstance(raw, list):
            candidates: list[str] = []
            for item in raw:
                if isinstance(item, str):
                    candidates.append(item)
                elif isinstance(item, dict):
                    sig = item.get("name") or item.get("signature") or item.get("text_signature")
                    if sig:
                        candidates.append(str(sig))
            return candidates
        if isinstance(raw, str):
            return [raw]
    if isinstance(functions, list):
        candidates: list[str] = []
        for item in functions:
            if isinstance(item, str):
                candidates.append(item)
            elif isinstance(item, dict):
                sig = item.get("name") or item.get("signature") or item.get("text_signature")
                if sig:
                    candidates.append(str(sig))
        return candidates
    return []
