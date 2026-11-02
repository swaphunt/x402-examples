# Quickstart: your first paid x402 call

One call to SwapHunt's `/v1/market/fear-greed` endpoint for $0.001 in USDC on Base. No account and no API key: the payment is the credential.

The paid call itself is only a few lines.

**Python**

```python
import asyncio, os
from eth_account import Account
from x402 import x402Client
from x402.http.clients import x402HttpxClient
from x402.mechanisms.evm import EthAccountSigner
from x402.mechanisms.evm.exact.register import register_exact_evm_client

async def main():
    client = x402Client()
    register_exact_evm_client(client, EthAccountSigner(Account.from_key(os.environ["PRIVATE_KEY"])))
    async with x402HttpxClient(client) as http:
        print((await http.get("https://x402.swaphunt.dev/v1/market/fear-greed")).json())

asyncio.run(main())
```

**TypeScript**

```typescript
import { wrapFetchWithPaymentFromConfig } from "@x402/fetch";
import { ExactEvmScheme } from "@x402/evm";
import { privateKeyToAccount } from "viem/accounts";

const account = privateKeyToAccount(process.env.PRIVATE_KEY as `0x${string}`);
const fetchWithPayment = wrapFetchWithPaymentFromConfig(fetch, {
  schemes: [{ network: "eip155:8453", client: new ExactEvmScheme(account) }],
});
const res = await fetchWithPayment("https://x402.swaphunt.dev/v1/market/fear-greed");
console.log(await res.json());
```

The full quickstart adds a dry run, a spending cap and cost reporting:
[`python/quickstart.py`](python/quickstart.py) and [`typescript/quickstart.ts`](typescript/quickstart.ts).

## Before you start

Use a dedicated wallet with a few dollars of USDC on Base mainnet. Never your main wallet.
The facilitator pays the gas, so the wallet only needs USDC.

```bash
export PRIVATE_KEY=0x...   # or put it in ../.env (see ../.env.example)
```

The scripts never pay unless you ask them to:

| Setting | Default | Effect |
|---|---|---|
| `--pay` or `X402_PAY=1` | off | Without it, the script only shows the price (dry run). |
| `MAX_SPEND_USD` | `0.10` | The script refuses to pay a price above this. |

## Python

Requires Python 3.10+.

```bash
cd python
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python quickstart.py          # dry run
.venv/bin/python quickstart.py --pay    # pays $0.001
```

## TypeScript

Requires Node.js 22.18+ (runs `.ts` files directly, no build step).

```bash
cd typescript
npm install
node quickstart.ts          # dry run
node quickstart.ts --pay    # pays $0.001
```

## Expected output

Dry run (both languages):

```
Price: $0.001 USDC on eip155:8453, payTo 0x<swaphunt-address>
Dry run: nothing paid. Re-run with --pay to pay.
```

Paid call (Python; TypeScript prints the same data as a JS object):

```
Price: $0.001 USDC on eip155:8453, payTo 0x<swaphunt-address>
200 {'value': 30, 'label': 'Fear', 'timestamp': '2026-10-31T00:00:00', 'source': 'alternative.me', 'attribution': 'Data provided by Alternative.me Crypto Fear & Greed Index'}
This run cost $0.001 (tx https://basescan.org/tx/0x<transaction-hash>)
```

Open the basescan link to see the USDC transfer on-chain.

## What happens under the hood

1. The script calls the endpoint without payment and gets `402 Payment Required`.
   The `PAYMENT-REQUIRED` header is base64 JSON with the price, network, asset and `payTo` address.
2. The x402 client signs a USDC transfer authorization (EIP-3009) for exactly that amount.
3. The script retries with the signed payment in the `PAYMENT-SIGNATURE` header.
4. A facilitator (Coinbase CDP) settles the payment on Base and the API returns `200` with the data.
   The `PAYMENT-RESPONSE` header contains the transaction hash.

All 19 endpoints and their prices: [`../docs/endpoints.md`](../docs/endpoints.md).
