from __future__ import annotations

from typing import Any

from .http import HttpClient


class TenderlySimulationAdapter:
    """Tenderly Simulation API adapter.

    Requires account slug, project slug, and access key. Without them the
    adapter reports config_missing and the analyzer remains deterministic.
    """

    def __init__(
        self,
        account: str | None,
        project: str | None,
        access_key: str | None,
        client: HttpClient | None = None,
        base_url: str = "https://api.tenderly.co",
    ) -> None:
        self.account = account
        self.project = project
        self.access_key = access_key
        self.client = client or HttpClient()
        self.base_url = base_url.rstrip("/")

    def simulate(self, chain_id: int, tx: dict[str, Any]) -> dict[str, Any]:
        if not (self.account and self.project and self.access_key):
            return {"status": "config_missing", "provider": "tenderly", "facts": []}

        payload = {
            "network_id": str(chain_id),
            "from": tx.get("from"),
            "to": tx.get("to"),
            "input": tx.get("data") or "0x",
            "value": tx.get("value") or "0x0",
            "gas": _hex_to_decimal_string(tx.get("gas")),
            "save": False,
            "save_if_fails": False,
            "simulation_type": "quick",
        }
        payload = {key: value for key, value in payload.items() if value is not None}
        headers = {"X-Access-Key": self.access_key}
        try:
            data = self.client.post_json(
                f"{self.base_url}/api/v1/account/{self.account}/project/{self.project}/simulate",
                payload=payload,
                headers=headers,
            )
        except Exception as exc:
            return {"status": "error", "provider": "tenderly", "error": str(exc), "facts": []}

        simulation = data.get("simulation") if isinstance(data.get("simulation"), dict) else data
        facts = _extract_simulation_facts(simulation)
        return {"status": "ok", "provider": "tenderly", "facts": facts, "rawSummary": _summarize_simulation(simulation)}


def _hex_to_decimal_string(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        try:
            return str(int(value, 16) if value.startswith(("0x", "0X")) else int(value))
        except ValueError:
            return None
    return None


def _extract_simulation_facts(simulation: dict[str, Any]) -> list[dict[str, Any]]:
    facts: list[dict[str, Any]] = []
    if not isinstance(simulation, dict):
        return facts
    status = simulation.get("status")
    if status is False or simulation.get("error_message"):
        facts.append({"type": "revert_or_error", "message": simulation.get("error_message") or simulation.get("error")})
    for key in ("asset_changes", "balance_diff", "balance_diffs"):
        value = simulation.get(key)
        if value:
            facts.append({"type": key, "value": value})
    tx_info = simulation.get("transaction") if isinstance(simulation.get("transaction"), dict) else {}
    if tx_info.get("call_trace"):
        facts.append({"type": "call_trace_present", "value": True})
    return facts


def _summarize_simulation(simulation: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(simulation, dict):
        return {}
    return {
        "id": simulation.get("id"),
        "status": simulation.get("status"),
        "error": simulation.get("error") or simulation.get("error_message"),
        "gasUsed": simulation.get("gas_used"),
    }
