from __future__ import annotations

from typing import Any

from signshield.adapters.calldata_resolver import CombinedCalldataResolver, FourByteDirectoryResolver, SourcifyOpenChainResolver
from signshield.adapters.contract_reputation import CompositeContractReputationAdapter
from signshield.adapters.simulation import TenderlySimulationAdapter
from signshield.adapters.threat_intel import CompositeThreatIntelAdapter


class FakeClient:
    def __init__(self, responses: dict[str, dict[str, Any]]) -> None:
        self.responses = responses
        self.calls: list[tuple[str, str, dict[str, Any] | None]] = []

    def get_json(self, url: str, *, params: dict[str, Any] | None = None, headers: dict[str, str] | None = None) -> dict[str, Any]:
        self.calls.append(("GET", url, params))
        for key, response in self.responses.items():
            if key in url:
                return response
        return {}

    def post_json(self, url: str, *, payload: dict[str, Any], headers: dict[str, str] | None = None) -> dict[str, Any]:
        self.calls.append(("POST", url, payload))
        for key, response in self.responses.items():
            if key in url:
                return response
        return {}


def test_sourcify_openchain_resolver_extracts_signature() -> None:
    client = FakeClient({"signature-database": {"result": {"function": {"0x12345678": [{"name": "doThing(uint256)", "hasVerifiedContract": True}]}}}})
    resolver = SourcifyOpenChainResolver(client=client)
    result = resolver.resolve("0x12345678")
    assert result["status"] == "resolved"
    assert result["signature"] == "doThing(uint256)"


def test_fourbyte_resolver_extracts_signature() -> None:
    client = FakeClient({"signatures": {"results": [{"text_signature": "doThing(uint256)"}]}})
    resolver = FourByteDirectoryResolver(client=client)
    result = resolver.resolve("0x12345678")
    assert result["status"] == "resolved"
    assert result["signature"] == "doThing(uint256)"


def test_combined_resolver_falls_back() -> None:
    first = FourByteDirectoryResolver(client=FakeClient({"signatures": {"results": []}}))
    second = SourcifyOpenChainResolver(client=FakeClient({"signature-database": {"result": {"function": {"0x12345678": ["fallback()"]}}}}))
    result = CombinedCalldataResolver([first, second]).resolve("0x12345678")
    assert result["signature"] == "fallback()"
    assert result["attempts"][0]["status"] == "not_found"


def test_tenderly_config_missing_and_response_summary() -> None:
    missing = TenderlySimulationAdapter(None, None, None).simulate(1, {})
    assert missing["status"] == "config_missing"

    client = FakeClient({"simulate": {"simulation": {"id": "sim-1", "status": True, "gas_used": 21000, "asset_changes": [{"type": "Transfer"}]}}})
    result = TenderlySimulationAdapter("acct", "proj", "key", client=client).simulate(1, {"from": "0x0", "to": "0x1"})
    assert result["status"] == "ok"
    assert result["rawSummary"]["gasUsed"] == 21000
    assert result["facts"][0]["type"] == "asset_changes"


def test_contract_reputation_parses_etherscan_and_blockscout() -> None:
    client = FakeClient(
        {
            "etherscan": {"status": "1", "message": "OK", "result": [{"SourceCode": "contract A {}", "ContractName": "A", "Proxy": "1", "Implementation": "0xabc"}]},
            "smart-contracts": {"is_verified": True, "name": "A", "is_proxy": True, "implementation_address": "0xabc"},
        }
    )
    adapter = CompositeContractReputationAdapter("key", "https://blockscout.example", client=client)
    result = adapter.inspect(1, "0x0000000000000000000000000000000000000001")
    assert result["etherscan"]["sourceVerified"] is True
    assert result["etherscan"]["proxy"] is True
    assert result["blockscout"]["sourceVerified"] is True


def test_threat_intel_parses_goplus_and_metamask() -> None:
    client = FakeClient(
        {
            "token_security": {"code": 1, "result": {"0x0000000000000000000000000000000000000001": {"is_honeypot": "1"}}},
            "config.json": {"blocklist": ["phish.example"], "allowlist": []},
        }
    )
    adapter = CompositeThreatIntelAdapter(client=client)
    result = adapter.inspect(1, ["0x0000000000000000000000000000000000000001"], "https://phish.example/path")
    match_types = {match["type"] for match in result["matches"]}
    assert match_types >= {"token_security", "domain_phishing"}
