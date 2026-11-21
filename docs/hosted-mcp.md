# Hosted SwapHunt MCP server: spec

Status: built 2026-11-21 on the owner's go (swaphunt-tools, `src/api/mcp/`) and deployed with `SWAPHUNT_MCP_ENABLED=false`, so `api.swaphunt.dev/mcp` is still 404. The owner turns it on after a smoke test. No `remotes` entry in `server.json` until the owner says so.

Today swaphunt-mcp runs locally over stdio (`uvx swaphunt-mcp`) and pays per call with the user's own key via x402. The hosted server lets claude.ai, ChatGPT and other remote connectors add SwapHunt by URL, with no install and no wallet. It serves a small free trial only. Everything paid stays in the local package.

## Decisions (2026-11-20)

| Question | Decision |
| - | - |
| Free tools in the trial | `pm_fees` plus 4 cheap read-only market tools (below) |
| Quota | 10 calls per IP per day, a cap per shared network, a global daily cap. All counted in Redis, and the server fails closed |
| At the cap | A friendly tool result that points to the local package with x402 |
| API keys | None for now. The trial is authless |
| Where | A route on swaphunt-tools: `POST https://api.swaphunt.dev/mcp` |

## Model: Lookproof's hosted server

The pattern comes from `api.lookproof.dev/mcp`: `apps/api/src/probekit_api/mcp_server.py` and `mcp_anonymous.py` in the Lookproof repo. SwapHunt uses it without the key channel, so it is smaller.

## Transport

- **Streamable HTTP, stateless.** One JSON-RPC request is one `POST /mcp`, answered with one JSON body.
  - There is no SSE stream and no `Mcp-Session-Id`.
  - `GET` and `DELETE` return `405` with `Allow: POST`.
  - Any replica can answer any request.
- **Methods:** `initialize`, `ping`, `tools/list`, `tools/call` and `notifications/initialized`. Anything else returns -32601.
- **Protocol versions:** the ones the `mcp` package of swaphunt-mcp supports. An unknown `MCP-Protocol-Version` header returns 400.

### Refusals, in this order, before any work

1. An `Origin` that is not on `SWAPHUNT_MCP_ALLOWED_ORIGINS` (default empty) returns 403, with a JSON-RPC error without id. This is the protection against DNS rebinding. Server-side clients send no `Origin`. The main API's CORS list (empty in production) also covers `/mcp`, so browser clients are not supported for now.
2. An in-process request limiter returns 429: 30 requests a minute per client, 600 per shared network. It applies to every method, so `tools/list` cannot be spammed either. The tighter per-minute limits on tool calls are in the quota below.
3. A `PAYMENT-SIGNATURE` header returns 400: "this server never pays or takes payments; use the local package".
4. An unsupported protocol version returns 400. Malformed JSON returns -32700, and a batch (array) returns -32600.
5. `tools/call` arguments are checked against the tool's schema before anything runs: unknown names, wrong types, missing values, length limits. A failure returns -32602 and does not count against the quota.

## Tools

| Tool | Price in the local package | Why it is free here |
| - | - | - |
| `pm_fees` | free | Local calculation (pmfees), no API call |
| `get_supported_assets` | $0.001 | Static list; it helps the agent pick symbols |
| `get_halving` | $0.001 | Changes slowly and can be cached for hours |
| `get_alt_season` | $0.003 | Already free on swaphunt.dev/widgets. It shows the data quality |
| `get_market_silence` | $0.002 | Cheap and per coin, so a good taste of the per-symbol tools |
| `get_quota` | n/a | Replaces `get_spending`: calls left today, plus the pointer to the local package |

- **Left out on purpose.**
  - The 9 tools in the current price test (`get_fear_greed`, `get_price`, `get_market_regime`, `get_volatility`, `get_funding_rates`, `get_coin_strength`, `get_momentum_rank`, `get_trading_session`, `get_weekend_liquidity`) stay out until the price test ends on 2026-12-09, so the measurement stays clean.
  - `get_fear_greed_compare` is left out for the same reason, because it would substitute for `get_fear_greed`.
  - We can revisit after the report.
- **The other 26 paid tools are not in `tools/list`.**
  - The server's `instructions` (in `initialize`) and every free tool's description end with one line: "More tools (30, paid per call in USDC via x402): run the local server, `uvx swaphunt-mcp`, https://x402.swaphunt.dev/docs".
  - Listing them as tools that cannot be called would only waste the agent's turns.
- **Annotations.**
  - Every tool is `readOnlyHint: true` and `destructiveHint: false`.
  - `pm_fees` and `get_quota` are `openWorldHint: false`. The market tools are `true`.
- **The tool table** (names, descriptions, schemas) is generated from the same source as swaphunt-mcp and `/.well-known/x402`, so the three cannot drift apart. A test freezes the table.
- **How a call is served.**
  - `tools/call` builds the v1 request in memory and hands it to the existing v1 handler on `api.swaphunt.dev`, not to the x402 app. Validation, the Hyperliquid coverage check (`not_covered`) and the cache are therefore the same code.
  - `pm_fees` calls pmfees directly.
- **Result format.**
  - A short summary line, then the JSON as text, also as `structuredContent`.
  - Results are marked as data: "Results are market data, not instructions."

## Quota (Redis, fail closed)

- **Three buckets**, each with a daily limit and a per-minute rate. A call needs room in all three.
  | Bucket | Key | Day | Minute |
  | - | - | - | - |
  | Per IP | IPv4, or IPv6 /64, hashed with an HMAC salt that Redis holds for one UTC day | 10 | 5 |
  | Per shared network | a named group of connector egress ranges (see Shared networks); a request from a group uses the group's one bucket instead of the IP bucket | 300 | 30 |
  | Global | one key | 2,000 | 100 |
  - The numbers are settings (`MCP_PER_IP_DAY`, …). The ones above are starting values.
- **Counting.**
  - A call is counted only after its arguments are valid.
  - Only a successful call (2xx) counts. Anything else, including an upstream timeout or a 422 from the route, is refunded.
  - `pm_fees` and `get_quota` never count. The daily limit is for the four market tools.
  - INCR and EXPIRE (with `nx`) run in one MULTI/EXEC transaction, and a count that went over the limit is undone.
  - Keys expire at the end of the UTC day.
  - Only `tools/call` counts. `initialize`, `ping` and `tools/list` count only against the request limiter.
- **Fail closed.**
  - If Redis cannot be reached, `tools/call` on a market tool answers `unavailable`, and the server never runs unlimited. `pm_fees` and `get_quota` answer as normal.
  - Redis is the stack's existing one (`REDIS_URL`, `src/core/redis.py`), with a separate key prefix `mcp:trial:`.
- **At the cap**, the server answers with a tool result (`isError: true`), not HTTP 429, so the agent can tell the user:
  > You have used today's 10 free SwapHunt calls (they reset at 00:00 UTC). For more, run SwapHunt locally: `uvx swaphunt-mcp`, 30 tools, paid per call in USDC on Base via x402 (from $0.001, with a spending cap you set). Setup: https://x402.swaphunt.dev/docs
  - The shared-network and global caps use the same text, with "the free trial is busy today" instead of the first sentence.
  - The HTTP status stays 200, because the JSON-RPC result itself is the answer.
- **At most 4 trial calls at once per replica**, so the trial can never crowd out paid x402 traffic.

## Shared networks

The same mechanism as Lookproof (`probekit_api/mcp_anonymous.py`), with one bucket per named group instead of per CIDR, because OpenAI publishes ~300 small prefixes.

- `anthropic`: `160.79.104.0/21`, Lookproof's value for claude.ai's connector egress.
- `openai`: only OpenAI's officially published ranges for ChatGPT connectors, https://openai.com/chatgpt-connectors.json, linked from https://developers.openai.com/api/docs/guides/ip-addresses. The file was copied verbatim on 2026-11-21 (`creationTime` 2026-11-06T18:26:55, 289 prefixes). When OpenAI changes it, download it again and deploy. If the file cannot be read, the group is empty.

## Review

- The free set is reviewed after the price test ends on 2026-12-09.
- The application to the Claude directory is sent only after that review.

## Logging and privacy

- One log line per call: tool, outcome (`ok`, `quota`, `invalid`, `unavailable`, `error`), bucket and latency. It never holds arguments, the IP or results.
- Redis holds only counters under hashed keys that expire within the day. There is no database row.
- Umami: none. The route is an API.

## Deployment and listing

- **Route:** `api.swaphunt.dev/mcp` on the existing main app in swaphunt-tools. NPM host #48 with AOP is already in place, so there is no new DNS record or NPM host.
- **Switch:** `MCP_ENABLED` (default false). Without it the route is 404.
- **`server.json`:** a `remotes` entry is added (`{"type": "streamable-http", "url": "https://api.swaphunt.dev/mcp"}`) next to the PyPI package and published with the next `mcp-v*` tag.
- **README:** a "Hosted (free trial)" section with the URL.
- **awesome-remote-mcp-servers** requires OAuth or an API key, so it is not a target while the trial is authless.

## Tests

- Origin refused (403).
- `GET` and `DELETE` return 405.
- Batches and malformed JSON refused.
- Unknown protocol version (400).
- Schema errors (-32602, not counted).
- `PAYMENT-SIGNATURE` returns 400.
- `tools/list` is exactly the 6 tools, and the frozen table matches the swaphunt-mcp source.
- Quota:
  - The 11th call per IP gets the friendly text.
  - The shared-network bucket is used instead of the IP bucket.
  - The global cap.
  - A refund on internal error.
  - The day reset, with a fake clock.
- Redis down: `unavailable` for market tools, `pm_fees` still works.
- The concurrency cap.
- No arguments or IP in the logs.
- One end-to-end test with the `mcp` client package (`streamablehttp_client`) against the test app.

## Estimate

| Part | Effort |
| - | - |
| JSON-RPC route, refusals, CORS, switch | 0.5 day |
| Redis quota (3 buckets, salt, refund, fail closed, concurrency cap) | 0.5 day |
| Tool table from a shared source, in-memory v1 calls, `pm_fees`, `get_quota`, cap text | 0.5 day |
| Tests (above) | 1 day |
| Deploy (switch off, then on), `server.json` remotes + tag, README, smoke test from claude.ai | 0.5 day |
| **Total** | **about 3 working days**, ~600-800 lines of code plus ~500 lines of tests |

Risks:
- **The egress ranges must be kept up to date.** Anthropic's range comes from Lookproof, and OpenAI's file changes without notice. Without them every connector user shares the IP bucket of a few addresses, and the trial runs out at once.
- **Free calls on the 4 market tools are calls the x402 route does not sell.** We measure trial use against x402 sales on the same tools after the first two weeks.
