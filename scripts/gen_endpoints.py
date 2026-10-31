"""Regenerate docs/endpoints.md from the SwapHunt API source.

Maintainer tool: reads PRICING/DISCOVERY from src/api/x402/pricing.py and the
captured responses in src/api/x402/examples.json of the (private) API repo.

Usage:
    python3 scripts/gen_endpoints.py /path/to/swaphunt-tools [output.md]
"""
import ast
import json
import sys
from pathlib import Path

src = Path(sys.argv[1]) / "src/api/x402"
out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(__file__).resolve().parent.parent / "docs/endpoints.md"

tree = ast.parse((src / "pricing.py").read_text())
ns: dict = {}
for node in tree.body:
    if isinstance(node, (ast.Assign, ast.AnnAssign)):
        code = compile(ast.Module(body=[node], type_ignores=[]), "pricing", "exec")
        exec(code, ns)
PRICING, DISCOVERY = ns["PRICING"], ns["DISCOVERY"]
captured = json.loads((src / "examples.json").read_text())
cap_at = captured.get("captured_at", "")
examples = captured["examples"]

# category comments from source order
cats: dict[str, str] = {}
cur = ""
for line in (src / "pricing.py").read_text().split("DISCOVERY")[0].splitlines():
    s = line.strip()
    if s.startswith("# ") and not s.startswith("# Route"):
        cur = s[2:]
    elif s.startswith('"GET '):
        cats[s.split('"')[1]] = cur


def trim(v, depth=0):
    if isinstance(v, dict):
        items = list(v.items())
        d = {k: trim(x, depth + 1) for k, x in items[:10]}
        if len(items) > 10:
            d["…"] = f"{len(items) - 10} more keys"
        return d
    if isinstance(v, list):
        return [trim(x, depth + 1) for x in v[:1]] + (["…"] if len(v) > 1 else [])
    if isinstance(v, str) and len(v) > 80:
        return v[:77] + "..."
    return v


def params_str(p):
    if not p:
        return "–"
    parts = []
    for name, m in p.items():
        s = f"`{name}`"
        if m.get("required"):
            s += " (required)"
        elif "default" in m:
            s += f"={m['default']}"
        parts.append(s)
    return ", ".join(parts)


L = []
L.append("# SwapHunt x402 endpoints\n")
L.append("Base URL: `https://x402.swaphunt.dev`. All paid routes are `GET`, return JSON, "
         "and answer `402 Payment Required` (x402 v2) until paid. No API key needed.\n")
L.append("Payment: USDC, scheme `exact`, network **Base mainnet** (`eip155:8453`, "
         "USDC `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`). "
         "Free routes: `/health`, `/`, `/docs`, `/openapi.json`. Rate limit: 60 requests/min per IP.\n")
L.append(f"Source: `src/api/x402/pricing.py` (prices, params) and `examples.json` "
         f"(real responses captured {cap_at[:10]}). Long responses are trimmed (`…`).\n")
L.append("## Overview\n")
L.append("| Category | Endpoint | Price (USDC) | Params |")
L.append("|---|---|---|---|")
for route, price in PRICING.items():
    L.append(f"| {cats.get(route, '')} | `{route.split(' ', 1)[1]}` | {price} | "
             f"{params_str(DISCOVERY.get(route, {}).get('params', {}))} |")
L.append(f"\n{len(PRICING)} paid endpoints. Cheapest: $0.001. Most expensive: "
         f"{max(PRICING.values(), key=lambda s: float(s[1:]))}.\n")
L.append("## Details and example responses\n")
cur = None
for route, price in PRICING.items():
    if cats.get(route) != cur:
        cur = cats.get(route)
        L.append(f"### {cur}\n")
    meta = DISCOVERY.get(route, {})
    path = route.split(" ", 1)[1]
    L.append(f"#### `{path}` — {price}\n")
    L.append(meta.get("description", "") + "\n")
    if route in examples:
        ex, label = examples[route]["response"], "Example response (captured)"
    else:
        ex, label = meta.get("output_example"), "Example response (hand-written, not captured)"
    L.append(f"{label}:\n")
    L.append("```json\n" + json.dumps(trim(ex), indent=2, ensure_ascii=False) + "\n```\n")
out.write_text("\n".join(L))
print(f"wrote {out}: {len(PRICING)} routes, captured {sum(r in examples for r in PRICING)}")
print("not captured:", [r for r in PRICING if r not in examples])
