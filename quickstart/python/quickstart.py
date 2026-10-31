"""One x402 call to SwapHunt. Dry run by default; pass --pay (or X402_PAY=1) to pay."""
import asyncio, os, sys

import httpx
from eth_account import Account
from x402 import x402Client
from x402.http import decode_payment_required_header, decode_payment_response_header
from x402.http.clients import x402HttpxClient
from x402.mechanisms.evm import EthAccountSigner
from x402.mechanisms.evm.exact.register import register_exact_evm_client

URL = "https://x402.swaphunt.dev/v1/market/fear-greed"
MAX_SPEND = float(os.getenv("MAX_SPEND_USD", "0.10"))
PAY = "--pay" in sys.argv or os.getenv("X402_PAY") == "1"


async def main() -> None:
    async with httpx.AsyncClient() as http:  # unpaid request -> 402 with the price
        req = decode_payment_required_header((await http.get(URL)).headers["PAYMENT-REQUIRED"]).accepts[0]
    price = int(req.amount) / 1e6  # USDC has 6 decimals
    print(f"Price: ${price:.3f} USDC on {req.network}, payTo {req.pay_to}")
    if not PAY:
        return print("Dry run: nothing paid. Re-run with --pay to pay.")
    if price > MAX_SPEND:
        sys.exit(f"Price ${price:.3f} exceeds MAX_SPEND_USD={MAX_SPEND}. Not paying.")
    if not os.getenv("PRIVATE_KEY"):
        sys.exit("Set PRIVATE_KEY (a dedicated wallet with a few dollars of USDC on Base).")

    client = x402Client().set_spend_controls({"max_amount_per_payment": f"${MAX_SPEND}"})
    register_exact_evm_client(client, EthAccountSigner(Account.from_key(os.environ["PRIVATE_KEY"])))
    async with x402HttpxClient(client) as http:
        resp = await http.get(URL)
    print(resp.status_code, resp.json())
    tx = decode_payment_response_header(resp.headers["PAYMENT-RESPONSE"]).transaction
    print(f"This run cost ${price:.3f} (tx https://basescan.org/tx/{tx})")


asyncio.run(main())
