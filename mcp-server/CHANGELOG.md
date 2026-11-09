# Changelog

## 0.5.0 (unreleased)

- Added: `PAYTO_ALLOWLIST`, optional comma-separated addresses the server may pay. A 402 asking for any other `payTo` is refused before anything is signed, in dry run too. Invalid entries stop the server at startup.
- Added: requests identify themselves with `User-Agent: swaphunt-mcp/<version>`.
- Added: dry-run results include `pay_to`.
- Added: tests against a local fake API (`tests/`): a contract per tool (path, price, required parameters, price in the description), dry run, price ceiling per tool, session cap, payment lock, allowlist, uncovered coins and key handling.
- Changed: `PRIVATE_KEY_FILE` must not be readable by other users (chmod 600), and setting both `PRIVATE_KEY` and `PRIVATE_KEY_FILE` is refused. The key is read when a payment is made, not copied into the environment at import.
- Changed: `--help` lists the settings; `--check` passes the required `level` to the breakout and support endpoints.
- Changed: an unreachable API or a malformed 402 now returns `Not paid: ...` instead of a tool error.

## 0.4.1 (2026-11-05)

- Changed: depends on `x402[httpx,evm]` 2.26.0 (was 2.25.0); built with hatchling 1.33.0. No tool or behaviour changes.
- Release: published to PyPI and the MCP registry from GitHub Actions (OIDC), no tokens.

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
