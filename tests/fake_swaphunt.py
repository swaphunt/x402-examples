"""A local stand-in for x402.swaphunt.dev, for testing the MCP server without real money.

It answers like the SwapHunt x402 API: an unpaid GET gets 402 with a PAYMENT-REQUIRED header
(x402 v2, USDC on Base, prices and payTo from tests/fixtures/endpoints_402.json, a snapshot of the
live 402s); a GET with a PAYMENT-SIGNATURE gets a small JSON body and a PAYMENT-RESPONSE header
with a fake transaction hash. Nothing touches a chain: the signature is decoded and its EIP-712
signer recovered, but nothing is settled. Use a throwaway key with it.

    python tests/fake_swaphunt.py [port]        # then SWAPHUNT_API_URL=http://127.0.0.1:<port>

Test knobs (environment, read on every request):
    FAKE_PRICE_FACTOR   multiply every price (e.g. 2 to test price checks)
    FAKE_PAY_TO         payTo address to quote (default: the snapshot's address)
    FAKE_SWITCH_PAY_TO  quote this payTo from the second 402 on (tests the payment lock)
    FAKE_STATUS         status for paid requests (e.g. 503 to test failures)
    FAKE_LIST_FACTOR    multiply every price in /.well-known/x402 (default 1, independent of the 402s)
    FAKE_LIST_STATUS    status for /.well-known/x402 (e.g. 503: the price list is unavailable)
/.well-known/x402 lists every endpoint with its USDC-on-Base amount, like the real API's price list.
A coin, symbol or asset of NOTCOVERED gets 422 not_covered before any 402, like the real API.
"""
import hashlib
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from eth_account import Account
from eth_account.messages import encode_typed_data
from x402.http import (decode_payment_signature_header, encode_payment_required_header,
                       encode_payment_response_header)
from x402.schemas import PaymentRequired, PaymentRequirements, ResourceInfo, SettleResponse

FIXTURE = json.loads((Path(__file__).resolve().parent / "fixtures/endpoints_402.json").read_text())
ENDPOINTS = {e["path"]: e for e in FIXTURE["endpoints"]}
USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
NOT_COVERED = "NOTCOVERED"

quotes_served = 0
price_list_fetches = 0
requests_log: list[dict] = []  # every request to an endpoint: path, query, User-Agent, signed or not
paid_log: list[dict] = []      # every request the fake "settled"


def requirements(e: dict) -> PaymentRequirements:
    global quotes_served
    quotes_served += 1
    pay_to = os.getenv("FAKE_PAY_TO") or e["pay_to"]
    if quotes_served > 1 and os.getenv("FAKE_SWITCH_PAY_TO"):
        pay_to = os.environ["FAKE_SWITCH_PAY_TO"]
    amount = int(int(e["amount"]) * float(os.getenv("FAKE_PRICE_FACTOR", "1")))
    return PaymentRequirements(scheme="exact", network="eip155:8453", asset=USDC, amount=str(amount),
                               pay_to=pay_to, max_timeout_seconds=60, extra={"name": "USD Coin", "version": "2"})


def recover_signer(payload) -> str:
    auth = payload.payload["authorization"]
    typed = {
        "types": {"EIP712Domain": [{"name": "name", "type": "string"}, {"name": "version", "type": "string"},
                                   {"name": "chainId", "type": "uint256"},
                                   {"name": "verifyingContract", "type": "address"}],
                  "TransferWithAuthorization": [
                      {"name": "from", "type": "address"}, {"name": "to", "type": "address"},
                      {"name": "value", "type": "uint256"}, {"name": "validAfter", "type": "uint256"},
                      {"name": "validBefore", "type": "uint256"}, {"name": "nonce", "type": "bytes32"}]},
        "primaryType": "TransferWithAuthorization",
        "domain": {"name": "USD Coin", "version": "2", "chainId": 8453, "verifyingContract": USDC},
        "message": {"from": auth["from"], "to": auth["to"], "value": int(auth["value"]),
                    "validAfter": int(auth["validAfter"]), "validBefore": int(auth["validBefore"]),
                    "nonce": auth["nonce"]},
    }
    return Account.recover_message(encode_typed_data(full_message=typed), signature=payload.payload["signature"])


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):  # quiet
        pass

    def _send(self, status: int, body: dict, headers: dict | None = None) -> None:
        raw = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(raw)

    def price_list(self):
        global price_list_fetches
        price_list_fetches += 1
        status = int(os.getenv("FAKE_LIST_STATUS", "200"))
        if status != 200:
            return self._send(status, {"error": "fake failure"})
        factor = float(os.getenv("FAKE_LIST_FACTOR", "1"))
        host = f"http://{self.headers.get('Host', 'fake')}"
        resources = [{"url": host + e["path"], "method": "GET", "price": f"${int(e['amount']) * factor / 1e6:g}",
                      "accepts": [{"scheme": "exact", "network": "eip155:8453", "asset": USDC,
                                   "amount": str(int(int(e["amount"]) * factor)), "payTo": e["pay_to"]}]}
                     for e in FIXTURE["endpoints"]]
        self._send(200, {"x402Version": 2, "kind": "resource-server", "name": "SwapHunt (fake)",
                         "resources": resources})

    def do_GET(self):
        url = urlsplit(self.path)
        if url.path == "/.well-known/x402":
            return self.price_list()
        e = ENDPOINTS.get(url.path)
        if e is None:
            return self._send(404, {"detail": "Not Found"})
        query = {k: v[0] for k, v in parse_qs(url.query).items()}
        sig = self.headers.get("PAYMENT-SIGNATURE")
        requests_log.append({"path": url.path, "query": query, "user_agent": self.headers.get("User-Agent", ""),
                             "signed": bool(sig)})
        coin = (query.get("coin") or query.get("symbol") or query.get("asset") or "").upper()
        if coin == NOT_COVERED:
            return self._send(422, {"error": "not_covered", "message": f"{coin} is not covered yet.",
                                    "symbol": coin, "covered": ["BTC", "ETH", "SOL"],
                                    "coverage_rule": "Top 50 Hyperliquid perpetuals by 30-day volume."})
        req = requirements(e)
        if not sig:
            pr = PaymentRequired(x402_version=2, resource=ResourceInfo(url=f"http://fake{self.path}"), accepts=[req])
            return self._send(402, {}, {"PAYMENT-REQUIRED": encode_payment_required_header(pr)})
        payload = decode_payment_signature_header(sig)
        auth = payload.payload["authorization"]
        a = payload.accepted
        if (a.amount != req.amount or a.pay_to.lower() != req.pay_to.lower() or int(auth["value"]) != int(req.amount)
                or auth["to"].lower() != req.pay_to.lower() or recover_signer(payload).lower() != auth["from"].lower()):
            return self._send(402, {"error": "payment_requirements_mismatch"})
        status = int(os.getenv("FAKE_STATUS", "200"))
        if status != 200:
            return self._send(status, {"error": "fake failure"})
        paid_log.append({"path": url.path, "amount": req.amount, "from": auth["from"], "to": auth["to"]})
        tx = "0x" + hashlib.sha256(sig.encode()).hexdigest()
        settle = SettleResponse(success=True, transaction=tx, network="eip155:8453", payer=auth["from"])
        self._send(200, {"path": url.path, "query": query, "source": "fake"},
                   {"PAYMENT-RESPONSE": encode_payment_response_header(settle)})


def reset() -> None:
    global quotes_served, price_list_fetches
    quotes_served = 0
    price_list_fetches = 0
    requests_log.clear()
    paid_log.clear()


def serve(port: int = 0) -> ThreadingHTTPServer:
    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


if __name__ == "__main__":
    server = serve(int(sys.argv[1]) if len(sys.argv) > 1 else 8402)
    print(f"fake SwapHunt API on http://127.0.0.1:{server.server_address[1]}", flush=True)
    server.serve_forever()
