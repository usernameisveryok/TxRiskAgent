from __future__ import annotations

from copy import deepcopy
from typing import Any

from .fixtures import TOKEN_RISK_FIXTURES


def default_erc20_token_risk() -> dict[str, Any]:
    return {
        "tokenSecurity": {
            "sourceVerified": None,
            "isProxy": None,
            "implementationVerified": None,
            "ownershipRenounced": None,
            "hiddenOwner": None,
            "canRegainOwnership": None,
            "mintable": None,
            "blacklistEnabled": None,
            "whitelistEnabled": None,
            "taxMutable": None,
            "balanceMutable": None,
            "withdrawFunction": None,
            "selfdestructPresent": None,
            "externalCallPresent": None,
            "transferPausable": None,
            "transferCooldown": None,
        },
        "marketControls": {
            "buyTaxBps": None,
            "sellTaxBps": None,
            "canBuy": None,
            "canSell": None,
            "cannotSellAll": None,
            "antiWhaleEnabled": None,
            "antiWhaleMutable": None,
        },
        "holderAndLiquidity": {
            "majorHolderRatio": None,
            "top10HolderRatio": None,
            "lpLockedRatio": None,
            "topLpHolderRatio": None,
        },
        "deployment": {
            "deployedAt": None,
            "ageDays": None,
            "deployer": None,
            "owner": None,
            "dexPair": None,
        },
        "metadata": {},
        "bytecodeScan": {},
        "subagentAssessments": [],
        "sources": [],
    }


def build_erc20_token_risk_profile(
    chain_id: int,
    token_address: str | None,
    *,
    token_metadata: dict[str, Any] | None,
    contract_reputation: dict[str, Any] | None,
    threat_intel: dict[str, Any] | None,
    bytecode_scan: dict[str, Any] | None,
) -> dict[str, Any]:
    profile = default_erc20_token_risk()
    if token_metadata:
        profile["metadata"] = token_metadata
    if token_address:
        fixture = TOKEN_RISK_FIXTURES.get((chain_id, token_address.lower()))
        if fixture:
            _deep_merge(profile, fixture)
            profile["sources"].append("local_token_risk_fixture")

    _merge_contract_reputation(profile, contract_reputation)
    _merge_goplus(profile, token_address, threat_intel)
    _merge_bytecode(profile, bytecode_scan)
    return profile


def _merge_contract_reputation(profile: dict[str, Any], contract_reputation: dict[str, Any] | None) -> None:
    if not isinstance(contract_reputation, dict):
        return
    profile["sources"].append("contract_reputation")
    for source_key in ("etherscan", "blockscout"):
        source = contract_reputation.get(source_key)
        if not isinstance(source, dict) or source.get("status") != "ok":
            continue
        _set_if_missing(profile["tokenSecurity"], "sourceVerified", source.get("sourceVerified"))
        _set_if_missing(profile["tokenSecurity"], "isProxy", source.get("proxy"))
        _set_if_missing(profile["tokenSecurity"], "implementationVerified", source.get("implementationVerified"))
        if source.get("implementation") and profile["tokenSecurity"].get("implementationVerified") is None:
            profile["tokenSecurity"]["implementationVerified"] = source.get("implementationSourceVerified")
        _set_if_missing(profile["deployment"], "deployer", source.get("deployer"))
        _set_if_missing(profile["deployment"], "deployedAt", source.get("deployedAt"))
        _set_if_missing(profile["deployment"], "ageDays", source.get("ageDays"))
        _set_if_missing(profile["deployment"], "owner", source.get("owner"))
        security_signals = source.get("securitySignals")
        if isinstance(security_signals, dict):
            _merge_security_signals(profile, security_signals)


def _merge_goplus(profile: dict[str, Any], token_address: str | None, threat_intel: dict[str, Any] | None) -> None:
    if not token_address or not isinstance(threat_intel, dict):
        return
    reports = threat_intel.get("providers", {}).get("goplus", {}).get("tokenReports", {})
    report = reports.get(token_address.lower()) if isinstance(reports, dict) else None
    if not isinstance(report, dict):
        return
    profile["sources"].append("goplus")
    mapping = {
        "is_honeypot": ("marketControls", "canSell", lambda v: False if _truthy(v) else None),
        "cannot_sell_all": ("marketControls", "cannotSellAll", _truthy),
        "hidden_owner": ("tokenSecurity", "hiddenOwner", _truthy),
        "is_proxy": ("tokenSecurity", "isProxy", _truthy),
        "is_blacklisted": ("tokenSecurity", "blacklistEnabled", _truthy),
        "is_whitelisted": ("tokenSecurity", "whitelistEnabled", _truthy),
        "is_mintable": ("tokenSecurity", "mintable", _truthy),
        "can_take_back_ownership": ("tokenSecurity", "canRegainOwnership", _truthy),
        "selfdestruct": ("tokenSecurity", "selfdestructPresent", _truthy),
        "external_call": ("tokenSecurity", "externalCallPresent", _truthy),
        "trading_cooldown": ("tokenSecurity", "transferCooldown", _truthy),
        "is_anti_whale": ("marketControls", "antiWhaleEnabled", _truthy),
    }
    for source_key, (section, target_key, transform) in mapping.items():
        if source_key in report:
            value = transform(report.get(source_key))
            if value is not None:
                profile[section][target_key] = value
    if report.get("buy_tax") not in {None, ""}:
        profile["marketControls"]["buyTaxBps"] = _tax_to_bps(report.get("buy_tax"))
    if report.get("sell_tax") not in {None, ""}:
        profile["marketControls"]["sellTaxBps"] = _tax_to_bps(report.get("sell_tax"))
    if profile["marketControls"].get("canSell") is None and report.get("is_honeypot") is not None:
        profile["marketControls"]["canSell"] = not _truthy(report.get("is_honeypot"))


def _merge_bytecode(profile: dict[str, Any], bytecode_scan: dict[str, Any] | None) -> None:
    if not isinstance(bytecode_scan, dict) or bytecode_scan.get("status") != "ok":
        profile["bytecodeScan"] = bytecode_scan or {}
        return
    profile["sources"].append("bytecode_scan")
    profile["bytecodeScan"] = bytecode_scan
    signals = bytecode_scan.get("signals", {})
    signal_mapping = {
        "selfdestructPresent": ("tokenSecurity", "selfdestructPresent"),
        "externalCallPresent": ("tokenSecurity", "externalCallPresent"),
        "mintable": ("tokenSecurity", "mintable"),
        "blacklistEnabled": ("tokenSecurity", "blacklistEnabled"),
        "whitelistEnabled": ("tokenSecurity", "whitelistEnabled"),
        "taxMutable": ("tokenSecurity", "taxMutable"),
        "transferPausable": ("tokenSecurity", "transferPausable"),
        "transferCooldown": ("tokenSecurity", "transferCooldown"),
        "withdrawFunction": ("tokenSecurity", "withdrawFunction"),
        "balanceMutable": ("tokenSecurity", "balanceMutable"),
        "canRegainOwnership": ("tokenSecurity", "canRegainOwnership"),
        "antiWhaleEnabled": ("marketControls", "antiWhaleEnabled"),
        "antiWhaleMutable": ("marketControls", "antiWhaleMutable"),
    }
    for source_key, (section, target_key) in signal_mapping.items():
        if signals.get(source_key):
            profile[section][target_key] = True


def _merge_security_signals(profile: dict[str, Any], security_signals: dict[str, Any]) -> None:
    signal_mapping = {
        "selfdestructPresent": ("tokenSecurity", "selfdestructPresent"),
        "externalCallPresent": ("tokenSecurity", "externalCallPresent"),
        "mintable": ("tokenSecurity", "mintable"),
        "blacklistEnabled": ("tokenSecurity", "blacklistEnabled"),
        "whitelistEnabled": ("tokenSecurity", "whitelistEnabled"),
        "taxMutable": ("tokenSecurity", "taxMutable"),
        "transferPausable": ("tokenSecurity", "transferPausable"),
        "transferCooldown": ("tokenSecurity", "transferCooldown"),
        "withdrawFunction": ("tokenSecurity", "withdrawFunction"),
        "balanceMutable": ("tokenSecurity", "balanceMutable"),
        "canRegainOwnership": ("tokenSecurity", "canRegainOwnership"),
        "antiWhaleEnabled": ("marketControls", "antiWhaleEnabled"),
    }
    for source_key, (section, target_key) in signal_mapping.items():
        signal = security_signals.get(source_key)
        if isinstance(signal, dict) and signal.get("present"):
            profile[section][target_key] = True


def _deep_merge(target: dict[str, Any], source: dict[str, Any]) -> None:
    for key, value in source.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _deep_merge(target[key], value)
        else:
            target[key] = deepcopy(value)


def _set_if_missing(target: dict[str, Any], key: str, value: Any) -> None:
    if value is not None and target.get(key) is None:
        target[key] = value


def _truthy(value: Any) -> bool:
    return value in {"1", 1, True, "true", "True", "TRUE"}


def _tax_to_bps(value: Any) -> int | None:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if numeric <= 1:
        return int(round(numeric * 10000))
    return int(round(numeric * 100))
