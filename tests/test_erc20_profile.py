from __future__ import annotations

import json
from pathlib import Path

from signshield import analyze_transaction
from signshield.contract_bytecode_scanner import scan_contract_bytecode
from signshield.erc20_scoring import apply_erc20_token_profile_rules
from signshield.token_metadata import TokenMetadataResolver
from signshield.token_security_normalizer import build_erc20_token_risk_profile


ROOT = Path(__file__).resolve().parents[1]


def load_dump(name_prefix: str) -> dict:
    path = next((ROOT / "dump-tx").glob(f"{name_prefix}*.json"))
    return json.loads(path.read_text(encoding="utf-8"))


def test_token_metadata_fixture_fallback_order() -> None:
    metadata = TokenMetadataResolver().metadata(1, "0x1000000000000000000000000000000000000103", {})
    assert metadata["symbol"] == "LAB-TAX"
    assert metadata["sources"] == ["local_fixture"]

    unknown = TokenMetadataResolver().metadata(1, "0x9999999999999999999999999999999999999999", {})
    assert unknown["symbol"] == "UNKNOWN_ERC20"
    assert unknown["sources"] == ["default"]


def test_bytecode_scanner_detects_selector_and_opcode_signals() -> None:
    scan = scan_contract_bytecode(1, "0x1000000000000000000000000000000000000105")
    assert scan["status"] == "ok"
    assert scan["signals"]["blacklistEnabled"] is True
    assert scan["signals"]["whitelistEnabled"] is True
    assert scan["signals"]["externalCallPresent"] is True
    assert scan["signals"]["selfdestructPresent"] is True


def test_goplus_flags_map_to_certik_schema() -> None:
    profile = build_erc20_token_risk_profile(
        1,
        "0x9999999999999999999999999999999999999999",
        token_metadata={},
        contract_reputation={},
        bytecode_scan={},
        threat_intel={
            "providers": {
                "goplus": {
                    "tokenReports": {
                        "0x9999999999999999999999999999999999999999": {
                            "is_honeypot": "1",
                            "cannot_sell_all": "1",
                            "hidden_owner": "1",
                            "is_blacklisted": "1",
                            "sell_tax": "0.18",
                        }
                    }
                }
            }
        },
    )
    assert profile["tokenSecurity"]["hiddenOwner"] is True
    assert profile["tokenSecurity"]["blacklistEnabled"] is True
    assert profile["marketControls"]["canSell"] is False
    assert profile["marketControls"]["cannotSellAll"] is True
    assert profile["marketControls"]["sellTaxBps"] == 1800


def test_erc20_scoring_combination_rules() -> None:
    profile = {
        "tokenSecurity": {
            "hiddenOwner": True,
            "canRegainOwnership": True,
            "balanceMutable": True,
            "blacklistEnabled": True,
            "mintable": True,
            "ownershipRenounced": False,
            "isProxy": True,
            "implementationVerified": False,
            "sourceVerified": False,
            "externalCallPresent": True,
            "transferPausable": True,
        },
        "marketControls": {"canSell": False, "cannotSellAll": True, "sellTaxBps": 1800, "buyTaxBps": 100},
        "holderAndLiquidity": {"lpLockedRatio": 0.05, "topLpHolderRatio": 0.9, "top10HolderRatio": 0.85},
    }
    factors: list[dict] = []
    apply_erc20_token_profile_rules(profile, factors)
    ids = {factor["id"] for factor in factors}
    assert ids >= {
        "hidden_owner",
        "ownership_regain_backdoor",
        "balance_mutable_by_privileged_role",
        "blacklist_and_sell_restriction",
        "mintable_owner_not_renounced",
        "proxy_implementation_unverified",
        "unverified_source_external_calls",
        "honeypot",
        "lp_not_locked",
        "major_holder_concentration",
    }


def test_all_erc20_fixtures_have_token_risk_profile() -> None:
    for path in sorted((ROOT / "dump-tx").glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        result = analyze_transaction(payload)
        if result["intent"]["category"] in {"ERC20_APPROVAL", "TOKEN_TRANSFER"}:
            profile = result["evidence"]["erc20TokenRisk"]
            assert profile is not None, path.name
            assert set(profile) >= {"tokenSecurity", "marketControls", "holderAndLiquidity", "deployment", "subagentAssessments"}


def test_certik_style_erc20_fixtures_emit_expected_risk_factors() -> None:
    cases = {
        "2026-06-03T00-16": "hidden_owner",
        "2026-06-03T00-17": "mintable_owner_not_renounced",
        "2026-06-03T00-18": "high_sell_tax",
        "2026-06-03T00-19": "cannot_sell_all",
        "2026-06-03T00-20": "blacklist_and_sell_restriction",
        "2026-06-03T00-21": "proxy_implementation_unverified",
        "2026-06-03T00-22": "lp_not_locked",
    }
    for prefix, expected_factor in cases.items():
        result = analyze_transaction(load_dump(prefix))
        ids = {factor["id"] for factor in result["riskFactors"]}
        assert expected_factor in ids
