"""SwapHunt MCP server: SwapHunt's x402 endpoints as MCP tools, paid per call in USDC on Base.

Dry run by default: tools report what a call would cost and return no data.
Set X402_PAY=1 and PRIVATE_KEY (or PRIVATE_KEY_FILE) to pay. Spending is capped per session (server process) by MAX_SPEND_USD.

Run:  python server.py          (stdio, for Claude Desktop / Claude Code)
      python server.py --check  (compare advertised prices with the live API, pays nothing)
"""
import asyncio
import os
import sys
from typing import Any

import httpx
from eth_account import Account
from mcp.server import MCPServer
from x402 import x402Client
from x402.http import decode_payment_required_header, decode_payment_response_header
from x402.http.clients import x402HttpxClient
from x402.mechanisms.evm import EthAccountSigner
from x402.mechanisms.evm.exact.register import register_exact_evm_client
from x402.schemas.errors import NoMatchingRequirementsError

BASE = "https://x402.swaphunt.dev"
MAX_SPEND = float(os.getenv("MAX_SPEND_USD", "0.10"))
PAY = os.getenv("X402_PAY") == "1"
# The key can come from a file, so it never has to sit in an MCP client's config file.
if not os.getenv("PRIVATE_KEY") and os.getenv("PRIVATE_KEY_FILE"):
    with open(os.path.expanduser(os.environ["PRIVATE_KEY_FILE"])) as f:
        os.environ["PRIVATE_KEY"] = f.read().strip()

mcp = MCPServer(
    "swaphunt",
    title="SwapHunt crypto market context",
    website_url="https://x402.swaphunt.dev/docs",
    instructions=(
        "Crypto market context for trading decisions: prices, regime, volatility, sentiment, "
        "derivatives, macro events and anti-FOMO sanity checks. Every tool except get_spending "
        "costs real USDC per call (price in each description), with a per-session spending cap. "
        "Prefer one well-chosen call over many. Nothing returned is investment advice."
    ),
)

_spent = 0.0
_calls = 0
_lock = asyncio.Lock()  # tools may run concurrently; budget checks must not race


BASE_MAINNET = "eip155:8453"
USDC_ON_BASE = "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913"  # canonical USDC, 6 decimals


def _usd(req) -> float:
    return int(req.amount) / 1e6  # only valid for USDC, which _quote enforces


async def _quote(path: str, params: dict) -> Any:
    """Unpaid request -> 402. Returns the USDC-on-Base option; any other asset or network is refused."""
    async with httpx.AsyncClient(timeout=30) as http:
        r = await http.get(BASE + path, params=params)
    if r.status_code != 402:
        raise RuntimeError(f"expected 402 from {path}, got {r.status_code}: {r.text[:200]}")
    for req in decode_payment_required_header(r.headers["PAYMENT-REQUIRED"]).accepts:
        if req.network == BASE_MAINNET and req.asset.lower() == USDC_ON_BASE:
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
    """Quote, check price and budget, pay, return the data plus what it cost."""
    global _spent, _calls
    params = {k: v for k, v in params.items() if v is not None}
    quote = await _quote(path, params)
    price = _usd(quote)
    if price > advertised:
        return {"error": f"Refused: {path} now costs ${price:.3f}, more than the advertised ${advertised:.3f}."}
    if not PAY:
        return {"dry_run": True, "would_cost_usd": price, "network": quote.network,
                "note": "Dry run, nothing paid and no data. The user can set X402_PAY=1 to enable payments."}
    async with _lock:
        if _spent + price > MAX_SPEND:
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
        async with x402HttpxClient(client, timeout=60) as http:
            r = await http.get(BASE + path, params=params)
    except Exception as e:
        if _refused_before_signing(e):
            async with _lock:
                _spent -= price
            return {"error": f"Not paid: the payment terms changed since the quote ({e})"}
        return {"error": f"Possibly paid ${price:.3f}, no data: {type(e).__name__}: {str(e)[:150]}. "
                         "Counted against the session cap; check the wallet on basescan.org."}
    receipt = r.headers.get("PAYMENT-RESPONSE")
    tx = decode_payment_response_header(receipt).transaction if receipt else None
    tx_link = f"https://basescan.org/tx/{tx}" if tx else None
    if r.status_code != 200:
        return {"error": f"Possibly paid ${price:.3f}, no data: HTTP {r.status_code}. Counted against the session cap.",
                "tx": tx_link}
    _calls += 1
    return {"data": r.json(), "cost_usd": price, "session_spent_usd": round(_spent, 6),
            "session_remaining_usd": round(MAX_SPEND - _spent, 6), "tx": tx_link}


def paid(price: float, summary: str):
    """Register a paid tool; the price goes into the description the agent sees."""
    return mcp.tool(description=f"{summary} Costs ${price:.3f} USDC per call.")


# --- Free -------------------------------------------------------------------

@mcp.tool(description="Free. Shows payment mode, USDC spent this session, calls made and budget left.")
async def get_spending() -> dict:
    return {"payments_enabled": PAY, "spent_usd": round(_spent, 6), "paid_calls": _calls,
            "cap_usd": MAX_SPEND, "remaining_usd": round(MAX_SPEND - _spent, 6)}


# --- Price ------------------------------------------------------------------

@paid(0.001, "Live spot price of one asset with 24h change, high, low and volume.")
async def get_price(asset: str = "BTC", currency: str = "USD") -> dict:
    return await call("/v1/tools/price", 0.001, asset=asset, currency=currency)


@paid(0.003, "Spot prices for up to 20 assets in one call (comma-separated, e.g. 'BTC,ETH,SOL').")
async def get_prices(assets: str = "BTC,ETH", currency: str = "USD") -> dict:
    return await call("/v1/tools/price/multi", 0.003, assets=assets, currency=currency)


# --- Market -----------------------------------------------------------------

@paid(0.001, "Crypto Fear & Greed Index (0-100) with its label, updated daily.")
async def get_fear_greed() -> dict:
    return await call("/v1/market/fear-greed", 0.001)


@paid(0.002, "Whole-market snapshot: total market cap, 24h volume, BTC and ETH dominance.")
async def get_market_overview() -> dict:
    return await call("/v1/market/global", 0.002)


@paid(0.003, "Alt-season read: Altcoin Season Index plus how many top alts beat BTC over `days` (1-30).")
async def get_alt_season(days: int = 7) -> dict:
    return await call("/v1/market/alt-season", 0.003, days=days)


@paid(0.003, "Top and bottom coins by return over `period` (24h, 7d, 30d); `limit` 1-20.")
async def get_momentum_rank(period: str = "24h", limit: int = 10) -> dict:
    return await call("/v1/market/momentum-rank", 0.003, period=period, limit=limit)


# --- Sentiment --------------------------------------------------------------

@paid(0.005, "Recent crypto headlines, each scored 1-10 for trading impact with a bullish/bearish tag.")
async def get_crypto_news(hours: int = 24, min_score: int | None = None, limit: int = 10) -> dict:
    return await call("/v1/sentiment/news", 0.005, hours=hours, min_score=min_score, limit=limit)


@paid(0.003, "Aggregated news sentiment (strong_bearish to strong_bullish) over the last `hours`.")
async def get_sentiment_summary(hours: int = 24) -> dict:
    return await call("/v1/sentiment/summary", 0.003, hours=hours)


# --- Regime and volatility --------------------------------------------------

@paid(0.002, "Current BTC market regime (BULLISH/BEARISH/NEUTRAL) from price vs the 12h EMA20.")
async def get_market_regime() -> dict:
    return await call("/v1/regime/current", 0.002)


@paid(0.003, "Is the asset trending or chopping? ADX-based, on `timeframe` (1h, 4h, 1d).")
async def get_chop_detection(asset: str = "BTC", timeframe: str = "4h") -> dict:
    return await call("/v1/regime/chop-detection", 0.003, asset=asset, timeframe=timeframe)


@paid(0.002, "Realized volatility (daily and annualized) with a low/normal/high/extreme level.")
async def get_volatility(asset: str = "BTC", period: str = "30d") -> dict:
    return await call("/v1/vol/realized", 0.002, asset=asset, period=period)


# --- Context and events -----------------------------------------------------

@paid(0.001, "Current trading session (Asia, London, New York, off-hours) and its typical volatility.")
async def get_trading_session() -> dict:
    return await call("/v1/context/session", 0.001)


@paid(0.003, "Upcoming macro events (FOMC, CPI, NFP ...) for the next `days`, optionally high-impact only.")
async def get_macro_events(days: int = 7, high_impact_only: bool = False) -> dict:
    return await call("/v1/events/macro", 0.003, days=days, high_impact_only=str(high_impact_only).lower())


# --- Derivatives ------------------------------------------------------------

@paid(0.003, "Live perpetual funding rates for up to 20 symbols (comma-separated). Positive = longs pay shorts.")
async def get_funding_rates(symbols: str = "BTC,ETH,SOL") -> dict:
    return await call("/v1/derivatives/funding-rates", 0.003, symbols=symbols)


@paid(0.003, "Long/short liquidations for BTC, ETH, SOL, XRP or BNB in the last 1-60 `minutes`.")
async def get_liquidations(coin: str = "BTC", minutes: int = 5) -> dict:
    return await call("/v1/derivatives/liquidations", 0.003, coin=coin, minutes=minutes)


# --- Sanity checks and anti-FOMO --------------------------------------------

@paid(0.003, "Is this drop a statistically significant dip or noise? Compares the move with ATR.")
async def is_this_a_dip(symbol: str = "BTC") -> dict:
    return await call("/v1/sanity/is-this-a-dip", 0.003, symbol=symbol)


@paid(0.003, "Is a breakout from price `level` real or a fakeout? `direction` up or down.")
async def is_this_a_breakout(level: float, symbol: str = "BTC", direction: str = "up") -> dict:
    return await call("/v1/sanity/is-this-a-breakout", 0.003, symbol=symbol, level=level, direction=direction)


@paid(0.003, "Multi-timeframe RSI oversold check (1h/4h/1d blended).")
async def is_this_oversold(symbol: str = "BTC") -> dict:
    return await call("/v1/sanity/is-this-oversold", 0.003, symbol=symbol)


@paid(0.003, "FOMO guard: how far price has run from the recent swing low (early/mid/late).")
async def how_late_am_i(symbol: str = "BTC") -> dict:
    return await call("/v1/fomo/how-late-am-i", 0.003, symbol=symbol)


@paid(0.003, "Is price over-extended from its MA20/MA50 and Bollinger bands? Returns a z-score.")
async def is_price_extended(symbol: str = "BTC") -> dict:
    return await call("/v1/fomo/already-extended", 0.003, symbol=symbol)


# --- Maintainer check -------------------------------------------------------

async def check_prices() -> None:
    """Compare every tool's advertised price with the live 402. Pays nothing."""
    import re

    src = open(__file__).read()
    pairs = re.findall(r'await call\("([^"]+)", ([0-9.]+)', src)
    bad = 0
    for path, adv in pairs:
        extra = {"level": 1} if path.endswith("breakout") else {}
        try:
            live = _usd(await _quote(path, extra))
        except Exception as e:
            bad += 1
            print(f"ERR {path:<36} {str(e)[:60]}")
            continue
        ok = abs(live - float(adv)) < 1e-9
        bad += not ok
        print(f"{'ok ' if ok else 'BAD'} {path:<36} advertised ${float(adv):.3f}  live ${live:.3f}")
    print(f"{len(pairs)} paid tools, {bad} mismatches")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    if "--check" in sys.argv:
        asyncio.run(check_prices())
    else:
        if PAY and not os.getenv("PRIVATE_KEY"):
            sys.exit("X402_PAY=1 needs PRIVATE_KEY or PRIVATE_KEY_FILE (a dedicated wallet with a few dollars of USDC on Base).")
        mcp.run()  # stdio
