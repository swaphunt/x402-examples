# SwapHunt x402 endpoints

Base URL: `https://x402.swaphunt.dev`. All paid routes are `GET`, return JSON, and answer `402 Payment Required` (x402 v2) until paid. No API key needed.

Payment: USDC, scheme `exact`, on any of these networks (same price on each; clients take the first one they support):

| Network | CAIP-2 id | USDC contract |
|---|---|---|
| Base | `eip155:8453` | `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` |
| Polygon | `eip155:137` | `0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359` |
| Arbitrum One | `eip155:42161` | `0xaf88d065e77c8cC2239327C5EDb3A432268e5831` |
| Solana | `solana:5eykt4UsFv8P8NJdTREpY1vzqKqZKvdp` | `EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v` |

Free routes: `/health`, `/`, `/docs`, `/openapi.json`. Rate limit: 60 requests/min per IP.

Generated from SwapHunt's pricing config, with real responses captured 2026-11-02. Long responses are trimmed (`…`).

Prices, regime, volatility, funding and alt season are computed from Hyperliquid perpetuals (USDC-margined), with prices in USDC. Fear & Greed data comes from [Alternative.me](https://alternative.me/crypto/fear-and-greed-index/); its responses include an `attribution` field: show that text next to the data wherever you display it.

## Overview

| Category | Endpoint | Price (USDC) | Params |
|---|---|---|---|
| Fear & Greed | `/v1/market/fear-greed` | $0.001 | – |
| Fear & Greed | `/v1/market/fear-greed/compare` | $0.002 | – |
| Fear & Greed | `/v1/market/fear-greed/history` | $0.005 | `days`=30, `start_date`, `end_date` |
| Halving | `/v1/market/halving` | $0.001 | `coin`=BTC |
| Context | `/v1/context/weekend-liquidity` | $0.001 | – |
| Context | `/v1/context/session` | $0.001 | – |
| Prices (Hyperliquid) | `/v1/tools/price` | $0.001 | `asset`=BTC, `currency`=USDC, `price_type`=mark |
| Prices (Hyperliquid) | `/v1/tools/price/multi` | $0.003 | `assets`=BTC,ETH, `currency`=USDC, `price_type`=mark |
| Prices (Hyperliquid) | `/v1/tools/price/supported` | $0.001 | – |
| Regime (Hyperliquid) | `/v1/regime/current` | $0.002 | – |
| Regime (Hyperliquid) | `/v1/regime/chop-detection` | $0.003 | `asset`=BTC, `timeframe`=4h, `quote`=USDC |
| Volatility (Hyperliquid) | `/v1/vol/realized` | $0.002 | `asset`=BTC, `period`=7d |
| Volatility (Hyperliquid) | `/v1/vol/silence` | $0.002 | `asset`=BTC, `lookback`=7d |
| Volatility (Hyperliquid) | `/v1/vol/compression-alert` | $0.003 | `asset`=BTC, `timeframe`=4h, `quote`=USDC |
| Volatility (Hyperliquid) | `/v1/vol/expected-move` | $0.003 | `asset`=BTC, `period`=1d, `quote`=USDC |
| Funding (Hyperliquid) | `/v1/derivatives/funding-rates` | $0.003 | `symbols`=BTC,ETH,SOL |
| Funding (Hyperliquid) | `/v1/derivatives/funding-rates/top` | $0.003 | `limit`=10, `sort`=highest |
| Funding (Hyperliquid) | `/v1/derivatives/funding-rates/history` | $0.004 | `symbol`=BTC, `days`=90 |
| Market (Hyperliquid) | `/v1/market/alt-season` | $0.003 | – |

19 paid endpoints. Cheapest: $0.001. Most expensive: $0.005.

## Details and example responses

### Fear & Greed

#### `/v1/market/fear-greed` — $0.001

Current Crypto Fear & Greed Index (0-100) with its label (Extreme Fear → Extreme Greed), updated daily. A single market-mood gauge for risk-on/risk-off context. For trend over time use /fear-greed/compare or /fear-greed/history.

Example response (captured):

```json
{
  "value": 37,
  "label": "Fear",
  "timestamp": "2026-11-02T00:00:00",
  "source": "alternative.me",
  "attribution": "Data provided by Alternative.me Crypto Fear & Greed Index"
}
```

#### `/v1/market/fear-greed/compare` — $0.002

Fear & Greed now vs yesterday, 7 days and 30 days ago — with the deltas — so an agent can see whether market sentiment is improving or deteriorating, not just today's number. Use for momentum-of-mood.

Example response (captured):

```json
{
  "value": 37,
  "label": "Fear",
  "timestamp": "2026-11-02T00:00:00",
  "source": "alternative.me",
  "attribution": "Data provided by Alternative.me Crypto Fear & Greed Index",
  "yesterday": 34,
  "week_ago": 50,
  "month_ago": 67,
  "change_1d": 3,
  "change_7d": -13,
  "…": "1 more keys"
}
```

#### `/v1/market/fear-greed/history` — $0.005

Historical Fear & Greed time series (up to 365 days), each day with value + classification. Use to backtest sentiment, chart mood cycles or correlate fear/greed with price. The raw series, not a summary.

Example response (captured):

```json
{
  "history": [
    {
      "date": "2026-11-02",
      "value": 37,
      "classification": "Fear"
    },
    "…"
  ],
  "start_date": "2026-10-04",
  "end_date": "2026-11-02",
  "count": 30,
  "source": "alternative.me",
  "attribution": "Data provided by Alternative.me Crypto Fear & Greed Index",
  "data_available_from": "2018-02-01"
}
```

### Halving

#### `/v1/market/halving` — $0.001

BTC or LTC halving countdown: blocks remaining and the estimated date of the next halving. Use for cycle-timing narratives and supply-shock context. Estimate (block-time based), not an exact timestamp.

Example response (captured):

```json
{
  "coin": "BTC",
  "coin_name": "Bitcoin",
  "current_block": 974224,
  "next_halving_block": 1050000,
  "blocks_remaining": 75776,
  "estimated_date": "2028-04-11T12:12:57.236825",
  "days_remaining": 526,
  "progress_pct": 63.92,
  "current_block_reward": 3.125,
  "next_block_reward": 1.5625,
  "…": "2 more keys"
}
```

### Context

#### `/v1/context/weekend-liquidity` — $0.001

Is it a weekend / low-liquidity window right now? Returns the current session and a 0-100 liquidity score. Use to widen stops and discount thin-market moves. Lightweight market-condition context.

Example response (captured):

```json
{
  "is_weekend": false,
  "is_low_liquidity": false,
  "day_of_week": "Monday",
  "weekday_number": 0,
  "current_hour_utc": 6,
  "session": "asian",
  "is_overlap": false,
  "liquidity_score": 95,
  "verdict": "Asian session. Moderate liquidity.",
  "updated_at": "2026-11-02T06:52:57.601489+00:00"
}
```

#### `/v1/context/session` — $0.001

Current trading session (Asia / London / NY / Off) plus historical volatility for that session. Use to time entries around the most active hours and set session-aware expectations.

Example response (captured):

```json
{
  "current_session": "asian",
  "session_name": "Asian",
  "markets_active": "Tokyo, Sydney, Singapore",
  "is_overlap": false,
  "session_start_utc": "2026-11-02T00:00:00+00:00",
  "session_end_utc": "2026-11-02T08:00:00+00:00",
  "minutes_remaining": 67,
  "next_session": "london",
  "expected_volatility": "low",
  "volatility_multiplier": 0.7,
  "…": "2 more keys"
}
```

### Prices (Hyperliquid)

#### `/v1/tools/price` — $0.001

SwapHunt — a crypto market-context toolkit for trading agents: live prices, market regime, volatility, sentiment, funding, macro events, seasonality and anti-FOMO sanity checks, all pay-per-call. This route returns one asset's live price from Hyperliquid perpetuals (USDC-margined), quoted in USDC: the perp mark price (or the order-book mid with price_type=mid), 24h mark change % and 24h notional volume in USDC. high_24h/low_24h are null. Any active Hyperliquid perp (BTC, ETH, SOL, ...); see /price/supported. For many assets at once use /price/multi.

Example response (captured):

```json
{
  "asset": "BTC",
  "price": 78162.0,
  "currency": "USDC",
  "price_type": "mark",
  "change_24h": 0.24,
  "high_24h": null,
  "low_24h": null,
  "volume_24h": 1133419438.352549,
  "updated_at": "2026-11-02T06:52:31.475981",
  "source": "Hyperliquid perpetuals"
}
```

#### `/v1/tools/price/multi` — $0.003

Batch prices for up to 20 assets in one call from Hyperliquid perpetuals (USDC-margined), quoted in USDC — each with the perp mark price (or order-book mid with price_type=mid), 24h mark change % and 24h notional volume, keyed by symbol. Unknown symbols are skipped. The cost-efficient way to price a basket or portfolio in a single request instead of N calls.

Example response (captured):

```json
{
  "prices": {
    "BTC": {
      "asset": "BTC",
      "price": 78162.0,
      "currency": "USDC",
      "price_type": "mark",
      "change_24h": 0.24,
      "high_24h": null,
      "low_24h": null,
      "volume_24h": 1133419438.352549,
      "updated_at": "2026-11-02T06:52:31.475981",
      "source": "Hyperliquid perpetuals"
    },
    "ETH": {
      "asset": "ETH",
      "price": 2284.7,
      "currency": "USDC",
      "price_type": "mark",
      "change_24h": 0.69,
      "high_24h": null,
      "low_24h": null,
      "volume_24h": 401683141.075109,
      "updated_at": "2026-11-02T06:52:31.475981",
      "source": "Hyperliquid perpetuals"
    }
  },
  "currency": "USDC",
  "price_type": "mark",
  "updated_at": "2026-11-02T06:52:56.501568",
  "source": "Hyperliquid perpetuals"
}
```

#### `/v1/tools/price/supported` — $0.001

Every asset /price and /price/multi can quote: all active Hyperliquid perpetuals (USDC-margined), by Hyperliquid name (e.g. kPEPE = 1,000 PEPE). Call this once to discover valid `asset` symbols before pricing. Returns an object with the asset list, count, quote currency (USDC) and source.

Example response (captured):

```json
{
  "assets": [
    "0G",
    "…"
  ],
  "count": 179,
  "currency": "USDC",
  "source": "Hyperliquid perpetuals"
}
```

### Regime (Hyperliquid)

#### `/v1/regime/current` — $0.002

Current BTC market regime — BULLISH / BEARISH / NEUTRAL — from Hyperliquid perpetuals (USDC-margined): the BTC perp price vs its 20-period EMA on 12h candles, with the EMA value and slope (prices in USDC). Updates at each 12h close (00:00 and 12:00 UTC). The top-level risk filter: trade-with-trend context before any entry. BTC-based; pair with per-asset tools for alts.

Example response (captured):

```json
{
  "regime": "BEARISH",
  "price": 78162.0,
  "ema20": 79470.17,
  "price_vs_ema_pct": -1.44,
  "ema_slope_pct": -1.352,
  "interval": "12h",
  "candle_close": "2026-11-01T23:59:59.999000Z",
  "next_update": "2026-11-02T11:59:59.999000Z",
  "updated_at": "2026-11-02T06:52:55.821997Z",
  "source": "Hyperliquid perpetuals"
}
```

#### `/v1/regime/chop-detection` — $0.003

ADX-based chop-vs-trend detector on candles from Hyperliquid perpetuals (USDC-margined) for an asset/timeframe: is price trending or stuck in a range? Returns is_chop, a chop level, ADX, +DI/-DI and trend direction; quote is USDC and pair like BTC-USDC. Use to avoid trend strategies in chop (and range strategies in trends).

Example response (captured):

```json
{
  "asset": "BTC",
  "quote": "USDC",
  "pair": "BTC-USDC",
  "timeframe": "4h",
  "is_chop": true,
  "chop_level": "moderate",
  "adx": 22.17,
  "adx_interpretation": {
    "below_20": "Choppy/ranging",
    "20_25": "Trend emerging",
    "25_50": "Strong trend",
    "above_50": "Very strong trend"
  },
  "plus_di": 19.74,
  "minus_di": 21.83,
  "…": "4 more keys"
}
```

### Volatility (Hyperliquid)

#### `/v1/vol/realized` — $0.002

Realized volatility for an asset from daily candles of Hyperliquid perpetuals (USDC-margined): daily and annualized %, a low/normal/high/extreme bucket and the current UTC day's high/low/range vs open. Use to size positions and set expectations. Backward-looking (realized), not implied/option vol.

Example response (captured):

```json
{
  "asset": "BTC",
  "realized_volatility_pct": 1.8,
  "annualized_volatility_pct": 34.3,
  "level": "normal",
  "high_24h_pct": 0.67,
  "low_24h_pct": -0.41,
  "range_24h_pct": 1.08,
  "period": "7d",
  "updated_at": "2026-11-02T06:49:20.584109",
  "source": "Hyperliquid perpetuals"
}
```

#### `/v1/vol/silence` — $0.002

Market-silence score 0-1 from daily candles of Hyperliquid perpetuals (USDC-margined) — a composite of low notional volume, low volatility and small price change. High silence often precedes expansion. Use to spot the calm-before-the-move. Pairs with /vol/compression-alert.

Example response (captured):

```json
{
  "asset": "BTC",
  "silence_score": 0.79,
  "level": "high",
  "recommendation": "reduce_activity",
  "factors": {
    "volume_ratio": 0.16,
    "volume_today_usd": 415798709.0,
    "volume_avg_usd": 2520293725.0,
    "volatility_pct": 1.83,
    "price_change_24h_pct": -0.2
  },
  "lookback": "7d",
  "updated_at": "2026-11-02T06:52:57.460530",
  "source": "Hyperliquid perpetuals"
}
```

#### `/v1/vol/compression-alert` — $0.003

Bollinger-Band squeeze detector on candles from Hyperliquid perpetuals (USDC-margined): is volatility compressing toward a likely expansion? Returns extreme/strong/moderate/none, band width and its percentile; quote is USDC and pair like BTC-USDC. Use to anticipate breakouts before they fire. Detects the setup, not the direction.

Example response (captured):

```json
{
  "asset": "BTC",
  "quote": "USDC",
  "pair": "BTC-USDC",
  "timeframe": "4h",
  "is_squeeze": true,
  "squeeze_level": "strong",
  "bollinger_width_pct": 2.2,
  "avg_width_pct": 4.32,
  "width_percentile": 12.5,
  "width_ratio": 0.51,
  "…": "5 more keys"
}
```

#### `/v1/vol/expected-move` — $0.003

ATR-based expected price range from candles of Hyperliquid perpetuals (USDC-margined): the 68% and 95% bands around the current price, in USDC; quote is USDC and pair like BTC-USDC. Use to set realistic targets, stops and breakout thresholds. A statistical range, not a directional forecast.

Example response (captured):

```json
{
  "asset": "BTC",
  "quote": "USDC",
  "pair": "BTC-USDC",
  "period": "daily",
  "current_price": 78173.0,
  "atr_14": 1894.14,
  "expected_move_usd": 1894.14,
  "expected_move_pct": 2.42,
  "expected_range": {
    "high": 80067.14,
    "low": 76278.86
  },
  "probability_ranges": {
    "68_pct": {
      "high": 80067.14,
      "low": 76278.86,
      "description": "68% of moves stay within this range"
    },
    "95_pct": {
      "high": 81961.29,
      "low": 74384.71,
      "description": "95% of moves stay within this range"
    }
  },
  "…": "4 more keys"
}
```

### Funding (Hyperliquid)

#### `/v1/derivatives/funding-rates` — $0.003

Current funding rates for up to 20 Hyperliquid perpetuals (USDC-margined). Funding is settled hourly: funding_rate_pct is the hourly rate and annualized_rate_pct = hourly rate × 8760, plus 7d/30d averages, mark price in USDC and a crowding signal. Positive = longs pay shorts (crowded longs). Use to read positioning before entering. Funding, not open interest.

Example response (captured):

```json
{
  "rates": [
    {
      "symbol": "BTC",
      "funding_rate": 1.3e-05,
      "funding_rate_pct": 0.00125,
      "annualized_rate_pct": 10.95,
      "mark_price": 78162.0,
      "next_funding_time": "2026-11-02T07:00:00",
      "signal": "neutral",
      "avg_7d": 0.001214,
      "avg_30d": 0.00101,
      "avg_7d_annualized_pct": 10.63,
      "…": "4 more keys"
    },
    "…"
  ],
  "count": 3,
  "updated_at": "2026-11-02T06:52:31.475981",
  "source": "Hyperliquid perpetuals"
}
```

#### `/v1/derivatives/funding-rates/top` — $0.003

Top N current funding rates, highest or lowest, across all active Hyperliquid perpetuals (USDC-margined; funding settled hourly, annualized = hourly rate × 8760) — a leaderboard of the most crowded longs (highest) or shorts (lowest). Use to spot squeeze and crowding extremes fast.

Example response (captured):

```json
{
  "entries": [
    {
      "symbol": "USELESS",
      "funding_rate": 9.7e-05,
      "funding_rate_pct": 0.009747,
      "annualized_rate_pct": 85.39,
      "mark_price": 0.12619,
      "signal": "elevated",
      "rank": 1
    },
    "…"
  ],
  "count": 10,
  "total_symbols": 179,
  "sort": "highest",
  "updated_at": "2026-11-02T06:52:31.475981",
  "source": "Hyperliquid perpetuals"
}
```

#### `/v1/derivatives/funding-rates/history` — $0.004

Settled hourly funding rates for one coin on Hyperliquid perpetuals (USDC-margined), with average, range, share of positive periods and the percentile of the latest rate. Up to 365 days; history_days shows coverage per coin. Annualized = hourly rate × 8760. Use to judge whether today's funding is unusual for that coin.

Example response (captured):

```json
{
  "symbol": "BTC",
  "days": 90,
  "interval_hours": 1.0,
  "count": 2160,
  "history_days": 90.0,
  "current_pct": 0.00125,
  "avg_pct": 0.000992,
  "min_pct": -0.001595,
  "max_pct": 0.008977,
  "avg_annualized_pct": 8.69,
  "…": "4 more keys"
}
```

### Market (Hyperliquid)

#### `/v1/market/alt-season` — $0.003

SwapHunt Alt Season Index (0-100), computed daily from Hyperliquid perpetuals (USDC-margined): share of the top 100 Hyperliquid perpetuals by 30-day volume (excl. BTC and stablecoins, delisted perps included while traded) outperforming BTC over 90 days; ≥75 alt season, ≤25 bitcoin season, otherwise neutral. Returns the index, label, is_alt_season, universe size, number outperforming and BTC's 90-day return. Use to time BTC↔alt rotation.

Example response (captured):

```json
{
  "alt_season_index": 50.0,
  "label": "Neutral",
  "is_alt_season": false,
  "date": "2026-11-01",
  "universe": 100,
  "outperforming": 50,
  "btc_return_90d_pct": 23.36,
  "method": "SwapHunt Alt Season Index: share of the top 100 Hyperliquid perpetuals by 30-...",
  "source": "Hyperliquid perpetuals",
  "updated_at": "2026-11-02T06:49:20.591855+00:00"
}
```
