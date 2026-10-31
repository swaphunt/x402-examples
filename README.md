# SwapHunt x402 examples

[SwapHunt](https://swaphunt.dev)'s x402 API sells crypto market context per call (prices, regime, volatility, sentiment, funding, macro events, anti-FOMO checks), paid in USDC on Base with the [x402 protocol](https://x402.org). No account, no API key: the payment is the credential.

These examples get you from zero to a paid call in a few minutes, and show how to build on it.

## Examples

| Example | Language | What it does | Cost per run |
|---|---|---|---|
| [quickstart](quickstart/) | Python, TypeScript | One paid call to `/v1/market/fear-greed` | $0.001 |
| [daily-brief](daily-brief/) | Python | Four endpoints, summarized by an LLM, delivered to stdout, Telegram, Discord or email | $0.008 + LLM (Haiku 5.5: $0.0002) |

More examples (an MCP server for AI agents and an alert bot) are on the way.

All 42 endpoints with prices, parameters and example responses: [docs/endpoints.md](docs/endpoints.md). Prices range from $0.001 to $0.008 per call.

## Quickstart

You need a wallet with a few dollars of USDC on Base mainnet (see [Security](#security)).

```bash
git clone https://github.com/swaphunt/x402-examples.git
cd x402-examples/quickstart/python
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

.venv/bin/python quickstart.py          # dry run: shows the price, pays nothing

cp ../../.env.example ../../.env        # put your PRIVATE_KEY in ../../.env
set -a; . ../../.env; set +a
.venv/bin/python quickstart.py --pay    # pays $0.001
```

Output of the paid call:

```
Price: $0.001 USDC on eip155:8453, payTo 0x<swaphunt-address>
200 {'value': 30, 'label': 'Fear', 'timestamp': '2026-10-31T00:00:00', 'source': 'alternative.me', ...}
This run cost $0.001 (tx https://basescan.org/tx/0x<transaction-hash>)
```

The TypeScript version and a 10-line minimal snippet are in [quickstart/](quickstart/).

## How x402 works

1. You call an endpoint without paying and get `402 Payment Required`, with the price, network and receiving address in the `PAYMENT-REQUIRED` header.
2. Your x402 client signs a USDC transfer for exactly that amount.
3. You retry with the signed payment. A facilitator settles it on Base, and you get `200` with the data and the transaction hash.

The official x402 client libraries ([Python](https://pypi.org/project/x402/), [TypeScript](https://www.npmjs.com/package/@x402/fetch)) do steps 2 and 3 for you.

## Security

- **Use a dedicated wallet with a few dollars of USDC on Base mainnet. Never your main wallet.** The facilitator pays the gas, so the wallet only needs USDC.
- **Dry run by default.** Every example shows what it would pay and stops. It only pays with `--pay` or `X402_PAY=1`.
- **Spending cap.** Every example refuses to spend more than `MAX_SPEND_USD` per run (default $0.10) and prints what the run cost.
- **Never commit keys.** Put `PRIVATE_KEY` and API keys in `.env` (ignored by git), using [.env.example](.env.example) as the template.

## Links

- SwapHunt: [swaphunt.dev](https://swaphunt.dev)
- API base URL: `https://x402.swaphunt.dev` (OpenAPI docs at [/docs](https://x402.swaphunt.dev/docs))
- x402 protocol: [x402.org](https://x402.org)

## License

[MIT](LICENSE)

Nothing here is investment advice.
