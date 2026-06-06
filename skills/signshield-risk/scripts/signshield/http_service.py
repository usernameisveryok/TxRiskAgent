from __future__ import annotations

import os
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .runtime import DefenseRuntime
from .types import AnalysisOptions


SCHEMA_VERSION = "signshield-risk/v0.2"
SERVICE_NAME = "tx-risk-agent"
VALID_MODES = {"offline", "live-best-effort", "production"}


def create_app(*, runtime: DefenseRuntime | None = None, options: AnalysisOptions | None = None) -> FastAPI:
    effective_runtime = runtime or DefenseRuntime(options or options_from_env())
    mode = effective_runtime.options.mode or ("live-best-effort" if effective_runtime.options.live else "offline")

    app = FastAPI(title="TxRiskAgent HTTP Service", version="0.1.0")
    app.state.runtime = effective_runtime
    app.state.mode = mode

    cors_origins = _csv_env("SIGNSSHIELD_CORS_ORIGINS")
    if cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_credentials=False,
            allow_methods=["GET", "POST"],
            allow_headers=["*"],
        )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {
            "status": "ok",
            "service": SERVICE_NAME,
            "schemaVersion": SCHEMA_VERSION,
            "mode": app.state.mode,
        }

    @app.post("/tx-scan", response_model=None)
    async def tx_scan(request: Request, response: Response) -> Any:
        request_id = uuid4().hex
        response.headers["X-Request-Id"] = request_id
        try:
            payload = await request.json()
        except Exception:
            return _error_response(
                400,
                "invalid_json",
                "Request body must be a JSON object.",
                request_id,
                response,
            )

        if not isinstance(payload, dict):
            return _error_response(
                400,
                "invalid_json",
                "Request body must be a JSON object.",
                request_id,
                response,
            )

        try:
            return app.state.runtime.analyze(payload, input_ref=f"http:tx-scan:{request_id}")
        except Exception as exc:
            return _error_response(
                500,
                "internal_error",
                f"Transaction scan failed: {exc.__class__.__name__}.",
                request_id,
                response,
            )

    return app


def options_from_env() -> AnalysisOptions:
    mode = os.getenv("SIGNSSHIELD_HTTP_MODE", "production").strip() or "production"
    if mode not in VALID_MODES:
        raise ValueError(f"SIGNSSHIELD_HTTP_MODE must be one of: {', '.join(sorted(VALID_MODES))}")

    return AnalysisOptions(
        live=mode != "offline",
        mode=mode,
        tenderly_account=os.getenv("TENDERLY_ACCOUNT_SLUG"),
        tenderly_project=os.getenv("TENDERLY_PROJECT_SLUG"),
        tenderly_access_key=os.getenv("TENDERLY_ACCESS_KEY"),
        etherscan_api_key=os.getenv("ETHERSCAN_API_KEY"),
        blockscout_base_url=os.getenv("BLOCKSCOUT_BASE_URL"),
        rpc_url=os.getenv("SIGNSSHIELD_RPC_URL"),
        public_rpc_fallback=_bool_env("SIGNSSHIELD_PUBLIC_RPC_FALLBACK", True),
        goplus_base_url=os.getenv("GOPLUS_BASE_URL", "https://api.gopluslabs.io"),
        metamask_config_url=os.getenv(
            "METAMASK_CONFIG_URL",
            "https://raw.githubusercontent.com/MetaMask/eth-phishing-detect/main/src/config.json",
        ),
        subagent_mode=os.getenv("SIGNSSHIELD_SUBAGENT_MODE", "off"),
        subagent_command=os.getenv("SIGNSSHIELD_SUBAGENT_COMMAND"),
        allow_fixture_risk=False,
    )


def _error_response(status_code: int, error: str, message: str, request_id: str, response: Response) -> JSONResponse:
    response.headers["X-Request-Id"] = request_id
    return JSONResponse(
        status_code=status_code,
        headers={"X-Request-Id": request_id},
        content={"error": error, "message": message, "requestId": request_id},
    )


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _csv_env(name: str) -> list[str]:
    value = os.getenv(name, "")
    return [item.strip() for item in value.split(",") if item.strip()]


app = create_app()
