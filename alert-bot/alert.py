"""Price alert: poll one SwapHunt endpoint via x402 and send a Telegram message when a threshold is crossed.

Dry run by default: shows the price per check and the expected cost per day, then stops.
Pass --pay (or X402_PAY=1) to start polling. --once does a single check (for cron).
The last state (past the threshold or not) is kept in a small file, so --once runs from
cron alert only on a new crossing.
"""
import asyncio
import json
import os
import sys
import time

import httpx
from eth_account import Account
from x402 import x402Client
from x402.http import decode_payment_required_header
from x402.http.clients import x402HttpxClient
from x402.mechanisms.evm import EthAccountSigner
from x402.mechanisms.evm.exact.register import register_exact_evm_client
from x402.schemas.errors import NoMatchingRequirementsError

URL = "https://x402.swaphunt.dev/v1/tools/price"
ASSET = os.getenv("ALERT_ASSET") or "BTC"
BELOW = float(os.environ["ALERT_BELOW"]) if os.getenv("ALERT_BELOW") else None
ABOVE = float(os.environ["ALERT_ABOVE"]) if os.getenv("ALERT_ABOVE") else None
INTERVAL_MIN = float(os.getenv("ALERT_INTERVAL_MIN") or "15")
MAX_SPEND = float(os.getenv("MAX_SPEND_USD") or "0.10")
PAY = "--pay" in sys.argv or os.getenv("X402_PAY") == "1"
ONCE = "--once" in sys.argv
STATE_FILE = os.path.expanduser(os.getenv("ALERT_STATE_FILE") or os.path.join(os.path.dirname(os.path.abspath(__file__)), ".alert-state.json"))
BASE_MAINNET = "eip155:8453"
USDC_ON_BASE = "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913"


def stop(msg: str) -> None:
    print(msg, file=sys.stderr)
    sys.exit(1)


def quote():
    """Unpaid request -> 402. Returns the USDC-on-Base payment option."""
    r = httpx.get(URL, params={"asset": ASSET}, timeout=30)
    if r.status_code != 402:
        stop(f"expected 402, got {r.status_code}")
    for req in decode_payment_required_header(r.headers["PAYMENT-REQUIRED"]).accepts:
        if req.network == BASE_MAINNET and req.asset.lower() == USDC_ON_BASE:
            return req
    stop("no USDC payment on Base offered")


async def pay_and_fetch(q) -> dict:
    """Pay exactly the quoted amount (asset, network, payTo locked) and return the price data."""
    client = x402Client().set_spend_controls({"max_amount_per_payment": f"${int(q.amount) / 1e6:.6f}"})
    client.register_policy(lambda version, reqs: [
        r for r in reqs if r.amount == q.amount and r.network == q.network
        and r.asset.lower() == q.asset.lower() and r.pay_to.lower() == q.pay_to.lower()])
    register_exact_evm_client(client, EthAccountSigner(Account.from_key(os.environ["PRIVATE_KEY"])))
    async with x402HttpxClient(client, timeout=60) as http:
        r = await http.get(URL, params={"asset": ASSET})
    if r.status_code != 200:
        raise RuntimeError(f"HTTP {r.status_code}")
    return r.json()


def telegram(text: str) -> bool:
    """Send the alert; True if Telegram accepted it. Errors never print the URL, which contains the bot token."""
    url = f"https://api.telegram.org/bot{os.environ['TELEGRAM_BOT_TOKEN']}/sendMessage"
    try:
        r = httpx.post(url, json={"chat_id": os.environ["TELEGRAM_CHAT_ID"], "text": text}, timeout=30)
        if r.is_error:
            print(f"Telegram failed: HTTP {r.status_code}", file=sys.stderr)
        return not r.is_error
    except httpx.HTTPError as e:
        print(f"Telegram failed: {type(e).__name__}", file=sys.stderr)
        return False


def load_alerted(rule: str) -> bool:
    """True if the last check was already past this threshold and the alert went out."""
    try:
        with open(STATE_FILE) as f:
            state = json.load(f)
        return state.get("rule") == rule and state.get("alerted") is True
    except (OSError, ValueError):
        return False  # no state yet, or unreadable: treat as not alerted


def save_alerted(rule: str, alerted: bool) -> None:
    with open(STATE_FILE, "w") as f:
        json.dump({"rule": rule, "alerted": alerted, "updated": time.strftime("%Y-%m-%dT%H:%M:%S")}, f)


def crossed(price: float) -> str | None:
    if BELOW is not None and price < BELOW:
        return f"{ASSET} is ${price:,.2f}, below your alert level ${BELOW:,.2f}"
    if ABOVE is not None and price > ABOVE:
        return f"{ASSET} is ${price:,.2f}, above your alert level ${ABOVE:,.2f}"
    return None


def main() -> None:
    if (BELOW is None) == (ABOVE is None):
        stop("Set exactly one threshold: ALERT_BELOW or ALERT_ABOVE (e.g. ALERT_BELOW=75000).")
    q = quote()
    price_per_check = int(q.amount) / 1e6
    checks_per_day = 1440 / INTERVAL_MIN
    rule = f"below ${BELOW:,.0f}" if BELOW is not None else f"above ${ABOVE:,.0f}"
    print(f"Alert: {ASSET} {rule}, checked every {INTERVAL_MIN:g} min via {URL}")
    print(f"Price per check: ${price_per_check:.3f} USDC on {q.network}, payTo {q.pay_to}")
    print(f"Expected cost: ${price_per_check * checks_per_day:.3f} per day ({checks_per_day:g} checks), "
          f"cap MAX_SPEND_USD={MAX_SPEND:g} per run (about {MAX_SPEND / price_per_check:.0f} checks)")
    if not PAY:
        print("Dry run: nothing paid. Re-run with --pay to start polling.")
        return
    for var in ("PRIVATE_KEY", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"):
        if not os.getenv(var):
            stop(f"Set {var}.")

    state_rule = f"{ASSET} {rule}"  # a changed asset or threshold starts fresh
    spent, alerted = 0.0, load_alerted(state_rule)
    while True:
        q = quote()
        price = int(q.amount) / 1e6
        if spent + price > MAX_SPEND:
            stop(f"Stopping: next check would bring spending to ${spent + price:.3f}, over MAX_SPEND_USD={MAX_SPEND:g}.")
        spent += price  # counted before paying; released only if nothing was signed
        try:
            data = asyncio.run(pay_and_fetch(q))
        except Exception as e:
            if isinstance(e, NoMatchingRequirementsError) or isinstance(e.__cause__, NoMatchingRequirementsError):
                spent -= price
                print(f"Not paid: price or terms changed ({e})", file=sys.stderr)
            else:
                print(f"Possibly paid ${price:.3f}, no data: {type(e).__name__}", file=sys.stderr)
        else:
            message = crossed(data["price"])
            stamp = time.strftime("%Y-%m-%d %H:%M")
            print(f"{stamp}  {ASSET} ${data['price']:,.2f}  paid ${price:.3f}  run total ${spent:.3f}"
                  + ("  ALERT" if message else ""))
            if not message:
                alerted = False  # back on the safe side: the next crossing alerts again
            elif not alerted:
                # Alert once per crossing. If delivery fails, the next check tries again.
                alerted = telegram(f"{message}. (SwapHunt x402 price check, not investment advice)")
            save_alerted(state_rule, alerted)
        if ONCE:
            print(f"This run cost ${spent:.3f}.")
            return
        time.sleep(INTERVAL_MIN * 60)


if __name__ == "__main__":
    main()
