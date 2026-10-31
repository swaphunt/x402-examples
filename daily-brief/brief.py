"""Daily crypto brief: pay for a few SwapHunt endpoints via x402, summarize with an LLM, deliver.

Dry run by default: shows what each endpoint costs and stops. Pass --pay (or X402_PAY=1) to pay.
Configuration is read from environment variables; see ../.env.example and README.md.
"""
import asyncio
import json
import os
import smtplib
import sys
from datetime import datetime, timezone
from email.message import EmailMessage

import httpx
from eth_account import Account
from x402 import x402Client
from x402.http import decode_payment_required_header, decode_payment_response_header
from x402.http.clients import x402HttpxClient
from x402.mechanisms.evm import EthAccountSigner
from x402.mechanisms.evm.exact.register import register_exact_evm_client

BASE = "https://x402.swaphunt.dev"
ENDPOINTS = [  # (path, query params)
    ("/v1/market/fear-greed", {}),
    ("/v1/regime/current", {}),
    ("/v1/market/global", {}),
    ("/v1/events/macro", {"days": 7, "high_impact_only": "true"}),
]
MAX_SPEND = float(os.getenv("MAX_SPEND_USD", "0.10"))
PAY = "--pay" in sys.argv or os.getenv("X402_PAY") == "1"
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "anthropic")  # anthropic | none
LLM_MODEL = os.getenv("LLM_MODEL", "claude-opus-5-5")
DELIVERY = os.getenv("DELIVERY", "stdout")  # stdout | telegram | discord | email

SYSTEM_PROMPT = (
    "You write a short daily crypto market brief in plain English for a busy reader. "
    "Use only the JSON data you are given. 5-8 sentences, no headings, no bullet points. "
    "Cover market mood (Fear & Greed), the BTC regime, total market size and dominance, "
    "and any high-impact macro events in the next seven days. "
    "State facts and context only. Never give buy or sell recommendations."
)


def stop(msg: str) -> None:
    print(msg, file=sys.stderr)
    sys.exit(1)


async def get_prices() -> list[float]:
    """Unpaid request to each endpoint -> 402 with the price. Nothing is paid here."""
    prices = []
    async with httpx.AsyncClient(timeout=30) as http:
        for path, params in ENDPOINTS:
            r = await http.get(BASE + path, params=params)
            if r.status_code != 402:
                stop(f"{path}: expected 402, got {r.status_code}")
            req = decode_payment_required_header(r.headers["PAYMENT-REQUIRED"]).accepts[0]
            prices.append(int(req.amount) / 1e6)  # USDC has 6 decimals
            print(f"  {path:<24} ${prices[-1]:.3f}  {req.network}  payTo {req.pay_to}")
    return prices


async def fetch_paid(prices: list[float]) -> tuple[dict, float]:
    """Pay for each endpoint, never letting the run total exceed MAX_SPEND_USD."""
    client = x402Client().set_spend_controls({"max_amount_per_payment": f"${MAX_SPEND}"})
    register_exact_evm_client(client, EthAccountSigner(Account.from_key(os.environ["PRIVATE_KEY"])))
    data, spent = {}, 0.0
    async with x402HttpxClient(client, timeout=60) as http:
        for (path, params), price in zip(ENDPOINTS, prices):
            if spent + price > MAX_SPEND:
                stop(f"Stopping before {path}: ${spent + price:.3f} would exceed MAX_SPEND_USD={MAX_SPEND}.")
            print(f"  paying ${price:.3f} for {path} ...", end=" ", flush=True)
            r = await http.get(BASE + path, params=params)
            if r.status_code != 200:
                stop(f"failed ({r.status_code}): {r.text[:200]}")
            spent += price
            tx = decode_payment_response_header(r.headers["PAYMENT-RESPONSE"]).transaction
            print(f"ok (tx {tx[:10]}…)")
            data[path] = r.json()
    return data, spent


def summarize(data: dict) -> tuple[str, str]:
    """Return (brief text, token usage line)."""
    if LLM_PROVIDER == "none":
        return json.dumps(data, indent=2), "LLM: none"
    if LLM_PROVIDER != "anthropic":
        stop(f"Unknown LLM_PROVIDER={LLM_PROVIDER!r} (use anthropic or none).")

    import anthropic

    today = datetime.now(timezone.utc).strftime("%A %d %B %Y")
    request = dict(
        model=LLM_MODEL,
        max_tokens=16000,
        output_config={"effort": "low"},  # a short summary needs little reasoning
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"Today is {today} (UTC). Data:\n{json.dumps(data)}"}],
    )
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY
    if LLM_MODEL in {"claude-opus-5-5", "claude-opus-5", "claude-fable-5-1", "claude-sonnet-5-5"}:
        # If a safety classifier declines, let the API retry on a suitable fallback model.
        resp = client.beta.messages.create(**request, betas=["server-side-fallback-2026-07-01"], fallbacks="default")
    else:
        resp = client.messages.create(**request)
    if resp.stop_reason == "refusal":
        stop("The model declined to write the brief.")
    text = "".join(b.text for b in resp.content if b.type == "text").strip()
    usage = f"LLM: {resp.model}, {resp.usage.input_tokens} input + {resp.usage.output_tokens} output tokens"
    return text, usage


def deliver(text: str) -> None:
    subject = f"Crypto brief {datetime.now(timezone.utc):%Y-%m-%d}"
    if DELIVERY == "stdout":
        print(f"\n{subject}\n{'-' * len(subject)}\n{text}\n")
    elif DELIVERY == "telegram":
        url = f"https://api.telegram.org/bot{os.environ['TELEGRAM_BOT_TOKEN']}/sendMessage"
        httpx.post(url, json={"chat_id": os.environ["TELEGRAM_CHAT_ID"], "text": f"{subject}\n\n{text}"}).raise_for_status()
    elif DELIVERY == "discord":
        content = f"**{subject}**\n{text}"[:2000]  # Discord message limit
        httpx.post(os.environ["DISCORD_WEBHOOK_URL"], json={"content": content}).raise_for_status()
    elif DELIVERY == "email":
        msg = EmailMessage()
        msg["Subject"], msg["From"], msg["To"] = subject, os.environ["MAIL_FROM"], os.environ["MAIL_TO"]
        msg.set_content(text + "\n\nData: SwapHunt x402 API. Not investment advice.")
        with smtplib.SMTP(os.environ["SMTP_HOST"], int(os.getenv("SMTP_PORT", "587"))) as smtp:
            smtp.starttls()
            smtp.login(os.environ["SMTP_USER"], os.environ["SMTP_PASSWORD"])
            smtp.send_message(msg)
    else:
        stop(f"Unknown DELIVERY={DELIVERY!r} (use stdout, telegram, discord or email).")
    if DELIVERY != "stdout":
        print(f"Delivered via {DELIVERY}.")


async def main() -> None:
    print("Prices (from the 402 responses):")
    prices = await get_prices()
    total = sum(prices)
    print(f"  total: ${total:.3f} per run (cap MAX_SPEND_USD={MAX_SPEND})")
    if not PAY:
        print("Dry run: nothing paid, no LLM call. Re-run with --pay to pay.")
        return
    if total > MAX_SPEND:
        stop(f"Run total ${total:.3f} exceeds MAX_SPEND_USD={MAX_SPEND}. Not paying.")
    if not os.getenv("PRIVATE_KEY"):
        stop("Set PRIVATE_KEY (a dedicated wallet with a few dollars of USDC on Base).")
    if LLM_PROVIDER == "anthropic" and not os.getenv("ANTHROPIC_API_KEY"):
        stop("Set ANTHROPIC_API_KEY, or LLM_PROVIDER=none to deliver the raw data.")

    data, spent = await fetch_paid(prices)
    text, usage = summarize(data)
    deliver(text)
    print(f"This run cost ${spent:.3f} in x402 payments. {usage}")


if __name__ == "__main__":
    asyncio.run(main())
