# SignShield Risk Branches

## Scope

Analyze EVM transaction requests only. Supported chain identifiers are numeric EVM ids or CAIP-2 `eip155:<id>` strings. For all other chains, produce `UNSUPPORTED_CHAIN`.

## Fact Layer

Collect facts before scoring:

- Input facts: chain id, sender, recipient, calldata, native value, origin.
- Calldata facts: selector, decoded standard function, decoded parameters.
- Simulation facts: native/token/NFT balance deltas, allowance changes, internal calls, logs, revert reason. The first prototype leaves these as unavailable unless fixtures provide a fact.
- Contract facts: source verification, proxy status, implementation verification, deployment age, labels, interaction count. The first prototype uses local demo fixtures only.
- Threat intel facts: domain denylist, suspicious address, known drainer/scam, compliance hits. Keep compliance separate from technical or scam risk.

## Branches

### ERC20_APPROVAL

Triggers:

- `approve(address,uint256)`
- ERC20 or EIP-2612 permit selectors
- Permit2 approval/permit-like selectors

Key risks:

- Unlimited allowance.
- Approval amount materially exceeds the immediate need.
- Spender is unknown, newly deployed, unverified, proxied, or known malicious.
- User-facing origin does not match a known protocol.

### NFT_APPROVAL

Triggers:

- `setApprovalForAll(address,bool)`

Key risks:

- `approved=true` grants collection-wide transfer permission.
- Operator is unknown, unverified, or known malicious.

### NATIVE_TRANSFER

Triggers:

- Empty calldata with `value > 0`.

Key risks:

- Recipient is burn/dead/null-like address.
- Recipient is known suspicious.
- Value is large relative to user context.

### TOKEN_TRANSFER

Triggers:

- `transfer(address,uint256)`
- `transferFrom(address,address,uint256)`

Key risks:

- Direct token outflow.
- `transferFrom` moves assets from a third-party owner or from the user through prior approval.
- Recipient is suspicious or burn-like.

### MULTICALL

Triggers:

- `multicall`
- `execute`
- arbitrary call selectors

Key risks:

- Bundled calls hide multiple asset or permission changes.
- Recursively decoded child calls include approvals, transfers, or unknown calls.

### UNKNOWN_CONTRACT

Triggers:

- Unknown selector.
- Source unavailable.
- Proxy implementation unavailable or unverified.
- Simulation unavailable and calldata cannot be confidently decoded.

Key risks:

- Behavior cannot be explained from facts.
- Hidden owner/admin/upgrader paths cannot be ruled out.

### FAILURE_OR_UNCERTAIN

Triggers:

- Simulation reverts.
- Simulation cannot run.
- Input is incomplete.

Key risks:

- User should not interpret missing evidence as safety.
