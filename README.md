# TxRiskAgent

SignShield-style EVM pre-signature transaction risk analyzer.

The project analyzes wallet transaction JSON before signing. It decodes EVM calldata, classifies approvals/transfers/multicalls/unknown calls, enriches facts through optional real-world adapters, scores risk, and emits structured JSON plus Chinese plain-language warnings.
For ERC20 interactions it also builds a CertiK-style token risk profile covering owner privileges, honeypot/sell restrictions, tax controls, proxy/source transparency, bytecode signals, holder concentration, and LP lock facts when available.

## Quick Start

```bash
uv run python skills/signshield-risk/scripts/analyze_evm_tx.py dump-tx --output output/risk-reports
```

Live enrichment mode:

```bash
uv run python skills/signshield-risk/scripts/analyze_evm_tx.py dump-tx --live --output output/risk-reports-live-smoke
```

Subagent dry-run context:

```bash
uv run python skills/signshield-risk/scripts/analyze_evm_tx.py dump-tx --subagent dry-run --output output/risk-reports-subagent-context
```

## Live Adapters

The live mode supports:

- Sourcify/OpenChain + 4byte calldata selector resolution
- Tenderly transaction simulation
- Etherscan / Blockscout contract reputation
- GoPlus token threat intelligence
- MetaMask eth-phishing-detect domain checks

Optional environment variables:

```bash
export TENDERLY_ACCOUNT_SLUG=...
export TENDERLY_PROJECT_SLUG=...
export TENDERLY_ACCESS_KEY=...
export ETHERSCAN_API_KEY=...
export BLOCKSCOUT_BASE_URL=...
export SIGNSSHIELD_RPC_URL=...
export SIGNSSHIELD_SUBAGENT_COMMAND=...
```

Missing credentials are reported in `evidence.limitations`; they do not abort analysis.

Subagent live mode uses `SIGNSSHIELD_SUBAGENT_COMMAND`. The command reads context JSON from stdin and writes assessment JSON to stdout.

## Validate

```bash
uv lock
uv run pytest -q
python3 -m py_compile $(find skills/signshield-risk/scripts -name '*.py' | sort)
```

## Skill

The Codex skill lives at:

```text
skills/signshield-risk/
```

Detailed adapter docs:

```text
skills/signshield-risk/references/external_adapters.md
```
