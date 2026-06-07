const snapId = 'local:http://localhost:8081';
const outputGrid = document.querySelector('#output-grid');
const constructedOutput = document.querySelector('#constructed-output');
const scanOutput = document.querySelector('#scan-output');
const connectButton = document.querySelector('#connect');
const claimAirdropButton = document.querySelector('#claim-airdrop');
const approveBscUsdtButton = document.querySelector('#approve-bsc-usdt');
const sendCustomButton = document.querySelector('#send-custom');
const customAddressInput = document.querySelector('#custom-address');
const endpointSelect = document.querySelector('#endpoint-select');
const networkSelect = document.querySelector('#network-select');
const sendModeToggle = document.querySelector('#send-mode');
const previewModeButton = document.querySelector('#preview-mode');
const sendModeButton = document.querySelector('#send-mode-button');
const scenarioButtons = document.querySelectorAll('[data-scenario]');

const txRiskEndpoints = {
  local: {
    label: 'Local dev',
    url: 'http://localhost:8000/tx-scan',
    apiKey: 'test-key',
  },
  prod: {
    label: 'Remote prod',
    url: 'http://43.137.17.169/tx-scan',
    apiKey: 'test-key',
  },
};
const txRiskRequestTimeoutMs = 300_000;
const fakeAirdropTokenAddress = '0x1000000000000000000000000000000000000001';
const fakeAirdropSpenderAddress = '0x3000000000000000000000000000000000000001';
const pointOneNativeTokenInWeiHex = '0x16345785d8a0000';
const uint256MaxHex =
  '0xffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff';
const ethMainnetChainId = '0x1';
const bscChainId = '0x38';
const nativeNetworks = {
  eth: {
    label: 'ETH',
    chainId: ethMainnetChainId,
    nativeSymbol: 'ETH',
  },
  bnb: {
    label: 'BNB',
    chainId: bscChainId,
    nativeSymbol: 'BNB',
    addEthereumChain: {
      chainId: bscChainId,
      chainName: 'BNB Smart Chain',
      nativeCurrency: {
        name: 'BNB',
        symbol: 'BNB',
        decimals: 18,
      },
      rpcUrls: ['https://bsc-dataseed.binance.org/'],
      blockExplorerUrls: ['https://bscscan.com'],
    },
  },
};
const bscUsdtAddress = '0x55d398326f99059fF775485246999027B3197955';
const atalisLoanAddress = '0xfEAd9619e88464e5aD1Ea9Df458dcc147F03ea0C';
const tenUsdtWith18DecimalsHex = '0x8ac7230489e80000';
let snapConnected = false;

const representativeRequests = {
  'nft-revoke': {
    label: 'NFT approval revoke',
    category: 'benign',
    expected: 'setApprovalForAll(operator, false) should read as a low-risk revoke.',
    payload: {
      chainId: 'eip155:1',
      transactionOrigin: 'https://wallet-revoke.invalid',
      transaction: {
        from: '0xb7c360aaa4c2b9f727ff934baa6ba300ccc0f284',
        to: '0x2000000000000000000000000000000000000001',
        data:
          '0xa22cb46500000000000000000000000030000000000000000000000000000000000000010000000000000000000000000000000000000000000000000000000000000000',
        value: '0x0',
        type: '0x2',
        gas: '0x30d40',
        maxFeePerGas: '0x8af56a60',
        maxPriorityFeePerGas: '0x77359400',
      },
    },
  },
  'erc20-unlimited': {
    label: 'ERC20 unlimited approval phishing',
    category: 'harmful',
    expected: 'approve(spender, uint256.max) to a synthetic drainer should be high risk.',
    payload: {
      chainId: 'eip155:1',
      transactionOrigin: 'https://claim-rewards.invalid',
      transaction: {
        from: '0xb7c360aaa4c2b9f727ff934baa6ba300ccc0f284',
        to: '0x1000000000000000000000000000000000000001',
        data:
          '0x095ea7b30000000000000000000000003000000000000000000000000000000000000001ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff',
        value: '0x0',
        type: '0x2',
        gas: '0x30d40',
        maxFeePerGas: '0x8af56a60',
        maxPriorityFeePerGas: '0x77359400',
      },
    },
  },
  'nft-approve-all': {
    label: 'NFT approve all fake airdrop',
    category: 'harmful',
    expected: 'setApprovalForAll(operator, true) to a synthetic drainer should be high risk.',
    payload: {
      chainId: 'eip155:137',
      transactionOrigin: 'https://polygon-nft-claim.invalid',
      transaction: {
        from: '0xb7c360aaa4c2b9f727ff934baa6ba300ccc0f284',
        to: '0x2000000000000000000000000000000000000137',
        data:
          '0xa22cb46500000000000000000000000030000000000000000000000000000000000001370000000000000000000000000000000000000000000000000000000000000001',
        value: '0x0',
        type: '0x2',
        gas: '0x30d40',
        maxFeePerGas: '0x8af56a60',
        maxPriorityFeePerGas: '0x77359400',
      },
    },
  },
  'hidden-multicall': {
    label: 'Hidden multicall approval and transfer',
    category: 'harmful',
    expected: 'A multicall hiding unlimited approval and transfer should be high risk.',
    payload: {
      chainId: 'eip155:1',
      transactionOrigin: 'https://bundle-claim.invalid',
      transaction: {
        from: '0xb7c360aaa4c2b9f727ff934baa6ba300ccc0f284',
        to: '0x3000000000000000000000000000000000000001',
        data:
          '0xac9650d800000000000000000000000000000000000000000000000000000000000000200000000000000000000000000000000000000000000000000000000000000002000000000000000000000000000000000000000000000000000000000000006000000000000000000000000000000000000000000000000000000000000000e00000000000000000000000000000000000000000000000000000000000000044095ea7b30000000000000000000000003000000000000000000000000000000000000001ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000044a9059cbb0000000000000000000000003000000000000000000000000000000000000002000000000000000000000000000000000000000000000000000000003b9aca0000000000000000000000000000000000000000000000000000000000',
        value: '0x0',
        type: '0x2',
        gas: '0x30d40',
        maxFeePerGas: '0x8af56a60',
        maxPriorityFeePerGas: '0x77359400',
      },
    },
  },
  'native-drainer': {
    label: 'Native transfer to synthetic drainer',
    category: 'harmful',
    expected: 'A native transfer to a synthetic drainer address should be high risk.',
    payload: {
      chainId: 'eip155:8453',
      transactionOrigin: 'https://support-case.invalid',
      transaction: {
        from: '0xb7c360aaa4c2b9f727ff934baa6ba300ccc0f284',
        to: '0x3000000000000000000000000000000000008453',
        data: '0x',
        value: '0x6f05b59d3b20000',
        type: '0x2',
        gas: '0x5208',
        maxFeePerGas: '0x8af56a60',
        maxPriorityFeePerGas: '0x77359400',
      },
    },
  },
};

const isSendMode = () => sendModeToggle.checked;

const formatOutput = (value) =>
  typeof value === 'string' ? value : JSON.stringify(value, null, 2);

const printConstructed = (value) => {
  constructedOutput.textContent = formatOutput(value);
};

const printScan = (value) => {
  scanOutput.textContent =
    typeof value === 'string' ? value : JSON.stringify(value, null, 2);
};

const print = (value) => {
  if (isSendMode()) {
    printConstructed(value);
    return;
  }
  printScan(value);
};

const syncOutputMode = () => {
  outputGrid.classList.toggle('send-mode', isSendMode());
  scanOutput.hidden = isSendMode();
  if (isSendMode() && constructedOutput.textContent === 'Waiting for transaction...') {
    printConstructed('Send mode enabled. Construct a transaction to open MetaMask.');
  }
};

const getProvider = () => {
  if (!window.ethereum) {
    throw new Error('MetaMask is not available in this browser.');
  }

  return window.ethereum;
};

const hexChainIdToCaip2 = (chainId) => `eip155:${Number.parseInt(chainId, 16)}`;

const getCurrentCaip2ChainId = async (provider) => {
  const chainId = await provider.request({ method: 'eth_chainId' });

  return hexChainIdToCaip2(chainId);
};

const getSelectedEndpoint = () => {
  const selectedKey = endpointSelect.value;

  return txRiskEndpoints[selectedKey] ?? txRiskEndpoints.local;
};

const getSelectedNativeNetwork = () => {
  const selectedKey = networkSelect.value;

  return nativeNetworks[selectedKey] ?? nativeNetworks.eth;
};

const syncSnapEndpoint = async () => {
  const provider = getProvider();
  const endpointKey = endpointSelect.value;

  return provider.request({
    method: 'wallet_invokeSnap',
    params: {
      snapId,
      request: {
        method: 'setEndpoint',
        params: {
          endpoint: endpointKey,
        },
      },
    },
  });
};

const scanTransactionRisk = async (payload) => {
  const endpoint = getSelectedEndpoint();
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), txRiskRequestTimeoutMs);
  const headers = {
    Accept: 'application/json',
    'Content-Type': 'application/json',
  };

  try {
    if (endpoint.apiKey) {
      headers['X-API-Key'] = endpoint.apiKey;
    }

    const response = await fetch(endpoint.url, {
      method: 'POST',
      headers,
      body: JSON.stringify(payload),
      signal: controller.signal,
    });

    if (!response.ok) {
      throw new Error(
        `${endpoint.label} TxRiskAgent API returned ${response.status}.`,
      );
    }

    return response.json();
  } catch (error) {
    if (error.name === 'AbortError') {
      throw new Error(
        `${endpoint.label} TxRiskAgent API timed out after ${Math.round(
          txRiskRequestTimeoutMs / 1000,
        )} seconds.`,
      );
    }
    throw error;
  } finally {
    clearTimeout(timeout);
  }
};

const selectRiskReportFields = (risk) => ({
  schemaVersion: risk.schemaVersion,
  inputRef: risk.inputRef,
  verdict: risk.verdict,
  summary: risk.summary,
  intent: risk.intent,
  assetImpact: risk.assetImpact,
  riskFactors: risk.riskFactors,
  evidence: risk.evidence,
  recommendation: risk.recommendation,
});

const previewRiskReport = async (payload, context = {}) => {
  const endpoint = getSelectedEndpoint();

  printConstructed({
    status: 'Constructed transaction',
    mode: 'simulate',
    ...context,
    request: payload,
  });
  printScan({
    status: `Scanning transaction with TxRiskAgent (${endpoint.label})...`,
    endpoint: endpoint.url,
    ...context,
  });

  const risk = await scanTransactionRisk(payload);

  printScan({
    status: `TxRiskAgent API response (${endpoint.label})`,
    endpoint: endpoint.url,
    ...context,
    response: selectRiskReportFields(risk),
  });

  return risk;
};

const handleTransactionFlow = async (
  provider,
  transaction,
  context = {},
  submittedStatus = 'Transaction submitted',
) => {
  const payload = {
    chainId: await getCurrentCaip2ChainId(provider),
    transactionOrigin: context.transactionOrigin ?? window.location.origin,
    transaction,
  };
  const displayContext = { ...context };
  delete displayContext.transactionOrigin;

  if (!isSendMode()) {
    return previewRiskReport(payload, displayContext);
  }

  printConstructed({
    status: 'Constructed transaction',
    mode: 'send',
    ...displayContext,
    request: payload,
  });

  const txHash = await provider.request({
    method: 'eth_sendTransaction',
    params: [transaction],
  });

  printConstructed({
    status: submittedStatus,
    txHash,
    ...displayContext,
    request: payload,
  });

  return null;
};

const enableDemoActions = () => {
  claimAirdropButton.disabled = false;
  approveBscUsdtButton.disabled = false;
  sendCustomButton.disabled = false;
};

const isSnapsUnavailableError = (error) => {
  const message = String(error?.message ?? '').toLowerCase();

  return (
    error?.code === -32601 ||
    message.includes('wallet_requestsnaps') ||
    (message.includes('snaps') && message.includes('not available'))
  );
};

const getProviderClientVersion = async (provider) => {
  try {
    return await provider.request({ method: 'web3_clientVersion' });
  } catch {
    return 'unknown provider';
  }
};

const requestSnaps = async () => {
  const provider = getProvider();

  try {
    await provider.request({
      method: 'wallet_requestSnaps',
      params: {
        [snapId]: {},
      },
    });
    const endpoint = await syncSnapEndpoint();
    snapConnected = true;

    enableDemoActions();
    print({
      status: `Snap connected: ${snapId}`,
      endpoint,
    });
  } catch (error) {
    if (!isSnapsUnavailableError(error)) {
      throw error;
    }

    enableDemoActions();
    print({
      status: 'Snaps RPC unavailable; API-only demo enabled',
      provider: await getProviderClientVersion(provider),
      nextSteps: [
        'Use MetaMask Flask for local Snap installation.',
        'Disable or deprioritize other wallet extensions if this browser is not using MetaMask.',
        'Reload this page after switching wallet extensions, then connect the Snap again.',
        'You can still click Claim LAB-USDC airdrop here to test the TxRiskAgent page scan.',
      ],
    });
  }
};

const sendTransaction = async (to) => {
  const provider = getProvider();
  await switchToSelectedNativeNetwork();
  const network = getSelectedNativeNetwork();

  const accounts = await provider.request({
    method: 'eth_requestAccounts',
  });
  const from = accounts[0];

  if (!from) {
    throw new Error('No MetaMask account is connected.');
  }

  const transaction = {
    from,
    to,
    value: pointOneNativeTokenInWeiHex,
  };
  await handleTransactionFlow(provider, transaction, {
    network: network.label,
    asset: network.nativeSymbol,
  }, `Transaction submitted on ${network.label}`);
};

const padAddressForCalldata = (address) => address.slice(2).padStart(64, '0');

const padHexQuantityForCalldata = (value) => value.slice(2).padStart(64, '0');

const buildApproveCalldata = (spender, amount) =>
  `0x095ea7b3${padAddressForCalldata(spender)}${padHexQuantityForCalldata(
    amount,
  )}`;

const claimFakeAirdrop = async () => {
  const provider = getProvider();
  await switchToNetwork(nativeNetworks.eth);

  const accounts = await provider.request({
    method: 'eth_requestAccounts',
  });
  const from = accounts[0];

  if (!from) {
    throw new Error('No MetaMask account is connected.');
  }

  const transaction = {
    from,
    to: fakeAirdropTokenAddress,
    value: '0x0',
    data: buildApproveCalldata(fakeAirdropSpenderAddress, uint256MaxHex),
  };
  await handleTransactionFlow(provider, transaction, {
    transactionOrigin: window.location.origin,
    network: nativeNetworks.eth.label,
    scenario: 'Fake LAB-USDC airdrop claim',
  }, 'Airdrop claim transaction submitted');
};

const switchToNetwork = async (network) => {
  const provider = getProvider();

  try {
    await provider.request({
      method: 'wallet_switchEthereumChain',
      params: [{ chainId: network.chainId }],
    });
  } catch (error) {
    if (error.code !== 4902 || !network.addEthereumChain) {
      throw error;
    }

    await provider.request({
      method: 'wallet_addEthereumChain',
      params: [network.addEthereumChain],
    });
  }
};

const switchToSelectedNativeNetwork = async () => {
  await switchToNetwork(getSelectedNativeNetwork());
};

const switchToBsc = async () => {
  await switchToNetwork(nativeNetworks.bnb);
};

const approveBscUsdt = async () => {
  const provider = getProvider();
  await switchToBsc();

  const accounts = await provider.request({
    method: 'eth_requestAccounts',
  });
  const from = accounts[0];

  if (!from) {
    throw new Error('No MetaMask account is connected.');
  }

  const transaction = {
    from,
    to: bscUsdtAddress,
    value: '0x0',
    data: buildApproveCalldata(atalisLoanAddress, tenUsdtWith18DecimalsHex),
  };
  await handleTransactionFlow(provider, transaction, {}, 'Transaction submitted');
};

connectButton.addEventListener('click', async () => {
  try {
    await requestSnaps();
  } catch (error) {
    print(error.message);
  }
});

claimAirdropButton.addEventListener('click', async () => {
  try {
    await claimFakeAirdrop();
  } catch (error) {
    print(error.message);
  }
});

approveBscUsdtButton.addEventListener('click', async () => {
  try {
    await approveBscUsdt();
  } catch (error) {
    print(error.message);
  }
});

scenarioButtons.forEach((button) => {
  button.addEventListener('click', async () => {
    try {
      const request = representativeRequests[button.dataset.scenario];

      if (!request) {
        throw new Error('Unknown representative request.');
      }

      await previewRiskReport(JSON.parse(JSON.stringify(request.payload)), {
        scenario: request.label,
        category: request.category,
        expected: request.expected,
        mode: 'request preview',
      });
    } catch (error) {
      print(error.message);
    }
  });
});

endpointSelect.addEventListener('change', async () => {
  const endpoint = getSelectedEndpoint();

  if (!snapConnected) {
    print({
      status: `Selected TxRisk endpoint: ${endpoint.label}`,
      endpoint: endpoint.url,
    });
    return;
  }

  try {
    const snapEndpoint = await syncSnapEndpoint();

    print({
      status: 'Snap TxRisk endpoint updated',
      endpoint: snapEndpoint,
    });
  } catch (error) {
    print(error.message);
  }
});

sendModeToggle.addEventListener('change', () => {
  syncOutputMode();
  if (isSendMode()) {
    printConstructed('Send mode enabled. The page will open MetaMask directly without a pre-scan.');
    return;
  }
  printConstructed('Preview Risk enabled. Constructed transactions will appear here.');
  printScan('TxRiskAgent output will appear here.');
});

previewModeButton.addEventListener('click', () => {
  sendModeToggle.checked = false;
  sendModeToggle.dispatchEvent(new Event('change'));
});

sendModeButton.addEventListener('click', () => {
  sendModeToggle.checked = true;
  sendModeToggle.dispatchEvent(new Event('change'));
});

sendCustomButton.addEventListener('click', async () => {
  try {
    const to = customAddressInput.value.trim();

    if (!/^0x[a-fA-F0-9]{40}$/.test(to)) {
      throw new Error('Enter a valid 0x address.');
    }

    await sendTransaction(to);
  } catch (error) {
    print(error.message);
  }
});

try {
  syncOutputMode();
  getProvider();
  printScan('MetaMask detected. Select a TxRisk endpoint, then choose a transaction.');
} catch (error) {
  printScan(error.message);
}
