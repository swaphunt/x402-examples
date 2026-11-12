# Changelog

## 0.7.0 (2026-11-12)

- Added: `pm_fees`, a free tool that runs locally. It gives the exact trading fee for one order on Kalshi, Polymarket US or polymarket.com: `fee_usd`, `fee_pct_of_trade_value`, the break-even exit price for a round trip, and the rates' `as_of` (plus Kalshi's fee schedule version). It is computed by [pmfees](https://github.com/swaphunt/pmfees) 0.1.1 (new dependency, pinned) from each platform's official fee schedule. No API call and no payment, and it does not count against `MAX_SPEND_USD`. Annotations: `readOnlyHint`, not destructive, closed world.
- Orders a platform would not accept return `{"error": "invalid_input"}` with pmfees' reason. Examples: fractional Kalshi contracts, Polymarket US sizes that are not a multiple of 0.01, polymarket.com without a category, a price outside 0-1, an unknown tier or multiplier.
- Tests: pmfees' README examples (Kalshi 0.33 × 7 = $0.1084, centicent rounding, multipliers and maker, Polymarket US tier 4, polymarket.com Crypto, break-even), the error messages, the annotations, and that the tool sends no request to the API.

## 0.6.0 (2026-11-11)

- Changed: the price a tool may pay is read from the API's own price list, `/.well-known/x402` on the same host, fetched on the first paid call and again after an hour. A price change on the API no longer needs a new release. A 402 that asks for more than the list says is still refused before anything is signed, in dry runs too. If the list cannot be fetched, the price built into the release is the limit (a list fetched earlier stays in use until a fetch succeeds).
- Added: a single call that costs more than `MAX_SPEND_USD` is refused before signing, in dry runs too.
- Changed: built-in prices follow SwapHunt's price test from 2026-11: `get_fear_greed`, `get_price`, `get_trading_session` and `get_weekend_liquidity` $0.005; `get_market_regime` and `get_volatility` $0.010; `get_funding_rates`, `get_coin_strength` and `get_momentum_rank` $0.015. Version 0.5.0 refuses these nine tools once the API charges the new prices; upgrade with `uvx swaphunt-mcp@latest`.
- Tests: the fake API serves `/.well-known/x402`; new tests for a price change in the list, a 402 above the list, an unavailable list (fallback), one fetch per session and the `MAX_SPEND_USD` limit.

## 0.5.0 (2026-11-09)

- Added: `PAYTO_ALLOWLIST`, a comma-separated list of addresses the server may pay. A quote to any other `payTo` is refused before anything is signed, in dry runs too. A malformed entry stops the server at start. Without it, any `payTo` can be paid (still capped by `MAX_SPEND_USD`), and the server says so on stderr when payments are on.
- Added: dry-run results include `pay_to`, the address the call would pay, so you can fill in `PAYTO_ALLOWLIST` from a dry run.
- Added: every request sends `User-Agent: swaphunt-mcp/<version>`.
- Changed: the price check (a tool refuses to pay more than the price in its description) and the session cap compare with a small tolerance, and a failed quote (network error, no 402) returns `Not paid: ...` instead of raising.
- Added: tests against a local fake API (`tests/`): a contract test of every tool against a snapshot of the live 402 responses (route, price, parameters, defaults), dry run, session cap, price check, payment lock, `PAYTO_ALLOWLIST`, `not_covered` and `--check`. `scripts/snapshot_402.py` refreshes the snapshot and pays nothing.
- `SWAPHUNT_API_URL` points the server at another base URL. It exists for the tests; leave it unset.

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
