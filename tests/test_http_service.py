from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import threading
import time

from fastapi.testclient import TestClient
import yaml

from signshield.http_service import create_app, http_thread_workers_from_env, options_from_env
from signshield.types import AnalysisOptions


ROOT = Path(__file__).resolve().parents[1]


class ThreadNameRuntime:
    def __init__(self) -> None:
        self.options = AnalysisOptions(live=False, mode="offline")

    def analyze(self, payload: dict, input_ref: str = "<memory>") -> dict:
        return {
            "schemaVersion": "signshield-risk/v0.2",
            "inputRef": input_ref,
            "workerThread": threading.current_thread().name,
        }


class BlockingRuntime:
    def __init__(self, delay: float = 0.1) -> None:
        self.options = AnalysisOptions(live=False, mode="offline")
        self.delay = delay
        self.active = 0
        self.max_active = 0
        self.lock = threading.Lock()

    def analyze(self, payload: dict, input_ref: str = "<memory>") -> dict:
        with self.lock:
            self.active += 1
            self.max_active = max(self.max_active, self.active)
        try:
            time.sleep(self.delay)
            return {
                "schemaVersion": "signshield-risk/v0.2",
                "inputRef": input_ref,
            }
        finally:
            with self.lock:
                self.active -= 1


def client_for_offline_service() -> TestClient:
    return TestClient(create_app(options=AnalysisOptions(live=False, mode="offline")))


def load_dump(name_prefix: str) -> dict:
    path = next((ROOT / "dump-tx").glob(f"{name_prefix}*.json"))
    return json.loads(path.read_text(encoding="utf-8"))


def test_health_reports_current_mode() -> None:
    client = TestClient(create_app(options=AnalysisOptions(live=True, mode="production")))

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "tx-risk-agent",
        "schemaVersion": "signshield-risk/v0.2",
        "mode": "production",
    }


def test_tx_scan_returns_risk_report_and_request_id() -> None:
    client = client_for_offline_service()

    response = client.post("/tx-scan", json=load_dump("2026-06-02T11-14"))

    body = response.json()
    request_id = response.headers["X-Request-Id"]
    assert response.status_code == 200
    assert request_id
    assert body["schemaVersion"] == "signshield-risk/v0.2"
    assert body["inputRef"] == f"http:tx-scan:{request_id}"
    assert body["verdict"]["riskLevel"] == "HIGH"
    assert body["intent"]["category"] == "NATIVE_TRANSFER"


def test_tx_scan_runs_analyzer_in_configured_thread_pool() -> None:
    client = TestClient(create_app(runtime=ThreadNameRuntime(), thread_workers=2))

    response = client.post("/tx-scan", json={"chainId": "eip155:1", "transaction": {}})

    body = response.json()
    assert response.status_code == 200
    assert body["schemaVersion"] == "signshield-risk/v0.2"
    assert body["workerThread"].startswith("tx-risk-scan")


def test_tx_scan_handles_multiple_requests_in_parallel() -> None:
    runtime = BlockingRuntime()
    client = TestClient(create_app(runtime=runtime, thread_workers=4))

    def post_scan() -> int:
        return client.post("/tx-scan", json={"chainId": "eip155:1", "transaction": {}}).status_code

    with ThreadPoolExecutor(max_workers=4) as executor:
        statuses = list(executor.map(lambda _: post_scan(), range(4)))

    assert statuses == [200, 200, 200, 200]
    assert runtime.max_active > 1


def test_tx_scan_requires_configured_api_key(monkeypatch) -> None:
    monkeypatch.setenv("TX_RISK_API_KEY", "expected-key")
    client = client_for_offline_service()

    response = client.post("/tx-scan", json=load_dump("2026-06-02T11-14"))

    body = response.json()
    assert response.status_code == 401
    assert response.headers["X-Request-Id"] == body["requestId"]
    assert body["error"] == "unauthorized"


def test_tx_scan_accepts_configured_api_key(monkeypatch) -> None:
    monkeypatch.setenv("TX_RISK_API_KEY", "expected-key")
    client = client_for_offline_service()

    response = client.post(
        "/tx-scan",
        headers={"X-API-Key": "expected-key"},
        json=load_dump("2026-06-02T11-14"),
    )

    assert response.status_code == 200
    assert response.json()["schemaVersion"] == "signshield-risk/v0.2"


def test_tx_scan_accepts_flat_transaction_payload() -> None:
    client = client_for_offline_service()

    response = client.post(
        "/tx-scan",
        json={
            "chainId": "eip155:1",
            "from": "0xb7c360aaa4c2b9f727ff934baa6ba300ccc0f284",
            "to": "0x000000000000000000000000000000000000dead",
            "value": "0x1",
            "data": "0x",
        },
    )

    body = response.json()
    assert response.status_code == 200
    assert body["schemaVersion"] == "signshield-risk/v0.2"
    assert body["intent"]["category"] == "NATIVE_TRANSFER"


def test_tx_scan_accepts_stringified_transaction_payload() -> None:
    client = client_for_offline_service()
    payload = load_dump("2026-06-02T09-47")
    payload["transaction"] = json.dumps(payload["transaction"])

    response = client.post("/tx-scan", json=payload)

    body = response.json()
    assert response.status_code == 200
    assert body["intent"]["category"] == "ERC20_APPROVAL"
    assert body["intent"]["decodedFunction"] == "approve(address,uint256)"
    assert {factor["id"] for factor in body["riskFactors"]} >= {"erc20_approval", "known_malicious_spender"}


def test_openapi_yaml_documents_tx_scan_security_and_body(monkeypatch) -> None:
    monkeypatch.setenv("TX_RISK_API_KEY", "expected-key")
    client = client_for_offline_service()

    response = client.get("/openapi.yaml")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/yaml")
    body = response.text
    assert "/tx-scan:" in body
    assert "X-API-Key" in body
    assert "requestBody:" in body
    assert "TransactionScanRequest" in body
    schema = yaml.safe_load(body)
    transaction_schema = schema["components"]["schemas"]["TransactionScanRequest"]["properties"]["transaction"]
    assert transaction_schema["type"] == "object"
    assert transaction_schema["additionalProperties"] is True
    assert "anyOf" not in transaction_schema


def test_tx_scan_rejects_non_object_json() -> None:
    client = client_for_offline_service()

    response = client.post("/tx-scan", json=["not", "an", "object"])

    body = response.json()
    assert response.status_code == 400
    assert response.headers["X-Request-Id"] == body["requestId"]
    assert body["error"] == "invalid_json"
    assert body["message"] == "Request body must be a JSON object."


def test_tx_scan_returns_unsupported_chain_as_business_result() -> None:
    client = client_for_offline_service()

    response = client.post("/tx-scan", json={"chainId": "solana:mainnet", "transaction": {}})

    body = response.json()
    assert response.status_code == 200
    assert body["schemaVersion"] == "signshield-risk/v0.2"
    assert body["verdict"]["riskLevel"] == "UNSUPPORTED"
    assert body["intent"]["category"] == "UNSUPPORTED_CHAIN"


def test_options_from_env_defaults_to_production_live(monkeypatch) -> None:
    monkeypatch.delenv("SIGNSSHIELD_HTTP_MODE", raising=False)
    monkeypatch.delenv("SIGNSSHIELD_PUBLIC_RPC_FALLBACK", raising=False)
    monkeypatch.delenv("SIGNSSHIELD_TIMEOUT", raising=False)

    options = options_from_env()

    assert options.mode == "production"
    assert options.live is True
    assert options.timeout == 30.0
    assert options.public_rpc_fallback is True
    assert options.allow_fixture_risk is False


def test_options_from_env_accepts_timeout_override(monkeypatch) -> None:
    monkeypatch.setenv("SIGNSSHIELD_TIMEOUT", "45")

    options = options_from_env()

    assert options.timeout == 45.0


def test_options_from_env_accepts_agent_loop_override(monkeypatch) -> None:
    monkeypatch.setenv("SIGNSSHIELD_AGENT_LOOP", "kimi")
    monkeypatch.setenv("SIGNSSHIELD_AGENT_LOOP_MAX_STEPS", "4")

    options = options_from_env()

    assert options.agent_loop == "kimi"
    assert options.agent_loop_max_steps == 4


def test_http_thread_workers_from_env_defaults_to_four(monkeypatch) -> None:
    monkeypatch.delenv("SIGNSSHIELD_HTTP_THREAD_WORKERS", raising=False)

    assert http_thread_workers_from_env() == 4


def test_http_thread_workers_from_env_accepts_override(monkeypatch) -> None:
    monkeypatch.setenv("SIGNSSHIELD_HTTP_THREAD_WORKERS", "2")

    assert http_thread_workers_from_env() == 2


def test_http_thread_workers_from_env_caps_at_four(monkeypatch) -> None:
    monkeypatch.setenv("SIGNSSHIELD_HTTP_THREAD_WORKERS", "8")

    assert http_thread_workers_from_env() == 4


def test_http_thread_workers_from_env_enforces_minimum_one(monkeypatch) -> None:
    monkeypatch.setenv("SIGNSSHIELD_HTTP_THREAD_WORKERS", "0")

    assert http_thread_workers_from_env() == 1


def test_http_thread_workers_from_env_ignores_invalid_override(monkeypatch) -> None:
    monkeypatch.setenv("SIGNSSHIELD_HTTP_THREAD_WORKERS", "not-an-int")

    assert http_thread_workers_from_env() == 4
