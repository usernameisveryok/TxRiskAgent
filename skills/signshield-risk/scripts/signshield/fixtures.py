TOKEN_FIXTURES = {
    (56, "0x55d398326f99059ff775485246999027b3197955"): {
        "symbol": "USDT",
        "name": "Tether USD",
        "decimals": 18,
    },
    (1, "0x1000000000000000000000000000000000000001"): {
        "symbol": "LAB-USDC",
        "name": "Synthetic USDC Fixture",
        "decimals": 6,
    },
    (1, "0x1000000000000000000000000000000000000002"): {
        "symbol": "LAB-DAI",
        "name": "Synthetic DAI Fixture",
        "decimals": 18,
    },
    (1, "0x1000000000000000000000000000000000000003"): {
        "symbol": "LAB-WETH",
        "name": "Synthetic WETH Fixture",
        "decimals": 18,
    },
    (10, "0x1000000000000000000000000000000000000004"): {
        "symbol": "LAB-OP",
        "name": "Synthetic Optimism Token Fixture",
        "decimals": 18,
    },
    (137, "0x1000000000000000000000000000000000000005"): {
        "symbol": "LAB-USDC",
        "name": "Synthetic Polygon USDC Fixture",
        "decimals": 6,
    },
    (42161, "0x1000000000000000000000000000000000000006"): {
        "symbol": "LAB-GOV",
        "name": "Synthetic Governance Token Fixture",
        "decimals": 18,
    },
    (8453, "0x1000000000000000000000000000000000000007"): {
        "symbol": "LAB-USDbC",
        "name": "Synthetic Base Stablecoin Fixture",
        "decimals": 6,
    },
    (1, "0x1000000000000000000000000000000000000101"): {
        "symbol": "LAB-HIDDEN",
        "name": "Synthetic Hidden Owner Token",
        "decimals": 18,
    },
    (1, "0x1000000000000000000000000000000000000102"): {
        "symbol": "LAB-MINT",
        "name": "Synthetic Mintable Owner Token",
        "decimals": 18,
    },
    (1, "0x1000000000000000000000000000000000000103"): {
        "symbol": "LAB-TAX",
        "name": "Synthetic High Tax Token",
        "decimals": 18,
    },
    (1, "0x1000000000000000000000000000000000000104"): {
        "symbol": "LAB-SELL",
        "name": "Synthetic Cannot Sell All Token",
        "decimals": 18,
    },
    (1, "0x1000000000000000000000000000000000000105"): {
        "symbol": "LAB-HONEY",
        "name": "Synthetic Blacklist Honeypot Token",
        "decimals": 18,
    },
    (1, "0x1000000000000000000000000000000000000106"): {
        "symbol": "LAB-PROXY",
        "name": "Synthetic Unverified Proxy Token",
        "decimals": 18,
    },
    (1, "0x1000000000000000000000000000000000000107"): {
        "symbol": "LAB-LP",
        "name": "Synthetic LP Unlocked Token",
        "decimals": 18,
    },
}

ADDRESS_FIXTURES = {
    (56, "0xfead9619e88464e5ad1ea9df458dcc147f03ea0c"): {
        "label": "Atlantis Loans proxy",
        "risk": "known_malicious_proxy",
        "summary": "该 Proxy 已被治理攻击篡改为恶意合约。",
        "source": "local_demo_fixture",
    },
    (1, "0x3000000000000000000000000000000000000001"): {
        "label": "Synthetic drainer spender",
        "risk": "known_malicious_proxy",
        "summary": "本地攻击实验 fixture：模拟钓鱼页面诱导用户授予恶意 spender 大额 ERC20 权限。",
        "source": "local_attack_fixture",
    },
    (1, "0x3000000000000000000000000000000000000002"): {
        "label": "Synthetic asset-drain recipient",
        "risk": "known_malicious_proxy",
        "summary": "本地攻击实验 fixture：模拟资金归集/接收地址，不代表真实链上归属。",
        "source": "local_attack_fixture",
    },
    (10, "0x3000000000000000000000000000000000000010"): {
        "label": "Synthetic cross-chain drainer",
        "risk": "known_malicious_proxy",
        "summary": "本地攻击实验 fixture：模拟跨链领取页面的恶意授权 spender。",
        "source": "local_attack_fixture",
    },
    (137, "0x3000000000000000000000000000000000000137"): {
        "label": "Synthetic NFT drainer operator",
        "risk": "known_malicious_proxy",
        "summary": "本地攻击实验 fixture：模拟 NFT 假空投页面的全集授权 operator。",
        "source": "local_attack_fixture",
    },
    (42161, "0x3000000000000000000000000000000000004216"): {
        "label": "Synthetic governance hijack helper",
        "risk": "known_malicious_proxy",
        "summary": "本地攻击实验 fixture：模拟治理/闪电贷攻击辅助合约入口。",
        "source": "local_attack_fixture",
    },
    (8453, "0x3000000000000000000000000000000000008453"): {
        "label": "Synthetic Base drainer",
        "risk": "known_malicious_proxy",
        "summary": "本地攻击实验 fixture：模拟 Base 链假迁移页面的恶意接收/授权地址。",
        "source": "local_attack_fixture",
    },
}

DOMAIN_FIXTURES = {
    "http://127.0.0.1:5173": {
        "label": "local demo origin",
        "risk": "local_demo",
        "severity": "low",
    }
}

TOKEN_RISK_FIXTURES = {
    (1, "0x1000000000000000000000000000000000000001"): {
        "tokenSecurity": {"sourceVerified": True, "ownershipRenounced": False, "mintable": True, "taxMutable": True},
        "marketControls": {"buyTaxBps": 0, "sellTaxBps": 0, "canBuy": True, "canSell": True, "cannotSellAll": False},
        "holderAndLiquidity": {"top10HolderRatio": 0.42, "lpLockedRatio": 0.8, "topLpHolderRatio": 0.2},
        "deployment": {"ageDays": 3, "deployer": "0x5000000000000000000000000000000000000001", "owner": "0x5000000000000000000000000000000000000002"},
    },
    (1, "0x1000000000000000000000000000000000000002"): {
        "tokenSecurity": {"sourceVerified": True, "ownershipRenounced": False, "hiddenOwner": True, "canRegainOwnership": True},
        "marketControls": {"canBuy": True, "canSell": True, "cannotSellAll": False},
    },
    (1, "0x1000000000000000000000000000000000000003"): {
        "tokenSecurity": {"sourceVerified": True, "ownershipRenounced": True},
        "marketControls": {"canBuy": True, "canSell": True, "cannotSellAll": False},
    },
    (10, "0x1000000000000000000000000000000000000004"): {
        "tokenSecurity": {"sourceVerified": False, "externalCallPresent": True},
        "marketControls": {"canBuy": True, "canSell": True, "cannotSellAll": False},
    },
    (8453, "0x1000000000000000000000000000000000000007"): {
        "tokenSecurity": {"sourceVerified": True, "isProxy": True, "implementationVerified": False, "ownershipRenounced": False},
        "marketControls": {"buyTaxBps": 0, "sellTaxBps": 1200, "canBuy": True, "canSell": True, "cannotSellAll": False},
        "holderAndLiquidity": {"lpLockedRatio": 0.1, "topLpHolderRatio": 0.82},
    },
    (1, "0x1000000000000000000000000000000000000101"): {
        "tokenSecurity": {"sourceVerified": True, "ownershipRenounced": True, "hiddenOwner": True},
        "marketControls": {"canBuy": True, "canSell": True, "cannotSellAll": False},
    },
    (1, "0x1000000000000000000000000000000000000102"): {
        "tokenSecurity": {"sourceVerified": True, "ownershipRenounced": False, "mintable": True},
        "marketControls": {"canBuy": True, "canSell": True, "cannotSellAll": False},
    },
    (1, "0x1000000000000000000000000000000000000103"): {
        "tokenSecurity": {"sourceVerified": True, "ownershipRenounced": False, "taxMutable": True},
        "marketControls": {"buyTaxBps": 300, "sellTaxBps": 1800, "canBuy": True, "canSell": True, "cannotSellAll": False},
    },
    (1, "0x1000000000000000000000000000000000000104"): {
        "tokenSecurity": {"sourceVerified": True, "ownershipRenounced": False},
        "marketControls": {"canBuy": True, "canSell": True, "cannotSellAll": True, "antiWhaleEnabled": True, "antiWhaleMutable": True},
    },
    (1, "0x1000000000000000000000000000000000000105"): {
        "tokenSecurity": {"sourceVerified": False, "ownershipRenounced": False, "blacklistEnabled": True, "whitelistEnabled": True},
        "marketControls": {"canBuy": True, "canSell": False, "cannotSellAll": True},
    },
    (1, "0x1000000000000000000000000000000000000106"): {
        "tokenSecurity": {"sourceVerified": True, "isProxy": True, "implementationVerified": False, "ownershipRenounced": False},
        "marketControls": {"canBuy": True, "canSell": True, "cannotSellAll": False},
    },
    (1, "0x1000000000000000000000000000000000000107"): {
        "tokenSecurity": {"sourceVerified": True, "ownershipRenounced": True},
        "marketControls": {"canBuy": True, "canSell": True, "cannotSellAll": False},
        "holderAndLiquidity": {"majorHolderRatio": 0.62, "top10HolderRatio": 0.82, "lpLockedRatio": 0.05, "topLpHolderRatio": 0.91},
    },
}

BYTECODE_FIXTURES = {
    (1, "0x1000000000000000000000000000000000000101"): "0x600035f2fde38b",
    (1, "0x1000000000000000000000000000000000000102"): "0x60003540c10f19",
    (1, "0x1000000000000000000000000000000000000103"): "0x6000353a7b36f4",
    (1, "0x1000000000000000000000000000000000000104"): "0x600035a2e62045ce4b2f7b",
    (1, "0x1000000000000000000000000000000000000105"): "0x600035f9f92be4a8f9e2d0f1ff",
    (1, "0x1000000000000000000000000000000000000106"): "0x600035f4",
    (1, "0x1000000000000000000000000000000000000107"): "0x600035",
}
