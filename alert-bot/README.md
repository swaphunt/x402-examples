# Alert bot

Checks one price at a fixed interval, paying $0.005 per check with x402, and sends you a Telegram message when it crosses your threshold. One endpoint, one threshold, one channel.

| | |
|---|---|
| Endpoint | `/v1/tools/price` ($0.005 per check) |
| Threshold | `ALERT_BELOW` or `ALERT_ABOVE` (set exactly one) |
| Delivery | Telegram |
| Cost | $0.005 per check: $0.48/day and $14.40/month at 15 minutes; $0.12/day and $3.60/month at 60 minutes |

It alerts once when the price crosses the threshold, and again only after the price has gone back and crossed again. The last state is kept in a small file (`.alert-state.json` next to the script, or `ALERT_STATE_FILE`), so this also works when cron starts a new process for every check. Changing the asset or threshold starts fresh. If Telegram delivery fails, the next check tries again.

Tested end to end on 31 October 2026: paid checks on Base mainnet, a real Telegram message on the first crossing, and no message on the next `--once` run.

## Setup

Use a dedicated wallet with a few dollars of USDC on Base mainnet. Never your main wallet.

1. Create a Telegram bot with [@BotFather](https://t.me/BotFather) and copy its token.
2. Send your bot a message, then open `https://api.telegram.org/bot<token>/getUpdates` and copy `chat.id`.
3. Install and configure:

```bash
cd alert-bot
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp ../.env.example ../.env    # fill in PRIVATE_KEY, TELEGRAM_*, ALERT_*
```

## Run

```bash
set -a; . ../.env; set +a
.venv/bin/python alert.py                 # dry run: shows price per check and cost per day
.venv/bin/python alert.py --pay           # polls every ALERT_INTERVAL_MIN minutes
.venv/bin/python alert.py --pay --once    # one check, then exit (for cron)
```

## Settings

| Variable | Default | |
|---|---|---|
| `ALERT_ASSET` | `BTC` | Any Hyperliquid perp symbol `/v1/tools/price` supports |
| `ALERT_BELOW` / `ALERT_ABOVE` | | Price level in USDC (Hyperliquid mark price); set exactly one |
| `ALERT_INTERVAL_MIN` | `15` | Minutes between checks |
| `MAX_SPEND_USD` | `0.10` | Cap per run; the bot stops before exceeding it (about 20 checks) |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | | Where alerts go |
| `ALERT_STATE_FILE` | `.alert-state.json` next to `alert.py` | Remembers whether the last check was already past the threshold |

Running continuously at 15 minutes, the default cap of $0.10 lasts about 5 hours. Raise `MAX_SPEND_USD` for longer runs, or use cron with `--once`, where each run is capped on its own.

## Expected output

Dry run:

```
Alert: BTC below $75,000, checked every 15 min via https://x402.swaphunt.dev/v1/tools/price
Price per check: $0.001 USDC on eip155:8453, payTo 0x<swaphunt-address>
Expected cost: $0.480 per day (96 checks), cap MAX_SPEND_USD=0.1 per run (about 20 checks)
Dry run: nothing paid. Re-run with --pay to start polling.
```

Paid check that triggers an alert:

```
2026-10-31 15:38  BTC $77,490.26  paid $0.005  run total $0.005  ALERT
This run cost $0.005.
```

The Telegram message reads: *BTC is $77,490.26, above your alert level $1,000.00. (SwapHunt x402 price check, not investment advice)*

## Cron

One check every 15 minutes, each run capped by `MAX_SPEND_USD`:

```cron
*/15 * * * * cd /path/to/x402-examples/alert-bot && set -a && . ../.env && set +a && PYTHONUNBUFFERED=1 .venv/bin/python alert.py --pay --once >> alert.log 2>&1
```

Each run reads and updates the state file, so you get one message per crossing, not one per check.

Nothing here is investment advice.
