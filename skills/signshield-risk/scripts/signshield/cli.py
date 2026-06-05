from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .analyzer import analyze_transaction
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
    parser = argparse.ArgumentParser(description="Analyze EVM transaction JSON and produce SignShield risk JSON.")
    parser.add_argument("input", type=Path, help="Input JSON file or directory containing JSON files.")
    parser.add_argument("--output", type=Path, help="Directory for .risk.json outputs. Defaults to stdout.")
    parser.add_argument("--live", action="store_true", help="Enable live external adapters where configured.")
    parser.add_argument("--tenderly-account", default=os.getenv("TENDERLY_ACCOUNT_SLUG"))
    parser.add_argument("--tenderly-project", default=os.getenv("TENDERLY_PROJECT_SLUG"))
    parser.add_argument("--tenderly-access-key", default=os.getenv("TENDERLY_ACCESS_KEY"))
    parser.add_argument("--etherscan-api-key", default=os.getenv("ETHERSCAN_API_KEY"))
    parser.add_argument("--blockscout-base-url", default=os.getenv("BLOCKSCOUT_BASE_URL"))
    parser.add_argument("--goplus-base-url", default=os.getenv("GOPLUS_BASE_URL", "https://api.gopluslabs.io"))
    parser.add_argument("--metamask-config-url", default=os.getenv("METAMASK_CONFIG_URL", "https://raw.githubusercontent.com/MetaMask/eth-phishing-detect/main/src/config.json"))
    args = parser.parse_args()

    options = AnalysisOptions(
        live=args.live,
        tenderly_account=args.tenderly_account,
        tenderly_project=args.tenderly_project,
        tenderly_access_key=args.tenderly_access_key,
        etherscan_api_key=args.etherscan_api_key,
        blockscout_base_url=args.blockscout_base_url,
        goplus_base_url=args.goplus_base_url,
        metamask_config_url=args.metamask_config_url,
    )

    files = iter_input_files(args.input)
    if not files:
        raise SystemExit(f"No JSON inputs found: {args.input}")
    for source in files:
        payload = json.loads(source.read_text(encoding="utf-8"))
        result = analyze_transaction(payload, str(source), options=options)
        write_result(result, args.output, source)
    return 0
