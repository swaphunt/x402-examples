# SwapHunt x402 examples

[SwapHunt](https://swaphunt.dev)'s x402 API sells crypto market context per call (prices, market regime, volatility, funding, coin strength vs BTC and anti-FOMO sanity checks computed from Hyperliquid perpetuals, alt season, the Crypto Fear & Greed Index, the halving countdown, trading session and weekend liquidity), paid in USDC on Base, Polygon, Arbitrum or Solana with the [x402 protocol](https://x402.org). No account, no API key: the payment is the credential.

The examples pay on Base. Every endpoint has the same price on all four networks; see [docs/endpoints.md](docs/endpoints.md) for the network list.

These examples get you from zero to a paid call in a few minutes, and show how to build on it.

## Examples

| Example | Language | What it does | Cost per run |
|---|---|---|---|
| [quickstart](quickstart/) | Python, TypeScript | One paid call to `/v1/market/fear-greed` | $0.001 |
| [daily-brief](daily-brief/) | Python | Fear & Greed with its 1, 7 and 30-day changes, halving countdown, trading session and weekend liquidity, summarized by an LLM and delivered to stdout, Telegram, Discord or email | $0.005 + LLM tokens |
| [mcp-server](mcp-server/) | Python (`uvx swaphunt-mcp`) | 30 SwapHunt tools (Hyperliquid prices, regime, volatility, funding, coin strength, dip/breakout/FOMO checks; Fear & Greed) for Claude and other AI agents, paid per call with a session cap | $0.001-0.005 per tool call |
| [alert-bot](alert-bot/) | Python | Checks one price on an interval and messages you on Telegram when it crosses a threshold | $0.001 per check |

The API has 30 paid endpoints, from $0.001 to $0.005 per call; the live list with parameters is in the [OpenAPI docs](https://x402.swaphunt.dev/docs). Prices, parameters and example responses for the core endpoints: [docs/endpoints.md](docs/endpoints.md).

Fear & Greed data comes from Alternative.me, which asks for attribution next to its data. The responses include an `attribution` field with the text to show.

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
- **Pinned receiving address (MCP server).** `PAYTO_ALLOWLIST=0xD6b585DD2F48263D08FB75EA28c1598d845d23a8` makes the MCP server refuse, before signing, any 402 that asks for payment to another address. See [mcp-server](mcp-server/#pinning-the-receiving-address).
- **Never commit keys.** Put `PRIVATE_KEY` and API keys in `.env` (ignored by git), using [.env.example](.env.example) as the template.

## Tests

The MCP server is tested against a local fake of the API, with no real money and no network:

```bash
python -m venv .venv && .venv/bin/pip install -r tests/requirements.txt
.venv/bin/python -m pytest tests
```

## Links

- SwapHunt: [swaphunt.dev](https://swaphunt.dev)
- API base URL: `https://x402.swaphunt.dev` (OpenAPI docs at [/docs](https://x402.swaphunt.dev/docs))
- x402 protocol: [x402.org](https://x402.org)

## License

[MIT](LICENSE)

Nothing here is investment advice.
