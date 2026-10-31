# Daily brief

Pays for four SwapHunt endpoints with x402, has an LLM write a short market brief in plain English, and delivers it to stdout, Telegram, Discord or email. Built to run once a day from cron.

| Endpoint | Price | What it adds |
|---|---|---|
| `/v1/market/fear-greed` | $0.001 | Market mood (0-100) |
| `/v1/regime/current` | $0.002 | BTC regime: bullish, bearish or neutral |
| `/v1/market/global` | $0.002 | Total market cap, volume, BTC dominance |
| `/v1/events/macro?days=7&high_impact_only=true` | $0.003 | High-impact macro events this week |
| **Total per run** | **$0.008** | |

The LLM writing the brief is extra. Measured on 31 October 2026; the script prints the token counts on every run:

| LLM | Price per MTok (in / out) | Tokens per run | LLM per run | Total per run | Total per month (30 runs) |
|---|---|---|---|---|---|
| Claude Haiku 5.5 (default) | $0.10 / $0.50 | 765 in + 270 out | $0.0002 | $0.0082 | $0.25 |
| Claude Opus 5.5 (`LLM_MODEL=claude-opus-5-5`) | $4 / $20 | 755 in + 505 out | $0.0131 | $0.0211 | $0.63 |
| Local model via Ollama (`LLM_PROVIDER=ollama`) | free | 714 in + 194 out | $0 | $0.0080 | $0.24 |

Claude prices from [Anthropic's pricing page](https://platform.claude.com/docs/en/about-claude/pricing) (Haiku 5.5 rate for prompts up to 100k tokens).

Haiku is plenty for a fact summary like this. Opus writes a somewhat richer brief if you want it.

## Setup

Use a dedicated wallet with a few dollars of USDC on Base mainnet. Never your main wallet.

```bash
cd daily-brief
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp ../.env.example ../.env    # then fill in PRIVATE_KEY and the LLM / delivery settings
```

## Run

```bash
set -a; . ../.env; set +a        # load settings into the environment
.venv/bin/python brief.py        # dry run: shows prices, pays nothing, no LLM call
.venv/bin/python brief.py --pay  # pays $0.008, writes and delivers the brief
```

Before paying, the script checks that the run total stays under `MAX_SPEND_USD` (default $0.10) and that the LLM is usable. Each payment is locked to the amount, network and `payTo` address shown in the dry run: if the server asks for anything else, the script refuses to pay.

## Settings

| Variable | Default | Values |
|---|---|---|
| `LLM_PROVIDER` | `anthropic` | `anthropic` (needs `ANTHROPIC_API_KEY`), `ollama` (local, needs [Ollama](https://ollama.com) running), `none` (delivers the raw JSON) |
| `LLM_MODEL` | per provider | `claude-haiku-5-5` for anthropic (or e.g. `claude-opus-5-5`), `qwen3.5:9b` for ollama |
| `OLLAMA_URL` | `http://localhost:11434` | |
| `DELIVERY` | `stdout` | `stdout`, `telegram`, `discord`, `email` |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | | for `telegram` |
| `DISCORD_WEBHOOK_URL` | | for `discord` |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `MAIL_FROM`, `MAIL_TO` | port 587 | for `email` (STARTTLS) |

## Expected output

Dry run:

```
Prices (from the 402 responses):
  /v1/market/fear-greed    $0.001  eip155:8453  payTo 0x<swaphunt-address>
  /v1/regime/current       $0.002  eip155:8453  payTo 0x<swaphunt-address>
  /v1/market/global        $0.002  eip155:8453  payTo 0x<swaphunt-address>
  /v1/events/macro         $0.003  eip155:8453  payTo 0x<swaphunt-address>
  total: $0.008 per run (cap MAX_SPEND_USD=0.1)
Dry run: nothing paid, no LLM call. Re-run with --pay to pay.
```

Paid run with the default `LLM_PROVIDER=anthropic` (31 October 2026):

```
Prices (from the 402 responses):
  ...
  total: $0.008 per run (cap MAX_SPEND_USD=0.1)
  paying $0.001 for /v1/market/fear-greed ... ok (tx 0x<hash>…)
  paying $0.002 for /v1/regime/current ... ok (tx 0x<hash>…)
  paying $0.002 for /v1/market/global ... ok (tx 0x<hash>…)
  paying $0.003 for /v1/events/macro ... ok (tx 0x<hash>…)

Crypto brief 2026-10-31
-----------------------
Crypto sentiment is in the Fear zone today, with the Fear & Greed Index at 30 as of the latest
reading from Alternative.me. The BTC regime is classified as BEARISH on the 12-hour timeframe,
with price at about $77,460, roughly 2.9% below its 20-period EMA of about $79,867, and the EMA
sloping downward at about -1.6%. The total crypto market capitalization stands near $2.60
trillion, with 24-hour trading volume of about $61.2 billion. Bitcoin's dominance is about 59.8%
and Ethereum's is about 10.6%. The next high-impact macro event in the data is the US Nonfarm
Payrolls release on Friday, 6 November 2026, at 13:30 UTC, and it is the only high-impact event
listed for the coming week.

This run cost $0.008 in x402 payments. LLM: claude-haiku-5-5, 765 input + 270 output tokens
```

With `LLM_MODEL=claude-opus-5-5` the brief is a little richer and the last line reads `LLM: claude-opus-5-5, 755 input + 505 output tokens`. With `LLM_PROVIDER=ollama` and `qwen3.5:9b` it takes about 20 seconds on a desktop GPU and reads `LLM: qwen3.5:9b (local), 714 input + 194 output tokens`.

## Run it daily with cron

Every day at 07:00, with the output appended to a log file:

```cron
0 7 * * * cd /path/to/x402-examples/daily-brief && set -a && . ../.env && set +a && PYTHONUNBUFFERED=1 X402_PAY=1 .venv/bin/python brief.py >> brief.log 2>&1
```

Cron runs with a minimal environment, so the line loads `../.env` itself. Set `DELIVERY` in `.env` to get the brief somewhere other than the log.

## Security notes

- The API data is passed to the LLM between `<data>` tags, and the model is told to treat it as data and ignore any instructions in it.
- Discord messages are sent with mentions disabled, so the brief can never ping `@everyone`.
- Delivery errors never print the webhook URL or bot token.

Nothing here is investment advice.
