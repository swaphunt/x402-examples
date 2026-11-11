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

Generated from SwapHunt's pricing config, with real responses captured 2026-11-03. Long responses are trimmed (`…`).

Prices, regime, volatility, funding and alt season are computed from Hyperliquid perpetuals (USDC-margined), with prices in USDC. Fear & Greed data comes from [Alternative.me](https://alternative.me/crypto/fear-and-greed-index/); its responses include an `attribution` field: show that text next to the data wherever you display it.

## Overview

| Category | Endpoint | Price (USDC) | Params |
|---|---|---|---|
| Fear & Greed | `/v1/market/fear-greed` | $0.005 | – |
| Fear & Greed | `/v1/market/fear-greed/compare` | $0.002 | – |
| Fear & Greed | `/v1/market/fear-greed/history` | $0.005 | `days`=30, `start_date`, `end_date` |
| Halving | `/v1/market/halving` | $0.001 | `coin`=BTC |
| Context | `/v1/context/weekend-liquidity` | $0.005 | – |
| Context | `/v1/context/session` | $0.005 | – |
| Prices (Hyperliquid) | `/v1/tools/price` | $0.005 | `asset`=BTC, `currency`=USDC, `price_type`=mark |
| Prices (Hyperliquid) | `/v1/tools/price/multi` | $0.003 | `assets`=BTC,ETH, `currency`=USDC, `price_type`=mark |
| Prices (Hyperliquid) | `/v1/tools/price/supported` | $0.001 | – |
| Regime (Hyperliquid) | `/v1/regime/current` | $0.010 | – |
| Regime (Hyperliquid) | `/v1/regime/chop-detection` | $0.003 | `asset`=BTC, `timeframe`=4h, `quote`=USDC |
| Volatility (Hyperliquid) | `/v1/vol/realized` | $0.010 | `asset`=BTC, `period`=7d |
| Volatility (Hyperliquid) | `/v1/vol/silence` | $0.002 | `asset`=BTC, `lookback`=7d |
| Volatility (Hyperliquid) | `/v1/vol/compression-alert` | $0.003 | `asset`=BTC, `timeframe`=4h, `quote`=USDC |
| Volatility (Hyperliquid) | `/v1/vol/expected-move` | $0.003 | `asset`=BTC, `period`=1d, `quote`=USDC |
| Funding (Hyperliquid) | `/v1/derivatives/funding-rates` | $0.015 | `symbols`=BTC,ETH,SOL |
| Funding (Hyperliquid) | `/v1/derivatives/funding-rates/top` | $0.003 | `limit`=10, `sort`=highest |
| Funding (Hyperliquid) | `/v1/derivatives/funding-rates/history` | $0.004 | `symbol`=BTC, `days`=90 |
| Market (Hyperliquid) | `/v1/market/alt-season` | $0.003 | – |
| Market (Hyperliquid) | `/v1/market/coin-strength` | $0.015 | `coin`=ETH, `period`=24h, `quote`=USDC |
| Market (Hyperliquid) | `/v1/market/momentum-rank` | $0.015 | `period`=24h, `limit`=10, `quote`=USDC |
| Market (Hyperliquid) | `/v1/market/correlation` | $0.003 | `coin`=ETH, `period`=7d, `quote`=USDC |
| Hyperliquid (Hyperliquid) | `/v1/sanity/is-this-a-dip` | $0.003 | `symbol`=BTC, `quote`=USDC |
| Hyperliquid (Hyperliquid) | `/v1/sanity/is-this-a-breakout` | $0.003 | `symbol`=BTC, `level` (required), `direction`=up, `quote`=USDC |
| Hyperliquid (Hyperliquid) | `/v1/sanity/is-this-support` | $0.003 | `symbol`=BTC, `level` (required), `quote`=USDC |
| Hyperliquid (Hyperliquid) | `/v1/sanity/is-this-oversold` | $0.003 | `symbol`=BTC, `quote`=USDC |
| Hyperliquid (Hyperliquid) | `/v1/fomo/how-late-am-i` | $0.003 | `symbol`=BTC, `quote`=USDC |
| Hyperliquid (Hyperliquid) | `/v1/fomo/pump-age` | $0.003 | `symbol`=BTC, `quote`=USDC |
| Hyperliquid (Hyperliquid) | `/v1/fomo/already-extended` | $0.003 | `symbol`=BTC, `quote`=USDC |
| Hyperliquid (Hyperliquid) | `/v1/fomo/green-candles-streak` | $0.003 | `symbol`=BTC, `interval`=4h, `quote`=USDC |

30 paid endpoints. Cheapest: $0.001. Most expensive: $0.015.

## Details and example responses

### Fear & Greed

#### `/v1/market/fear-greed` — $0.005

Current Crypto Fear & Greed Index (0-100) with its label (Extreme Fear to Extreme Greed), updated daily. A single market-mood gauge for risk-on/risk-off context. For trend over time use /v1/market/fear-greed/compare or /v1/market/fear-greed/history

Example response (captured):

```json
{
  "value": 26,
  "label": "Fear",
  "timestamp": "2026-11-03T00:00:00",
  "source": "alternative.me",
  "attribution": "Data provided by Alternative.me Crypto Fear & Greed Index"
}
```

#### `/v1/market/fear-greed/compare` — $0.002

Fear & Greed now vs yesterday, 7 days and 30 days ago, with the deltas, so an agent can see whether market sentiment is improving or deteriorating, not just today's number. Use for momentum-of-mood

Example response (captured):

```json
{
  "value": 26,
  "label": "Fear",
  "timestamp": "2026-11-03T00:00:00",
  "source": "alternative.me",
  "attribution": "Data provided by Alternative.me Crypto Fear & Greed Index",
  "yesterday": 37,
  "week_ago": 48,
  "month_ago": 65,
  "change_1d": -11,
  "change_7d": -22,
  "…": "1 more keys"
}
```

#### `/v1/market/fear-greed/history` — $0.005

Historical Fear & Greed time series (up to 365 days), each day with value + classification. Use to backtest sentiment, chart mood cycles or correlate fear/greed with price. The raw series, not a summary

Example response (captured):

```json
{
  "history": [
    {
      "date": "2026-11-03",
      "value": 26,
      "classification": "Fear"
    },
    "…"
  ],
  "start_date": "2026-10-05",
  "end_date": "2026-11-03",
  "count": 30,
  "source": "alternative.me",
  "attribution": "Data provided by Alternative.me Crypto Fear & Greed Index",
  "data_available_from": "2018-02-01"
}
```

### Halving

#### `/v1/market/halving` — $0.001

BTC or LTC halving countdown: blocks remaining and the estimated date of the next halving. Use for cycle-timing narratives and supply-shock context. Estimate (block-time based), not an exact timestamp

Example response (captured):

```json
{
  "coin": "BTC",
  "coin_name": "Bitcoin",
  "current_block": 974435,
  "next_halving_block": 1050000,
  "blocks_remaining": 75565,
  "estimated_date": "2028-04-11T14:29:22.567210",
  "days_remaining": 524,
  "progress_pct": 64.02,
  "current_block_reward": 3.125,
  "next_block_reward": 1.5625,
  "…": "2 more keys"
}
```

### Context

#### `/v1/context/weekend-liquidity` — $0.005

Is it a weekend / low-liquidity window right now? Returns the current session and a 0-100 liquidity score. Use to widen stops and discount thin-market moves. Lightweight market-condition context

Example response (captured):

```json
{
  "is_weekend": false,
  "is_low_liquidity": false,
  "day_of_week": "Tuesday",
  "weekday_number": 1,
  "current_hour_utc": 20,
  "session": "new_york",
  "is_overlap": false,
  "liquidity_score": 100,
  "verdict": "New York session. High liquidity. Good conditions.",
  "updated_at": "2026-11-03T20:19:23.818269+00:00"
}
```

#### `/v1/context/session` — $0.005

Current trading session (Asia / London / NY / Off) plus historical volatility for that session. Use to time entries around the most active hours and set session-aware expectations

Example response (captured):

```json
{
  "current_session": "new_york",
  "session_name": "New York",
  "markets_active": "New York, Chicago",
  "is_overlap": false,
  "session_start_utc": "2026-11-03T13:00:00+00:00",
  "session_end_utc": "2026-11-03T21:00:00+00:00",
  "minutes_remaining": 40,
  "next_session": "off_hours",
  "expected_volatility": "high",
  "volatility_multiplier": 1.2,
  "…": "2 more keys"
}
```

### Prices (Hyperliquid)

#### `/v1/tools/price` — $0.005

SwapHunt is a crypto market-context API for trading agents, with live prices, funding, volatility and market regime from Hyperliquid perpetuals, the SwapHunt Alt Season Index, Fear & Greed, the halving and session context, all pay-per-call (docs and pricing at https://swaphunt.dev/api). This route returns one asset's live price from Hyperliquid perpetuals (USDC-margined), quoted in USDC: the perp mark price (or the order-book mid with price_type=mid), 24h mark change % and 24h notional volume in USDC. high_24h/low_24h are null. Any active Hyperliquid perp such as BTC, ETH or SOL; see /v1/tools/price/supported. For many assets at once use /v1/tools/price/multi

Example response (captured):

```json
{
  "asset": "BTC",
  "price": 77711.9,
  "currency": "USDC",
  "price_type": "mark",
  "change_24h": 1.06,
  "high_24h": null,
  "low_24h": null,
  "volume_24h": 2213766142.913264,
  "updated_at": "2026-11-03T20:19:21.622646",
  "source": "Hyperliquid perpetuals"
}
```

#### `/v1/tools/price/multi` — $0.003

Batch prices for up to 20 assets in one call from Hyperliquid perpetuals (USDC-margined), quoted in USDC, each with the perp mark price (or order-book mid with price_type=mid), 24h mark change % and 24h notional volume, keyed by symbol. Unknown symbols are skipped. The cost-efficient way to price a basket or portfolio in a single request instead of N calls

Example response (captured):

```json
{
  "prices": {
    "BTC": {
      "asset": "BTC",
      "price": 77711.9,
      "currency": "USDC",
      "price_type": "mark",
      "change_24h": 1.06,
      "high_24h": null,
      "low_24h": null,
      "volume_24h": 2213766142.913264,
      "updated_at": "2026-11-03T20:19:21.622646",
      "source": "Hyperliquid perpetuals"
    },
    "ETH": {
      "asset": "ETH",
      "price": 2284.4,
      "currency": "USDC",
      "price_type": "mark",
      "change_24h": 1.53,
      "high_24h": null,
      "low_24h": null,
      "volume_24h": 614747645.623131,
      "updated_at": "2026-11-03T20:19:21.622646",
      "source": "Hyperliquid perpetuals"
    }
  },
  "currency": "USDC",
  "price_type": "mark",
  "updated_at": "2026-11-03T20:19:21.687895",
  "source": "Hyperliquid perpetuals"
}
```

#### `/v1/tools/price/supported` — $0.001

Every asset /v1/tools/price and /v1/tools/price/multi can quote: all active Hyperliquid perpetuals (USDC-margined), by Hyperliquid name (e.g. kPEPE = 1,000 PEPE). Call this once to discover valid `asset` symbols before pricing. Returns an object with the asset list, count, quote currency (USDC) and source, plus `covered`: the coins the analysis endpoints accept (top 50 Hyperliquid perpetuals by 30-day volume, recomputed daily) and the `coverage_rule`

Example response (captured):

```json
{
  "assets": [
    "0G",
    "…"
  ],
  "count": 179,
  "currency": "USDC",
  "source": "Hyperliquid perpetuals",
  "covered": [
    "AAVE",
    "…"
  ],
  "coverage_rule": "Top 50 Hyperliquid perpetuals by 30-day notional volume (stablecoins excluded..."
}
```

### Regime (Hyperliquid)

#### `/v1/regime/current` — $0.010

Current BTC market regime (BULLISH / BEARISH / NEUTRAL) from Hyperliquid perpetuals (USDC-margined): the BTC perp price vs its 20-period EMA on 12h candles, with the EMA value and slope (prices in USDC). Updates at each 12h close (00:00 and 12:00 UTC). The top-level risk filter: trade-with-trend context before any entry. BTC-based; pair with per-asset tools for alts

Example response (captured):

```json
{
  "regime": "BEARISH",
  "price": 77681.0,
  "ema20": 78888.67,
  "price_vs_ema_pct": -2.28,
  "ema_slope_pct": -1.098,
  "interval": "12h",
  "candle_close": "2026-11-03T11:59:59.999000Z",
  "next_update": "2026-11-03T23:59:59.999000Z",
  "updated_at": "2026-11-03T20:18:40.402653Z",
  "source": "Hyperliquid perpetuals"
}
```

#### `/v1/regime/chop-detection` — $0.003

ADX-based chop-vs-trend detector on candles from Hyperliquid perpetuals (USDC-margined) for an asset/timeframe: is price trending or stuck in a range? Returns is_chop, a chop level, ADX, +DI/-DI and trend direction; quote is USDC and pair like BTC-USDC. Use to avoid trend strategies in chop (and range strategies in trends)

Example response (captured):

```json
{
  "asset": "BTC",
  "quote": "USDC",
  "pair": "BTC-USDC",
  "timeframe": "4h",
  "is_chop": true,
  "chop_level": "high",
  "adx": 19.88,
  "adx_interpretation": {
    "below_20": "Choppy/ranging",
    "20_25": "Trend emerging",
    "25_50": "Strong trend",
    "above_50": "Very strong trend"
  },
  "plus_di": 16.5,
  "minus_di": 20.44,
  "…": "4 more keys"
}
```

### Volatility (Hyperliquid)

#### `/v1/vol/realized` — $0.010

Realized volatility for an asset from daily candles of Hyperliquid perpetuals (USDC-margined): daily and annualized %, a low/normal/high/extreme bucket and the current UTC day's high/low/range vs open. Use to size positions and set expectations. Backward-looking (realized), not implied/option vol

Example response (captured):

```json
{
  "asset": "BTC",
  "realized_volatility_pct": 1.92,
  "annualized_volatility_pct": 36.7,
  "level": "normal",
  "high_24h_pct": 1.39,
  "low_24h_pct": -0.6,
  "range_24h_pct": 1.99,
  "period": "7d",
  "updated_at": "2026-11-03T20:15:29.703159",
  "source": "Hyperliquid perpetuals"
}
```

#### `/v1/vol/silence` — $0.002

Market-silence score 0-1 from daily candles of Hyperliquid perpetuals (USDC-margined): a composite of low notional volume, low volatility and small price change. High silence often precedes expansion. Use to spot the calm-before-the-move. Pairs with /v1/vol/compression-alert

Example response (captured):

```json
{
  "asset": "BTC",
  "silence_score": 0.45,
  "level": "medium",
  "recommendation": "be_cautious",
  "factors": {
    "volume_ratio": 0.7,
    "volume_today_usd": 1766352090.0,
    "volume_avg_usd": 2508802713.0,
    "volatility_pct": 1.96,
    "price_change_24h_pct": 1.16
  },
  "lookback": "7d",
  "updated_at": "2026-11-03T20:19:23.127003",
  "source": "Hyperliquid perpetuals"
}
```

#### `/v1/vol/compression-alert` — $0.003

Bollinger-Band squeeze detector on candles from Hyperliquid perpetuals (USDC-margined): is volatility compressing toward a likely expansion? Returns extreme/strong/moderate/none, band width and its percentile; quote is USDC and pair like BTC-USDC. Use to anticipate breakouts before they fire. Detects the setup, not the direction

Example response (captured):

```json
{
  "asset": "BTC",
  "quote": "USDC",
  "pair": "BTC-USDC",
  "timeframe": "4h",
  "is_squeeze": true,
  "squeeze_level": "strong",
  "bollinger_width_pct": 2.51,
  "avg_width_pct": 4.27,
  "width_percentile": 22.5,
  "width_ratio": 0.59,
  "…": "5 more keys"
}
```

#### `/v1/vol/expected-move` — $0.003

ATR-based expected price range from candles of Hyperliquid perpetuals (USDC-margined): the 68% and 95% bands around the current price, in USDC; quote is USDC and pair like BTC-USDC. Use to set realistic targets, stops and breakout thresholds. A statistical range, not a directional forecast

Example response (captured):

```json
{
  "asset": "BTC",
  "quote": "USDC",
  "pair": "BTC-USDC",
  "period": "daily",
  "current_price": 77695.0,
  "atr_14": 1937.79,
  "expected_move_usd": 1937.79,
  "expected_move_pct": 2.49,
  "expected_range": {
    "high": 79632.79,
    "low": 75757.21
  },
  "probability_ranges": {
    "68_pct": {
      "high": 79632.79,
      "low": 75757.21,
      "description": "68% of moves stay within this range"
    },
    "95_pct": {
      "high": 81570.57,
      "low": 73819.43,
      "description": "95% of moves stay within this range"
    }
  },
  "…": "4 more keys"
}
```

### Funding (Hyperliquid)

#### `/v1/derivatives/funding-rates` — $0.015

Current funding rates for up to 20 Hyperliquid perpetuals (USDC-margined). Funding is settled hourly: funding_rate_pct is the hourly rate and annualized_rate_pct = hourly rate times 8760, plus 7d/30d averages, mark price in USDC and a crowding signal. Positive = longs pay shorts (crowded longs). Use to read positioning before entering. Funding, not open interest

Example response (captured):

```json
{
  "rates": [
    {
      "symbol": "BTC",
      "funding_rate": 1.3e-05,
      "funding_rate_pct": 0.00125,
      "annualized_rate_pct": 10.95,
      "mark_price": 77711.9,
      "next_funding_time": "2026-11-03T21:00:00",
      "signal": "neutral",
      "avg_7d": 0.001221,
      "avg_30d": 0.001021,
      "avg_7d_annualized_pct": 10.7,
      "…": "4 more keys"
    },
    "…"
  ],
  "count": 3,
  "updated_at": "2026-11-03T20:19:21.622646",
  "source": "Hyperliquid perpetuals"
}
```

#### `/v1/derivatives/funding-rates/top` — $0.003

Top N current funding rates, highest or lowest, across all active Hyperliquid perpetuals (USDC-margined; funding settled hourly, annualized = hourly rate times 8760): a leaderboard of the most crowded longs (highest) or shorts (lowest). Use to spot squeeze and crowding extremes fast

Example response (captured):

```json
{
  "entries": [
    {
      "symbol": "GOAT",
      "funding_rate": 0.000145,
      "funding_rate_pct": 0.014509,
      "annualized_rate_pct": 127.1,
      "mark_price": 0.013856,
      "signal": "extreme_positive",
      "rank": 1
    },
    "…"
  ],
  "count": 10,
  "total_symbols": 179,
  "sort": "highest",
  "updated_at": "2026-11-03T20:19:21.622646",
  "source": "Hyperliquid perpetuals"
}
```

#### `/v1/derivatives/funding-rates/history` — $0.004

Settled hourly funding rates for one coin on Hyperliquid perpetuals (USDC-margined), with average, range, share of positive periods and the percentile of the latest rate. Up to 365 days; history_days shows coverage per coin. Annualized = hourly rate times 8760. Use to judge whether today's funding is unusual for that coin

Example response (captured):

```json
{
  "symbol": "BTC",
  "days": 90,
  "interval_hours": 1.0,
  "count": 2160,
  "history_days": 90.0,
  "current_pct": 0.00125,
  "avg_pct": 0.001008,
  "min_pct": -0.001595,
  "max_pct": 0.008977,
  "avg_annualized_pct": 8.83,
  "…": "4 more keys"
}
```

### Market (Hyperliquid)

#### `/v1/market/alt-season` — $0.003

SwapHunt Alt Season Index (0-100), computed daily from Hyperliquid perpetuals (USDC-margined): share of the top 100 Hyperliquid perpetuals by 30-day volume (excl. BTC and stablecoins, delisted perps included while traded) outperforming BTC over 90 days. 75 or above is alt season, 25 or below is bitcoin season, otherwise neutral. Returns the index, label, is_alt_season, universe size, number outperforming and BTC's 90-day return. Use to time rotation between BTC and alts

Example response (captured):

```json
{
  "alt_season_index": 51.0,
  "label": "Neutral",
  "is_alt_season": false,
  "date": "2026-11-02",
  "universe": 100,
  "outperforming": 51,
  "btc_return_90d_pct": 19.88,
  "method": "SwapHunt Alt Season Index: share of the top 100 Hyperliquid perpetuals by 30-...",
  "source": "Hyperliquid perpetuals",
  "updated_at": "2026-11-03T20:15:29.706930+00:00"
}
```

#### `/v1/market/coin-strength` — $0.015

Relative strength of a coin vs BTC on Hyperliquid perpetuals (USDC-margined): the coin's return minus BTC's over 24h, 7d or 30d, as a category (very_strong to very_weak) plus the strength ratio. Use to see whether an alt is leading or lagging BTC before entering. A strength read, not a price target. Coverage: top 50 Hyperliquid perpetuals by 30-day volume; see /v1/tools/price/supported (other coins get 422 not_covered, no charge)

Example response (captured):

```json
{
  "coin": "ETH",
  "quote": "USDC",
  "pair": "ETH-USDC",
  "period": "24h",
  "coin_return_pct": 1.61,
  "btc_return_pct": 0.82,
  "vs_btc_pct": 0.79,
  "strength_ratio": 1.008,
  "strength": "neutral",
  "is_outperforming": true,
  "…": "3 more keys"
}
```

#### `/v1/market/momentum-rank` — $0.015

Momentum leaderboard of the covered Hyperliquid perpetuals (USDC-margined): every covered coin ranked by return over 24h, 7d or 30d, with top and bottom performers, notional volume in USDC and the average return. Use to surface rotation candidates and what is bleeding. Ranked movers, not fundamentals. Coverage: top 50 Hyperliquid perpetuals by 30-day volume; see /v1/tools/price/supported (other coins get 422 not_covered, no charge)

Example response (captured):

```json
{
  "period": "24h",
  "quote": "USDC",
  "total_coins_analyzed": 50,
  "avg_return_pct": 1.67,
  "top_performers": [
    {
      "coin": "ZRO",
      "return_pct": 9.12,
      "volume_usd": 10904427.0,
      "current_price": 1.8644,
      "rank": 1
    },
    "…"
  ],
  "bottom_performers": [
    {
      "coin": "XPL",
      "return_pct": -5.83,
      "volume_usd": 27580199.0,
      "current_price": 0.063288,
      "rank": 50
    },
    "…"
  ],
  "all_ranked": [
    {
      "coin": "ZRO",
      "return_pct": 9.12,
      "volume_usd": 10904427.0,
      "current_price": 1.8644,
      "rank": 1
    },
    "…"
  ],
  "source": "Hyperliquid perpetuals",
  "updated_at": "2026-11-03T20:19:22.814006+00:00"
}
```

#### `/v1/market/correlation` — $0.003

Pearson correlation (-1 to +1) of a coin's returns vs BTC on Hyperliquid perpetuals (USDC-margined): 7d on 1h candles or 30d on 4h candles, with a strength label and data point count. Use to judge diversification and whether an alt moves on its own or just tracks BTC. A correlation coefficient, not a beta. Coverage: top 50 Hyperliquid perpetuals by 30-day volume; see /v1/tools/price/supported (other coins get 422 not_covered, no charge)

Example response (captured):

```json
{
  "coin": "ETH",
  "base": "BTC",
  "quote": "USDC",
  "period": "7d",
  "correlation": 0.881,
  "correlation_strength": "very_high",
  "interpretation": "ETH moves almost identically with BTC",
  "data_points": 167,
  "source": "Hyperliquid perpetuals",
  "updated_at": "2026-11-03T20:19:22.884822+00:00"
}
```

### Hyperliquid (Hyperliquid)

#### `/v1/sanity/is-this-a-dip` — $0.003

Is this drop a real dip or just noise? Compares the fall from the 14-day high with the 14-day ATR on daily candles of Hyperliquid perpetuals (USDC-margined) and returns is_dip, drop %, ATR %, drop/ATR and a verdict; prices in USDC. Use before buying the dip to check the dip is real. Coverage: top 50 Hyperliquid perpetuals by 30-day volume; see /v1/tools/price/supported (other coins get 422 not_covered, no charge)

Example response (captured):

```json
{
  "symbol": "BTC",
  "quote": "USDC",
  "pair": "BTC-USDC",
  "is_dip": true,
  "current_price": 77695.0,
  "recent_high": 84850.0,
  "drop_pct": 8.43,
  "atr_pct": 2.49,
  "drop_vs_atr": 3.38,
  "verdict": "Definitely. 8.4% is 3.4x normal volatility. Actual dip.",
  "…": "2 more keys"
}
```

#### `/v1/sanity/is-this-a-breakout` — $0.003

Is a breakout from a given level real or a fakeout? Checks volume vs the 20-candle average and how many 1h closes held beyond the level, on Hyperliquid perpetuals (USDC-margined), and returns is_confirmed, a fakeout probability and a verdict. Use to validate a breakout before chasing it. Requires the level in USDC. Coverage: top 50 Hyperliquid perpetuals by 30-day volume; see /v1/tools/price/supported (other coins get 422 not_covered, no charge)

Example response (captured):

```json
{
  "symbol": "BTC",
  "quote": "USDC",
  "pair": "BTC-USDC",
  "level": 79146.0,
  "direction": "down",
  "current_price": 77712.0,
  "is_beyond_level": true,
  "is_confirmed": false,
  "volume_ratio": 0.62,
  "time_beyond_mins": 360,
  "…": "5 more keys"
}
```

#### `/v1/sanity/is-this-support` — $0.003

Is a price level valid support? Counts touches within 0.5% over 90 daily candles of Hyperliquid perpetuals (USDC-margined), with recency and bounce quality, so an agent can judge whether the level is likely to hold. Use before leaning on a support for entries or stops. Requires the level in USDC. Coverage: top 50 Hyperliquid perpetuals by 30-day volume; see /v1/tools/price/supported (other coins get 422 not_covered, no charge)

Example response (captured):

```json
{
  "symbol": "BTC",
  "quote": "USDC",
  "pair": "BTC-USDC",
  "level": 76000.0,
  "current_price": 77695.0,
  "is_valid_support": true,
  "touch_count": 7,
  "days_since_last_touch": 0.8,
  "bounce_quality": "strong",
  "avg_bounce_pct": 2.16,
  "…": "3 more keys"
}
```

#### `/v1/sanity/is-this-oversold` — $0.003

Multi-timeframe RSI oversold check on Hyperliquid perpetuals (USDC-margined): RSI 14 on 1h, 4h and 1d candles, weighted 20/30/50, returning is_oversold, each RSI and the weighted RSI. Use to confirm an oversold condition across timeframes rather than trusting a single chart. RSI-based, not a buy signal on its own. Coverage: top 50 Hyperliquid perpetuals by 30-day volume; see /v1/tools/price/supported (other coins get 422 not_covered, no charge)

Example response (captured):

```json
{
  "symbol": "BTC",
  "quote": "USDC",
  "pair": "BTC-USDC",
  "current_price": 77712.0,
  "is_oversold": false,
  "rsi_1h": 79.6,
  "rsi_4h": 46.9,
  "rsi_1d": 30.5,
  "weighted_rsi": 45.2,
  "oversold_timeframes": 0,
  "…": "3 more keys"
}
```

#### `/v1/fomo/how-late-am-i` — $0.003

FOMO guard on 4h candles of Hyperliquid perpetuals (USDC-margined): how far price has already run from the recent swing low, in % and ATR multiples, and where that move ranks against past 20-candle moves, with an early/middle/late verdict. Use so an agent does not buy the top. Coverage: top 50 Hyperliquid perpetuals by 30-day volume; see /v1/tools/price/supported (other coins get 422 not_covered, no charge)

Example response (captured):

```json
{
  "symbol": "BTC",
  "quote": "USDC",
  "pair": "BTC-USDC",
  "current_price": 77712.0,
  "swing_low": 76342.0,
  "move_pct": 1.79,
  "move_in_atr": 1.92,
  "candles_since_low": 4,
  "historical_avg_move": 5.92,
  "move_percentile": 0.0,
  "…": "3 more keys"
}
```

#### `/v1/fomo/pump-age` — $0.003

Active pump detector on the last 24 hours of 15m candles of Hyperliquid perpetuals (USDC-margined): is the coin pumping now, since when, how far, and how that compares with the average pump length in the window. Use to judge whether a move is fresh or exhausted before joining it. Coverage: top 50 Hyperliquid perpetuals by 30-day volume; see /v1/tools/price/supported (other coins get 422 not_covered, no charge)

Example response (captured):

```json
{
  "symbol": "BTC",
  "quote": "USDC",
  "pair": "BTC-USDC",
  "current_price": 77660.0,
  "is_pumping": false,
  "pump_start": null,
  "pump_start_price": null,
  "pump_duration_mins": 0,
  "pump_pct": 0,
  "avg_pump_duration_mins": 75.0,
  "…": "5 more keys"
}
```

#### `/v1/fomo/already-extended` — $0.003

Is price over-extended? Distance from MA20 and MA50, Bollinger Band position and a z-score on 4h candles of Hyperliquid perpetuals (USDC-margined), in one read. Use to avoid entering after price has stretched far from its mean. Mean-reversion context. Coverage: top 50 Hyperliquid perpetuals by 30-day volume; see /v1/tools/price/supported (other coins get 422 not_covered, no charge)

Example response (captured):

```json
{
  "symbol": "BTC",
  "quote": "USDC",
  "pair": "BTC-USDC",
  "current_price": 77712.0,
  "is_extended": false,
  "direction": "up",
  "ma20": 77623.75,
  "ma50": 78731.94,
  "distance_from_ma20_pct": 0.11,
  "distance_from_ma50_pct": -1.3,
  "…": "5 more keys"
}
```

#### `/v1/fomo/green-candles-streak` — $0.003

Counts consecutive green candles on 1h, 4h or 1d candles of Hyperliquid perpetuals (USDC-margined) and how often the next candle was green after streaks that long in the last 100 candles. Use to gauge exhaustion risk before buying a long green run. Coverage: top 50 Hyperliquid perpetuals by 30-day volume; see /v1/tools/price/supported (other coins get 422 not_covered, no charge)

Example response (captured):

```json
{
  "symbol": "BTC",
  "quote": "USDC",
  "pair": "BTC-USDC",
  "interval": "4h",
  "streak": 1,
  "streak_gain_pct": 0.16,
  "historical_avg_streak": 1.8,
  "historical_max_streak": 5,
  "next_green_probability": 45.8,
  "verdict": "1 green candles. Below avg (1.8). Streak could continue.",
  "…": "2 more keys"
}
```
