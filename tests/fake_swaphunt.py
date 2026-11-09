"""A local stand-in for x402.swaphunt.dev, for testing the MCP server without real money.

It answers like the SwapHunt x402 API: an unpaid request gets 402 with a PAYMENT-REQUIRED header
(x402 v2, USDC on Base, prices from tests/contract.json); a request with a PAYMENT-SIGNATURE gets a
small JSON body and a PAYMENT-RESPONSE header with a fake transaction hash. Nothing touches a chain:
the signature is decoded and its EIP-712 signer recovered, but nothing is settled. Use a throwaway key.

    python tests/fake_swaphunt.py [port]        # then SWAPHUNT_API_URL=http://127.0.0.1:<port>

Test knobs (environment):
    FAKE_PRICE_FACTOR   multiply every price (e.g. 2 to test the price ceiling)
    FAKE_PAY_TO         payTo address to quote
    FAKE_SWITCH_PAY_TO  quote this payTo on the second 402 (tests the payment lock)
    FAKE_STATUS         status for paid requests (e.g. 503 to test failures)
    FAKE_NOT_COVERED    comma-separated symbols answered with 422 not_covered before any payment
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

CONTRACT = json.loads((Path(__file__).resolve().parent / "contract.json").read_text())["endpoints"]
ENDPOINTS = {e["path"]: e for e in CONTRACT}
USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
DEFAULT_PAY_TO = "0x000000000000000000000000000000000000dEaD"
quotes_served = 0
paid_log: list[dict] = []
requests_log: list[dict] = []  # every request to an endpoint: path, params, User-Agent, signed or not


def requirements(e: dict) -> PaymentRequirements:
    global quotes_served
    quotes_served += 1
    pay_to = os.getenv("FAKE_PAY_TO", DEFAULT_PAY_TO)
    if quotes_served > 1 and os.getenv("FAKE_SWITCH_PAY_TO"):
        pay_to = os.environ["FAKE_SWITCH_PAY_TO"]
    amount = int(e["price_atomic"] * float(os.getenv("FAKE_PRICE_FACTOR", "1")))
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

    def do_GET(self):
        url = urlsplit(self.path)
        e = ENDPOINTS.get(url.path)
        if e is None:
            return self._send(404, {"error": "not_found"})
        params = {k: v[0] for k, v in parse_qs(url.query).items()}
        sig = self.headers.get("PAYMENT-SIGNATURE")
        requests_log.append({"path": url.path, "params": params, "user_agent": self.headers.get("User-Agent", ""),
                             "signed": bool(sig)})
        missing = [p for p in e["required"] if p not in params]
        if missing:
            return self._send(422, {"error": "validation_error", "missing": missing})
        coin = params.get("symbol") or params.get("coin")
        uncovered = {c.strip().upper() for c in os.getenv("FAKE_NOT_COVERED", "").split(",") if c.strip()}
        if coin and coin.upper() in uncovered:
            return self._send(422, {"error": "not_covered", "symbol": coin.upper(),
                                    "message": f"{coin.upper()} is not covered.", "covered": ["BTC", "ETH"],
                                    "coverage_rule": "top 50 Hyperliquid perpetuals by 30-day volume"})
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
        self._send(200, {"path": url.path, "params": params, "source": "fake"},
                   {"PAYMENT-RESPONSE": encode_payment_response_header(settle)})


def reset() -> None:
    global quotes_served
    quotes_served = 0
    paid_log.clear()
    requests_log.clear()


def serve(port: int = 0) -> ThreadingHTTPServer:
    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


if __name__ == "__main__":
    server = serve(int(sys.argv[1]) if len(sys.argv) > 1 else 8402)
    print(f"fake SwapHunt API on http://127.0.0.1:{server.server_address[1]}", flush=True)
    server.serve_forever()
