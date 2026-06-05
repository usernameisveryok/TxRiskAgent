from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any

from ..fixtures import ADDRESS_FIXTURES
from ..utils import normalize_address
from .http import HttpClient

ETHERSCAN_CHAIN_HOSTS = {
    1: "https://api.etherscan.io/v2/api",
    10: "https://api.etherscan.io/v2/api",
    56: "https://api.etherscan.io/v2/api",
    137: "https://api.etherscan.io/v2/api",
    42161: "https://api.etherscan.io/v2/api",
    8453: "https://api.etherscan.io/v2/api",
    43114: "https://api.etherscan.io/v2/api",
}

SOURCE_SIGNAL_PATTERNS = {
    "blacklistEnabled": re.compile(r"\bblacklist|blacklisted\b", re.IGNORECASE),
    "whitelistEnabled": re.compile(r"\bwhitelist|whitelisted\b", re.IGNORECASE),
    "mintable": re.compile(r"\b(mint|issue)\s*\(", re.IGNORECASE),
    "taxMutable": re.compile(r"\b(setTax|setFee|setFees|setParams|setBuyTax|setSellTax)\s*\(", re.IGNORECASE),
    "transferPausable": re.compile(r"\b(pause|unpause|whenNotPaused|whenPaused|paused)\b", re.IGNORECASE),
    "withdrawFunction": re.compile(r"\b(withdraw|rescue|sweep|recoverERC20|recoverToken)\s*\(", re.IGNORECASE),
    "balanceMutable": re.compile(r"\b(setBalance|destroyBlackFunds|airdrop|reflect|rebase)\s*\(", re.IGNORECASE),
    "canRegainOwnership": re.compile(r"\b(claimOwnership|recoverOwnership|setOwner|takeOwnership)\s*\(", re.IGNORECASE),
    "externalCallPresent": re.compile(r"\.(call|delegatecall|staticcall)\s*\{?\(", re.IGNORECASE),
    "selfdestructPresent": re.compile(r"\b(selfdestruct|suicide)\s*\(", re.IGNORECASE),
    "antiWhaleEnabled": re.compile(r"\b(maxTx|maxWallet|antiWhale|tradingLimit)\b", re.IGNORECASE),
    "transferCooldown": re.compile(r"\b(cooldown|coolDown|transferDelay)\b", re.IGNORECASE),
}

ABI_SIGNAL_NAMES = {
    "blacklistEnabled": {"addblacklist", "removeblacklist", "blacklist", "setblacklist", "getblackliststatus"},
    "whitelistEnabled": {"addwhitelist", "removewhitelist", "setwhitelist", "iswhitelisted"},
    "mintable": {"mint", "issue"},
    "taxMutable": {"settax", "setfee", "setfees", "setparams", "setbuytax", "setselltax"},
    "transferPausable": {"pause", "unpause"},
    "withdrawFunction": {"withdraw", "rescue", "sweep", "recovererc20", "recovertoken"},
    "balanceMutable": {"setbalance", "destroyblackfunds", "airdrop", "rebase"},
    "canRegainOwnership": {"claimownership", "recoverownership", "setowner", "takeownership"},
    "antiWhaleEnabled": {"setmaxtx", "setmaxwallet", "settradinglimit", "setcooldown"},
    "transferCooldown": {"setcooldown", "settransferdelay"},
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
        etherscan = self._etherscan_report(chain_id, address)
        blockscout = self._blockscout_source(address)
        return {
            "status": "ok" if facts or etherscan.get("status") == "ok" or blockscout.get("status") == "ok" else "limited",
            "address": address,
            "facts": facts,
            "etherscan": etherscan,
            "blockscout": blockscout,
        }

    def _etherscan_report(self, chain_id: int, address: str, depth: int = 0) -> dict[str, Any]:
        if not self.etherscan_api_key:
            return {"status": "config_missing", "provider": "etherscan"}
        base_url = ETHERSCAN_CHAIN_HOSTS.get(chain_id)
        if not base_url:
            return {"status": "unsupported_chain", "provider": "etherscan", "chainId": chain_id}
        source_data = self._etherscan_request(chain_id, "contract", "getsourcecode", {"address": address})
        if source_data.get("status") == "error":
            return source_data
        result = source_data.get("result")
        first = result[0] if isinstance(result, list) and result else {}
        if not isinstance(first, dict):
            return {"status": "unexpected_response", "provider": "etherscan", "endpoint": "getsourcecode", "rawStatus": source_data.get("rawStatus"), "rawMessage": source_data.get("rawMessage")}
        source = first.get("SourceCode") or ""
        abi = _parse_abi(first.get("ABI"))
        abi_summary = _summarize_abi(abi)
        source_summary = _summarize_source(source)
        security_signals = _security_signals(source, abi_summary.get("functionNames", []))
        implementation = first.get("Implementation") or None
        implementation = normalize_address(implementation) or implementation
        implementation_report = None
        if implementation and depth == 0:
            implementation_report = self._etherscan_report(chain_id, implementation, depth + 1)

        creation = self._etherscan_contract_creation(chain_id, address) if depth == 0 else {"status": "skipped_nested_implementation"}
        account = self._etherscan_account_summary(chain_id, address) if depth == 0 else {"status": "skipped_nested_implementation"}
        token = self._etherscan_token_summary(chain_id, address) if depth == 0 else {"status": "skipped_nested_implementation"}
        nametag = self._etherscan_address_tag(chain_id, address) if depth == 0 else {"status": "skipped_nested_implementation"}
        deployed_at = creation.get("deployedAt") or account.get("firstTxAt")
        age_days = _age_days(deployed_at)
        creator = normalize_address(creation.get("contractCreator")) or creation.get("contractCreator")
        return {
            "status": "ok",
            "provider": "etherscan",
            "sourceVerified": bool(source),
            "contractName": first.get("ContractName") or None,
            "compilerVersion": first.get("CompilerVersion") or None,
            "compilerType": first.get("CompilerType") or None,
            "optimizationUsed": _truthy_string(first.get("OptimizationUsed")),
            "licenseType": first.get("LicenseType") or None,
            "similarMatch": normalize_address(first.get("SimilarMatch")) or None,
            "sourceSummary": source_summary,
            "abiSummary": abi_summary,
            "securitySignals": security_signals,
            "proxy": first.get("Proxy") == "1",
            "implementation": implementation,
            "implementationVerified": implementation_report.get("sourceVerified") if implementation_report else None,
            "implementationSourceVerified": implementation_report.get("sourceVerified") if implementation_report else None,
            "implementationReport": implementation_report,
            "creation": creation,
            "account": account,
            "token": token,
            "nametag": nametag,
            "providerLimitations": _provider_limitations(creation, account, token, nametag),
            "deployer": creator,
            "deployedAt": deployed_at,
            "ageDays": age_days,
            "owner": first.get("Owner") or None,
            "rawStatus": source_data.get("rawStatus"),
            "rawMessage": source_data.get("rawMessage"),
        }

    def _etherscan_request(self, chain_id: int | None, module: str, action: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        if not self.etherscan_api_key:
            return {"status": "config_missing", "provider": "etherscan", "endpoint": action}
        base_url = ETHERSCAN_CHAIN_HOSTS.get(chain_id or 1)
        if not base_url:
            return {"status": "unsupported_chain", "provider": "etherscan", "chainId": chain_id, "endpoint": action}
        request_params = {
            "module": module,
            "action": action,
            "apikey": self.etherscan_api_key,
        }
        if chain_id is not None:
            request_params["chainid"] = str(chain_id)
        request_params.update(params or {})
        try:
            data = self.client.get_json(base_url, params=request_params)
        except Exception as exc:
            return {"status": "error", "provider": "etherscan", "endpoint": action, "error": str(exc)}
        raw_status = data.get("status")
        raw_message = data.get("message")
        result = data.get("result")
        status = "ok" if raw_status == "1" or (raw_status is None and result is not None and result != "") else _etherscan_not_ok_status(result, raw_message)
        return {
            "status": status,
            "provider": "etherscan",
            "endpoint": action,
            "rawStatus": raw_status,
            "rawMessage": raw_message,
            "result": result,
        }

    def _etherscan_contract_creation(self, chain_id: int, address: str) -> dict[str, Any]:
        data = self._etherscan_request(chain_id, "contract", "getcontractcreation", {"contractaddresses": address})
        result = data.get("result")
        first = result[0] if isinstance(result, list) and result else {}
        if data.get("status") != "ok" or not isinstance(first, dict):
            return _compact_endpoint_status(data)
        tx_hash = first.get("txHash") or first.get("hash")
        creation = {
            "status": "ok",
            "contractCreator": normalize_address(first.get("contractCreator")) or first.get("contractCreator"),
            "txHash": tx_hash,
            "blockNumber": _int_or_none(first.get("blockNumber")),
            "rawStatus": data.get("rawStatus"),
            "rawMessage": data.get("rawMessage"),
        }
        tx = self._etherscan_tx_by_hash(chain_id, tx_hash) if tx_hash else {}
        if tx.get("status") == "ok":
            creation["blockNumber"] = creation.get("blockNumber") or tx.get("blockNumber")
            creation["deployedAt"] = tx.get("timeStamp")
            creation["creationValueWei"] = tx.get("value")
            creation["gasUsed"] = tx.get("gasUsed")
        return creation

    def _etherscan_tx_by_hash(self, chain_id: int, tx_hash: str | None) -> dict[str, Any]:
        if not tx_hash:
            return {"status": "no_tx_hash"}
        data = self._etherscan_request(chain_id, "proxy", "eth_getTransactionByHash", {"txhash": tx_hash})
        result = data.get("result")
        if data.get("status") != "ok" or not isinstance(result, dict):
            return _compact_endpoint_status(data)
        block_number = _int_or_none(result.get("blockNumber"))
        block = self._etherscan_block_by_number(chain_id, block_number) if block_number is not None else {}
        return {
            "status": "ok",
            "blockNumber": block_number,
            "timeStamp": block.get("timeStamp"),
            "from": normalize_address(result.get("from")) or result.get("from"),
            "to": normalize_address(result.get("to")) or result.get("to"),
            "value": _int_or_none(result.get("value")),
            "gas": _int_or_none(result.get("gas")),
            "gasPrice": _int_or_none(result.get("gasPrice")),
            "gasUsed": None,
        }

    def _etherscan_block_by_number(self, chain_id: int, block_number: int | None) -> dict[str, Any]:
        if block_number is None:
            return {"status": "no_block_number"}
        data = self._etherscan_request(chain_id, "proxy", "eth_getBlockByNumber", {"tag": hex(block_number), "boolean": "false"})
        result = data.get("result")
        if data.get("status") != "ok" or not isinstance(result, dict):
            return _compact_endpoint_status(data)
        return {"status": "ok", "blockNumber": block_number, "timeStamp": _timestamp_iso(_int_or_none(result.get("timestamp")))}

    def _etherscan_account_summary(self, chain_id: int, address: str) -> dict[str, Any]:
        balance_data = self._etherscan_request(chain_id, "account", "balance", {"address": address, "tag": "latest"})
        first_tx_data = self._etherscan_request(chain_id, "account", "txlist", {"address": address, "startblock": "0", "endblock": "99999999", "page": "1", "offset": "1", "sort": "asc"})
        last_tx_data = self._etherscan_request(chain_id, "account", "txlist", {"address": address, "startblock": "0", "endblock": "99999999", "page": "1", "offset": "1", "sort": "desc"})
        first_tx = _first_dict(first_tx_data.get("result"))
        last_tx = _first_dict(last_tx_data.get("result"))
        return {
            "status": "ok" if any(item.get("status") == "ok" for item in (balance_data, first_tx_data, last_tx_data)) else "limited",
            "nativeBalanceWei": _int_or_none(balance_data.get("result")) if balance_data.get("status") == "ok" else None,
            "firstTxAt": _tx_timestamp(first_tx),
            "firstTxHash": first_tx.get("hash") if first_tx else None,
            "lastTxAt": _tx_timestamp(last_tx),
            "lastTxHash": last_tx.get("hash") if last_tx else None,
            "firstTxStatus": _compact_endpoint_status(first_tx_data) if first_tx_data.get("status") != "ok" else None,
            "lastTxStatus": _compact_endpoint_status(last_tx_data) if last_tx_data.get("status") != "ok" else None,
            "balanceStatus": _compact_endpoint_status(balance_data) if balance_data.get("status") != "ok" else None,
        }

    def _etherscan_token_summary(self, chain_id: int, address: str) -> dict[str, Any]:
        supply_data = self._etherscan_request(chain_id, "stats", "tokensupply", {"contractaddress": address})
        info_data = self._etherscan_request(chain_id, "token", "tokeninfo", {"contractaddress": address})
        transfers_data = self._etherscan_request(chain_id, "account", "tokentx", {"contractaddress": address, "page": "1", "offset": "5", "sort": "desc"})
        holder_count_data = self._etherscan_request(chain_id, "token", "tokenholdercount", {"contractaddress": address})
        info = _first_dict(info_data.get("result"))
        transfers = transfers_data.get("result") if isinstance(transfers_data.get("result"), list) else []
        return {
            "status": "ok" if any(item.get("status") == "ok" for item in (supply_data, info_data, transfers_data, holder_count_data)) else "limited",
            "totalSupplyRaw": _int_or_none(supply_data.get("result")) if supply_data.get("status") == "ok" else None,
            "holderCount": _int_or_none(holder_count_data.get("result")) if holder_count_data.get("status") == "ok" else None,
            "info": _sanitize_token_info(info) if info else None,
            "recentTransfers": [_summarize_token_transfer(item) for item in transfers[:5] if isinstance(item, dict)],
            "supplyStatus": _compact_endpoint_status(supply_data) if supply_data.get("status") != "ok" else None,
            "infoStatus": _compact_endpoint_status(info_data) if info_data.get("status") != "ok" else None,
            "transferStatus": _compact_endpoint_status(transfers_data) if transfers_data.get("status") != "ok" else None,
            "holderCountStatus": _compact_endpoint_status(holder_count_data) if holder_count_data.get("status") != "ok" else None,
        }

    def _etherscan_address_tag(self, chain_id: int, address: str) -> dict[str, Any]:
        data = self._etherscan_request(chain_id, "nametag", "getaddresstag", {"address": address})
        result = data.get("result")
        first = result[0] if isinstance(result, list) and result else {}
        if data.get("status") != "ok" or not isinstance(first, dict):
            return _compact_endpoint_status(data)
        return {
            "status": "ok",
            "nametag": first.get("nametag") or None,
            "labels": first.get("labels") if isinstance(first.get("labels"), list) else [],
            "labelsSlug": first.get("labels_slug") if isinstance(first.get("labels_slug"), list) else [],
            "reputation": _int_or_none(first.get("reputation")),
            "url": first.get("url") or None,
            "lastUpdatedAt": _timestamp_iso(_int_or_none(first.get("lastupdatedtimestamp"))),
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


def _etherscan_not_ok_status(result: Any, message: Any) -> str:
    if isinstance(result, dict):
        return "ok"
    if isinstance(result, list):
        return "ok"
    text = str(result or message or "").lower()
    if "no transactions found" in text or "no records found" in text:
        return "not_found"
    if "pro" in text or "not available" in text or "subscription" in text:
        return "plan_required"
    if "invalid api key" in text:
        return "auth_error"
    return "limited"


def _parse_abi(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, str) or raw in {"", "Contract source code not verified"}:
        return []
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []


def _summarize_abi(abi: list[dict[str, Any]]) -> dict[str, Any]:
    functions = [item for item in abi if isinstance(item, dict) and item.get("type") == "function"]
    events = [item for item in abi if isinstance(item, dict) and item.get("type") == "event"]
    function_names = sorted({item.get("name") for item in functions if isinstance(item.get("name"), str)})
    event_names = sorted({item.get("name") for item in events if isinstance(item.get("name"), str)})
    return {
        "functionCount": len(functions),
        "eventCount": len(events),
        "functionNames": function_names[:80],
        "eventNames": event_names[:80],
        "truncated": len(function_names) > 80 or len(event_names) > 80,
    }


def _summarize_source(source: str) -> dict[str, Any]:
    if not source:
        return {"available": False, "bytes": 0, "sha256": None}
    lines = source.count("\n") + 1
    return {
        "available": True,
        "bytes": len(source.encode("utf-8")),
        "lines": lines,
        "sha256": sha256(source.encode("utf-8")).hexdigest(),
        "isStandardJson": source.strip().startswith("{"),
    }


def _security_signals(source: str, function_names: list[str]) -> dict[str, Any]:
    normalized_names = {name.lower() for name in function_names}
    signals: dict[str, Any] = {}
    for key, pattern in SOURCE_SIGNAL_PATTERNS.items():
        source_hit = bool(source and pattern.search(source))
        abi_hits = sorted(name for name in normalized_names if name in ABI_SIGNAL_NAMES.get(key, set()))
        signals[key] = {
            "present": source_hit or bool(abi_hits),
            "sourceKeywordHit": source_hit,
            "abiFunctionHits": abi_hits,
        }
    privileged = [
        name
        for name in function_names
        if name.lower()
        in {
            "transferownership",
            "renounceownership",
            "pause",
            "unpause",
            "setparams",
            "setfee",
            "setfees",
            "settax",
            "mint",
            "issue",
            "addblacklist",
            "removeblacklist",
            "destroyblackfunds",
            "withdraw",
            "rescue",
            "sweep",
        }
    ]
    signals["privilegedFunctionNames"] = sorted(privileged)
    return signals


def _compact_endpoint_status(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": data.get("status"),
        "provider": data.get("provider"),
        "endpoint": data.get("endpoint"),
        "rawStatus": data.get("rawStatus"),
        "rawMessage": data.get("rawMessage"),
        "resultSummary": _result_summary(data.get("result")),
        **({"error": data.get("error")} if data.get("error") else {}),
    }


def _result_summary(result: Any) -> Any:
    if isinstance(result, str):
        return result[:160]
    if isinstance(result, list):
        return {"type": "list", "count": len(result)}
    if isinstance(result, dict):
        return {"type": "dict", "keys": sorted(result)[:20]}
    return result


def _first_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, list) and value and isinstance(value[0], dict):
        return value[0]
    return {}


def _sanitize_token_info(info: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "contractAddress",
        "tokenName",
        "symbol",
        "divisor",
        "tokenType",
        "totalSupply",
        "blueCheckmark",
        "description",
        "website",
        "twitter",
        "discord",
        "telegram",
        "github",
    )
    return {key: info.get(key) for key in keys if info.get(key) not in {None, ""}}


def _summarize_token_transfer(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "hash": item.get("hash"),
        "timeStamp": _tx_timestamp(item),
        "from": normalize_address(item.get("from")) or item.get("from"),
        "to": normalize_address(item.get("to")) or item.get("to"),
        "value": item.get("value"),
        "tokenSymbol": item.get("tokenSymbol"),
    }


def _provider_limitations(*sections: dict[str, Any]) -> list[dict[str, Any]]:
    limitations = []
    for section in sections:
        if not isinstance(section, dict):
            continue
        if section.get("status") not in {None, "ok"}:
            limitations.append(_compact_endpoint_status(section))
        for value in section.values():
            if isinstance(value, dict) and value.get("status") not in {None, "ok"}:
                limitations.append(_compact_endpoint_status(value))
    return limitations


def _tx_timestamp(tx: dict[str, Any]) -> str | None:
    return _timestamp_iso(_int_or_none(tx.get("timeStamp"))) if tx else None


def _timestamp_iso(value: int | None) -> str | None:
    if value is None:
        return None
    try:
        return datetime.fromtimestamp(value, tz=timezone.utc).isoformat().replace("+00:00", "Z")
    except (OSError, OverflowError, ValueError):
        return None


def _age_days(value: Any) -> int | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return max((datetime.now(timezone.utc) - parsed).days, 0)


def _int_or_none(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    if not isinstance(value, str) or value == "":
        return None
    try:
        if value.startswith(("0x", "0X")):
            return int(value, 16)
        return int(value)
    except ValueError:
        return None


def _truthy_string(value: Any) -> bool | None:
    if value in {None, ""}:
        return None
    return str(value).lower() in {"1", "true", "yes"}
