from __future__ import annotations

from typing import Any

from .utils import add_factor


def apply_erc20_token_profile_rules(profile: dict[str, Any] | None, factors: list[dict[str, Any]]) -> None:
    if not isinstance(profile, dict):
        return
    token_security = profile.get("tokenSecurity", {})
    market = profile.get("marketControls", {})
    holder = profile.get("holderAndLiquidity", {})

    if token_security.get("hiddenOwner"):
        add_factor(factors, "hidden_owner", "technical", "CRITICAL", 60, "Token 存在隐藏 owner", "合约可能存在绕过表面 owner 状态的隐藏所有者权限。", {"field": "tokenSecurity.hiddenOwner"})
    if token_security.get("canRegainOwnership"):
        add_factor(factors, "ownership_regain_backdoor", "technical", "CRITICAL", 60, "Owner 可重新获得所有权", "合约可能存在 renounce 后重新取回所有权的后门。", {"field": "tokenSecurity.canRegainOwnership"})
    if token_security.get("balanceMutable"):
        add_factor(factors, "balance_mutable_by_privileged_role", "technical", "CRITICAL", 70, "特权角色可修改余额", "特权角色可能绕过正常 ERC20 语义直接修改账户余额。", {"field": "tokenSecurity.balanceMutable"})
    if token_security.get("blacklistEnabled") and (market.get("canSell") is False or market.get("cannotSellAll")):
        add_factor(factors, "blacklist_and_sell_restriction", "technical", "CRITICAL", 65, "黑名单机制叠加卖出限制", "Token 同时存在黑名单能力和卖出/退出限制，用户可能无法正常退出。", {"fields": ["tokenSecurity.blacklistEnabled", "marketControls.canSell", "marketControls.cannotSellAll"]})

    if token_security.get("mintable") and token_security.get("ownershipRenounced") is False:
        add_factor(factors, "mintable_owner_not_renounced", "technical", "HIGH", 45, "未放弃 owner 且可增发", "Owner 未放弃且 token 存在增发能力，可能稀释持有人资产。", {"fields": ["tokenSecurity.mintable", "tokenSecurity.ownershipRenounced"]})
    if token_security.get("isProxy") and token_security.get("implementationVerified") is False:
        add_factor(factors, "proxy_implementation_unverified", "technical", "HIGH", 45, "Proxy implementation 未验证", "Token 是 proxy 且 implementation 未验证，实际逻辑可能不可审查或可升级变化。", {"fields": ["tokenSecurity.isProxy", "tokenSecurity.implementationVerified"]})
    if token_security.get("sourceVerified") is False and token_security.get("externalCallPresent"):
        add_factor(factors, "unverified_source_external_calls", "technical", "HIGH", 40, "未开源且存在外部调用", "未验证源码叠加外部调用能力会降低交易行为可解释性并扩大攻击面。", {"fields": ["tokenSecurity.sourceVerified", "tokenSecurity.externalCallPresent"]})
    if token_security.get("transferPausable") and token_security.get("ownershipRenounced") is False:
        add_factor(factors, "transfer_pausable_owner_not_renounced", "technical", "HIGH", 40, "Owner 可暂停转账", "Owner 未放弃且存在暂停转账能力，用户可能无法转出或卖出。", {"fields": ["tokenSecurity.transferPausable", "tokenSecurity.ownershipRenounced"]})
    if token_security.get("selfdestructPresent"):
        add_factor(factors, "selfdestruct_capability", "technical", "HIGH", 40, "Bytecode 出现 selfdestruct", "合约 bytecode 中出现 selfdestruct 信号，应作为 rug pull/可用性风险处理。", {"field": "tokenSecurity.selfdestructPresent"})
    if token_security.get("withdrawFunction"):
        add_factor(factors, "withdraw_function", "technical", "MEDIUM", 25, "合约存在 withdraw 类能力", "合约可能允许特权角色提取资产，需要结合源码和资产路径进一步确认。", {"field": "tokenSecurity.withdrawFunction"})
    if token_security.get("taxMutable"):
        add_factor(factors, "mutable_tax", "technical", "MEDIUM", 30, "税率可被修改", "即使当前税率较低，特权角色后续也可能调高买卖税。", {"field": "tokenSecurity.taxMutable"})
    if token_security.get("transferCooldown"):
        add_factor(factors, "transfer_cooldown", "technical", "MEDIUM", 20, "Token 存在转账冷却限制", "冷却时间可能限制用户交易频率或退出速度。", {"field": "tokenSecurity.transferCooldown"})

    buy_tax = market.get("buyTaxBps")
    sell_tax = market.get("sellTaxBps")
    if isinstance(buy_tax, int) and buy_tax >= 1000:
        add_factor(factors, "high_buy_tax", "technical", "MEDIUM", 25, "买税较高", f"Token buy tax 约为 {buy_tax / 100:.2f}%。", {"buyTaxBps": buy_tax})
    if isinstance(sell_tax, int) and sell_tax >= 1000:
        add_factor(factors, "high_sell_tax", "technical", "HIGH", 35, "卖税较高", f"Token sell tax 约为 {sell_tax / 100:.2f}%。", {"sellTaxBps": sell_tax})
    if isinstance(buy_tax, int) and isinstance(sell_tax, int) and sell_tax - buy_tax >= 1000:
        add_factor(factors, "sell_tax_much_higher_than_buy_tax", "technical", "HIGH", 35, "卖税明显高于买税", "卖出成本显著高于买入，可能是软性 honeypot 或退出惩罚机制。", {"buyTaxBps": buy_tax, "sellTaxBps": sell_tax})
    if market.get("canBuy") is False:
        add_factor(factors, "cannot_buy", "technical", "MEDIUM", 25, "检测到买入限制", "Token 可能存在白名单、交易开关、最大交易额或路由限制。", {"field": "marketControls.canBuy"})
    if market.get("canSell") is False:
        add_factor(factors, "honeypot", "technical", "CRITICAL", 70, "疑似貔貅 / 无法卖出", "Token 安全画像显示用户可能无法正常卖出。", {"field": "marketControls.canSell"})
    if market.get("cannotSellAll"):
        add_factor(factors, "cannot_sell_all", "technical", "HIGH", 40, "无法一次性卖出全部", "Token 可能限制用户一次性退出全部持仓。", {"field": "marketControls.cannotSellAll"})
    if market.get("antiWhaleEnabled"):
        add_factor(factors, "anti_whale_restriction", "technical", "MEDIUM", 20, "存在反鲸限制", "Token 可能限制单笔交易、单钱包持仓或转账频率。", {"field": "marketControls.antiWhaleEnabled"})
    if market.get("antiWhaleMutable"):
        add_factor(factors, "mutable_anti_whale", "technical", "MEDIUM", 25, "反鲸规则可修改", "当前限制不高不代表未来安全，特权角色可能修改规则。", {"field": "marketControls.antiWhaleMutable"})

    lp_locked = holder.get("lpLockedRatio")
    top_lp = holder.get("topLpHolderRatio")
    top10 = holder.get("top10HolderRatio")
    major = holder.get("majorHolderRatio")
    if isinstance(lp_locked, (int, float)) and lp_locked < 0.25:
        add_factor(factors, "lp_not_locked", "technical", "HIGH", 40, "LP 锁定比例较低", "LP 未锁定或锁定比例很低，项目方可能撤池导致用户无法卖出。", {"lpLockedRatio": lp_locked})
    if isinstance(top_lp, (int, float)) and top_lp > 0.7:
        add_factor(factors, "lp_holder_concentration", "technical", "HIGH", 35, "LP 持有人高度集中", "LP token 高度集中会提高撤池或流动性操纵风险。", {"topLpHolderRatio": top_lp})
    if isinstance(top10, (int, float)) and top10 > 0.7:
        add_factor(factors, "major_holder_concentration", "technical", "HIGH", 35, "Top holders 占比过高", "大户占比过高会带来砸盘、操纵和流动性冲击风险。", {"top10HolderRatio": top10})
    if isinstance(major, (int, float)) and major > 0.5:
        add_factor(factors, "major_holder_ratio_high", "technical", "MEDIUM", 25, "大股东比例较高", "主要持有人集中可能带来市场波动和中心化风险。", {"majorHolderRatio": major})
