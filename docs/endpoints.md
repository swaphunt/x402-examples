# SwapHunt x402 endpoints

Base URL: `https://x402.swaphunt.dev`. All paid routes are `GET`, return JSON, and answer `402 Payment Required` (x402 v2) until paid. No API key needed.

Payment: USDC, scheme `exact`, network **Base mainnet** (`eip155:8453`, USDC `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`). Free routes: `/health`, `/`, `/docs`, `/openapi.json`. Rate limit: 60 requests/min per IP.

Generated from SwapHunt's pricing config, with real responses captured 2026-10-29. Long responses are trimmed (`…`).

## Overview

| Category | Endpoint | Price (USDC) | Params |
|---|---|---|---|
| Price | `/v1/tools/price` | $0.001 | `asset`=BTC, `currency`=USD |
| Price | `/v1/tools/price/multi` | $0.003 | `assets`=BTC,ETH, `currency`=USD |
| Price | `/v1/tools/price/supported` | $0.001 | – |
| Market | `/v1/market/fear-greed` | $0.001 | – |
| Market | `/v1/market/fear-greed/compare` | $0.002 | – |
| Market | `/v1/market/fear-greed/history` | $0.005 | `days`=30, `start_date`, `end_date` |
| Market | `/v1/market/dominance` | $0.001 | – |
| Market | `/v1/market/global` | $0.002 | – |
| Market | `/v1/market/halving` | $0.001 | `coin`=BTC |
| Market | `/v1/market/alt-season` | $0.003 | `days`=7 |
| Market | `/v1/market/coin-strength` | $0.003 | `coin`=ETH, `period`=24h, `quote`=USDT |
| Market | `/v1/market/momentum-rank` | $0.003 | `period`=24h, `limit`=10, `quote`=USDT |
| Market | `/v1/market/correlation` | $0.003 | `coin`=ETH, `period`=7d, `quote`=USDT |
| Sentiment | `/v1/sentiment/news` | $0.005 | `category`, `min_score`, `limit`=10, `hours`=24 |
| Sentiment | `/v1/sentiment/summary` | $0.003 | `category`=all, `hours`=24 |
| Regime | `/v1/regime/current` | $0.002 | – |
| Regime | `/v1/regime/chop-detection` | $0.003 | `asset`=BTC, `timeframe`=4h, `quote`=USDT |
| Volatility | `/v1/vol/realized` | $0.002 | `asset`=BTC, `period`=30d |
| Volatility | `/v1/vol/silence` | $0.002 | `asset`=BTC, `lookback`=7d |
| Volatility | `/v1/vol/compression-alert` | $0.003 | `asset`=BTC, `timeframe`=4h, `quote`=USDT |
| Volatility | `/v1/vol/expected-move` | $0.003 | `asset`=BTC, `period`=1d, `quote`=USDT |
| Sanity Check | `/v1/sanity/is-this-a-dip` | $0.003 | `symbol`=BTC, `quote`=USDT |
| Sanity Check | `/v1/sanity/is-this-a-breakout` | $0.003 | `symbol`=BTC, `level` (required), `direction`=up, `quote`=USDT |
| Sanity Check | `/v1/sanity/is-this-support` | $0.003 | `symbol`=BTC, `level` (required), `quote`=USDT |
| Sanity Check | `/v1/sanity/is-this-oversold` | $0.003 | `symbol`=BTC, `quote`=USDT |
| Anti-FOMO | `/v1/fomo/how-late-am-i` | $0.003 | `symbol`=BTC, `quote`=USDT |
| Anti-FOMO | `/v1/fomo/pump-age` | $0.003 | `symbol`=BTC, `quote`=USDT |
| Anti-FOMO | `/v1/fomo/already-extended` | $0.003 | `symbol`=BTC, `quote`=USDT |
| Anti-FOMO | `/v1/fomo/green-candles-streak` | $0.003 | `symbol`=BTC, `interval`=4h, `quote`=USDT |
| Context | `/v1/context/weekend-liquidity` | $0.001 | – |
| Context | `/v1/context/session` | $0.001 | – |
| Timing & Cycles | `/v1/cycle/weekly-pattern` | $0.004 | `asset`=BTC, `days`=365 |
| Timing & Cycles | `/v1/cycle/monthly-pattern` | $0.004 | `asset`=BTC, `years`=2 |
| Timing & Cycles | `/v1/cycle/daily-range-used` | $0.002 | `asset`=BTC, `quote`=USDT |
| Timing & Cycles | `/v1/cycle/hourly-pattern` | $0.004 | `asset`=BTC, `days`=30, `quote`=USDT |
| Derivatives | `/v1/derivatives/funding-rates` | $0.003 | `symbols`=BTC,ETH,SOL |
| Derivatives | `/v1/derivatives/funding-rates/top` | $0.003 | `limit`=10, `sort`=highest |
| Derivatives | `/v1/derivatives/funding-rates/history` | $0.004 | `symbol`=BTCUSDT, `days`=90 |
| Derivatives | `/v1/derivatives/liquidations` | $0.003 | `coin`=BTC, `minutes`=5 |
| Derivatives | `/v1/derivatives/liquidations/history` | $0.008 | `coin`=BTC, `hours`=24 |
| Events | `/v1/events/macro` | $0.003 | `days`=7, `country`, `high_impact_only`=False |
| Events | `/v1/events/macro/history` | $0.005 | `days`=30, `start_date`, `end_date`, `country` |

42 paid endpoints. Cheapest: $0.001. Most expensive: $0.008.

## Details and example responses

### Price

#### `/v1/tools/price` — $0.001

SwapHunt — a crypto market-context toolkit for trading agents: live prices, market regime, volatility, sentiment, funding, macro events, seasonality and anti-FOMO sanity checks, all pay-per-call. This route returns a single asset's live spot price with 24h context: price, 24h change %, 24h high/low and volume — one clean JSON snapshot (BTC, ETH, SOL, any major). For many assets at once use /price/multi.

Example response (captured):

```json
{
  "asset": "BTC",
  "price": 80745.859696,
  "currency": "USD",
  "change_24h": 0.019,
  "high_24h": 81896.898216,
  "low_24h": 79637.94216,
  "volume_24h": 1302464863.094671,
  "updated_at": "2026-10-29T18:09:32.852317"
}
```

#### `/v1/tools/price/multi` — $0.003

Batch spot prices for up to 20 assets in one call — each with price, 24h change and volume, keyed by symbol. The cost-efficient way to price a basket or portfolio in a single request instead of N calls.

Example response (captured):

```json
{
  "prices": {
    "BTC": {
      "asset": "BTC",
      "price": 80745.859696,
      "currency": "USD",
      "change_24h": 0.019,
      "high_24h": 81896.898216,
      "low_24h": 79637.94216,
      "volume_24h": 1302464863.094671,
      "updated_at": "2026-10-29T18:09:32.852317"
    },
    "ETH": {
      "asset": "ETH",
      "price": 2337.345128,
      "currency": "USD",
      "change_24h": -0.136,
      "high_24h": 2389.388039,
      "low_24h": 2291.36673,
      "volume_24h": 547408526.161647,
      "updated_at": "2026-10-29T18:09:32.852993"
    }
  },
  "currency": "USD",
  "updated_at": "2026-10-29T18:09:32.914371"
}
```

#### `/v1/tools/price/supported` — $0.001

The full list of coins /price and /price/multi can quote — every base asset with a live {SYMBOL}USDT spot pair on Binance (hundreds, refreshed hourly). Call this once to discover valid `asset` symbols before pricing; returns a JSON array of symbols (e.g. ["BTC", "ETH", "SOL", ...]).

Example response (captured):

```json
[
  "0G",
  "…"
]
```

### Market

#### `/v1/market/fear-greed` — $0.001

Current Crypto Fear & Greed Index (0-100) with its label (Extreme Fear → Extreme Greed), updated daily. A single market-mood gauge for risk-on/risk-off context. For trend over time use /fear-greed/compare or /fear-greed/history.

Example response (captured):

```json
{
  "value": 51,
  "label": "Neutral",
  "timestamp": "2026-10-29T00:00:00",
  "source": "alternative.me",
  "attribution": "Data provided by Alternative.me Crypto Fear & Greed Index"
}
```

#### `/v1/market/fear-greed/compare` — $0.002

Fear & Greed now vs yesterday, 7 days and 30 days ago — with the deltas — so an agent can see whether market sentiment is improving or deteriorating, not just today's number. Use for momentum-of-mood.

Example response (captured):

```json
{
  "value": 51,
  "label": "Neutral",
  "timestamp": "2026-10-29T00:00:00",
  "source": "alternative.me",
  "attribution": "Data provided by Alternative.me Crypto Fear & Greed Index",
  "yesterday": 51,
  "week_ago": 68,
  "month_ago": 73,
  "change_1d": 0,
  "change_7d": -17,
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
      "date": "2026-10-29",
      "value": 51,
      "classification": "Neutral"
    },
    "…"
  ],
  "start_date": "2026-09-30",
  "end_date": "2026-10-29",
  "count": 30,
  "source": "alternative.me",
  "attribution": "Data provided by Alternative.me Crypto Fear & Greed Index",
  "data_available_from": "2018-02-01"
}
```

#### `/v1/market/dominance` — $0.001

BTC and ETH market-cap dominance (% of total crypto market cap), plus total market cap and active-coin count, refreshed every ~5 min. Use to gauge whether capital sits in majors vs alts. For the alt-rotation read specifically, use /alt-season.

Example response (captured):

```json
{
  "btc_dominance": 60.079302,
  "eth_dominance": 10.566395,
  "total_market_cap_usd": 2703662866561.508,
  "active_cryptocurrencies": 8084,
  "updated_at": "2026-10-29T18:00:59.999000"
}
```

#### `/v1/market/global` — $0.002

Whole-market snapshot: total crypto market cap, total 24h volume, BTC dominance, and counts of active coins and markets. One call for the macro state of crypto — the top-of-funnel context before drilling into an asset.

Example response (captured):

```json
{
  "total_market_cap_usd": 2703662866561.508,
  "total_24h_volume_usd": 81007775305.65,
  "btc_dominance": 60.079302,
  "eth_dominance": 10.566395,
  "active_cryptocurrencies": 8084,
  "active_markets": 109463,
  "updated_at": "2026-10-29T18:00:59.999000"
}
```

#### `/v1/market/halving` — $0.001

BTC or LTC halving countdown: blocks remaining and the estimated date of the next halving. Use for cycle-timing narratives and supply-shock context. Estimate (block-time based), not an exact timestamp.

Example response (captured):

```json
{
  "coin": "BTC",
  "coin_name": "Bitcoin",
  "current_block": 973726,
  "next_halving_block": 1050000,
  "blocks_remaining": 76274,
  "estimated_date": "2028-04-11T10:28:21.592652",
  "days_remaining": 529,
  "progress_pct": 63.68,
  "current_block_reward": 3.125,
  "next_block_reward": 1.5625,
  "…": "2 more keys"
}
```

#### `/v1/market/alt-season` — $0.003

Alt-season read: CoinMarketCap's Altcoin Season Index (0-100, top-100 alts vs BTC over 90 days) plus SwapHunt's short-term check of how many of the top-10 alts beat BTC over the lookback window, their average return vs BTC, leaders and laggards, and an is_alt_season verdict. Use to time BTC↔alt rotation. Complements /dominance (capital location) with relative-performance signal.

Example response (captured):

```json
{
  "altcoin_season_index": {
    "value": 59.0,
    "label": "Neutral",
    "date": "2026-10-29",
    "source": "coinmarketcap",
    "note": "CoinMarketCap index: share of top-100 alts beating BTC over 90 days, 0-100"
  },
  "is_alt_season": false,
  "season_strength": "none",
  "period_days": 7,
  "btc_performance_pct": -3.9,
  "btc_dominance_pct": 60.07,
  "dominance_signal": "high",
  "dominance_note": "High BTC dominance - favors BTC over alts",
  "alts_outperforming": 1,
  "alts_total": 10,
  "…": "7 more keys"
}
```

#### `/v1/market/coin-strength` — $0.003

Relative strength of a coin vs BTC over a period, returned as a category (very_strong → very_weak) plus a numeric score. Use to rank a coin's momentum against the benchmark before entering. A strength read, not a price target.

Example response (captured):

```json
{
  "coin": "ETH",
  "quote": "USDT",
  "pair": "ETHUSDT",
  "period": "24h",
  "coin_return_pct": -0.22,
  "btc_return_pct": -0.06,
  "vs_btc_pct": -0.15,
  "strength_ratio": 0.998,
  "strength": "neutral",
  "is_outperforming": false,
  "…": "2 more keys"
}
```

#### `/v1/market/momentum-rank` — $0.003

Top and bottom momentum coins ranked by return over the chosen period — a leaderboard of what's running and what's bleeding. Use to surface rotation candidates. Returns ranked movers, not full fundamentals.

Example response (captured):

```json
{
  "period": "24h",
  "quote": "USDT",
  "total_coins_analyzed": 20,
  "avg_return_pct": 0.3,
  "top_performers": [
    {
      "coin": "INJ",
      "return_pct": 3.34,
      "volume_usd": 16313703.0,
      "current_price": 8.02,
      "rank": 1
    },
    "…"
  ],
  "bottom_performers": [
    {
      "coin": "NEAR",
      "return_pct": -2.26,
      "volume_usd": 160043691.0,
      "current_price": 4.493,
      "rank": 20
    },
    "…"
  ],
  "all_ranked": [
    {
      "coin": "INJ",
      "return_pct": 3.34,
      "volume_usd": 16313703.0,
      "current_price": 8.02,
      "rank": 1
    },
    "…"
  ],
  "updated_at": "2026-10-29T18:08:22.675996+00:00"
}
```

#### `/v1/market/correlation` — $0.003

Pearson correlation of a coin's returns vs BTC (-1 to +1) over the period. Use to judge diversification and whether an alt is moving independently or just tracking BTC. A correlation coefficient, not a beta or causation claim.

Example response (captured):

```json
{
  "coin": "ETH",
  "base": "BTC",
  "quote": "USDT",
  "period": "7d",
  "correlation": 0.929,
  "correlation_strength": "very_high",
  "interpretation": "ETH moves almost identically with BTC",
  "data_points": 167,
  "updated_at": "2026-10-29T18:08:23.311088+00:00"
}
```

### Sentiment

#### `/v1/sentiment/news` — $0.005

Recent crypto news headlines each scored 1-10 for trading impact by an LLM (qwen3:8b), with a bullish/bearish/neutral tag. Filter by category, minimum score and lookback hours. Use to surface market-moving stories; for the aggregate read use /sentiment/summary.

Example response (captured):

```json
{
  "articles": [
    {
      "id": 6078877,
      "headline": "Klarna gains amid some takeover speculation",
      "summary": "",
      "full_content": null,
      "condensed_content": null,
      "source": "SeekingAlpha",
      "source_type": "finnhub",
      "url": "https://seekingalpha.com/news/4660568-klarna-gains-amid-some-takeover-specula...",
      "category": "merger",
      "published_at": "2026-10-29T17:27:40",
      "…": "3 more keys"
    },
    "…"
  ],
  "count": 50,
  "filters": {
    "category": null,
    "min_score": null,
    "limit": 50,
    "hours": 24
  },
  "source": "finnhub",
  "scored_by": "qwen3:8b"
}
```

#### `/v1/sentiment/summary` — $0.003

Aggregated market sentiment label (strong_bearish → strong_bullish) with a normalized score, computed from LLM-scored news over the window. One-number mood read for an agent that just needs the verdict, not the individual articles.

Example response (captured):

```json
{
  "score": 6.5,
  "label": "slightly_bullish",
  "articles_analyzed": 125,
  "category": "crypto",
  "breakdown": {
    "crypto": {
      "score": 6.5,
      "count": 125
    }
  },
  "top_high_impact": [
    {
      "headline": "HYPE token skyrockets as NYSE owner moves to bring Hyperliquid perpetual futu...",
      "score": 9,
      "source": "Forexlive"
    },
    "…"
  ],
  "top_low_impact": [
    {
      "headline": "ECB President Christine Lagarde to step down in February 2027",
      "score": 3,
      "source": "Cointelegraph"
    }
  ],
  "period_hours": 24,
  "updated_at": "2026-10-29T18:08:10.009659",
  "source": "finnhub",
  "…": "1 more keys"
}
```

### Regime

#### `/v1/regime/current` — $0.002

Current BTC market regime — BULLISH / BEARISH / NEUTRAL — derived from price vs its 20-period EMA on the 12h candle, with the EMA value and slope. The top-level risk filter: trade-with-trend context before any entry. BTC-based; pair with per-asset tools for alts.

Example response (captured):

```json
{
  "regime": "NEUTRAL",
  "price": 80739.44,
  "ema20": 81098.56,
  "price_vs_ema_pct": -1.24,
  "ema_slope_pct": -0.349,
  "interval": "12h",
  "candle_close": "2026-10-29T11:59:59.999000Z",
  "next_update": "2026-10-29T23:59:59.999000Z",
  "updated_at": "2026-10-29T18:09:32.607208Z"
}
```

#### `/v1/regime/chop-detection` — $0.003

ADX-based chop-vs-trend detector for an asset/timeframe: is price trending or stuck in a range? Returns is_chop, a chop level, ADX and +DI/-DI. Use to avoid trend strategies in chop (and range strategies in trends).

Example response (captured):

```json
{
  "asset": "BTC",
  "quote": "USDT",
  "pair": "BTCUSDT",
  "timeframe": "4h",
  "is_chop": false,
  "chop_level": "low",
  "adx": 30.57,
  "adx_interpretation": {
    "below_20": "Choppy/ranging",
    "20_25": "Trend emerging",
    "25_50": "Strong trend",
    "above_50": "Very strong trend"
  },
  "plus_di": 23.59,
  "minus_di": 17.49,
  "…": "3 more keys"
}
```

### Volatility

#### `/v1/vol/realized` — $0.002

Realized volatility for an asset: daily and annualized %, plus a low/normal/high/extreme bucket and the 24h high/low/range. Use to size positions and set expectations. Backward-looking (realized), not implied/option vol.

Example response (captured):

```json
{
  "asset": "BTC",
  "realized_volatility_pct": 0.66,
  "annualized_volatility_pct": 12.5,
  "level": "low",
  "high_24h_pct": 0.77,
  "low_24h_pct": -2.01,
  "range_24h_pct": 2.78,
  "period": "7d",
  "updated_at": "2026-10-29T18:08:10.242394"
}
```

#### `/v1/vol/silence` — $0.002

Market-silence score 0-1 — a composite of low volume, low volatility and small price change. High silence often precedes expansion. Use to spot the calm-before-the-move. Pairs with /vol/compression-alert.

Example response (captured):

```json
{
  "asset": "BTC",
  "silence_score": 0.47,
  "level": "medium",
  "recommendation": "be_cautious",
  "factors": {
    "volume_ratio": 0.91,
    "volume_today_usd": 965159314.0,
    "volume_avg_usd": 1059859842.0,
    "volatility_pct": 0.61,
    "price_change_24h_pct": -0.64
  },
  "lookback": "7d",
  "updated_at": "2026-10-29T18:08:23.982941"
}
```

#### `/v1/vol/compression-alert` — $0.003

Bollinger-Band squeeze detector: is volatility compressing toward a likely expansion? Returns extreme/strong/moderate/none plus bandwidth. Use to anticipate breakouts before they fire. Detects the setup, not the direction.

Example response (captured):

```json
{
  "asset": "BTC",
  "quote": "USDT",
  "pair": "BTCUSDT",
  "timeframe": "4h",
  "is_squeeze": false,
  "squeeze_level": "none",
  "bollinger_width_pct": 3.17,
  "avg_width_pct": 3.31,
  "width_percentile": 60.0,
  "width_ratio": 0.96,
  "…": "4 more keys"
}
```

#### `/v1/vol/expected-move` — $0.003

ATR-based expected price range for the period: the 68% and 95% probability bands around current price. Use to set realistic targets, stops and breakout thresholds. A statistical range, not a directional forecast.

Example response (captured):

```json
{
  "asset": "BTC",
  "quote": "USDT",
  "pair": "BTCUSDT",
  "period": "daily",
  "current_price": 80810.69,
  "atr_14": 1837.64,
  "expected_move_usd": 1837.64,
  "expected_move_pct": 2.27,
  "expected_range": {
    "high": 82648.33,
    "low": 78973.05
  },
  "probability_ranges": {
    "68_pct": {
      "high": 82648.33,
      "low": 78973.05,
      "description": "68% of moves stay within this range"
    },
    "95_pct": {
      "high": 84485.98,
      "low": 77135.4,
      "description": "95% of moves stay within this range"
    }
  },
  "…": "3 more keys"
}
```

### Sanity Check

#### `/v1/sanity/is-this-a-dip` — $0.003

Is this drop a statistically significant dip or just noise? Compares the move against the asset's ATR and returns a verdict + the drawdown size. Use before 'buy the dip' to check the dip is real.

Example response (captured):

```json
{
  "symbol": "BTC",
  "quote": "USDT",
  "pair": "BTCUSDT",
  "is_dip": true,
  "current_price": 80818.92,
  "recent_high": 84898.0,
  "drop_pct": 4.8,
  "atr_pct": 2.27,
  "drop_vs_atr": 2.11,
  "verdict": "Definitely. 4.8% is 2.1x normal volatility. Actual dip.",
  "…": "1 more keys"
}
```

#### `/v1/sanity/is-this-a-breakout` — $0.003

Is a breakout from a given level real or a fakeout? Checks volume confirmation, time held above/below, and fakeout probability. Use to validate a breakout before chasing it. Requires the level to test.

Example response (captured):

```json
{
  "symbol": "BTC",
  "quote": "USDT",
  "pair": "BTCUSDT",
  "level": 79146.0,
  "direction": "down",
  "current_price": 77525.83,
  "is_beyond_level": true,
  "is_confirmed": false,
  "volume_ratio": 0.23,
  "time_beyond_mins": 360,
  "…": "4 more keys"
}
```

#### `/v1/sanity/is-this-support` — $0.003

Is a price level valid support? Returns touch count, recency and bounce quality so an agent can judge whether the level is likely to hold. Use before leaning on a support for entries or stops. Requires the level.

Example response (captured):

```json
{
  "symbol": "BTC",
  "quote": "USDT",
  "pair": "BTCUSDT",
  "level": 76000.0,
  "current_price": 77525.83,
  "is_valid_support": true,
  "touch_count": 5,
  "days_since_last_touch": 1.4,
  "bounce_quality": "strong",
  "avg_bounce_pct": 2.18,
  "…": "2 more keys"
}
```

#### `/v1/sanity/is-this-oversold` — $0.003

Multi-timeframe RSI oversold check (1h/4h/1d, weighted) returning a boolean + the blended RSI. Use to confirm an oversold condition across timeframes rather than trusting a single chart. RSI-based, not a buy signal on its own.

Example response (captured):

```json
{
  "symbol": "BTC",
  "quote": "USDT",
  "pair": "BTCUSDT",
  "current_price": 80818.93,
  "is_oversold": false,
  "rsi_1h": 57.6,
  "rsi_4h": 55.7,
  "rsi_1d": 42.4,
  "weighted_rsi": 49.4,
  "oversold_timeframes": 0,
  "…": "2 more keys"
}
```

### Anti-FOMO

#### `/v1/fomo/how-late-am-i` — $0.003

FOMO guard: how far has price already run from the recent swing low — in % and ATR multiples — versus the historical average move? Returns an early/mid/late read so an agent doesn't buy the top. Anti-chase context.

Example response (captured):

```json
{
  "symbol": "BTC",
  "quote": "USDT",
  "pair": "BTCUSDT",
  "current_price": 80818.93,
  "swing_low": 79451.35,
  "move_pct": 1.72,
  "move_in_atr": 1.5,
  "candles_since_low": 19,
  "historical_avg_move": 3.64,
  "move_percentile": 0.0,
  "…": "2 more keys"
}
```

#### `/v1/fomo/pump-age` — $0.003

Active-pump detector: is the asset currently pumping, and for how long vs the historical average pump length? Use to judge whether a move is fresh or exhausted before joining it.

Example response (captured):

```json
{
  "symbol": "BTC",
  "quote": "USDT",
  "pair": "BTCUSDT",
  "current_price": 80818.93,
  "is_pumping": false,
  "pump_start": null,
  "pump_start_price": null,
  "pump_duration_mins": 0,
  "pump_pct": 0,
  "avg_pump_duration_mins": 68.0,
  "…": "4 more keys"
}
```

#### `/v1/fomo/already-extended` — $0.003

Is price over-extended? Distance from MA20/MA50, Bollinger-band position and a z-score in one read. Use to avoid entering after price has stretched far from its mean. Mean-reversion context.

Example response (captured):

```json
{
  "symbol": "BTC",
  "quote": "USDT",
  "pair": "BTCUSDT",
  "current_price": 80818.92,
  "is_extended": false,
  "direction": "up",
  "ma20": 80598.1,
  "ma50": 81059.52,
  "distance_from_ma20_pct": 0.27,
  "distance_from_ma50_pct": -0.3,
  "…": "4 more keys"
}
```

#### `/v1/fomo/green-candles-streak` — $0.003

Counts consecutive green candles on the chosen interval and returns the historical outcome stats after streaks of that length (mean-reversion odds). Use to gauge exhaustion risk before buying a long green run.

Example response (captured):

```json
{
  "symbol": "BTC",
  "quote": "USDT",
  "pair": "BTCUSDT",
  "interval": "4h",
  "streak": 0,
  "streak_gain_pct": 0,
  "historical_avg_streak": 1.5,
  "historical_max_streak": 5,
  "next_green_probability": 46.2,
  "verdict": "No streak. Last candle was red.",
  "…": "1 more keys"
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
  "day_of_week": "Thursday",
  "weekday_number": 3,
  "current_hour_utc": 18,
  "session": "new_york",
  "is_overlap": false,
  "liquidity_score": 100,
  "verdict": "New York session. High liquidity. Good conditions.",
  "updated_at": "2026-10-29T18:09:37.182069+00:00"
}
```

#### `/v1/context/session` — $0.001

Current trading session (Asia / London / NY / Off) plus historical volatility for that session. Use to time entries around the most active hours and set session-aware expectations.

Example response (captured):

```json
{
  "current_session": "new_york",
  "session_name": "New York",
  "markets_active": "New York, Chicago",
  "is_overlap": false,
  "session_start_utc": "2026-10-29T13:00:00+00:00",
  "session_end_utc": "2026-10-29T21:00:00+00:00",
  "minutes_remaining": 170,
  "next_session": "off_hours",
  "expected_volatility": "high",
  "volatility_multiplier": 1.2,
  "…": "2 more keys"
}
```

### Timing & Cycles

#### `/v1/cycle/weekly-pattern` — $0.004

Historical performance by day of week (avg return + win rate per weekday) over the lookback. Use to time entries/exits around statistically stronger or weaker days. Seasonality, not a forecast.

Example response (captured):

```json
{
  "asset": "BTC",
  "period_days": 365,
  "pattern": [
    {
      "day": "Monday",
      "weekday": 0,
      "avg_return_pct": 0.343,
      "std_dev": 2.34,
      "win_rate_pct": 51.9,
      "sample_size": 52
    },
    "…"
  ],
  "best_day": "Monday",
  "worst_day": "Thursday",
  "note": "Based on daily close-to-close returns",
  "data_source": "binance",
  "cache_ttl_hours": 24,
  "updated_at": "2026-10-29T18:08:27.764312+00:00"
}
```

#### `/v1/cycle/monthly-pattern` — $0.004

Historical performance by calendar month (e.g. 'Uptober') — avg return and win rate per month. Use for seasonal positioning. Pattern from history, not a prediction.

Example response (captured):

```json
{
  "asset": "BTC",
  "period_years": 2,
  "actual_days_analyzed": 730,
  "pattern": [
    {
      "month": "January",
      "month_num": 1,
      "avg_daily_return_pct": -0.002,
      "total_return_pct": -0.13,
      "std_dev": 2.24,
      "win_rate_pct": 51.6,
      "sample_days": 62
    },
    "…"
  ],
  "best_month": "April",
  "worst_month": "February",
  "note": "Based on daily returns aggregated by month",
  "data_source": "binance",
  "cache_ttl_hours": 24,
  "updated_at": "2026-10-29T18:08:28.107892+00:00"
}
```

#### `/v1/cycle/daily-range-used` — $0.002

How much of today's expected (ATR) range has already been used — low/moderate/high/extended — with the % consumed. Use to judge remaining room before chasing intraday. Tells you how 'full' the day is.

Example response (captured):

```json
{
  "asset": "BTC",
  "quote": "USDT",
  "pair": "BTCUSDT",
  "today_range_usd": 2261.0,
  "atr_14_usd": 1837.64,
  "range_used_pct": 123.0,
  "range_status": "extended",
  "today_high": 81971.0,
  "today_low": 79710.0,
  "today_open": 81343.51,
  "…": "6 more keys"
}
```

#### `/v1/cycle/hourly-pattern` — $0.004

Historical volatility by hour of day (UTC) plus a session comparison — which hours move most. Use to time entries to active hours and avoid dead zones. Intraday seasonality.

Example response (captured):

```json
{
  "asset": "BTC",
  "quote": "USDT",
  "pair": "BTCUSDT",
  "period_days": 30,
  "pattern": [
    {
      "hour_utc": 0,
      "hour_label": "00:00 UTC",
      "avg_range_pct": 0.39,
      "avg_volume": 539.0,
      "avg_return_pct": -0.0266,
      "volatility": 0.214,
      "sample_size": 30
    },
    "…"
  ],
  "most_volatile_hours_utc": [
    14,
    "…"
  ],
  "least_volatile_hours_utc": [
    21,
    "…"
  ],
  "avg_hourly_range_pct": 0.46,
  "sessions": {
    "asia": {
      "avg_range_pct": 0.432,
      "hours_utc": "00:00-08:00"
    },
    "london": {
      "avg_range_pct": 0.549,
      "hours_utc": "08:00-16:00"
    },
    "new_york": {
      "avg_range_pct": 0.548,
      "hours_utc": "13:00-21:00"
    }
  },
  "note": "Hours are in UTC. Range = (high-low)/open as percentage.",
  "…": "1 more keys"
}
```

### Derivatives

#### `/v1/derivatives/funding-rates` — $0.003

Live perpetual funding rates for up to 20 symbols (WebSocket-sourced, ~2 min refresh). Positive = longs pay shorts (crowded longs). Use to read positioning and crowding before entering. Funding, not open interest.

Example response (captured):

```json
{
  "rates": [
    {
      "symbol": "BTCUSDT",
      "funding_rate": 0.0001,
      "funding_rate_pct": 0.01,
      "annualized_rate_pct": 10.95,
      "mark_price": 80798.2,
      "next_funding_time": "2026-10-30T00:00:00",
      "signal": "neutral",
      "avg_7d": 0.00691,
      "avg_30d": 0.004123,
      "updated_at": "2026-10-29T18:08:44.191111",
      "…": "1 more keys"
    },
    "…"
  ],
  "count": 3,
  "updated_at": "2026-10-29T18:09:37.497851",
  "source": "binance"
}
```

#### `/v1/derivatives/funding-rates/top` — $0.003

Top N funding rates ranked highest or lowest across all tracked perps — a leaderboard of the most crowded longs (highest) or shorts (lowest). Use to spot squeeze and crowding extremes fast.

Example response (captured):

```json
{
  "entries": [
    {
      "symbol": "GPROUSDT",
      "funding_rate": 0.001429,
      "funding_rate_pct": 0.142936,
      "annualized_rate_pct": 156.51,
      "mark_price": 1.015049,
      "signal": "extreme_positive",
      "rank": 1
    },
    "…"
  ],
  "count": 10,
  "total_symbols": 945,
  "sort": "highest",
  "updated_at": "2026-10-29T18:09:37.829849",
  "source": "binance"
}
```

#### `/v1/derivatives/funding-rates/history` — $0.004

Settled funding rates for one Binance USDT perpetual, up to 365 days, with average, range, share of positive periods and the percentile of the latest rate. Annualized at the symbol's own interval (1h, 4h or 8h). Use to judge whether today's funding is unusual for that coin.

Example response (captured):

```json
{
  "symbol": "BTCUSDT",
  "days": 90,
  "interval_hours": 8.0,
  "count": 270,
  "current_pct": 0.01,
  "avg_pct": 0.00529,
  "min_pct": -0.004135,
  "max_pct": 0.01,
  "avg_annualized_pct": 5.79,
  "positive_share_pct": 92.6,
  "…": "3 more keys"
}
```

#### `/v1/derivatives/liquidations` — $0.003

Long and short liquidations for BTC, ETH, SOL, XRP or BNB in the last 1-60 minutes from Binance and Bybit USDT perps: counts, USD volume, bias, largest order, cascade flag and the individual events. Use to see forced selling or a short squeeze as it happens. Totals are a floor.

Example response (captured):

```json
{
  "coin": "BTC",
  "window_minutes": 5,
  "long_count": 2,
  "short_count": 1,
  "long_volume_usd": 4686.16,
  "short_volume_usd": 161.66,
  "total_volume_usd": 4847.81,
  "bias": 0.9333,
  "largest_usd": 4605.37,
  "cascade_detected": false,
  "…": "6 more keys"
}
```

#### `/v1/derivatives/liquidations/history` — $0.008

Liquidation history in 1h, 4h or 1d buckets for up to 30 days, with window totals and the largest single order, from SwapHunt's own stored record of Binance and Bybit liquidations (not available from the exchanges' free APIs). Use to chart liquidation waves or backtest them.

Example response (captured):

```json
{
  "coin": "BTC",
  "hours": 24,
  "bucket": "1h",
  "long_usd": 2765446.02,
  "short_usd": 5026759.69,
  "long_count": 150,
  "short_count": 256,
  "largest_usd": 383706.22,
  "data_since": "2026-10-29T15:00:04.018863",
  "buckets": [
    {
      "start": "2026-10-28T19:00:00",
      "long_usd": 0.0,
      "short_usd": 0.0,
      "long_count": 0,
      "short_count": 0
    },
    "…"
  ],
  "…": "1 more keys"
}
```

### Events

#### `/v1/events/macro` — $0.003

Upcoming macro events (FOMC, CPI, NFP, etc.) with date, country and impact level, filterable to high-impact only. Use to avoid trading into scheduled volatility or to plan around it. Forward calendar; for past actuals use /macro/history.

Example response (captured):

```json
{
  "events": [],
  "count": 0,
  "days_ahead": 7,
  "source": "finnhub"
}
```

#### `/v1/events/macro/history` — $0.005

Historical macro events with actual vs estimate values (e.g. CPI came in above/below forecast). Use to study how markets reacted to surprises and to backtest event-driven strategies.

Example response (captured):

```json
{
  "events": [
    {
      "event": "GDP Growth Rate (QoQ)",
      "country": "US",
      "event_time": "2026-10-29T12:30:00",
      "impact": "high",
      "unit": "%"
    },
    "…"
  ],
  "count": 4,
  "start_date": "2026-09-29T00:00:00",
  "end_date": "2026-10-29T23:59:59.999999",
  "source": "finnhub"
}
```
