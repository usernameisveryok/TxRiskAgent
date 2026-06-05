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
