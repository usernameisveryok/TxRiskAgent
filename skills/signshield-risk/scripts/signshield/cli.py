from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .analyzer import analyze_transaction
from .env import load_dotenv
from .token_metadata import TokenMetadataResolver
from .types import AnalysisOptions


def iter_input_files(path: Path) -> list[Path]:
    if path.is_dir():
        return sorted(p for p in path.iterdir() if p.suffix.lower() == ".json")
    return [path]


def write_result(result: dict, output_dir: Path | None, source: Path) -> None:
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if output_dir is None:
        print(text)
        return
    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / f"{source.stem}.risk.json"
    target.write_text(text + "\n", encoding="utf-8")
    print(str(target))


def main() -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Analyze EVM transaction JSON and produce SignShield risk JSON.")
    parser.add_argument("input", type=Path, help="Input JSON file or directory containing JSON files.")
    parser.add_argument("--output", type=Path, help="Directory for .risk.json outputs. Defaults to stdout.")
    parser.add_argument("--live", action="store_true", help="Enable live external adapters where configured.")
    parser.add_argument("--mode", choices=["offline", "live-best-effort", "production"], help="Runtime mode. --live maps to live-best-effort when omitted.")
    parser.add_argument("--tenderly-account", default=os.getenv("TENDERLY_ACCOUNT_SLUG"))
    parser.add_argument("--tenderly-project", default=os.getenv("TENDERLY_PROJECT_SLUG"))
    parser.add_argument("--tenderly-access-key", default=os.getenv("TENDERLY_ACCESS_KEY"))
    parser.add_argument("--etherscan-api-key", default=os.getenv("ETHERSCAN_API_KEY"))
    parser.add_argument("--blockscout-base-url", default=os.getenv("BLOCKSCOUT_BASE_URL"))
    parser.add_argument("--rpc-url", default=os.getenv("SIGNSSHIELD_RPC_URL"))
    parser.add_argument("--no-public-rpc-fallback", action="store_true", help="Disable public RPC fallback when --live is enabled and --rpc-url is absent.")
    parser.add_argument("--goplus-base-url", default=os.getenv("GOPLUS_BASE_URL", "https://api.gopluslabs.io"))
    parser.add_argument("--metamask-config-url", default=os.getenv("METAMASK_CONFIG_URL", "https://raw.githubusercontent.com/MetaMask/eth-phishing-detect/main/src/config.json"))
    parser.add_argument("--subagent", choices=["off", "dry-run", "live"], default=os.getenv("SIGNSSHIELD_SUBAGENT_MODE", "off"))
    parser.add_argument("--subagent-command", default=os.getenv("SIGNSSHIELD_SUBAGENT_COMMAND"))
    parser.add_argument("--allow-fixture-risk", action="store_true", help="Allow local fixture labels to create high-confidence risk factors outside offline mode.")
    args = parser.parse_args()
    mode = args.mode or ("live-best-effort" if args.live else "offline")

    options = AnalysisOptions(
        live=args.live,
        mode=mode,
        tenderly_account=args.tenderly_account,
        tenderly_project=args.tenderly_project,
        tenderly_access_key=args.tenderly_access_key,
        etherscan_api_key=args.etherscan_api_key,
        blockscout_base_url=args.blockscout_base_url,
        rpc_url=args.rpc_url,
        public_rpc_fallback=not args.no_public_rpc_fallback,
        goplus_base_url=args.goplus_base_url,
        metamask_config_url=args.metamask_config_url,
        subagent_mode=args.subagent,
        subagent_command=args.subagent_command,
        allow_fixture_risk=(mode == "offline" or args.allow_fixture_risk),
    )

    files = iter_input_files(args.input)
    if not files:
        raise SystemExit(f"No JSON inputs found: {args.input}")
    token_metadata_provider = TokenMetadataResolver(args.rpc_url, public_fallback=mode != "offline" and not args.no_public_rpc_fallback)
    for source in files:
        payload = json.loads(source.read_text(encoding="utf-8"))
        result = analyze_transaction(payload, str(source), options=options, token_metadata_provider=token_metadata_provider)
        write_result(result, args.output, source)
    return 0
