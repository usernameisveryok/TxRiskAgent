# TxRiskAgent：钱包签名前的交易风险扫描

TxRiskAgent 面向钱包和交易入口，在用户签名前把 EVM 交易转成可读的风险报告：它会解码 calldata、识别授权/转账/Permit/NFT 全集授权/multicall/未知合约入口，输出资产影响、风险等级、证据摘要和建议动作。

## 核心能力

- 交易意图识别：覆盖 native transfer、ERC20 approve/transfer/transferFrom、EIP-2612 permit、NFT setApprovalForAll、multicall 和未知 selector。
- 风险证据汇总：结合 calldata 解码、模拟结果、链上地址/合约画像、token 风险画像、威胁情报；当 Kimi agent loop 正常可用时，会补充 web_search 证据。
- 钱包可执行建议：统一输出 `riskLevel`、`score`、`confidence` 和 `recommendedAction`，支持拒绝、谨慎继续、降低授权额度等动作。
- 接口形态清晰：非流式 `POST /tx-scan` 适合后端直连，流式 `/tx-scan/stream` 适合前端展示工具调用过程。

## 这轮样例运行

- 服务地址：`http://43.137.17.169`
- 非流式接口：`POST /tx-scan`
- 样例来源：`dump-tx/*.json` 共 24 条
- 原始请求与原始返回：[`tx-scan-nonstream-all-samples.json`](./tx-scan-nonstream-all-samples.json)

首轮结果统计：connection_refused: 4, connection_reset: 1, ok: 9, terminated: 2, timeout: 8。

HTTP 200 风险报告中，风险等级统计：CRITICAL: 5, HIGH: 1, LOW: 1, MEDIUM: 2。

Agent loop 状态统计：error: 8, ok: 1。本轮有 8 条报告因为 Kimi provider 返回 401 invalid authentication 而降级到 deterministic fallback；fallback 报告不会包含 `web_search` trace。只有第 8 条 agent loop 正常完成，并在 reasoning trace 中包含 `web_search`。

| # | 样例 | 首轮结果 | 风险等级 | 建议动作 | Agent loop | 耗时 ms |
|---:|---|---|---|---|---|---:|
| 1 | `2026-06-02T09-47-56-133Z-a850707e-9421-4cd9-a5e6-6fa636023746.json` | ok | MEDIUM | REDUCE_ALLOWANCE | error | 39481 |
| 2 | `2026-06-02T11-14-54-807Z-20571aef-0d9a-489d-b3e1-3b4aaf982fbd.json` | ok | HIGH | REJECT | error | 21690 |
| 3 | `2026-06-03T00-01-00-000Z-erc20-unlimited-approval-phishing.json` | ok | CRITICAL | REJECT | error | 26575 |
| 4 | `2026-06-03T00-02-00-000Z-erc20-large-approval-fake-swap.json` | ok | CRITICAL | REJECT | error | 18684 |
| 5 | `2026-06-03T00-03-00-000Z-eip2612-permit-unlimited-drainer.json` | ok | CRITICAL | REJECT | error | 19671 |
| 6 | `2026-06-03T00-04-00-000Z-nft-setapprovalforall-fake-airdrop.json` | ok | MEDIUM | CONTINUE_WITH_CAUTION | error | 16124 |
| 7 | `2026-06-03T00-05-00-000Z-nft-setapprovalforall-revoke-benign.json` | ok | LOW | CONTINUE | error | 11958 |
| 8 | `2026-06-03T00-06-00-000Z-token-transfer-to-drainer.json` | ok | CRITICAL | REJECT | ok | 203156 |
| 9 | `2026-06-03T00-07-00-000Z-token-transfer-to-dead.json` | ok | CRITICAL | REJECT | error | 280266 |
| 10 | `2026-06-03T00-08-00-000Z-transferfrom-prior-allowance-drain.json` | timeout | - | - | - | 180147 |
| 11 | `2026-06-03T00-09-00-000Z-multicall-hidden-approval-and-transfer.json` | terminated | - | - | - | 48355 |
| 12 | `2026-06-03T00-10-00-000Z-multicall-deadline-fake-migration.json` | timeout | - | - | - | 40007 |
| 13 | `2026-06-03T00-11-00-000Z-universal-router-execute-permit2-style-drain.json` | timeout | - | - | - | 40007 |
| 14 | `2026-06-03T00-12-00-000Z-unknown-claim-rewards-selector.json` | timeout | - | - | - | 40013 |
| 15 | `2026-06-03T00-13-00-000Z-flashloan-oracle-attack-helper-unknown.json` | terminated | - | - | - | 14876 |
| 16 | `2026-06-03T00-14-00-000Z-native-address-poisoning-lookalike.json` | timeout | - | - | - | 40006 |
| 17 | `2026-06-03T00-15-00-000Z-native-transfer-to-synthetic-drainer.json` | timeout | - | - | - | 40018 |
| 18 | `2026-06-03T00-16-00-000Z-erc20-hidden-owner-token.json` | timeout | - | - | - | 40007 |
| 19 | `2026-06-03T00-17-00-000Z-erc20-mintable-owner-token.json` | timeout | - | - | - | 40006 |
| 20 | `2026-06-03T00-18-00-000Z-erc20-high-sell-tax-token.json` | connection_reset | - | - | - | 21557 |
| 21 | `2026-06-03T00-19-00-000Z-erc20-cannot-sell-all-token.json` | connection_refused | - | - | - | 53 |
| 22 | `2026-06-03T00-20-00-000Z-erc20-blacklist-honeypot-token.json` | connection_refused | - | - | - | 47 |
| 23 | `2026-06-03T00-21-00-000Z-erc20-proxy-unverified-token.json` | connection_refused | - | - | - | 53 |
| 24 | `2026-06-03T00-22-00-000Z-erc20-lp-unlocked-holder-concentration-token.json` | connection_refused | - | - | - | 55 |

## 适合展示的场景

- 授权钓鱼：无限授权、超大额度授权、恶意 spender、历史授权复用。
- 资产不可找回：转入 `0x000...dead` 或高风险归集地址。
- NFT 权限风险：`setApprovalForAll(true)` 和 revoke 对照样例。
- 聚合调用风险：multicall / router 类入口中隐藏授权和转账。
- Token 合约风险：隐藏 owner、可增发、高税、黑名单、不可卖、未验证 proxy、LP/持仓集中等画像。

## 对外表述建议

TxRiskAgent 不只告诉用户“这是什么函数”，而是把签名后的资产后果和证据质量一起呈现：哪些资产会离开钱包、谁会获得授权、证据来自模拟还是链上画像、是否存在情报命中、是否需要拒绝或降低授权额度。

当前公网演示服务还需要修复 Kimi agent loop 鉴权和长请求稳定性；修复后，web_search、reputation、threat intel 和 simulation 可以形成更完整的签名前风险链路。
