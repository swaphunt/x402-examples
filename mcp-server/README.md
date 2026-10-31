# SwapHunt MCP server

<!-- mcp-name: io.github.swaphunt/swaphunt-mcp -->

An [MCP](https://modelcontextprotocol.io) server that gives Claude and other AI agents 20 SwapHunt tools: prices, market regime, volatility, sentiment, derivatives, macro events and anti-FOMO sanity checks. The agent pays per call in USDC on Base via x402, from a wallet you control, with a spending cap per session.

Every tool description states its price, so the agent can see what a call costs before making it.

```bash
uvx swaphunt-mcp            # needs uv: https://docs.astral.sh/uv/
```

## Tools

| Tool | Price | Tool | Price |
|---|---|---|---|
| `get_spending` | free | `get_volatility` | $0.002 |
| `get_price` | $0.001 | `get_trading_session` | $0.001 |
| `get_prices` | $0.003 | `get_macro_events` | $0.003 |
| `get_fear_greed` | $0.001 | `get_funding_rates` | $0.003 |
| `get_market_overview` | $0.002 | `get_liquidations` | $0.003 |
| `get_alt_season` | $0.003 | `is_this_a_dip` | $0.003 |
| `get_momentum_rank` | $0.003 | `is_this_a_breakout` | $0.003 |
| `get_crypto_news` | $0.005 | `is_this_oversold` | $0.003 |
| `get_sentiment_summary` | $0.003 | `how_late_am_i` | $0.003 |
| `get_market_regime` | $0.002 | `is_price_extended` | $0.003 |
| `get_chop_detection` | $0.003 | | |

`get_spending` is free and shows what the session has spent and how much budget is left.

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

Tool results include third-party text (news headlines). The spending cap and price checks still apply whatever the agent is told.

## Claude Code

```bash
claude mcp add swaphunt \
  --env X402_PAY=1 \
  --env PRIVATE_KEY_FILE=$HOME/.swaphunt-wallet.key \
  --env MAX_SPEND_USD=0.25 \
  -- uvx swaphunt-mcp
```

Then ask, for example: *"What's the crypto market mood today, and is BTC trending or chopping on the 4h chart?"*

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
