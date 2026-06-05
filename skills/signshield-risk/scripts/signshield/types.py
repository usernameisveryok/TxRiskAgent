from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class ChainRef:
    supported: bool
    raw: Any
    chain_id: int | None
    caip2: str | None
    name: str | None


@dataclass(frozen=True)
class AnalysisOptions:
    live: bool = False
    timeout: float = 8.0
    tenderly_account: str | None = None
    tenderly_project: str | None = None
    tenderly_access_key: str | None = None
    etherscan_api_key: str | None = None
    blockscout_base_url: str | None = None
    goplus_base_url: str = "https://api.gopluslabs.io"
    metamask_config_url: str = "https://raw.githubusercontent.com/MetaMask/eth-phishing-detect/main/src/config.json"


class CalldataResolver(Protocol):
    def resolve(self, selector: str) -> dict[str, Any] | None:
        ...


class SimulationAdapter(Protocol):
    def simulate(self, chain_id: int, tx: dict[str, Any]) -> dict[str, Any]:
        ...


class ContractReputationAdapter(Protocol):
    def inspect(self, chain_id: int, address: str | None) -> dict[str, Any]:
        ...


class ThreatIntelAdapter(Protocol):
    def inspect(self, chain_id: int, addresses: list[str], origin: str | None) -> dict[str, Any]:
        ...
