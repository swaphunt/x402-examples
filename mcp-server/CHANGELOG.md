# Changelog

## 0.4.0 (2026-11-03)

First release on PyPI and the MCP registry since 0.1.0. Versions 0.2.0 and 0.3.0 were never published; their changes are merged into this release.

The SwapHunt x402 API sells 30 endpoints, and the server has 30 paid tools plus `get_spending`. Everything coin-specific is computed from Hyperliquid perpetuals (USDC-margined); the rest is Fear & Greed, the halving countdown and trading-session context.

- Added (coin analysis and sanity checks, $0.003 each): `get_coin_strength`, `get_momentum_rank`, `get_correlation`, `is_this_a_dip`, `is_this_a_breakout`, `is_this_support`, `is_this_oversold`, `how_late_am_i`, `get_pump_age`, `is_price_extended`, `get_green_candle_streak`. They cover the top 50 Hyperliquid perpetuals by 30-day volume. For any other coin the API answers `422 not_covered` before asking for payment; the tool returns a clear message with the covered list, nothing is paid and nothing counts against the session cap.
- Added: `get_supported_assets` ($0.001), `get_market_silence` ($0.002), `get_compression_alert` ($0.003), `get_expected_move` ($0.003), `get_top_funding_rates` ($0.003), `get_funding_history` ($0.004), `get_fear_greed_compare` ($0.002), `get_fear_greed_history` ($0.005), `get_halving` ($0.001), `get_weekend_liquidity` ($0.001).
- Removed: `get_market_overview`, `get_liquidations`, `get_crypto_news`, `get_sentiment_summary`, `get_macro_events`. Their endpoints are no longer on the x402 API.
- Changed: tools follow the API's current parameters and defaults. Prices are quoted in USDC (`currency`/`quote` default `USDC`; `USD` and `USDT` are accepted as aliases), `get_price` and `get_prices` take `price_type` `mark` (default) or `mid`, `get_volatility` defaults to `period="7d"`, and `get_alt_season` takes no parameters.
- Funding is hourly: annualized rate = hourly rate x 8760. `get_funding_history` covers up to 365 days and reports `history_days` per coin.

## 0.3.0 and 0.2.0 (unreleased)

Never published. Merged into 0.4.0.

## 0.1.0 (2026-10-31)

First packaged release as `swaphunt-mcp` (not published to PyPI).
