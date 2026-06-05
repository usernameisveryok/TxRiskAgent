# CertiK Token Scan ERC20 风险点临时总结

来源页面：
https://v1.skynet.cdn.certik.com/zh-CN/tools/token-scan/bsc/0x7ede261faf197771e4bb9b7277e8086fb52e72a4

样例对象：

- Chain: BSC
- Token: `cpt token` / `CPT`
- Token address: `0x7ede261faf197771e4bb9b7277e8086fb52e72a4`
- 页面显示扫描结果：`0` 个警报，`2` 个注意事项，`21` 个通过
- 页面显示代币扫描分数：`0.00`

> 说明：本文件只整理 CertiK Token Scan 页面中对 ERC20/token 风险有参考价值的检查项，不判断该样例 token 本身是否安全。后续应把这些检查项拆成可复用的事实字段和评分规则。

## 一、CertiK 页面覆盖的 ERC20 主要风险维度

### 1. 持有人集中度 / 市场波动风险

页面项：

- `大股东比例`
- Category: `Volatile Market, Centralization`
- 页面描述：Major holders ratio，不包含交易所和锁仓地址。
- 页面还展示：
  - 前 10 名持有者比例
  - Top holders 明细

项目可映射字段：

- `tokenHolder.top10Ratio`
- `tokenHolder.majorHolderRatio`
- `tokenHolder.exchangeAndLockedExcluded`
- `riskFactors.major_holder_concentration`

风险解释：

- 大户占比过高会带来价格操纵、砸盘、流动性冲击风险。
- 这类风险不是交易本身造成的权限风险，但对用户“买入/接收/交互该 token”有提示价值。

### 2. 所有权未放弃 / Owner 权限风险

页面项：

- `未放弃所有权`
- Category: `Centralization`
- 页面描述：所有者特权尚未放弃。

项目可映射字段：

- `contract.owner`
- `contract.ownershipRenounced`
- `riskFactors.owner_privileges_not_renounced`

风险解释：

- owner 仍保留权限时，需要进一步检查 owner 是否可修改税率、黑白名单、暂停转账、铸币、改余额、提取资产等。
- 单独“未放弃所有权”不一定恶意，但会提高中心化和后门风险。

### 3. 买税 / 卖税

页面项：

- `买税`
- `卖税`
- Category: `Market`
- 页面展示 buy tax / sell tax 百分比。

项目可映射字段：

- `tokenTax.buyTaxBps`
- `tokenTax.sellTaxBps`
- `riskFactors.high_buy_tax`
- `riskFactors.high_sell_tax`

风险解释：

- 高买税/卖税会导致用户实际成交或退出损失。
- 卖税明显高于买税时，常见于高滑点、软性 honeypot、退出惩罚型 token。

### 4. 买不到 / 买入限制

页面项：

- `买不到`
- Category: `Market`
- 页面描述：是否检测到购买 token 限制。

项目可映射字段：

- `tradeability.canBuy`
- `tradeability.buyRestrictions`
- `riskFactors.cannot_buy`

风险解释：

- 买入限制可能来自白名单、交易开关、最大交易额、黑名单、冷却时间或路由限制。
- 对 pre-signature 风控来说，应提示“模拟买入/交易路径是否能成功”。

### 5. 貔貅 / Honeypot

页面项：

- `是貔貅骗局`
- Category: `Rugpull`
- 页面描述：是否发现 honeypot 风险。

项目可映射字段：

- `tradeability.isHoneypot`
- `tradeability.canSell`
- `riskFactors.honeypot`

风险解释：

- honeypot 通常表现为可以买入但卖不出，或只能特定地址卖出。
- 本项目应结合 simulation / GoPlus / sell test / router quote 生成证据。

### 6. 铸币权限 / Mintable

页面项：

- `存在铸币权限`
- Category: `Centralization`
- 页面描述：是否找到 mintable 功能。

项目可映射字段：

- `privileges.mintable`
- `privileges.minter`
- `riskFactors.mintable_token`

风险解释：

- 可增发会稀释持有人资产，也可用于 rug pull。
- 若 owner 未放弃且存在 mint 权限，应组合提高风险。

### 7. 黑名单机制

页面项：

- `已列入黑名单`
- Category: `Centralization`
- 页面描述：是否找到 token blacklist。

项目可映射字段：

- `privileges.blacklistEnabled`
- `privileges.blacklistController`
- `riskFactors.blacklist_capability`

风险解释：

- 黑名单机制可能阻止用户转出或卖出。
- 它不一定恶意，稳定币等合规 token 也可能存在，但对普通用户必须清楚提示。

### 8. 白名单机制

页面项：

- `有白名单`
- Category: `Centralization`
- 页面描述：是否找到 token whitelist。

项目可映射字段：

- `privileges.whitelistEnabled`
- `riskFactors.whitelist_capability`

风险解释：

- 白名单可能限制买卖或转账参与者。
- 与“买不到/卖不完/转账暂停/冷却时间”组合时风险更高。

### 9. 反鲸机制

页面项：

- `反鲸`
- Category: `Market`
- 页面描述：是否找到 anti-whale 机制。

项目可映射字段：

- `marketControls.antiWhaleEnabled`
- `marketControls.maxTxAmount`
- `marketControls.maxWalletAmount`
- `riskFactors.anti_whale_restriction`

风险解释：

- 反鲸可能限制单笔交易、单钱包持仓或转账频率。
- 若规则可被 owner 修改，应视为更强中心化风险。

### 10. 可修改税率

页面项：

- `可修改税率`
- Category: `Centralization`
- 页面描述：token tax 是否能由特权角色修改。

项目可映射字段：

- `privileges.taxMutable`
- `privileges.taxController`
- `riskFactors.mutable_tax`

风险解释：

- 即使当前买卖税为 0，也可能在用户买入后被 owner 调高。
- 应与 owner 未放弃、proxy、外部调用组合评分。

### 11. 卖不完 / Sell-all 限制

页面项：

- `卖不完`
- Category: `Market`
- 页面描述：是否检测到出售全部 token 限制。

项目可映射字段：

- `tradeability.cannotSellAll`
- `riskFactors.cannot_sell_all`

风险解释：

- 用户可能无法一次性退出全部持仓。
- 这类机制常与最大卖出比例、冷却期、动态税率或黑名单组合。

### 12. 不开源 / 合约透明度

页面项：

- `不开放源代码`
- Category: `Transparency`
- 页面描述：token 是否开源。

项目可映射字段：

- `contract.sourceVerified`
- `contract.sourceProvider`
- `riskFactors.source_unverified`

风险解释：

- 未开源不等于恶意，但会显著降低可解释性。
- 本项目应切换到 bytecode + simulation + reputation fallback。

### 13. 隐藏所有者

页面项：

- `有隐藏的所有者`
- Category: `Centralization`
- 页面描述：是否找到 hidden owner。

项目可映射字段：

- `privileges.hiddenOwner`
- `riskFactors.hidden_owner`

风险解释：

- hidden owner 会绕过表面上的 renounce ownership。
- 这是典型 rug pull / 权限后门信号。

### 14. 自毁功能

页面项：

- `可以自毁`
- Category: `Rugpull`
- 页面描述：是否找到 selfdestruct。

项目可映射字段：

- `bytecode.selfdestructPresent`
- `riskFactors.selfdestruct_capability`

风险解释：

- 自毁能力可能破坏合约可用性或资产路径。
- 新版 EVM 语义有变化，但仍应作为高风险 bytecode 信号保留。

### 15. Proxy 合约

页面项：

- `是代理合同`
- Category: `Centralization`
- 页面描述：token 是否 proxy contract。

项目可映射字段：

- `contract.isProxy`
- `contract.implementation`
- `contract.implementationVerified`
- `riskFactors.proxy_contract`
- `riskFactors.proxy_implementation_unverified`

风险解释：

- proxy 本身不一定危险，但 implementation 可升级时，用户看到的逻辑可能变化。
- 与 owner 未放弃、implementation 未验证、授权/permit 交易组合时风险明显提高。

### 16. 可修改余额

页面项：

- `可以修改平衡`
- Category: `Centralization`
- 页面描述：token balance 是否能由特权角色修改。

项目可映射字段：

- `privileges.balanceMutable`
- `riskFactors.balance_mutable_by_privileged_role`

风险解释：

- 特权角色可改余额是极高中心化风险。
- 可能绕过正常 transfer/mint/burn 语义。

### 17. 可提取代币

页面项：

- `可以提取代币`
- Category: `Centralization`
- 页面描述：是否找到 withdraw function。

项目可映射字段：

- `privileges.withdrawToken`
- `riskFactors.withdraw_function`

风险解释：

- 合约可被特权角色提取资产时，用户应知道资金是否可能被管理员转移。
- 对 staking、pool、LP wrapper 类交互尤其重要。

### 18. 外部合约调用

页面项：

- `有外部合约调用`
- Category: `General`
- 页面描述：是否找到 external call。

项目可映射字段：

- `bytecode.externalCallPresent`
- `riskFactors.external_call_capability`

风险解释：

- 外部调用不是直接恶意，但会扩大攻击面。
- 应进一步识别 call target、delegatecall、任意地址调用和重入风险。

### 19. 可重新获得所有权

页面项：

- `可以重新获得所有权`
- Category: `Centralization`
- 页面描述：是否找到 regain ownership backdoor。

项目可映射字段：

- `privileges.canRegainOwnership`
- `riskFactors.ownership_regain_backdoor`

风险解释：

- 表面 renounce 后仍可重新获得 owner，是强后门信号。
- 应优先级高于普通“未放弃所有权”。

### 20. 转账冷却时间

页面项：

- `是转移冷却时间`
- Category: `Centralization`
- 页面描述：是否找到 transfer cooldown。

项目可映射字段：

- `marketControls.transferCooldown`
- `riskFactors.transfer_cooldown`

风险解释：

- 冷却时间可能限制用户交易频率或退出速度。
- 与 sell restriction / anti-whale / mutable tax 组合时应提高市场风险。

### 21. 转账可暂停

页面项：

- `转接是否可暂停`
- Category: `Centralization`
- 页面描述：是否找到 pausable transfer。

项目可映射字段：

- `privileges.transferPausable`
- `riskFactors.transfer_pausable`

风险解释：

- 特权角色可暂停转账时，用户可能无法转出或交易。
- 对普通用户应解释为“代币可被冻结交易”。

### 22. 反鲸机制可修改

页面项：

- `反鲸鱼是否可以修改`
- Category: `Market`
- 页面描述：anti-whale 机制是否可修改。

项目可映射字段：

- `marketControls.antiWhaleMutable`
- `riskFactors.mutable_anti_whale`

风险解释：

- 当前限制不高不代表未来安全，特权角色可修改规则时风险上升。

### 23. LP 锁定比例 / 流动性锁定

页面区域：

- `10 大 LP 持有者`
- `LP 锁定比率`

项目可映射字段：

- `liquidity.lpLockedRatio`
- `liquidity.topLpHolderRatio`
- `riskFactors.lp_not_locked`
- `riskFactors.lp_holder_concentration`

风险解释：

- LP 未锁定或高度集中时，项目方可能撤池导致用户无法卖出或价格崩溃。
- 这是 ERC20 rug pull 评估的关键市场/流动性指标。

### 24. 部署时间 / 部署者 / owner / DEX 地址

页面区域：

- `部署时间`
- `代币地址`
- `部署者地址`
- `拥有者地址`
- `DEX 地址`

项目可映射字段：

- `contract.deployedAt`
- `contract.ageDays`
- `contract.deployer`
- `contract.owner`
- `liquidity.dexPair`
- `riskFactors.newly_deployed_token`
- `riskFactors.suspicious_deployer`

风险解释：

- 新部署 token + 未开源 + owner 权限 + LP 未锁 是典型高风险组合。
- deployer 历史应接入 explorer / labels / threat intel。

## 二、建议加入本项目的 ERC20 风险 Schema

```json
{
  "tokenSecurity": {
    "sourceVerified": true,
    "isProxy": false,
    "implementationVerified": null,
    "ownershipRenounced": false,
    "hiddenOwner": false,
    "canRegainOwnership": false,
    "mintable": false,
    "blacklistEnabled": false,
    "whitelistEnabled": false,
    "taxMutable": false,
    "balanceMutable": false,
    "withdrawFunction": false,
    "selfdestructPresent": false,
    "externalCallPresent": false,
    "transferPausable": false,
    "transferCooldown": false
  },
  "marketControls": {
    "buyTaxBps": 0,
    "sellTaxBps": 0,
    "canBuy": true,
    "canSell": true,
    "cannotSellAll": false,
    "antiWhaleEnabled": false,
    "antiWhaleMutable": false
  },
  "holderAndLiquidity": {
    "majorHolderRatio": null,
    "top10HolderRatio": null,
    "lpLockedRatio": null,
    "topLpHolderRatio": null
  },
  "deployment": {
    "deployedAt": null,
    "ageDays": null,
    "deployer": null,
    "owner": null,
    "dexPair": null
  }
}
```

## 三、建议加入 scoring 的组合规则

高优先级组合：

- `hiddenOwner` + `ownershipRenounced=true` 表象：Critical
- `mintable` + `owner not renounced`：High
- `blacklistEnabled` + `cannotSellAll` 或 `canSell=false`：Critical
- `taxMutable` + 当前低税率：Medium/High，提示“未来可调高”
- `isProxy` + `implementationVerified=false`：High
- `sourceVerified=false` + `externalCallPresent=true`：High
- `lpLockedRatio` 很低 + `topLpHolderRatio` 很高：High/Critical
- `top10HolderRatio` 极高 + LP 未锁：High
- `transferPausable` + owner 未放弃：High
- `balanceMutable`：Critical
- `canRegainOwnership`：Critical
- `selfdestructPresent`：High/Critical

## 四、和当前项目已有模块的差距

当前已有：

- `GoPlus Token Security` 初步映射部分 flag。
- `Etherscan/Blockscout` 初步判断源码 verified、proxy、implementation。
- ERC20 `approve / permit / transfer / transferFrom` 交易级解析。
- 大额/无限授权、恶意 spender/recipient、本地 fixture。

建议补齐：

- 真实 token metadata 与 token security 统一结构。
- holder concentration 与 LP locked ratio。
- owner/deployer/deployedAt 历史与标签。
- blacklist/whitelist/pausable/cooldown/tax mutable/mintable 等权限字段。
- sell test / buy test / cannot sell all 的模拟结果。
- proxy implementation 递归验证。
- 组合规则评分，而不是单项线性加分。

