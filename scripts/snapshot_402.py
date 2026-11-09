"""Snapshot the live 402 responses of every endpoint the MCP server uses, for the tests.

Maintainer tool. Sends one unpaid GET per endpoint to the SwapHunt x402 API and writes
tests/fixtures/endpoints_402.json: the Base USDC price and payTo, and the query parameters
the API declares in its Bazaar discovery extension. It pays nothing and signs nothing.

The endpoint list comes from mcp-server/src/swaphunt_mcp/server.py, so a tool for a route the
API does not sell shows up here as an error.

Usage:
    python3 scripts/snapshot_402.py [base-url]
"""
import base64
import json
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SERVER = ROOT / "mcp-server/src/swaphunt_mcp/server.py"
OUT = ROOT / "tests/fixtures/endpoints_402.json"
BASE_MAINNET = "eip155:8453"
USDC_ON_BASE = "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913"


def fetch_402(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "swaphunt-x402-examples-snapshot"})
    try:
        urllib.request.urlopen(req, timeout=30)
    except urllib.error.HTTPError as e:
        header = e.headers.get("PAYMENT-REQUIRED")
        if e.code == 402 and header:
            return json.loads(base64.b64decode(header))
        raise RuntimeError(f"{url}: HTTP {e.code} without PAYMENT-REQUIRED") from e
    raise RuntimeError(f"{url}: expected 402, got 200")


def main() -> None:
    base = (sys.argv[1] if len(sys.argv) > 1 else "https://x402.swaphunt.dev").rstrip("/")
    paths = re.findall(r'await call\("([^"]+)"', SERVER.read_text())
    endpoints = []
    for path in paths:
        pr = fetch_402(base + path)
        (base_usdc,) = [a for a in pr["accepts"] if a["network"] == BASE_MAINNET
                        and a["asset"].lower() == USDC_ON_BASE and a["scheme"] == "exact"]
        qp = pr["extensions"]["bazaar"]["schema"]["properties"]["input"]["properties"].get("queryParams", {})
        required = set(qp.get("required", []))
        params = {name: {"type": spec.get("type"), "required": name in required,
                         **({"default": spec["default"]} if "default" in spec else {})}
                  for name, spec in qp.get("properties", {}).items()}
        endpoints.append({"path": path, "amount": base_usdc["amount"], "pay_to": base_usdc["payTo"],
                          "params": params})
        print(f"{path:<40} {int(base_usdc['amount']) / 1e6:.3f} {', '.join(params) or '-'}")
    OUT.write_text(json.dumps({"captured_at": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                               "base_url": base, "endpoints": endpoints}, indent=1) + "\n")
    print(f"{len(endpoints)} endpoints -> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
