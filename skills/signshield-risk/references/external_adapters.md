# External Adapters

## CLI Mode

Default mode is offline and deterministic:

```bash
uv run python skills/signshield-risk/scripts/analyze_evm_tx.py dump-tx --output output/risk-reports
```

Live mode enables all configured adapters:

```bash
uv run python skills/signshield-risk/scripts/analyze_evm_tx.py dump-tx --live --output output/risk-reports-live
```

ERC20 subagent modes:

```bash
uv run python skills/signshield-risk/scripts/analyze_evm_tx.py dump-tx --subagent dry-run --output output/risk-reports-subagent-context
uv run python skills/signshield-risk/scripts/analyze_evm_tx.py dump-tx --subagent live --subagent-command ./agent-command --output output/risk-reports-subagent-live
```

## 1. OpenChain / 4byte Calldata Resolver

Implementation:

- `signshield.adapters.calldata_resolver.SourcifyOpenChainResolver`
- `signshield.adapters.calldata_resolver.FourByteDirectoryResolver`
- `signshield.adapters.calldata_resolver.CombinedCalldataResolver`

Provider behavior:

- Try Sourcify's OpenChain-compatible `https://api.4byte.sourcify.dev/signature-database/v1/lookup`.
- Fall back to 4byte.directory `https://www.4byte.directory/api/v1/signatures/`.
- Store provider details under `evidence.calldata.resolver`.

No API key is required.

## 2. Tenderly Simulation Adapter

Implementation:

- `signshield.adapters.simulation.TenderlySimulationAdapter`

Environment variables:

- `TENDERLY_ACCOUNT_SLUG`
- `TENDERLY_PROJECT_SLUG`
- `TENDERLY_ACCESS_KEY`

Provider behavior:

- Calls Tenderly Simulation API only when all three settings are present.
- Missing settings produce `{"status": "config_missing"}`.
- Parsed facts are stored under `evidence.simulation.facts`.

## 3. Etherscan / Blockscout Contract Adapter

Implementation:

- `signshield.adapters.contract_reputation.CompositeContractReputationAdapter`

Environment variables:

- `ETHERSCAN_API_KEY`
- `BLOCKSCOUT_BASE_URL`

Provider behavior:

- Etherscan uses v2 `contract/getsourcecode` with `chainid`.
- Blockscout uses `/api/v2/smart-contracts/{address}`.
- Missing settings produce provider-specific `config_missing` statuses.
- Parsed facts are stored under `evidence.contractReputation`.

## 4. GoPlus Threat Intel Adapter

Implementation:

- `signshield.adapters.threat_intel.CompositeThreatIntelAdapter`

Environment variables:

- `GOPLUS_BASE_URL`, default `https://api.gopluslabs.io`

Provider behavior:

- Calls `/api/v1/token_security/{chain_id}?contract_addresses=...`.
- Converts high-risk token flags into `goplus_token_security_flags` risk factors.
- Parsed facts are stored under `evidence.threatIntel.providers.goplus`.

## 5. MetaMask Phishing Domain Adapter

Implementation:

- `signshield.adapters.threat_intel.CompositeThreatIntelAdapter`

Environment variables:

- `METAMASK_CONFIG_URL`, default `https://raw.githubusercontent.com/MetaMask/eth-phishing-detect/main/src/config.json`

Provider behavior:

- Checks the origin host against MetaMask `blocklist` and `fuzzylist`.
- Respects `allowlist`.
- Adds `phishing_domain_match` risk factor for matches.
- Parsed facts are stored under `evidence.threatIntel.providers.metamask`.

## Testing

Unit tests mock provider responses and do not require live credentials:

```bash
uv run pytest -q
```

Optional smoke checks for no-key providers:

```bash
PYTHONPATH=skills/signshield-risk/scripts uv run python - <<'PY'
from signshield.adapters.calldata_resolver import SourcifyOpenChainResolver
print(SourcifyOpenChainResolver().resolve("0xa9059cbb"))
PY
```

Use live mode for end-to-end enrichment. If credentials are absent, the result remains valid and documents missing providers in `limitations`.

## 6. ERC20 Token Risk Profile

Implementation:

- `signshield.token_metadata.TokenMetadataResolver`
- `signshield.token_security_normalizer.build_erc20_token_risk_profile`
- `signshield.contract_bytecode_scanner.scan_contract_bytecode`
- `signshield.erc20_scoring.apply_erc20_token_profile_rules`

Provider behavior:

- Token metadata uses local fixtures first, optional RPC second, and explorer contract names as fallback.
- GoPlus raw token reports are normalized into CertiK-style fields when available.
- Bytecode scanning is lightweight and only marks selector/opcode presence. It does not prove source-level semantics.
- Missing holder/LP/deployment fields remain `null`.

## 7. Subagent Harness

Implementation:

- `signshield.subagent_context_builder.build_subagent_context`
- `signshield.subagent_harness.run_subagent_harness`

Command protocol:

- The command receives JSON context on stdin.
- The command must print JSON with `status`, `assessments`, and `limitations`.
- Invalid JSON or non-zero exit is converted to structured `error`.
