# Daily brief

Pays for four SwapHunt endpoints with x402, has an LLM write a short market brief in plain English, and delivers it to stdout, Telegram, Discord or email. Built to run once a day from cron.

The example shows the mechanics: paying several x402 endpoints in one run, keeping the spend under a cap, and having an LLM turn the answers into a few sentences. It is not a full market report. The data covers market sentiment, the halving countdown and trading session context, not prices or news.

| Endpoint | Price | What it adds |
|---|---|---|
| `/v1/market/fear-greed/compare` | $0.002 | Market mood (Fear & Greed Index, 0-100) today, with the change over 1, 7 and 30 days |
| `/v1/market/halving?coin=BTC` | $0.001 | Bitcoin halving countdown: blocks and estimated days remaining |
| `/v1/context/session` | $0.001 | Current trading session (Asia, London, New York, off-hours) and its typical volatility |
| `/v1/context/weekend-liquidity` | $0.001 | Weekend or low-liquidity window, with a 0-100 liquidity score |
| **Total per run** | **$0.005** | $0.15 per month at one run a day |

The session and liquidity readings describe the moment the script runs, so pick a cron time that matters to you.

The LLM writing the brief is extra. The script prints the input and output token counts on every run, so you can work out the cost from your provider's per-token prices ([Anthropic pricing](https://platform.claude.com/docs/en/about-claude/pricing)). With `LLM_PROVIDER=ollama` the LLM is free and a run costs only the $0.005 in x402 payments.

The Fear & Greed data comes from Alternative.me, which asks for attribution next to its data. The script adds that attribution line below the brief (a fixed text, not taken from the API response).

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
.venv/bin/python brief.py --pay  # pays $0.005, writes and delivers the brief
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
  /v1/market/fear-greed/compare    $0.002  eip155:8453  payTo 0x<swaphunt-address>
  /v1/market/halving               $0.001  eip155:8453  payTo 0x<swaphunt-address>
  /v1/context/session              $0.001  eip155:8453  payTo 0x<swaphunt-address>
  /v1/context/weekend-liquidity    $0.001  eip155:8453  payTo 0x<swaphunt-address>
  total: $0.005 per run (cap MAX_SPEND_USD=0.1)
Dry run: nothing paid, no LLM call. Re-run with --pay to pay.
```

A paid run prints one `paying $0.00x for /v1/... ok (tx 0x<hash>…)` line per endpoint, then the brief (5-8 sentences followed by the Alternative.me attribution line), then a last line with the cost and token counts:

```
This run cost $0.005 in x402 payments. LLM: <model>, <n> input + <n> output tokens
```

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
