# SwapHunt MCP server

<!-- mcp-name: io.github.swaphunt/swaphunt-mcp -->

An [MCP](https://modelcontextprotocol.io) server that gives Claude and other AI agents 19 paid SwapHunt tools: prices, BTC market regime, chop detection, volatility, expected move, funding rates and the Alt Season Index, all computed from Hyperliquid perpetuals (USDC-margined); plus the Crypto Fear & Greed Index (current, compared with earlier days, and daily history), the halving countdown, and the current trading session and weekend liquidity. The agent pays per call in USDC on Base via x402, from a wallet you control, with a spending cap per session.

Every tool description states its price, so the agent can see what a call costs before making it.

```bash
uvx swaphunt-mcp            # needs uv: https://docs.astral.sh/uv/
```

## Tools

| Tool | Price | What it returns |
|---|---|---|
| `get_spending` | free | What the session has spent and how much budget is left |
| `get_fear_greed` | $0.001 | Crypto Fear & Greed Index (0-100) with its label |
| `get_fear_greed_compare` | $0.002 | The index now vs yesterday, 7 and 30 days ago, with the changes |
| `get_fear_greed_history` | $0.005 | Daily index values for up to 365 days |
| `get_halving` | $0.001 | Halving countdown for BTC or LTC |
| `get_trading_session` | $0.001 | Current trading session and its typical volatility |
| `get_weekend_liquidity` | $0.001 | Weekend or low-liquidity window, with a 0-100 liquidity score |

### From Hyperliquid perpetuals (USDC-margined)

These tools are computed from Hyperliquid perpetuals, and every result has `"source": "Hyperliquid perpetuals"`. Prices are in USDC (`USD` and `USDT` are accepted as aliases). Funding is settled hourly; the annualized rate is the hourly rate x 8760.

| Tool | Price | What it returns |
|---|---|---|
| `get_price` | $0.001 | One asset's price in USDC (`price_type` `mark` or `mid`), 24h change and volume |
| `get_prices` | $0.003 | Prices for up to 20 assets in one call |
| `get_supported_assets` | $0.001 | Every asset the price tools can quote (all active Hyperliquid perps) |
| `get_market_regime` | $0.002 | BTC regime (BULLISH/BEARISH/NEUTRAL) from price vs the 12h EMA20 |
| `get_chop_detection` | $0.003 | Trending or chopping (ADX, +DI/-DI) on 1h, 4h or 1d |
| `get_volatility` | $0.002 | Realized volatility over 7d, 14d or 30d with a low/normal/high/extreme level |
| `get_market_silence` | $0.002 | Market-silence score 0-1 (low volume, low volatility, small moves) |
| `get_compression_alert` | $0.003 | Volatility squeeze (Bollinger band width percentile) on 1h, 4h or 1d |
| `get_expected_move` | $0.003 | ATR-based 68% and 95% price ranges for 4h, 1d or 1w |
| `get_funding_rates` | $0.003 | Current hourly funding for up to 20 coins, annualized, with 7d/30d averages |
| `get_top_funding_rates` | $0.003 | The most positive or most negative funding rates across all perps |
| `get_funding_history` | $0.004 | Hourly funding history for one coin, up to 365 days, with percentile of the latest rate |
| `get_alt_season` | $0.003 | SwapHunt Alt Season Index (0-100): share of top perps beating BTC over 90 days |

Fear & Greed results include an `attribution` field. Alternative.me, the source of the index, asks for that text next to its data, and the tool descriptions tell the agent to include it.

## Setup

Use a dedicated wallet with a few dollars of USDC on Base mainnet. Never your main wallet.

Store the wallet key in a file only you can read, so it never sits in a config file:

```bash
install -m 600 /dev/null ~/.swaphunt-wallet.key
nano ~/.swaphunt-wallet.key        # paste the private key, save
```

The server runs with [uv](https://docs.astral.sh/uv/)'s `uvx`, which downloads it from PyPI into its own environment. There is nothing to clone or install by hand. Try it without a wallet first: with no settings, every tool is a dry run.

## Settings

| Variable | Default | Effect |
|---|---|---|
| `X402_PAY` | off | Without `X402_PAY=1`, every tool runs as a dry run: it reports the price and returns no data. |
| `PRIVATE_KEY_FILE` | | Path to a file with the wallet's private key (recommended). |
| `PRIVATE_KEY` | | The key itself, if you prefer an environment variable. |
| `MAX_SPEND_USD` | `0.10` | Spending cap for the session (one server process). Calls beyond it are refused, not paid. |

Each payment is also locked to the price, asset (USDC), network (Base) and `payTo` address the API quoted for that call, and a tool refuses to pay more than the price in its description. If a call fails after the payment was sent, it still counts against the cap and is reported as "possibly paid".

## Claude Code

```bash
claude mcp add swaphunt \
  --env X402_PAY=1 \
  --env PRIVATE_KEY_FILE=$HOME/.swaphunt-wallet.key \
  --env MAX_SPEND_USD=0.25 \
  -- uvx swaphunt-mcp
```

Then ask, for example:

- *"What's the crypto market mood today, how has it changed over the past month, and how long until the next Bitcoin halving?"*
- *"What are BTC, ETH and SOL trading at, and is BTC in a bullish or bearish regime right now?"*
- *"Is ETH chopping or trending on the 4h chart, and is its volatility compressing?"*
- *"Which coins have the most crowded longs by funding, and is BTC's current funding unusual compared with the last 90 days?"*
- *"How far could SOL move today, and are we in alt season?"*

## Claude Desktop

Add this to `claude_desktop_config.json` (Settings → Developer → Edit Config) and restart Claude Desktop:

```json
{
  "mcpServers": {
    "swaphunt": {
      "command": "uvx",
      "args": ["swaphunt-mcp"],
      "env": {
        "X402_PAY": "1",
        "PRIVATE_KEY_FILE": "/home/you/.swaphunt-wallet.key",
        "MAX_SPEND_USD": "0.25"
      }
    }
  }
}
```

If Claude Desktop can't find `uvx`, use its full path (`which uvx` on macOS/Linux, `where uvx` on Windows).

## What a tool call returns

Paid:

```json
{
  "data": {"value": 30, "label": "Fear", "timestamp": "2026-10-31T00:00:00", "source": "alternative.me", "...": "..."},
  "cost_usd": 0.001,
  "session_spent_usd": 0.001,
  "session_remaining_usd": 0.099,
  "tx": "https://basescan.org/tx/0x<transaction-hash>"
}
```

Dry run (no `X402_PAY=1`):

```json
{"dry_run": true, "would_cost_usd": 0.001, "network": "eip155:8453",
 "note": "Dry run, nothing paid and no data. The user can set X402_PAY=1 to enable payments."}
```

When the cap is reached:

```json
{"error": "Session spending cap reached: $0.002 spent of MAX_SPEND_USD=$0.0025; this call costs $0.001. Restart the server or raise MAX_SPEND_USD."}
```

## Run from source

```bash
git clone https://github.com/swaphunt/x402-examples.git
cd x402-examples/mcp-server
uv run swaphunt-mcp            # or: uv run swaphunt-mcp --check
```

## For maintainers

`uvx swaphunt-mcp --check` compares every tool's advertised price with the live API. It pays nothing.

Source, issues and the other x402 examples (quickstart, daily brief, alert bot): [github.com/swaphunt/x402-examples](https://github.com/swaphunt/x402-examples).

Nothing here is investment advice.
