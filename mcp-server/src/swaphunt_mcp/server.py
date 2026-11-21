"""SwapHunt MCP server: SwapHunt's x402 endpoints as MCP tools, paid per call in USDC on Base.

Dry run by default: tools report what a call would cost and return no data.
Set X402_PAY=1 and PRIVATE_KEY (or PRIVATE_KEY_FILE) to pay. Spending is capped per session (server process) by MAX_SPEND_USD.
PAYTO_ALLOWLIST (optional) limits which addresses the server may pay; anything else is refused before signing.

Prices: the price a call may cost is read from the API's own price list, /.well-known/x402 on the same
host (cached for an hour), so a price change needs no new release. A 402 that asks for more than that list
says is refused. If the list cannot be fetched, the prices built into this release are used instead.

pm_fees is free and runs locally with pmfees (https://github.com/swaphunt/pmfees): no API call, no payment.

Run:  uvx swaphunt-mcp            (stdio, for Claude Desktop / Claude Code)
      uvx swaphunt-mcp --check    (compare advertised prices with the live API, pays nothing)
"""
import asyncio
import math
import os
import re
import sys
import time
from decimal import Decimal
from typing import Any, Literal
from urllib.parse import urlsplit

import httpx
import pmfees
from eth_account import Account
from mcp.server import MCPServer
from mcp.types import Icon, ToolAnnotations
from x402 import x402Client

from swaphunt_mcp import __version__
from x402.http import decode_payment_required_header, decode_payment_response_header
from x402.http.clients import x402HttpxClient
from x402.mechanisms.evm import EthAccountSigner
from x402.mechanisms.evm.exact.register import register_exact_evm_client
from x402.schemas.errors import NoMatchingRequirementsError

BASE = (os.getenv("SWAPHUNT_API_URL") or "https://x402.swaphunt.dev").rstrip("/")  # override only for tests
ICON_URL = "https://raw.githubusercontent.com/swaphunt/x402-examples/main/mcp-server/assets/icon-512.png"
MAX_SPEND = float(os.getenv("MAX_SPEND_USD") or "0.10")  # empty counts as unset
PAY = os.getenv("X402_PAY") == "1"
HEADERS = {"User-Agent": f"swaphunt-mcp/{__version__}"}  # so SwapHunt can tell this client's traffic apart
# The key can come from a file, so it never has to sit in an MCP client's config file.
if not os.getenv("PRIVATE_KEY") and os.getenv("PRIVATE_KEY_FILE"):
    with open(os.path.expanduser(os.environ["PRIVATE_KEY_FILE"])) as f:
        os.environ["PRIVATE_KEY"] = f.read().strip()


def _payto_allowlist() -> set[str]:
    """Optional PAYTO_ALLOWLIST: comma-separated addresses the server may pay. Empty = any payTo."""
    entries = [a.strip() for a in (os.getenv("PAYTO_ALLOWLIST") or "").split(",") if a.strip()]
    bad = [a for a in entries if not re.fullmatch(r"0x[0-9a-fA-F]{40}", a)]
    if bad:
        sys.exit(f"PAYTO_ALLOWLIST has an entry that is not an address: {bad[0]!r}")
    return {a.lower() for a in entries}


PAYTO_ALLOWLIST = _payto_allowlist()

mcp = MCPServer(
    "swaphunt",
    title="SwapHunt crypto market context",
    version=__version__,
    website_url="https://x402.swaphunt.dev/docs",
    icons=[Icon(src=ICON_URL, mime_type="image/png", sizes=["512x512"])],
    instructions=(
        "Crypto market context: the Fear & Greed Index (current, compared and history), the "
        "halving countdown, trading session and weekend liquidity, and tools computed from Hyperliquid "
        "perpetuals (USDC-margined): prices in USDC, BTC market regime, chop detection, volatility, "
        "expected move, hourly funding rates, the Alt Season Index, coin strength, momentum and "
        "correlation vs BTC, and sanity checks (is this a dip, breakout, support, oversold; how late am I, "
        "pump age, extension, green-candle streak). The coin-level analysis tools cover the top 50 "
        "Hyperliquid perpetuals by 30-day volume; other coins are rejected with not_covered and not "
        "charged. Every tool except get_spending "
        "costs real USDC per call (price in each description), with a per-session spending cap. "
        "Prefer one well-chosen call over many. When showing Fear & Greed values, include the "
        "attribution text from the result. Nothing returned is investment advice."
    ),
)

_spent = 0.0
_calls = 0
_lock = asyncio.Lock()  # tools may run concurrently; budget checks must not race


BASE_MAINNET = "eip155:8453"
USDC_ON_BASE = "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913"  # canonical USDC, 6 decimals


def _usd(req) -> float:
    return int(req.amount) / 1e6  # only valid for USDC, which _quote enforces


# --- Advertised prices from the API's price list -----------------------------------
# /.well-known/x402 lists every paid route with its accepted payments. Its USDC-on-Base amount is the
# "advertised" price a 402 may not exceed. The list is fetched on the first paid call and again after
# PRICE_LIST_TTL seconds. If it cannot be fetched (or a route is missing from it), the price built into
# this release is the limit; a list that was fetched before stays in use until a fetch succeeds again.

PRICE_LIST_URL = BASE + "/.well-known/x402"
PRICE_LIST_TTL = 3600.0
_price_list: dict[str, float] = {}
_price_list_at: float | None = None  # monotonic time of the last fetch attempt
_price_lock = asyncio.Lock()


def _parse_price_list(doc: Any) -> dict[str, float]:
    """{path: USD} from a /.well-known/x402 document; only GET routes with a USDC-on-Base amount."""
    out: dict[str, float] = {}
    for res in (doc or {}).get("resources") or []:
        if not isinstance(res, dict) or str(res.get("method", "GET")).upper() != "GET":
            continue
        path = urlsplit(str(res.get("url", ""))).path
        for acc in res.get("accepts") or []:
            if (isinstance(acc, dict) and acc.get("network") == BASE_MAINNET
                    and str(acc.get("asset", "")).lower() == USDC_ON_BASE):
                try:
                    usd = int(acc["amount"]) / 1e6
                except (KeyError, TypeError, ValueError):
                    break
                if path.startswith("/v1/") and math.isfinite(usd) and usd > 0:
                    out[path] = usd
                break
    return out


async def _refresh_price_list() -> None:
    global _price_list, _price_list_at
    async with _price_lock:
        now = time.monotonic()
        if _price_list_at is not None and now - _price_list_at < PRICE_LIST_TTL:
            return
        _price_list_at = now
        try:
            async with httpx.AsyncClient(timeout=10, headers=HEADERS) as http:
                r = await http.get(PRICE_LIST_URL)
            r.raise_for_status()
            fresh = _parse_price_list(r.json())
        except Exception as e:
            print(f"swaphunt-mcp: price list unavailable ({type(e).__name__}); using "
                  f"{'the last fetched list' if _price_list else 'built-in prices'}", file=sys.stderr)
            return
        if fresh:
            _price_list = fresh


async def advertised_price(path: str, built_in: float) -> tuple[float, str]:
    """The most a call to `path` may cost, and where that limit comes from."""
    await _refresh_price_list()
    if path in _price_list:
        return _price_list[path], "the API's price list"
    return built_in, "the price built into this release"


class NotCovered(Exception):
    """The API rejected the coin before asking for payment (HTTP 422 not_covered). Nothing is charged."""

    def __init__(self, body: dict):
        super().__init__(body.get("message", "not covered"))
        self.body = body


def _not_covered(r: httpx.Response) -> dict | None:
    """The 422 not_covered body, or None. The API sends it before any payment is requested."""
    if r.status_code != 422:
        return None
    try:
        body = r.json()
    except ValueError:
        return None
    return body if isinstance(body, dict) and body.get("error") == "not_covered" else None


def _not_covered_result(body: dict) -> dict:
    """What the agent sees for an uncovered coin: a clear message and the covered list, no charge."""
    return {"error": "not_covered", "charged": False,
            "message": f"{body.get('message', 'This coin is not covered.')} Nothing was paid. "
                       "Retry with one of the covered coins.",
            "symbol": body.get("symbol"), "covered": body.get("covered", []),
            "coverage_rule": body.get("coverage_rule")}


async def _quote(path: str, params: dict) -> Any:
    """Unpaid request -> 402. Returns the USDC-on-Base option; any other asset or network is refused."""
    async with httpx.AsyncClient(timeout=30, headers=HEADERS) as http:
        r = await http.get(BASE + path, params=params)
    nc = _not_covered(r)
    if nc is not None:
        raise NotCovered(nc)
    if r.status_code != 402 or "PAYMENT-REQUIRED" not in r.headers:
        raise RuntimeError(f"expected 402 from {path}, got HTTP {r.status_code}: {r.text[:200]!r}")
    for req in decode_payment_required_header(r.headers["PAYMENT-REQUIRED"]).accepts:
        if req.scheme == "exact" and req.network == BASE_MAINNET and req.asset.lower() == USDC_ON_BASE:
            return req
    raise RuntimeError(f"{path} offers no USDC payment on Base")


def _locked_to(quote):
    """Payment policy: pay only exactly what was quoted, in that asset, on that network, to that address."""
    def policy(version, reqs):
        return [r for r in reqs if r.amount == quote.amount and r.network == quote.network
                and r.asset.lower() == quote.asset.lower() and r.pay_to.lower() == quote.pay_to.lower()]
    return policy


def _refused_before_signing(e: BaseException) -> bool:
    """True only if the client rejected the payment terms, which happens before anything is signed.

    Checks the exception and its explicit cause only; anything less certain counts as possibly paid.
    """
    return isinstance(e, NoMatchingRequirementsError) or isinstance(e.__cause__, NoMatchingRequirementsError)


async def call(path: str, advertised: float, **params: Any) -> dict:
    """Quote, check price and budget, pay, return the data plus what it cost.

    `advertised` is the built-in fallback; the limit normally comes from the API's price list.
    """
    global _spent, _calls
    params = {k: v for k, v in params.items() if v is not None}
    try:
        quote = await _quote(path, params)
    except NotCovered as e:
        return _not_covered_result(e.body)
    except Exception as e:
        return {"error": f"Not paid: {type(e).__name__}: {str(e)[:300]}"}
    price = _usd(quote)
    limit, source = await advertised_price(path, advertised)
    # These checks run before anything is signed, in dry runs too, so a dry run shows what would be refused.
    if price > limit + 1e-9:
        return {"error": f"Refused: {path} now costs ${price:.3f}, more than the advertised ${limit:.3f} "
                         f"({source}). Nothing was signed or paid."}
    if price > MAX_SPEND + 1e-9:
        return {"error": f"Refused: {path} costs ${price:.3f}, more than MAX_SPEND_USD=${MAX_SPEND:g}. "
                         "Nothing was signed or paid."}
    if PAYTO_ALLOWLIST and quote.pay_to.lower() not in PAYTO_ALLOWLIST:
        return {"error": f"Refused: {path} asks for payment to {quote.pay_to}, which is not in PAYTO_ALLOWLIST. "
                         "Nothing was signed or paid."}
    if not PAY:
        return {"dry_run": True, "would_cost_usd": price, "network": quote.network, "pay_to": quote.pay_to,
                "note": "Dry run, nothing paid and no data. The user can set X402_PAY=1 to enable payments."}
    async with _lock:
        if _spent + price > MAX_SPEND + 1e-9:
            return {"error": f"Session spending cap reached: ${_spent:.3f} spent of MAX_SPEND_USD=${MAX_SPEND:g}; "
                             f"this call costs ${price:.3f}. Restart the server or raise MAX_SPEND_USD."}
        _spent += price  # reserve before paying so parallel calls can't overshoot
    # The reservation is released only when it is certain nothing was signed. Any failure after
    # the request starts (timeout, non-200, missing receipt) stays counted as possibly paid.
    try:
        client = x402Client().set_spend_controls({"max_amount_per_payment": f"${price:.6f}"})
        client.register_policy(_locked_to(quote))
        register_exact_evm_client(client, EthAccountSigner(Account.from_key(os.environ["PRIVATE_KEY"])))
    except Exception as e:
        async with _lock:
            _spent -= price
        return {"error": f"Not paid (wallet setup failed): {type(e).__name__}"}
    try:
        async with x402HttpxClient(client, timeout=60, headers=HEADERS) as http:
            r = await http.get(BASE + path, params=params)
    except Exception as e:
        if _refused_before_signing(e):
            async with _lock:
                _spent -= price
            return {"error": f"Not paid: the payment terms changed since the quote ({e})"}
        return {"error": f"Possibly paid ${price:.3f}, no data: {type(e).__name__}: {str(e)[:150]}. "
                         "Counted against the session cap; check the wallet on basescan.org."}
    receipt = r.headers.get("PAYMENT-RESPONSE")
    nc = _not_covered(r)
    if nc is not None and not receipt:
        # Coverage changed between quote and call. Only give the reservation back when it is certain
        # nothing was signed: the final request carried no payment header. If a payment was signed,
        # the API still does not settle on errors, but keep it counted against the cap to be safe.
        sent = getattr(r, "request", None)
        signed = sent is not None and any(h in sent.headers for h in ("payment-signature", "x-payment"))
        if not signed:
            async with _lock:
                _spent -= price
            return _not_covered_result(nc)
        result = _not_covered_result(nc)
        result["charged"] = "unlikely"
        result["message"] = (f"{nc.get('message', 'This coin is not covered.')} A payment was signed, but the API "
                             "does not settle on errors. It stays counted against the session cap to be safe. "
                             "Retry with one of the covered coins.")
        return result
    tx = decode_payment_response_header(receipt).transaction if receipt else None
    tx_link = f"https://basescan.org/tx/{tx}" if tx else None
    if r.status_code != 200:
        return {"error": f"Possibly paid ${price:.3f}, no data: HTTP {r.status_code}. Counted against the session cap.",
                "tx": tx_link}
    _calls += 1
    return {"data": r.json(), "cost_usd": price, "session_spent_usd": round(_spent, 6),
            "session_remaining_usd": round(MAX_SPEND - _spent, 6), "tx": tx_link}


def paid(price: float, summary: str):
    """Register a paid tool; the built-in price goes into the description the agent sees."""
    return mcp.tool(description=f"{summary} Costs ${price:.3f} USDC per call.")


# --- Free -------------------------------------------------------------------

@mcp.tool(
    description="Free, runs locally (no API call, no payment). Use when the user asks how much this session "
                "has spent or what budget is left. Returns whether payments are enabled, USDC spent, paid calls, "
                "the MAX_SPEND_USD cap and the remaining budget. Ex: no parameters",
)
async def get_spending() -> dict:
    return {"payments_enabled": PAY, "spent_usd": round(_spent, 6), "paid_calls": _calls,
            "cap_usd": MAX_SPEND, "remaining_usd": round(MAX_SPEND - _spent, 6)}


# --- Prediction market fees (free, local) ----------------------------------
# Computed in-process by pmfees from its bundled, sourced fee schedules. No network, no x402.

LOCAL = ToolAnnotations(read_only_hint=True, destructive_hint=False, open_world_hint=False)


def _num(d: Decimal | None) -> float | None:
    return None if d is None else float(d)


@mcp.tool(
    description="Free, runs locally (no API call, no payment). Use when the user asks the fee for an order on "
                "Kalshi, Polymarket US or polymarket.com. Returns fee_usd, fee %, break-even exit, rates as_of. "
                "contracts = USD / price; polymarket needs category; at = fill time (default now). Ex: "
                "platform=polymarket, price=0.4, contracts=250, category=Politics",
    annotations=LOCAL,
)
async def pm_fees(platform: Literal["kalshi", "polymarket-us", "polymarket"], price: float, contracts: float,
                  side: Literal["taker", "maker"] = "taker", direction: Literal["buy", "sell"] = "buy",
                  category: str | None = None, tier: str | None = None,
                  multiplier: float | None = None, at: str | None = None) -> dict:
    kwargs: dict[str, Any] = {"maker": side == "maker"}
    if at is not None and platform == "polymarket":
        # polymarket.com's rates depend on the fill time (new rates from 2026-11-20 23:59 UTC); default now
        kwargs["at"] = at
    if category is not None:
        kwargs["category"] = category
    if tier is not None:
        kwargs["tier"] = int(tier) if str(tier).isdigit() else tier
    if multiplier is not None:
        kwargs["multiplier"] = multiplier
    try:
        r = pmfees.fee(platform, price, contracts, direction, **kwargs)
        be = pmfees.break_even(platform, price, contracts, direction, **kwargs)
    except ValueError as e:  # pmfees' own rules: price range, order size step, category, tier, multiplier
        return {"error": "invalid_input", "message": str(e), "platform": platform}
    pct = r.fee_pct_of_trade_value
    return {
        "platform": r.platform, "platform_name": r.platform_name, "side": r.role, "direction": r.side,
        "price": float(r.price), "contracts": float(r.contracts), "trade_value_usd": float(r.trade_value),
        "fee_usd": float(r.fee), "fee_pct_of_trade_value": None if pct is None else round(float(pct), 4),
        "raw_fee_usd": float(r.raw_fee), "rounding": r.rounding, "formula": r.formula,
        "break_even": {
            "exit_direction": "sell" if direction == "buy" else "buy",
            "exit_price": _num(be.exit_price), "move_cents": _num(be.move_cents),
            "entry_fee_usd": float(be.entry_fee), "exit_fee_usd": _num(be.exit_fee),
            "profit_at_exit_usd": _num(be.profit_at_exit),
        },
        "details": dict(r.details), "notes": list(r.notes),
        "as_of": r.rates_as_of, "fee_schedule_version": r.details.get("fee_schedule_version"),
        "source_url": r.source_url, "pmfees_version": pmfees.__version__,
        "computed": "locally by pmfees (https://github.com/swaphunt/pmfees); nothing was paid",
    }


# --- Fear & Greed -----------------------------------------------------------
# Alternative.me asks for attribution next to its data: show the `attribution` field with the values.

@paid(0.005, "Use when the user asks how fearful or greedy the crypto market is today. Returns the Crypto "
             "Fear & Greed Index (0-100), its label (Extreme Fear to Extreme Greed) and the attribution to "
             "show with it; daily. For trend use get_fear_greed_compare. Show `attribution` with the "
             "values. Ex: no parameters")
async def get_fear_greed() -> dict:
    return await call("/v1/market/fear-greed", 0.005)


@paid(0.002, "Use when the user asks whether crypto sentiment is improving or worsening. Returns Fear & "
             "Greed now with its label, the values yesterday, 7 and 30 days ago, the changes (change_1d, "
             "change_7d, change_30d) and the attribution. Show `attribution` with the values. Ex: no "
             "parameters")
async def get_fear_greed_compare() -> dict:
    return await call("/v1/market/fear-greed/compare", 0.002)


@paid(0.005, "Use when the user wants the Fear & Greed time series to chart, backtest or compare with "
             "price. Returns daily value and classification for the last `days` (max 365) or start_date to "
             "end_date (YYYY-MM-DD), with attribution. Raw series, no summary. Show `attribution` with the "
             "values. Ex: days=90")
async def get_fear_greed_history(days: int = 30, start_date: str | None = None, end_date: str | None = None) -> dict:
    return await call("/v1/market/fear-greed/history", 0.005, days=days, start_date=start_date, end_date=end_date)


# --- Halving ----------------------------------------------------------------

@paid(0.001, "Use when the user asks when the next Bitcoin or Litecoin halving is. Returns current and "
             "halving block, blocks and days remaining, estimated date, progress % and block reward before "
             "and after. Estimated from block time, not an exact timestamp. Ex: symbol=LTC")
async def get_halving(symbol: str = "BTC") -> dict:
    return await call("/v1/market/halving", 0.001, symbol=symbol)


# --- Hyperliquid perpetuals -------------------------------------------------
# Everything below is computed from Hyperliquid perpetuals (USDC-margined); prices are in USDC.

@paid(0.005, "Use when the user asks the current price of one coin. Returns the mark price (or order-book "
             "mid with price_type=mid) on Hyperliquid perpetuals in USDC, 24h change % and 24h notional "
             "volume; high/low are null. For several coins use get_prices. Ex: symbol=ETH")
async def get_price(symbol: str = "BTC", price_type: str = "mark") -> dict:
    return await call("/v1/tools/price", 0.005, symbol=symbol, price_type=price_type)


@paid(0.003, "Use when the user asks the prices of several coins or a portfolio. Returns, keyed by symbol "
             "(max 20), the mark or mid price on Hyperliquid perpetuals in USDC, 24h change % and 24h "
             "notional volume; unknown symbols are skipped. Works with one symbol too. Ex: "
             "symbols=BTC,ETH,SOL")
async def get_prices(symbols: str = "BTC,ETH", price_type: str = "mark") -> dict:
    return await call("/v1/tools/price/multi", 0.003, symbols=symbols, price_type=price_type)


@paid(0.001, "Use when the user asks which coins are supported, or a symbol is uncertain (Hyperliquid "
             "names, e.g. kPEPE = 1,000 PEPE). Returns every active Hyperliquid perpetuals market, the "
             "count and `covered`: the top 50 by 30-day volume that analysis routes accept. Ex: no "
             "parameters")
async def get_supported_assets() -> dict:
    return await call("/v1/tools/price/supported", 0.001)


@paid(0.010, "Use when the user asks whether the crypto market (BTC) is bullish, bearish or neutral. "
             "Returns the regime from the BTC price on Hyperliquid perpetuals vs its 20-period EMA on 12h "
             "candles, with EMA, distance and slope; updates 00:00 and 12:00 UTC. BTC only. Ex: no "
             "parameters")
async def get_market_regime() -> dict:
    return await call("/v1/regime/current", 0.010)


@paid(0.003, "Use when the user asks whether a coin is trending or stuck in a range. Returns is_chop, chop "
             "level, ADX, +DI/-DI, trend direction and a verdict on 1h, 4h or 1d candles of Hyperliquid "
             "perpetuals. Any active market. Ex: symbol=SOL, timeframe=4h")
async def get_chop_detection(symbol: str = "BTC", timeframe: str = "4h") -> dict:
    return await call("/v1/regime/chop-detection", 0.003, symbol=symbol, timeframe=timeframe)


@paid(0.010, "Use when the user asks how volatile a coin has been. Returns daily and annualized realized "
             "volatility % over 7d, 14d or 30d of daily candles on Hyperliquid perpetuals, a "
             "low/normal/high/extreme level and today's UTC range vs open. Not implied vol. Ex: "
             "symbol=BTC, period=30d")
async def get_volatility(symbol: str = "BTC", period: str = "7d") -> dict:
    return await call("/v1/vol/realized", 0.010, symbol=symbol, period=period)


@paid(0.002, "Use when the user asks whether a coin is unusually quiet. Returns a 0-1 silence score, level "
             "and advice from today's volume vs the period average, volatility and 24h change on "
             "Hyperliquid perpetuals (7d, 14d, 30d). For a squeeze use get_compression_alert. Ex: "
             "symbol=ETH, period=14d")
async def get_market_silence(symbol: str = "BTC", period: str = "7d") -> dict:
    return await call("/v1/vol/silence", 0.002, symbol=symbol, period=period)


@paid(0.003, "Use when the user asks whether a coin is in a volatility squeeze before a breakout. Returns "
             "is_squeeze, level (extreme, strong, moderate, none), Bollinger width and its percentile on "
             "1h, 4h or 1d candles of Hyperliquid perpetuals. Setup, not direction. Ex: symbol=BTC, "
             "timeframe=1d")
async def get_compression_alert(symbol: str = "BTC", timeframe: str = "4h") -> dict:
    return await call("/v1/vol/compression-alert", 0.003, symbol=symbol, timeframe=timeframe)


@paid(0.003, "Use when the user asks how far a coin may move, or where to put targets and stops. Returns "
             "ATR(14)-based 68% and 95% price ranges in USDC around the current price on Hyperliquid "
             "perpetuals for the next 4h, 1d or 1w. A statistical range, not a forecast. Ex: symbol=BTC, "
             "period=1w")
async def get_expected_move(symbol: str = "BTC", period: str = "1d") -> dict:
    return await call("/v1/vol/expected-move", 0.003, symbol=symbol, period=period)


@paid(0.015, "Use when the user asks the funding rate of specific coins or whether longs or shorts are "
             "crowded. Returns per coin (max 20) hourly funding % on Hyperliquid perpetuals, annualized (x "
             "8760), 7d/30d averages, mark price and a crowding signal; positive = longs pay. Ex: "
             "symbols=BTC,ETH,SOL")
async def get_funding_rates(symbols: str = "BTC,ETH,SOL") -> dict:
    return await call("/v1/derivatives/funding-rates", 0.015, symbols=symbols)


@paid(0.003, "Use when the user asks which coins have the most extreme funding right now. Returns the top "
             "`limit` (1-50) current hourly funding rates across all Hyperliquid perpetuals, annualized (x "
             "8760), sort=highest (crowded longs) or lowest (crowded shorts). Ex: sort=lowest, limit=10")
async def get_top_funding_rates(limit: int = 10, sort: str = "highest") -> dict:
    return await call("/v1/derivatives/funding-rates/top", 0.003, limit=limit, sort=sort)


@paid(0.004, "Use when the user asks whether a coin's funding is unusual for it. Returns settled hourly "
             "funding on Hyperliquid perpetuals for the last `days` (1-365): average, min/max, annualized "
             "(x 8760), share of positive hours and the latest rate's percentile. Ex: symbol=ETH, days=90")
async def get_funding_history(symbol: str = "BTC", days: int = 90) -> dict:
    return await call("/v1/derivatives/funding-rates/history", 0.004, symbol=symbol, days=days)


@paid(0.003, "Use when the user asks if it is alt season. Returns the SwapHunt Alt Season Index (0-100, "
             "daily): share of the top 100 Hyperliquid perpetuals by 30-day volume beating BTC over 90 "
             "days; 75 or above is alt season, 25 or below is bitcoin season. Ex: no parameters")
async def get_alt_season() -> dict:
    return await call("/v1/market/alt-season", 0.003)


# --- Coin analysis (Hyperliquid perpetuals, covered coins only) -------------
# These endpoints cover only the top 50 Hyperliquid perpetuals by 30-day volume. Other coins are
# rejected with HTTP 422 not_covered before any payment is asked; call() returns the covered list.

@paid(0.015, "Use when the user asks if a coin is outperforming or lagging BTC. Returns its return minus "
             "BTC's over 24h, 7d or 30d, a rating (very_strong to very_weak) and the ratio. Top 50 "
             "Hyperliquid perpetuals by 30-day volume only (see get_supported_assets), others unpaid. Ex: "
             "symbol=SOL, period=7d")
async def get_coin_strength(symbol: str = "ETH", period: str = "24h") -> dict:
    return await call("/v1/market/coin-strength", 0.015, symbol=symbol, period=period)


@paid(0.015, "Use when the user asks which coins are the biggest gainers or losers. Returns coins ranked "
             "by 24h, 7d or 30d return: `limit` (1-20) top and bottom, full list, average. Top 50 "
             "Hyperliquid perpetuals by 30-day volume only (see get_supported_assets), others unpaid. Ex: "
             "period=7d, limit=5")
async def get_momentum_rank(period: str = "24h", limit: int = 10) -> dict:
    return await call("/v1/market/momentum-rank", 0.015, period=period, limit=limit)


@paid(0.003, "Use when the user asks if a coin just tracks BTC. Returns Pearson correlation (-1 to +1) of "
             "returns vs BTC over 7d (1h candles) or 30d (4h); no 24h. With strength label. Top 50 "
             "Hyperliquid perpetuals by 30-day volume only (see get_supported_assets), others unpaid. Ex: "
             "symbol=ETH, period=30d")
async def get_correlation(symbol: str = "ETH", period: str = "7d") -> dict:
    return await call("/v1/market/correlation", 0.003, symbol=symbol, period=period)


@paid(0.003, "Use when the user asks if a drop is a real dip or noise. Returns is_dip, drop % from the "
             "14-day high, 14-day ATR %, drop/ATR and a verdict on daily candles. Top 50 Hyperliquid "
             "perpetuals by 30-day volume only (see get_supported_assets), others unpaid. Ex: symbol=SOL")
async def is_this_a_dip(symbol: str = "BTC") -> dict:
    return await call("/v1/sanity/is-this-a-dip", 0.003, symbol=symbol)


@paid(0.003, "Use when the user asks if a break of a price level is real or a fakeout. Returns "
             "is_confirmed, fakeout odds, verdict from volume and 1h closes past the level (USDC, "
             "required). Top 50 Hyperliquid perpetuals by 30-day volume only (see get_supported_assets), "
             "others unpaid. Ex: symbol=BTC, level=100000")
async def is_this_a_breakout(level: float, symbol: str = "BTC", direction: str = "up") -> dict:
    return await call("/v1/sanity/is-this-a-breakout", 0.003, symbol=symbol, level=level, direction=direction)


@paid(0.003, "Use when the user asks if a price level is real support. Returns touches within 0.5% over 90 "
             "daily candles, recency, bounce quality, verdict. Level in USDC, required. Top 50 Hyperliquid "
             "perpetuals by 30-day volume only (see get_supported_assets), others unpaid. Ex: symbol=ETH, "
             "level=3000")
async def is_this_support(level: float, symbol: str = "BTC") -> dict:
    return await call("/v1/sanity/is-this-support", 0.003, symbol=symbol, level=level)


@paid(0.003, "Use when the user asks if a coin is oversold. Returns is_oversold, RSI(14) on 1h, 4h and 1d, "
             "a weighted RSI (20/30/50%) and a verdict; not a buy signal alone. Top 50 Hyperliquid "
             "perpetuals by 30-day volume only (see get_supported_assets), others unpaid. Ex: symbol=BTC")
async def is_this_oversold(symbol: str = "BTC") -> dict:
    return await call("/v1/sanity/is-this-oversold", 0.003, symbol=symbol)


@paid(0.003, "Use when the user asks if they are too late to buy after a run-up. Returns the move from the "
             "4h swing low in % and ATR, its percentile vs past moves, early/middle/late verdict. Top 50 "
             "Hyperliquid perpetuals by 30-day volume only (see get_supported_assets), others unpaid. Ex: "
             "symbol=SOL")
async def how_late_am_i(symbol: str = "BTC") -> dict:
    return await call("/v1/fomo/how-late-am-i", 0.003, symbol=symbol)


@paid(0.003, "Use when the user asks if a coin is pumping now and how old the move is. Returns is_pumping, "
             "start, duration and size vs the average pump in the last 24h of 15m candles. Top 50 "
             "Hyperliquid perpetuals by 30-day volume only (see get_supported_assets), others unpaid. Ex: "
             "symbol=SOL")
async def get_pump_age(symbol: str = "BTC") -> dict:
    return await call("/v1/fomo/pump-age", 0.003, symbol=symbol)


@paid(0.003, "Use when the user asks if price is stretched far from its average. Returns distance from "
             "MA20 and MA50, Bollinger position, z-score on 4h candles, is_extended and a verdict. Top 50 "
             "Hyperliquid perpetuals by 30-day volume only (see get_supported_assets), others unpaid. Ex: "
             "symbol=ETH")
async def is_price_extended(symbol: str = "BTC") -> dict:
    return await call("/v1/fomo/already-extended", 0.003, symbol=symbol)


@paid(0.003, "Use when the user asks how many green candles in a row a coin has. Returns the streak on 1h, "
             "4h or 1d and how often the next candle was green after such streaks. Top 50 Hyperliquid "
             "perpetuals by 30-day volume only (see get_supported_assets), others unpaid. Ex: symbol=BTC, "
             "interval=1d")
async def get_green_candle_streak(symbol: str = "BTC", interval: str = "4h") -> dict:
    return await call("/v1/fomo/green-candles-streak", 0.003, symbol=symbol, interval=interval)


# --- Trading context --------------------------------------------------------

@paid(0.005, "Use when the user asks which trading session is active or how volatile this time of day "
             "usually is. Returns the session (Asian, London, New York, Off-hours), overlap, minutes left, "
             "the next session and its typical volatility multiplier, from the UTC clock. Ex: no "
             "parameters")
async def get_trading_session() -> dict:
    return await call("/v1/context/session", 0.005)


@paid(0.005, "Use when the user asks whether crypto liquidity is thin right now, e.g. on a weekend or in "
             "off-hours. Returns is_weekend, is_low_liquidity, the session, a 0-100 liquidity score and a "
             "verdict, from the UTC clock (no market data). Ex: no parameters")
async def get_weekend_liquidity() -> dict:
    return await call("/v1/context/weekend-liquidity", 0.005)


# --- Maintainer check -------------------------------------------------------

async def check_prices() -> None:
    """Compare every tool's advertised price with the live 402. Pays nothing."""
    src = open(__file__).read()
    pairs = re.findall(r'await call\("([^"]+)", ([0-9.]+)', src)
    bad = 0
    for path, adv in pairs:
        try:
            live = _usd(await _quote(path, {}))
        except Exception as e:
            bad += 1
            print(f"ERR {path:<36} {str(e)[:60]}")
            continue
        ok = abs(live - float(adv)) < 1e-9
        bad += not ok
        print(f"{'ok ' if ok else 'BAD'} {path:<36} advertised ${float(adv):.3f}  live ${live:.3f}")
    print(f"{len(pairs)} paid tools, {bad} mismatches")
    sys.exit(1 if bad else 0)


def main() -> None:
    """Entry point for `swaphunt-mcp` (and `uvx swaphunt-mcp`)."""
    if "--version" in sys.argv:
        print(f"swaphunt-mcp {__version__}")
    elif "--check" in sys.argv:
        asyncio.run(check_prices())
    else:
        if PAY and not os.getenv("PRIVATE_KEY"):
            sys.exit("X402_PAY=1 needs PRIVATE_KEY or PRIVATE_KEY_FILE (a dedicated wallet with a few dollars of USDC on Base).")
        if PAY and not PAYTO_ALLOWLIST:
            print("swaphunt-mcp: PAYTO_ALLOWLIST is not set, so any payTo address the API quotes can be paid "
                  "(still capped by MAX_SPEND_USD).", file=sys.stderr)
        mcp.run()  # stdio


if __name__ == "__main__":
    main()
