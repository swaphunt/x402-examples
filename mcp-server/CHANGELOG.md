# Changelog

## 0.3.0 (2026-11-02)

The SwapHunt x402 API now sells 19 endpoints: 13 computed from Hyperliquid perpetuals (USDC-margined), Fear & Greed, the halving countdown and trading-session context. The server has 19 paid tools plus `get_spending`.

- Added: `get_supported_assets` ($0.001), `get_market_silence` ($0.002), `get_compression_alert` ($0.003), `get_expected_move` ($0.003), `get_top_funding_rates` ($0.003), `get_funding_history` ($0.004), `get_fear_greed_compare` ($0.002), `get_fear_greed_history` ($0.005), `get_halving` ($0.001), `get_weekend_liquidity` ($0.001).
- Removed: `get_market_overview`, `get_momentum_rank`, `get_liquidations`, `get_crypto_news`, `get_sentiment_summary`, `get_macro_events`, `is_this_a_dip`, `is_this_a_breakout`, `is_this_oversold`, `how_late_am_i`, `is_price_extended`. Their endpoints are no longer on the x402 API.
- Changed: tools follow the API's current parameters and defaults. Prices are quoted in USDC (`currency`/`quote` default `USDC`; `USD` and `USDT` are accepted as aliases), `get_price` and `get_prices` take `price_type` `mark` (default) or `mid`, and `get_volatility` defaults to `period="7d"`.
- Funding is hourly: annualized rate = hourly rate x 8760. `get_funding_history` covers up to 365 days and reports `history_days` per coin.

## 0.1.0 (2026-10-31)

First packaged release as `swaphunt-mcp` (not published to PyPI).
