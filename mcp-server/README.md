# SwapHunt MCP server

<!-- mcp-name: io.github.swaphunt/swaphunt-mcp -->

An [MCP](https://modelcontextprotocol.io) server that gives Claude and other AI agents 30 paid SwapHunt tools: prices, BTC market regime, chop detection, volatility, expected move, funding rates, the Alt Season Index, coin strength, momentum and correlation vs BTC, and anti-FOMO sanity checks (is this a dip, a breakout, support, oversold; how late am I, pump age, extension, green-candle streak), all computed from Hyperliquid perpetuals (USDC-margined); plus the Crypto Fear & Greed Index (current, compared with earlier days, and daily history), the halving countdown, and the current trading session and weekend liquidity. The agent pays per call in USDC on Base via x402, from a wallet you control, with a spending cap per session.

Every tool description states its price, so the agent can see what a call costs before making it. Prices can change: the server reads the current prices from the API's price list, [`/.well-known/x402`](https://x402.swaphunt.dev/.well-known/x402), and the prices in the table below are the ones built into this release.

```bash
uvx swaphunt-mcp            # needs uv: https://docs.astral.sh/uv/
```

## Tools

| Tool | Price | What it returns |
|---|---|---|
| `get_spending` | free | What the session has spent and how much budget is left |
| `get_fear_greed` | $0.005 | Crypto Fear & Greed Index (0-100) with its label |
| `get_fear_greed_compare` | $0.002 | The index now vs yesterday, 7 and 30 days ago, with the changes |
| `get_fear_greed_history` | $0.005 | Daily index values for up to 365 days |
| `get_halving` | $0.001 | Halving countdown for BTC or LTC |
| `get_trading_session` | $0.005 | Current trading session and its typical volatility |
| `get_weekend_liquidity` | $0.005 | Weekend or low-liquidity window, with a 0-100 liquidity score |

### From Hyperliquid perpetuals (USDC-margined)

These tools are computed from Hyperliquid perpetuals, and every result has `"source": "Hyperliquid perpetuals"`. Prices are in USDC (`USD` and `USDT` are accepted as aliases). Funding is settled hourly; the annualized rate is the hourly rate x 8760.

| Tool | Price | What it returns |
|---|---|---|
| `get_price` | $0.005 | One asset's price in USDC (`price_type` `mark` or `mid`), 24h change and volume |
| `get_prices` | $0.003 | Prices for up to 20 assets in one call |
| `get_supported_assets` | $0.001 | Every asset the price tools can quote (all active Hyperliquid perps) |
| `get_market_regime` | $0.010 | BTC regime (BULLISH/BEARISH/NEUTRAL) from price vs the 12h EMA20 |
| `get_chop_detection` | $0.003 | Trending or chopping (ADX, +DI/-DI) on 1h, 4h or 1d |
| `get_volatility` | $0.010 | Realized volatility over 7d, 14d or 30d with a low/normal/high/extreme level |
| `get_market_silence` | $0.002 | Market-silence score 0-1 (low volume, low volatility, small moves) |
| `get_compression_alert` | $0.003 | Volatility squeeze (Bollinger band width percentile) on 1h, 4h or 1d |
| `get_expected_move` | $0.003 | ATR-based 68% and 95% price ranges for 4h, 1d or 1w |
| `get_funding_rates` | $0.015 | Current hourly funding for up to 20 coins, annualized, with 7d/30d averages |
| `get_top_funding_rates` | $0.003 | The most positive or most negative funding rates across all perps |
| `get_funding_history` | $0.004 | Hourly funding history for one coin, up to 365 days, with percentile of the latest rate |
| `get_alt_season` | $0.003 | SwapHunt Alt Season Index (0-100): share of top perps beating BTC over 90 days |

### Coin analysis and sanity checks (Hyperliquid perpetuals, top 50 coins)

These tools are also computed from Hyperliquid perpetuals (USDC-margined), with prices and levels in USDC. They cover the top 50 Hyperliquid perpetuals by 30-day volume (the `covered` list from `get_supported_assets`). For any other coin the API answers `422 not_covered` before asking for payment: nothing is charged, nothing counts against the session cap, and the tool returns the covered list so the agent can pick another coin.

| Tool | Price | What it returns |
|---|---|---|
| `get_coin_strength` | $0.015 | A coin's return minus BTC's over 24h, 7d or 30d, rated very_strong to very_weak |
| `get_momentum_rank` | $0.015 | Covered coins ranked by return over 24h, 7d or 30d: top and bottom performers |
| `get_correlation` | $0.003 | Pearson correlation of a coin's returns with BTC's over 7d or 30d |
| `is_this_a_dip` | $0.003 | Drop from the 14-day high vs the 14-day ATR: real dip or noise |
| `is_this_a_breakout` | $0.003 | Breakout through a price level up or down: confirmed or likely fakeout |
| `is_this_support` | $0.003 | Whether a price level is real support: touches, recency and bounce quality over 90 days |
| `is_this_oversold` | $0.003 | RSI(14) on 1h, 4h and 1d combined into a weighted RSI, with a verdict |
| `how_late_am_i` | $0.003 | How far a move has run from its 4h swing low, in % and ATR multiples |
| `get_pump_age` | $0.003 | Active pump detection on 15m candles: start, duration and size vs the average pump |
| `is_price_extended` | $0.003 | Distance from the 20 and 50 MA on 4h, Bollinger position and z-score |
| `get_green_candle_streak` | $0.003 | Current green-candle streak on 1h, 4h or 1d and how often the next candle was green |

An uncovered coin returns, for example:

```json
{"error": "not_covered", "charged": false,
 "message": "SEI is not covered yet. Covered: top 50 Hyperliquid perpetuals by 30-day volume. Nothing was paid. Retry with one of the covered coins.",
 "symbol": "SEI", "covered": ["AAVE", "ADA", "AERO", "...", "kPEPE"],
 "coverage_rule": "Top 50 Hyperliquid perpetuals by 30-day notional volume (stablecoins excluded), recomputed daily. ..."}
```

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
| `PAYTO_ALLOWLIST` | any | Comma-separated addresses the server may pay. A quote to any other `payTo` is refused before anything is signed. |

Each payment is also locked to the price, asset (USDC), network (Base) and `payTo` address the API quoted for that call, and a tool refuses to pay more than the advertised price. The advertised price comes from the API's price list at `/.well-known/x402` (fetched on the first paid call and again after an hour), so a price change needs no new release. If the list cannot be fetched, the price built into this release (the one in the tool description) is the limit. A call that costs more than `MAX_SPEND_USD` on its own is refused as well. If a call fails after the payment was sent, it still counts against the cap and is reported as "possibly paid".

`PAYTO_ALLOWLIST` adds a check you control: the server pays only addresses on your list. A dry run shows the address a call would pay (`pay_to`), so you can copy it from there. On 2026-11-09 SwapHunt's 402 responses on Base asked for payment to `0xD6b585DD2F48263D08FB75EA28c1598d845d23a8`. If SwapHunt ever changes its address, calls are refused until you update the list, which is the point.

## Claude Code

```bash
claude mcp add swaphunt \
  --env X402_PAY=1 \
  --env PRIVATE_KEY_FILE=$HOME/.swaphunt-wallet.key \
  --env MAX_SPEND_USD=0.25 \
  --env PAYTO_ALLOWLIST=0xD6b585DD2F48263D08FB75EA28c1598d845d23a8 \
  -- uvx swaphunt-mcp
```

Without the `--env` lines it runs as a dry run: `claude mcp add swaphunt -- uvx swaphunt-mcp`.

Then ask, for example:

- *"What's the crypto market mood today, how has it changed over the past month, and how long until the next Bitcoin halving?"*
- *"What are BTC, ETH and SOL trading at, and is BTC in a bullish or bearish regime right now?"*
- *"Is ETH chopping or trending on the 4h chart, and is its volatility compressing?"*
- *"Which coins have the most crowded longs by funding, and is BTC's current funding unusual compared with the last 90 days?"*
- *"How far could SOL move today, and are we in alt season?"*
- *"ETH dropped today. Is it a real dip or just noise, is it oversold, and how late would I be buying the bounce?"*
- *"SOL is pumping. How old is the pump, is it already extended, and is it stronger than BTC this week?"*

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
        "MAX_SPEND_USD": "0.25",
        "PAYTO_ALLOWLIST": "0xD6b585DD2F48263D08FB75EA28c1598d845d23a8"
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
 "pay_to": "0xD6b585DD2F48263D08FB75EA28c1598d845d23a8",
 "note": "Dry run, nothing paid and no data. The user can set X402_PAY=1 to enable payments."}
```

When the quote asks for an address that is not in `PAYTO_ALLOWLIST` (nothing is signed):

```json
{"error": "Refused: /v1/market/fear-greed asks for payment to 0x..., which is not in PAYTO_ALLOWLIST. Nothing was signed or paid."}
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

Tests run against a local fake API, with no money involved:

```bash
pip install -r tests/requirements.txt
python -m pytest tests -q
```

`python3 scripts/snapshot_402.py` refreshes `tests/fixtures/endpoints_402.json` from the live 402 responses (unpaid requests only); the contract test then checks every tool's route, price, parameters and defaults against it.

Source, issues and the other x402 examples (quickstart, daily brief, alert bot): [github.com/swaphunt/x402-examples](https://github.com/swaphunt/x402-examples).

Nothing here is investment advice.
