"""SwapHunt MCP server: SwapHunt's x402 endpoints as MCP tools, paid per call in USDC on Base.

Dry run by default: tools report what a call would cost and return no data.
Set X402_PAY=1 and PRIVATE_KEY (or PRIVATE_KEY_FILE) to pay. Spending is capped per session (server process) by MAX_SPEND_USD.

Run:  uvx swaphunt-mcp            (stdio, for Claude Desktop / Claude Code)
      uvx swaphunt-mcp --check    (compare advertised prices with the live API, pays nothing)
"""
import asyncio
import os
import sys
from typing import Any

import httpx
from eth_account import Account
from mcp.server import MCPServer
from mcp.types import Icon
from x402 import x402Client

from swaphunt_mcp import __version__
from x402.http import decode_payment_required_header, decode_payment_response_header
from x402.http.clients import x402HttpxClient
from x402.mechanisms.evm import EthAccountSigner
from x402.mechanisms.evm.exact.register import register_exact_evm_client
from x402.schemas.errors import NoMatchingRequirementsError

BASE = "https://x402.swaphunt.dev"
ICON_URL = "https://raw.githubusercontent.com/swaphunt/x402-examples/main/mcp-server/assets/icon-512.png"
MAX_SPEND = float(os.getenv("MAX_SPEND_USD") or "0.10")  # empty counts as unset
PAY = os.getenv("X402_PAY") == "1"
# The key can come from a file, so it never has to sit in an MCP client's config file.
if not os.getenv("PRIVATE_KEY") and os.getenv("PRIVATE_KEY_FILE"):
    with open(os.path.expanduser(os.environ["PRIVATE_KEY_FILE"])) as f:
        os.environ["PRIVATE_KEY"] = f.read().strip()

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
        "expected move, hourly funding rates and the Alt Season Index. Every tool except get_spending "
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


# --- Fear & Greed -----------------------------------------------------------
# Alternative.me asks for attribution next to its data: show the `attribution` field with the values.

@paid(0.001, "Crypto Fear & Greed Index (0-100) with its label, updated daily. "
             "When showing the value, include the `attribution` text from the result.")
async def get_fear_greed() -> dict:
    return await call("/v1/market/fear-greed", 0.001)


@paid(0.002, "Fear & Greed Index now vs yesterday, 7 and 30 days ago, with the changes. "
             "When showing the values, include the `attribution` text from the result.")
async def get_fear_greed_compare() -> dict:
    return await call("/v1/market/fear-greed/compare", 0.002)


@paid(0.005, "Daily Fear & Greed history: the last `days` (up to 365), or `start_date` to `end_date` "
             "(YYYY-MM-DD). When showing the values, include the `attribution` text from the result.")
async def get_fear_greed_history(days: int = 30, start_date: str | None = None,
                                 end_date: str | None = None) -> dict:
    return await call("/v1/market/fear-greed/history", 0.005, days=days, start_date=start_date, end_date=end_date)


# --- Halving ----------------------------------------------------------------

@paid(0.001, "Halving countdown for `coin` (BTC or LTC): blocks remaining and estimated date of the next halving.")
async def get_halving(coin: str = "BTC") -> dict:
    return await call("/v1/market/halving", 0.001, coin=coin)


# --- Hyperliquid perpetuals -------------------------------------------------
# Everything below is computed from Hyperliquid perpetuals (USDC-margined); prices are in USDC.

HL = "From Hyperliquid perpetuals (USDC-margined)."


@paid(0.001, "Live price of one asset in USDC: perp mark price (`price_type` mark) or order-book mid "
             "(`price_type` mid), with 24h change and 24h volume. `asset` is any active perp (BTC, ETH, SOL ...; "
             f"BTCUSDT and BTC-PERP also mean BTC). `currency` is USDC (USD and USDT accepted as aliases). {HL}")
async def get_price(asset: str = "BTC", currency: str = "USDC", price_type: str = "mark") -> dict:
    return await call("/v1/tools/price", 0.001, asset=asset, currency=currency, price_type=price_type)


@paid(0.003, "Prices in USDC for up to 20 assets in one call (`assets` comma-separated, e.g. 'BTC,ETH,SOL'), "
             "each with 24h change and volume; unknown symbols are skipped. `price_type` mark or mid. "
             f"Cheaper than several get_price calls. {HL}")
async def get_prices(assets: str = "BTC,ETH", currency: str = "USDC", price_type: str = "mark") -> dict:
    return await call("/v1/tools/price/multi", 0.003, assets=assets, currency=currency, price_type=price_type)


@paid(0.001, "List of every asset get_price and get_prices can quote: all active perps, by Hyperliquid name "
             f"(e.g. kPEPE = 1,000 PEPE). {HL}")
async def get_supported_assets() -> dict:
    return await call("/v1/tools/price/supported", 0.001)


@paid(0.002, "Current BTC market regime (BULLISH/BEARISH/NEUTRAL): BTC perp price vs its 20-period EMA on 12h "
             f"candles, with EMA value and slope. Updates at 00:00 and 12:00 UTC. {HL}")
async def get_market_regime() -> dict:
    return await call("/v1/regime/current", 0.002)


@paid(0.003, "Is `asset` trending or chopping? ADX-based, with +DI/-DI and trend direction, on `timeframe` "
             f"(1h, 4h, 1d). `quote` is USDC (USD and USDT accepted as aliases). {HL}")
async def get_chop_detection(asset: str = "BTC", timeframe: str = "4h", quote: str = "USDC") -> dict:
    return await call("/v1/regime/chop-detection", 0.003, asset=asset, timeframe=timeframe, quote=quote)


@paid(0.002, "Realized volatility of `asset` over `period` (7d, 14d, 30d): daily and annualized %, a "
             f"low/normal/high/extreme level and today's UTC range. Backward-looking, not implied vol. {HL}")
async def get_volatility(asset: str = "BTC", period: str = "7d") -> dict:
    return await call("/v1/vol/realized", 0.002, asset=asset, period=period)


@paid(0.002, "Market-silence score 0-1 for `asset` over `lookback` (7d, 14d, 30d): low volume, low volatility "
             f"and small price change combined. High silence often comes before a big move. {HL}")
async def get_market_silence(asset: str = "BTC", lookback: str = "7d") -> dict:
    return await call("/v1/vol/silence", 0.002, asset=asset, lookback=lookback)


@paid(0.003, "Volatility squeeze detector (Bollinger band width and its percentile) for `asset` on `timeframe` "
             "(1h, 4h, 1d): extreme/strong/moderate/none. Detects the setup, not the direction. "
             f"`quote` is USDC (USD and USDT accepted as aliases). {HL}")
async def get_compression_alert(asset: str = "BTC", timeframe: str = "4h", quote: str = "USDC") -> dict:
    return await call("/v1/vol/compression-alert", 0.003, asset=asset, timeframe=timeframe, quote=quote)


@paid(0.003, "ATR-based expected price range for `asset` over `period` (4h, 1d, 1w): 68% and 95% bands around "
             "the current price, in USDC. A statistical range, not a forecast. "
             f"`quote` is USDC (USD and USDT accepted as aliases). {HL}")
async def get_expected_move(asset: str = "BTC", period: str = "1d", quote: str = "USDC") -> dict:
    return await call("/v1/vol/expected-move", 0.003, asset=asset, period=period, quote=quote)


@paid(0.003, "Current funding rates for up to 20 coins (`symbols` comma-separated, e.g. 'BTC,ETH,SOL'). Funding "
             "is hourly: funding_rate_pct is the hourly rate, annualized = hourly x 8760; with 7d/30d averages "
             f"and a crowding signal. Positive = longs pay shorts. {HL}")
async def get_funding_rates(symbols: str = "BTC,ETH,SOL") -> dict:
    return await call("/v1/derivatives/funding-rates", 0.003, symbols=symbols)


@paid(0.003, "Leaderboard of the `limit` (1-50) most extreme current funding rates across all active perps, "
             "`sort` highest (crowded longs) or lowest (crowded shorts). Hourly funding, annualized = hourly x 8760. "
             f"{HL}")
async def get_top_funding_rates(limit: int = 10, sort: str = "highest") -> dict:
    return await call("/v1/derivatives/funding-rates/top", 0.003, limit=limit, sort=sort)


@paid(0.004, "Settled hourly funding history for one coin (`symbol`) over the last `days` (1-365): average, "
             "range, share of positive hours and the percentile of the latest rate. `history_days` in the result "
             f"shows how much history that coin has. Annualized = hourly x 8760. {HL}")
async def get_funding_history(symbol: str = "BTC", days: int = 90) -> dict:
    return await call("/v1/derivatives/funding-rates/history", 0.004, symbol=symbol, days=days)


@paid(0.003, "SwapHunt Alt Season Index (0-100), daily: share of the top 100 perps by 30-day volume (excl. BTC "
             f"and stablecoins) that beat BTC over 90 days. >=75 alt season, <=25 bitcoin season. {HL}")
async def get_alt_season() -> dict:
    return await call("/v1/market/alt-season", 0.003)


# --- Trading context --------------------------------------------------------

@paid(0.001, "Current trading session (Asia, London, New York, off-hours) and its typical volatility.")
async def get_trading_session() -> dict:
    return await call("/v1/context/session", 0.001)


@paid(0.001, "Is it a weekend or low-liquidity window right now? Returns a 0-100 liquidity score and the session.")
async def get_weekend_liquidity() -> dict:
    return await call("/v1/context/weekend-liquidity", 0.001)


# --- Maintainer check -------------------------------------------------------

async def check_prices() -> None:
    """Compare every tool's advertised price with the live 402. Pays nothing."""
    import re

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
        mcp.run()  # stdio


if __name__ == "__main__":
    main()
