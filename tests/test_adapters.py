from __future__ import annotations

from typing import Any

from signshield.adapters.calldata_resolver import CombinedCalldataResolver, FourByteDirectoryResolver, SourcifyOpenChainResolver
from signshield.adapters.contract_reputation import CompositeContractReputationAdapter
from signshield.adapters.simulation import TenderlySimulationAdapter
from signshield.adapters.threat_intel import CompositeThreatIntelAdapter
from signshield.analyzer import apply_contract_reputation_rules


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
    assert result["etherscan"]["implementationVerified"] is True
    assert result["blockscout"]["sourceVerified"] is True


def test_contract_reputation_recurses_into_unverified_implementation() -> None:
    class SequentialClient(FakeClient):
        def __init__(self) -> None:
            super().__init__({})
            self.etherscan_calls = 0

        def get_json(self, url: str, *, params: dict[str, Any] | None = None, headers: dict[str, str] | None = None) -> dict[str, Any]:
            if "etherscan" in url:
                self.etherscan_calls += 1
                if self.etherscan_calls == 1:
                    return {"status": "1", "result": [{"SourceCode": "proxy", "ContractName": "Proxy", "Proxy": "1", "Implementation": "0x00000000000000000000000000000000000000ab"}]}
                return {"status": "1", "result": [{"SourceCode": "", "ContractName": "Impl", "Proxy": "0", "Implementation": ""}]}
            return {}

    adapter = CompositeContractReputationAdapter("key", None, client=SequentialClient())
    result = adapter.inspect(1, "0x0000000000000000000000000000000000000001")
    assert result["etherscan"]["implementation"] == "0x00000000000000000000000000000000000000ab"
    assert result["etherscan"]["implementationVerified"] is False


def test_etherscan_report_collects_security_and_deployment_facts() -> None:
    class ActionClient(FakeClient):
        def __init__(self) -> None:
            super().__init__({})

        def get_json(self, url: str, *, params: dict[str, Any] | None = None, headers: dict[str, str] | None = None) -> dict[str, Any]:
            self.calls.append(("GET", url, params))
            action = params["action"] if params else None
            if action == "getsourcecode":
                return {
                    "status": "1",
                    "message": "OK",
                    "result": [
                        {
                            "SourceCode": "contract Risky { function pause() public {} function mint(address,uint256) public {} function selfdestructNow() public { selfdestruct(payable(msg.sender)); } }",
                            "ABI": '[{"type":"function","name":"pause","inputs":[]},{"type":"function","name":"mint","inputs":[{"type":"address"},{"type":"uint256"}]}]',
                            "ContractName": "Risky",
                            "CompilerVersion": "v0.8.20",
                            "OptimizationUsed": "1",
                            "LicenseType": "MIT",
                            "Proxy": "0",
                            "Implementation": "",
                            "SimilarMatch": "0x0000000000000000000000000000000000000002",
                        }
                    ],
                }
            if action == "getcontractcreation":
                return {"status": "1", "message": "OK", "result": [{"contractCreator": "0x00000000000000000000000000000000000000aa", "txHash": "0xcreate"}]}
            if action == "eth_getTransactionByHash":
                return {"result": {"blockNumber": "0x10", "from": "0x00000000000000000000000000000000000000aa", "to": None, "value": "0x0", "gas": "0x5208", "gasPrice": "0x1"}}
            if action == "eth_getBlockByNumber":
                return {"result": {"timestamp": "0x5f5e100"}}
            if action == "balance":
                return {"status": "1", "message": "OK", "result": "123"}
            if action == "txlist":
                return {"status": "1", "message": "OK", "result": [{"hash": "0xtx", "timeStamp": "100000000"}]}
            if action == "tokentx":
                return {"status": "1", "message": "OK", "result": [{"hash": "0xtoken", "timeStamp": "100000001", "from": "0x00000000000000000000000000000000000000aa", "to": "0x00000000000000000000000000000000000000bb", "value": "5", "tokenSymbol": "RISK"}]}
            if action in {"tokeninfo", "tokenholdercount"}:
                return {"status": "0", "message": "NOTOK", "result": "Sorry, it looks like you are trying to access an API Pro endpoint. Contact us to upgrade to API Pro."}
            if action == "getaddresstag":
                return {"status": "1", "message": "OK", "result": [{"nametag": "Fake_Phishing", "labels": ["Phish / Hack"], "labels_slug": ["phish-hack"], "reputation": "2"}]}
            return {}

    result = CompositeContractReputationAdapter("key", None, client=ActionClient()).inspect(1, "0x0000000000000000000000000000000000000001")
    etherscan = result["etherscan"]
    assert etherscan["sourceVerified"] is True
    assert etherscan["deployer"] == "0x00000000000000000000000000000000000000aa"
    assert etherscan["deployedAt"] == "1973-03-03T09:46:40Z"
    assert etherscan["abiSummary"]["functionCount"] == 2
    assert etherscan["securitySignals"]["mintable"]["present"] is True
    assert etherscan["securitySignals"]["transferPausable"]["present"] is True
    assert etherscan["securitySignals"]["selfdestructPresent"]["present"] is True
    assert etherscan["token"]["recentTransfers"][0]["tokenSymbol"] == "RISK"
    assert etherscan["providerLimitations"]

    factors: list[dict[str, Any]] = []
    apply_contract_reputation_rules(result, factors)
    ids = {factor["id"] for factor in factors}
    assert "etherscan_address_security_label" in ids
    assert "etherscan_source_selfdestruct_signal" in ids


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
