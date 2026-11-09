"""Tests for the swaphunt-mcp server against a local fake API (tests/fake_swaphunt.py). No real money.

The server runs as a subprocess over stdio, the way an MCP client runs it. The fake answers with
the prices, payTo and parameters of tests/fixtures/endpoints_402.json, a snapshot of the live 402
responses (refresh with scripts/snapshot_402.py), so the contract tests compare every tool with what
the real API declares.

    pip install -r tests/requirements.txt
    python -m pytest tests -q
"""
import json
import os
import re
import subprocess
import sys
import threading
import tomllib
from pathlib import Path

import anyio
import pytest
from eth_account import Account

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fake_swaphunt  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PKG = ROOT / "mcp-server"
VERSION = re.search(r'__version__ = "([^"]+)"', (PKG / "src/swaphunt_mcp/__init__.py").read_text())[1]
FIXTURE = json.loads((ROOT / "tests/fixtures/endpoints_402.json").read_text())
ENDPOINTS = {e["path"]: e for e in FIXTURE["endpoints"]}
PAY_TO = FIXTURE["endpoints"][0]["pay_to"]
OTHER_PAY_TO = "0x000000000000000000000000000000000000dEaD"
REQUIRED_ARGS = {"is_this_a_breakout": {"level": 1.0}, "is_this_support": {"level": 1.0}}
ENV_KEYS = ("FAKE_PRICE_FACTOR", "FAKE_PAY_TO", "FAKE_SWITCH_PAY_TO", "FAKE_STATUS", "X402_PAY", "PRIVATE_KEY",
            "PRIVATE_KEY_FILE", "MAX_SPEND_USD", "PAYTO_ALLOWLIST", "SWAPHUNT_API_URL")


@pytest.fixture()
def api(monkeypatch):
    for k in ENV_KEYS:
        monkeypatch.delenv(k, raising=False)
    fake_swaphunt.reset()
    server = fake_swaphunt.serve(0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{server.server_address[1]}"
    monkeypatch.setenv("SWAPHUNT_API_URL", url)
    yield url
    server.shutdown()


@pytest.fixture()
def key():
    return Account.create().key.hex()  # throwaway; the fake never settles anything


def server_env(extra: dict | None = None) -> dict:
    return {**os.environ, "PYTHONPATH": str(PKG / "src"), **(extra or {})}


async def _session(env: dict, calls: list[tuple[str, dict]]):
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    params = StdioServerParameters(command=sys.executable, args=["-m", "swaphunt_mcp"], env=server_env(env))
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as s:
            init = await s.initialize()
            tools = (await s.list_tools()).tools
            results = []
            for name, args in calls:
                res = await s.call_tool(name, args)
                results.append(json.loads(res.content[0].text))
            return init, tools, results


def mcp_run(env: dict, calls: list[tuple[str, dict]]):
    return anyio.run(_session, env, calls)


def run_cli(*args, env=None):
    return subprocess.run([sys.executable, "-m", "swaphunt_mcp", *args], capture_output=True, text=True,
                          timeout=120, env=server_env(env))


def advertised(description: str) -> float:
    return float(re.search(r"Costs \$([0-9.]+) USDC per call\.$", description)[1])


def signed_requests() -> list[dict]:
    return [r for r in fake_swaphunt.requests_log if r["signed"]]


# --- Contract: every tool against the API's own 402 -------------------------

def test_every_tool_matches_the_api_contract(api):
    _, tools, _ = mcp_run({}, [])
    paid = [t for t in tools if t.name != "get_spending"]
    assert {t.name for t in tools} >= {"get_spending"} and len(paid) == len(ENDPOINTS)
    _, _, results = mcp_run({}, [(t.name, REQUIRED_ARGS.get(t.name, {})) for t in paid])
    log = fake_swaphunt.requests_log
    assert len(log) == len(paid), "each dry run sends exactly one unpaid request"
    seen = {}
    for tool, result, req in zip(paid, results, log):
        e = ENDPOINTS.get(req["path"])
        assert e is not None, f"{tool.name} calls {req['path']}, which the API does not sell"
        assert req["path"] not in seen, f"{tool.name} and {seen.get(req['path'])} call the same route"
        seen[req["path"]] = tool.name
        price = int(e["amount"]) / 1e6
        assert advertised(tool.description) == pytest.approx(price), f"{tool.name}: price in description"
        assert result["dry_run"] is True and result["would_cost_usd"] == pytest.approx(price), tool.name
        api_params = e["params"]
        props = tool.input_schema.get("properties", {})
        assert set(props) <= set(api_params), f"{tool.name}: parameters the API does not declare"
        assert set(req["query"]) <= set(api_params), f"{tool.name}: sent parameters the API does not declare"
        required = {n for n, p in api_params.items() if p["required"]}
        assert required <= set(tool.input_schema.get("required", [])), f"{tool.name}: API-required params"
        for name, spec in props.items():
            if "default" in spec and "default" in api_params[name]:
                assert spec["default"] == api_params[name]["default"], f"{tool.name}.{name} default"
    assert set(seen) == set(ENDPOINTS), f"routes without a tool: {sorted(set(ENDPOINTS) - set(seen))}"


def test_tools_and_server_identify_themselves(api):
    init, tools, (spending,) = mcp_run({}, [("get_spending", {})])
    assert init.server_info.name == "swaphunt" and init.server_info.version == VERSION
    assert len(tools) == len(ENDPOINTS) + 1
    assert spending == {"payments_enabled": False, "spent_usd": 0.0, "paid_calls": 0, "cap_usd": 0.1,
                        "remaining_usd": 0.1}


# --- Dry run ------------------------------------------------------------------

def test_dry_run_pays_nothing_and_sends_user_agent(api, key):
    # A key is configured but X402_PAY is not set: still a dry run.
    _, _, (dry, spending) = mcp_run({"PRIVATE_KEY": key}, [("get_fear_greed", {}), ("get_spending", {})])
    assert dry["dry_run"] is True and dry["would_cost_usd"] == 0.001
    assert dry["network"] == "eip155:8453" and dry["pay_to"] == PAY_TO
    assert signed_requests() == [] and fake_swaphunt.paid_log == []
    assert spending["spent_usd"] == 0 and spending["paid_calls"] == 0
    assert {r["user_agent"] for r in fake_swaphunt.requests_log} == {f"swaphunt-mcp/{VERSION}"}


def test_not_covered_is_free(api, key):
    _, _, (res, spending) = mcp_run({"X402_PAY": "1", "PRIVATE_KEY": key},
                                    [("is_this_a_dip", {"symbol": "notcovered"}), ("get_spending", {})])
    assert res["error"] == "not_covered" and res["charged"] is False and res["covered"] == ["BTC", "ETH", "SOL"]
    assert signed_requests() == [] and spending["spent_usd"] == 0


# --- Paying and the session cap -----------------------------------------------

def test_pays_and_caps_the_session(api, key):
    calls = [("get_fear_greed", {}), ("get_market_regime", {}), ("get_halving", {}),
             ("get_trading_session", {}), ("get_spending", {})]
    _, _, (fg, regime, halving, capped, spending) = mcp_run(
        {"X402_PAY": "1", "PRIVATE_KEY": key, "MAX_SPEND_USD": "0.004"}, calls)
    assert fg["cost_usd"] == 0.001 and fg["tx"].startswith("https://basescan.org/tx/0x")
    assert fg["data"]["path"] == "/v1/market/fear-greed"
    assert regime["cost_usd"] == 0.002 and halving["session_spent_usd"] == pytest.approx(0.004)
    assert halving["session_remaining_usd"] == pytest.approx(0)
    assert "Session spending cap reached" in capped["error"]
    assert spending["paid_calls"] == 3 and spending["spent_usd"] == pytest.approx(0.004)
    assert [p["path"] for p in fake_swaphunt.paid_log] == [
        "/v1/market/fear-greed", "/v1/regime/current", "/v1/market/halving"]
    assert all(p["to"].lower() == PAY_TO.lower() for p in fake_swaphunt.paid_log)
    # The capped call got its quote but was never signed.
    assert len(signed_requests()) == 3
    assert {r["user_agent"] for r in fake_swaphunt.requests_log} == {f"swaphunt-mcp/{VERSION}"}


def test_cap_of_zero_pays_nothing(api, key):
    _, _, (res,) = mcp_run({"X402_PAY": "1", "PRIVATE_KEY": key, "MAX_SPEND_USD": "0"}, [("get_fear_greed", {})])
    assert "Session spending cap reached" in res["error"] and signed_requests() == []


def test_refuses_price_above_advertised(api, key, monkeypatch):
    monkeypatch.setenv("FAKE_PRICE_FACTOR", "2")  # read by the fake API in this process
    _, _, (res, dry) = mcp_run({"X402_PAY": "1", "PRIVATE_KEY": key, "MAX_SPEND_USD": "1"},
                               [("get_funding_rates", {}), ("get_spending", {})])
    assert res["error"].startswith("Refused: /v1/derivatives/funding-rates now costs $0.006")
    assert signed_requests() == [] and dry["spent_usd"] == 0
    _, _, (res,) = mcp_run({}, [("get_funding_rates", {})])  # a dry run reports the refusal too
    assert res["error"].startswith("Refused:")


def test_payment_locked_to_the_quote(api, key, monkeypatch):
    monkeypatch.setenv("FAKE_SWITCH_PAY_TO", OTHER_PAY_TO)  # the paid retry quotes another payTo
    _, _, (res, spending) = mcp_run({"X402_PAY": "1", "PRIVATE_KEY": key},
                                    [("get_fear_greed", {}), ("get_spending", {})])
    assert res["error"].startswith("Not paid: the payment terms changed")
    assert signed_requests() == [] and fake_swaphunt.paid_log == [] and spending["spent_usd"] == 0


def test_failed_paid_call_counts_as_possibly_paid(api, key, monkeypatch):
    monkeypatch.setenv("FAKE_STATUS", "503")
    _, _, (res, spending) = mcp_run({"X402_PAY": "1", "PRIVATE_KEY": key},
                                    [("get_fear_greed", {}), ("get_spending", {})])
    assert res["error"].startswith("Possibly paid $0.001") and spending["spent_usd"] == 0.001


# --- PAYTO_ALLOWLIST ----------------------------------------------------------

def test_payto_allowlist_refuses_before_signing(api, key):
    env = {"X402_PAY": "1", "PRIVATE_KEY": key, "PAYTO_ALLOWLIST": OTHER_PAY_TO}
    _, _, (res, spending) = mcp_run(env, [("get_fear_greed", {}), ("get_spending", {})])
    assert res["error"].startswith(f"Refused: /v1/market/fear-greed asks for payment to {PAY_TO}")
    assert "not in PAYTO_ALLOWLIST" in res["error"]
    assert signed_requests() == [] and fake_swaphunt.paid_log == [] and spending["spent_usd"] == 0
    _, _, (dry,) = mcp_run({"PAYTO_ALLOWLIST": OTHER_PAY_TO}, [("get_fear_greed", {})])
    assert dry["error"].startswith("Refused:"), "a dry run shows the refusal as well"


def test_payto_allowlist_allows_listed_address(api, key):
    # Case does not matter, and several addresses may be listed.
    env = {"X402_PAY": "1", "PRIVATE_KEY": key, "PAYTO_ALLOWLIST": f"{OTHER_PAY_TO}, {PAY_TO.upper().replace('0X', '0x')}"}
    _, _, (res,) = mcp_run(env, [("get_fear_greed", {})])
    assert res["cost_usd"] == 0.001 and len(fake_swaphunt.paid_log) == 1


def test_payto_allowlist_rejects_bad_entries(api):
    r = run_cli("--version", env={"PAYTO_ALLOWLIST": "0x1234,not-an-address"})
    assert r.returncode == 1 and "PAYTO_ALLOWLIST has an entry that is not an address: '0x1234'" in r.stderr


# --- Command line -------------------------------------------------------------

def test_version(api):
    r = run_cli("--version")
    assert r.returncode == 0 and r.stdout.strip() == f"swaphunt-mcp {VERSION}"


def test_check_compares_prices_and_pays_nothing(api, monkeypatch):
    r = run_cli("--check")
    assert r.returncode == 0, r.stdout + r.stderr
    assert f"{len(ENDPOINTS)} paid tools, 0 mismatches" in r.stdout
    assert signed_requests() == []
    monkeypatch.setenv("FAKE_PRICE_FACTOR", "2")
    r = run_cli("--check")
    assert r.returncode == 1 and f"{len(ENDPOINTS)} mismatches" in r.stdout


def test_pay_without_key_refuses_to_start(api):
    r = run_cli(env={"X402_PAY": "1"})
    assert r.returncode == 1 and "needs PRIVATE_KEY or PRIVATE_KEY_FILE" in r.stderr


# --- Package metadata ---------------------------------------------------------

def test_versions_and_settings_agree():
    sj = json.loads((PKG / "server.json").read_text())
    pyproject = tomllib.loads((PKG / "pyproject.toml").read_text())
    assert sj["version"] == VERSION
    (pkg,) = sj["packages"]
    assert pkg["version"] == VERSION and pkg["identifier"] == pyproject["project"]["name"] == "swaphunt-mcp"
    assert 1 <= len(sj["description"]) <= 100  # registry schema limit
    env_names = {e["name"] for e in pkg["environmentVariables"]}
    assert env_names == {"X402_PAY", "PRIVATE_KEY_FILE", "PRIVATE_KEY", "MAX_SPEND_USD", "PAYTO_ALLOWLIST"}
    assert f"## {VERSION} " in (PKG / "CHANGELOG.md").read_text()
    readme = (PKG / "README.md").read_text()
    for name in env_names:
        assert f"`{name}`" in readme, f"README does not document {name}"
