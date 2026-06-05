from __future__ import annotations

from typing import Any

from ..fixtures import ADDRESS_FIXTURES
from .http import HttpClient

ETHERSCAN_CHAIN_HOSTS = {
    1: "https://api.etherscan.io/v2/api",
    10: "https://api.etherscan.io/v2/api",
    56: "https://api.etherscan.io/v2/api",
    137: "https://api.etherscan.io/v2/api",
    42161: "https://api.etherscan.io/v2/api",
    8453: "https://api.etherscan.io/v2/api",
}


class CompositeContractReputationAdapter:
    def __init__(
        self,
        etherscan_api_key: str | None = None,
        blockscout_base_url: str | None = None,
        client: HttpClient | None = None,
    ) -> None:
        self.etherscan_api_key = etherscan_api_key
        self.blockscout_base_url = blockscout_base_url.rstrip("/") if blockscout_base_url else None
        self.client = client or HttpClient()

    def inspect(self, chain_id: int, address: str | None) -> dict[str, Any]:
        if not address:
            return {"status": "no_address", "facts": []}
        facts: list[dict[str, Any]] = []
        fixture = ADDRESS_FIXTURES.get((chain_id, address.lower()))
        if fixture:
            facts.append({"source": "local_demo_fixture", "address": address, **fixture})
        etherscan = self._etherscan_source(chain_id, address)
        blockscout = self._blockscout_source(address)
        return {
            "status": "ok" if facts or etherscan.get("status") == "ok" or blockscout.get("status") == "ok" else "limited",
            "address": address,
            "facts": facts,
            "etherscan": etherscan,
            "blockscout": blockscout,
        }

    def _etherscan_source(self, chain_id: int, address: str, depth: int = 0) -> dict[str, Any]:
        if not self.etherscan_api_key:
            return {"status": "config_missing", "provider": "etherscan"}
        base_url = ETHERSCAN_CHAIN_HOSTS.get(chain_id)
        if not base_url:
            return {"status": "unsupported_chain", "provider": "etherscan", "chainId": chain_id}
        try:
            data = self.client.get_json(
                base_url,
                params={
                    "chainid": str(chain_id),
                    "module": "contract",
                    "action": "getsourcecode",
                    "address": address,
                    "apikey": self.etherscan_api_key,
                },
            )
        except Exception as exc:
            return {"status": "error", "provider": "etherscan", "error": str(exc)}
        result = data.get("result")
        first = result[0] if isinstance(result, list) and result else {}
        if not isinstance(first, dict):
            return {"status": "unexpected_response", "provider": "etherscan", "raw": data}
        source = first.get("SourceCode") or ""
        implementation = first.get("Implementation") or None
        implementation_report = None
        if implementation and depth == 0:
            implementation_report = self._etherscan_source(chain_id, implementation, depth + 1)
        return {
            "status": "ok",
            "provider": "etherscan",
            "sourceVerified": bool(source),
            "contractName": first.get("ContractName") or None,
            "proxy": first.get("Proxy") == "1",
            "implementation": implementation,
            "implementationVerified": implementation_report.get("sourceVerified") if implementation_report else None,
            "implementationSourceVerified": implementation_report.get("sourceVerified") if implementation_report else None,
            "implementationReport": implementation_report,
            "deployer": first.get("Deployer") or None,
            "deployedAt": first.get("DeployedAt") or None,
            "ageDays": first.get("AgeDays") or None,
            "owner": first.get("Owner") or None,
            "rawStatus": data.get("status"),
            "rawMessage": data.get("message"),
        }

    def _blockscout_source(self, address: str, depth: int = 0) -> dict[str, Any]:
        if not self.blockscout_base_url:
            return {"status": "config_missing", "provider": "blockscout"}
        try:
            data = self.client.get_json(f"{self.blockscout_base_url}/api/v2/smart-contracts/{address}")
        except Exception as exc:
            return {"status": "error", "provider": "blockscout", "error": str(exc)}
        implementation = data.get("implementation_address")
        implementation_hash = _address_hash(implementation)
        implementation_report = None
        if implementation_hash and depth == 0:
            implementation_report = self._blockscout_source(implementation_hash, depth + 1)
        return {
            "status": "ok",
            "provider": "blockscout",
            "sourceVerified": bool(data.get("is_verified") or data.get("is_fully_verified")),
            "contractName": data.get("name"),
            "proxy": bool(data.get("is_proxy")),
            "implementation": implementation_hash,
            "implementationVerified": implementation_report.get("sourceVerified") if implementation_report else data.get("implementation_verified"),
            "implementationSourceVerified": implementation_report.get("sourceVerified") if implementation_report else data.get("implementation_verified"),
            "implementationReport": implementation_report,
            "deployer": _address_hash(data.get("creator_address_hash") or data.get("creator_address")),
            "deployedAt": data.get("creation_timestamp") or data.get("created_at"),
            "ageDays": data.get("age_days"),
            "owner": _address_hash(data.get("owner_address_hash") or data.get("owner_address")),
        }


def _address_hash(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        nested = value.get("hash") or value.get("address")
        return nested if isinstance(nested, str) else None
    return None
