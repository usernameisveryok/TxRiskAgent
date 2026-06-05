---
name: signshield-risk
description: Analyze EVM pre-signature transaction JSON for SignShield-style wallet risk explanations. Use when Codex needs to inspect chainId/from/to/data/value/origin inputs, decode EVM calldata, classify approvals/transfers/multicalls/unknown contracts, score risk, and output structured JSON plus plain-language user warnings before signing.
---

# SignShield Risk

## Overview

Produce a SignShield risk structure for EVM transaction requests before a user signs. Keep the workflow fact-first: decode and normalize transaction facts, apply deterministic rules, then explain those facts in natural language.

This skill is EVM-only. For non-`eip155` chains, return an unsupported result instead of attempting chain-specific analysis.

## Quick Start

Run the analyzer from a project that has `uv`:

```bash
uv run python skills/signshield-risk/scripts/analyze_evm_tx.py dump-tx --output output/risk-reports
```

For a single file:

```bash
uv run python skills/signshield-risk/scripts/analyze_evm_tx.py dump-tx/example.json
```

Default mode is deterministic and offline except for local fixtures. Use `--live` to enable real-world adapters:

```bash
uv run python skills/signshield-risk/scripts/analyze_evm_tx.py dump-tx --live --output output/risk-reports-live
```

Live adapters are best-effort. Missing API keys or provider failures are written into `evidence` and `limitations`; they should not crash the analysis.

ERC20 semantic review can be enabled separately:

```bash
uv run python skills/signshield-risk/scripts/analyze_evm_tx.py dump-tx --subagent dry-run
uv run python skills/signshield-risk/scripts/analyze_evm_tx.py dump-tx --subagent live --subagent-command ./agent-command
```

## Workflow

1. Normalize input.
   Accept either `chainId` plus `transaction`, or a flat transaction-like object. Convert `eip155:<id>` into an EVM chain id. Validate addresses and hex values.

2. Build the fact layer.
   Decode calldata selectors and standard ABI parameters. Extract native value, token/spender/operator/amount, and origin. For ERC20 interactions, build `evidence.erc20TokenRisk` from token metadata, token security facts, contract reputation, bytecode scan signals, holder/liquidity facts, and optional subagent assessments. In live mode, enrich facts through Sourcify/OpenChain + 4byte, Tenderly, Etherscan/Blockscout, GoPlus, and MetaMask eth-phishing-detect.

3. Classify intent.
   Route to one primary category: `NATIVE_TRANSFER`, `ERC20_APPROVAL`, `NFT_APPROVAL`, `TOKEN_TRANSFER`, `MULTICALL`, `UNKNOWN_CONTRACT`, or `UNSUPPORTED_CHAIN`.

4. Score and separate risk domains.
   Keep technical risk, scam/phishing risk, and compliance risk as separate lists and score contributions. Never conflate OFAC/compliance hits with contract exploit evidence.

5. Explain only structured facts.
   Generate summaries and recommendations from decoded facts, simulation facts, reputation facts, and limitations. Do not invent source verification, deployment age, labels, or simulation outcomes if they were not observed.

## Risk Branches

- `ERC20_APPROVAL`: detect `approve(address,uint256)`, permit variants, Permit2, unlimited or overlarge allowances, unknown or malicious spenders, and proxy reputation.
- `NFT_APPROVAL`: detect `setApprovalForAll(address,bool)` and mark collection-wide operator permissions as high risk when enabled.
- `NATIVE_TRANSFER`: detect empty calldata with native value. Flag burn/dead addresses, suspicious recipients, and large value transfers.
- `TOKEN_TRANSFER`: detect `transfer` and `transferFrom`; use simulation facts when available to describe actual asset movement.
- `MULTICALL`: detect `multicall`, `execute`, or arbitrary-call selectors; recursively decode embedded calls when the implementation adds support.
- `UNKNOWN_CONTRACT`: use when selector is unknown, source is unavailable, proxy implementation is unverified, or facts are insufficient.
- `UNSUPPORTED_CHAIN`: use for any non-EVM chain.

## Output Contract

Return JSON compatible with `references/output_schema.md`. Every result should include:

- `verdict`: risk level, score, confidence, recommended action.
- `intent`: primary category and natural-language description.
- `assetImpact`: assets, permissions, or balances affected.
- `riskFactors`: concrete factors with severity, domain, score contribution, and evidence.
- `evidence`: decoded calldata, simulation placeholder, contract reputation, threat intel, ERC20 token risk profile when applicable, and limitations.
- `summary` and `recommendation`: user-facing Chinese explanations in this prototype.

## References

- Read `references/risk_branches.md` when changing branch logic.
- Read `references/output_schema.md` when changing JSON fields.
- Read `references/external_adapters.md` when changing live provider integrations.
- Read `dump-tx/certik-token-scan-erc20-risk-summary.md` when changing ERC20 token-risk profile fields or CertiK-style scoring rules.
- Use `scripts/analyze_evm_tx.py` as the deterministic baseline implementation.

## Validation

```bash
uv lock
uv run pytest -q
python3 -m py_compile $(find skills/signshield-risk/scripts -name '*.py' | sort)
uv run --with pyyaml python /Users/lihangzhe/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/signshield-risk
```
