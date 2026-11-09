"""Tests for the swaphunt-mcp server, against a local fake of the SwapHunt x402 API (tests/fake_swaphunt.py).

No real money and no network: every payment is signed with a throwaway key and only checked locally
by the fake. tests/contract.json is the contract: one entry per paid endpoint with its tool, path,
price and required parameters, taken from the published price list. Run from the repository root:

    python -m venv .venv && .venv/bin/pip install -r tests/requirements.txt
    .venv/bin/python -m pytest tests
"""
import json
import os
import re
import secrets
import subprocess
import sys
import threading
import tomllib
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "mcp-server/src"))
import fake_swaphunt  # noqa: E402
from swaphunt_mcp import __version__ as VERSION  # noqa: E402  (only __init__, no dependencies)

ROOT = Path(__file__).resolve().parent.parent
PKG = ROOT / "mcp-server"
CONTRACT = fake_swaphunt.CONTRACT
OTHER_PAY_TO = "0x1111111111111111111111111111111111111111"
UA = f"swaphunt-mcp/{VERSION}"
# Run the package from source.
SERVER_ENV = {"PYTHONPATH": str(PKG / "src")}
KNOBS = ("FAKE_PRICE_FACTOR", "FAKE_PAY_TO", "FAKE_SWITCH_PAY_TO", "FAKE_STATUS", "FAKE_NOT_COVERED",
         "X402_PAY", "PRIVATE_KEY", "PRIVATE_KEY_FILE", "MAX_SPEND_USD", "PAYTO_ALLOWLIST")


@pytest.fixture()
def api(monkeypatch):
    for k in KNOBS:
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
    return "0x" + secrets.token_hex(32)


def args_for(e: dict) -> dict:
    """Arguments for a tool call: the endpoint's required parameters, nothing else."""
    return {p: 100000 for p in e["required"]}  # `level` is the only required parameter today


async def mcp_session(env: dict, calls: list[tuple[str, dict]]):
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    params = StdioServerParameters(command=sys.executable, args=["-m", "swaphunt_mcp"],
                                   env={**os.environ, **SERVER_ENV, **env})
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            tools = (await session.list_tools()).tools
            results = []
            for name, a in calls:
                res = await session.call_tool(name, a)
                results.append(json.loads(res.content[0].text))
            return init, tools, results


def mcp_run(env, calls):
    import anyio
    return anyio.run(mcp_session, env, calls)


def run(*args, env=None):
    return subprocess.run([sys.executable, *map(str, args)], capture_output=True, text=True,
                          env={**os.environ, **SERVER_ENV, **(env or {})}, timeout=120)


def signed_requests():
    return [r for r in fake_swaphunt.requests_log if r["signed"]]


# --- Contract ---------------------------------------------------------------

def test_contract_has_one_entry_per_endpoint():
    paths = [e["path"] for e in CONTRACT]
    tools = [e["tool"] for e in CONTRACT]
    assert len(CONTRACT) == 30 and len(set(paths)) == 30 and len(set(tools)) == 30


def test_every_tool_matches_contract(api):
    """Each contract entry has a tool whose description states the contract price, and nothing else is listed."""
    init, tools, _ = mcp_run({}, [])
    assert init.server_info.name == "swaphunt" and init.server_info.version == VERSION
    by_name = {t.name: t for t in tools}
    assert set(by_name) == {e["tool"] for e in CONTRACT} | {"get_spending"}
    for e in CONTRACT:
        price = e["price_atomic"] / 1e6
        assert f"Costs ${price:.3f} USDC per call." in by_name[e["tool"]].description, e["tool"]
        schema = by_name[e["tool"]].input_schema
        assert set(schema.get("required", [])) == set(e["required"]), e["tool"]


def test_every_tool_dry_run_quotes_contract_price(api):
    """Dry run: every tool calls its own path, reports the contract price and pays nothing."""
    calls = [(e["tool"], args_for(e)) for e in CONTRACT]
    _, _, results = mcp_run({}, calls)
    for e, res in zip(CONTRACT, results):
        assert res.get("dry_run") is True, (e["tool"], res)
        assert res["would_cost_usd"] == e["price_atomic"] / 1e6, e["tool"]
        assert res["pay_to"] == fake_swaphunt.DEFAULT_PAY_TO and res["network"] == "eip155:8453"
    assert [r["path"] for r in fake_swaphunt.requests_log] == [e["path"] for e in CONTRACT]
    assert {r["user_agent"] for r in fake_swaphunt.requests_log} == {UA}
    assert signed_requests() == [] and fake_swaphunt.paid_log == []


def test_every_tool_refuses_price_above_advertised(api, key, monkeypatch):
    """Price ceiling per tool: if the API asks more than the tool advertises, nothing is signed."""
    monkeypatch.setenv("FAKE_PRICE_FACTOR", "2")
    calls = [(e["tool"], args_for(e)) for e in CONTRACT] + [("get_spending", {})]
    _, _, results = mcp_run({"X402_PAY": "1", "PRIVATE_KEY": key, "MAX_SPEND_USD": "1"}, calls)
    *refused, spending = results
    for e, res in zip(CONTRACT, refused):
        assert res["error"].startswith(f"Refused: {e['path']} now costs"), (e["tool"], res)
    assert spending["spent_usd"] == 0 and spending["paid_calls"] == 0
    assert signed_requests() == [] and fake_swaphunt.paid_log == []


def test_check_matches_contract(api, monkeypatch):
    r = run("-m", "swaphunt_mcp", "--check")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "30 paid tools, 0 mismatches" in r.stdout
    monkeypatch.setenv("FAKE_PRICE_FACTOR", "2")  # read by the fake API in this process
    r = run("-m", "swaphunt_mcp", "--check")
    assert r.returncode == 1 and "30 mismatches" in r.stdout
    assert signed_requests() == [] and fake_swaphunt.paid_log == []


# --- Paying and the session cap ---------------------------------------------

def test_pays_and_caps_session(api, key):
    calls = [("get_price", {}), ("get_fear_greed_compare", {}), ("get_fear_greed_history", {}),
             ("get_spending", {})]
    _, _, (price, compare, capped, spending) = mcp_run(
        {"X402_PAY": "1", "PRIVATE_KEY": key, "MAX_SPEND_USD": "0.005"}, calls)
    assert price["cost_usd"] == 0.001 and price["data"]["path"] == "/v1/tools/price"
    assert price["tx"].startswith("https://basescan.org/tx/0x")
    assert compare["cost_usd"] == 0.002 and compare["session_spent_usd"] == 0.003
    assert capped["error"].startswith("Session spending cap reached")  # 0.003 + 0.005 > 0.005
    assert spending == {"payments_enabled": True, "spent_usd": 0.003, "paid_calls": 2, "cap_usd": 0.005,
                        "remaining_usd": 0.002}
    assert [p["path"] for p in fake_swaphunt.paid_log] == ["/v1/tools/price", "/v1/market/fear-greed/compare"]
    assert {r["user_agent"] for r in fake_swaphunt.requests_log} == {UA}


def test_cap_is_inclusive(api, key):
    """Spending exactly up to the cap is allowed (no float rounding refusals)."""
    calls = [("get_price", {})] * 3 + [("get_halving", {})]
    _, _, results = mcp_run({"X402_PAY": "1", "PRIVATE_KEY": key, "MAX_SPEND_USD": "0.003"}, calls)
    assert [r.get("cost_usd") for r in results[:3]] == [0.001] * 3
    assert results[3]["error"].startswith("Session spending cap reached")


def test_payment_locked_to_quote(api, key, monkeypatch):
    monkeypatch.setenv("FAKE_SWITCH_PAY_TO", OTHER_PAY_TO)
    _, _, (res, spending) = mcp_run({"X402_PAY": "1", "PRIVATE_KEY": key},
                                    [("get_price", {}), ("get_spending", {})])
    assert res["error"].startswith("Not paid: the payment terms changed")
    assert spending["spent_usd"] == 0
    assert fake_swaphunt.paid_log == []


def test_failed_paid_call_stays_counted(api, key, monkeypatch):
    monkeypatch.setenv("FAKE_STATUS", "503")
    _, _, (res, spending) = mcp_run({"X402_PAY": "1", "PRIVATE_KEY": key},
                                    [("get_price", {}), ("get_spending", {})])
    assert "HTTP 503" in res["error"]
    assert spending["spent_usd"] == 0.001 and spending["paid_calls"] == 0


def test_not_covered_is_free(api, key, monkeypatch):
    monkeypatch.setenv("FAKE_NOT_COVERED", "DOGE")
    _, _, (res, spending) = mcp_run({"X402_PAY": "1", "PRIVATE_KEY": key},
                                    [("is_this_a_dip", {"symbol": "DOGE"}), ("get_spending", {})])
    assert res["error"] == "not_covered" and res["charged"] is False and res["covered"] == ["BTC", "ETH"]
    assert spending["spent_usd"] == 0
    assert signed_requests() == []


# --- PAYTO_ALLOWLIST --------------------------------------------------------

def test_payto_allowlist_refuses_before_signing(api, key):
    calls = [("get_price", {}), ("get_spending", {})]
    _, _, (res, spending) = mcp_run({"X402_PAY": "1", "PRIVATE_KEY": key, "PAYTO_ALLOWLIST": OTHER_PAY_TO}, calls)
    assert res["error"].startswith("Refused: /v1/tools/price asks for payment to")
    assert "not in PAYTO_ALLOWLIST" in res["error"]
    assert spending["spent_usd"] == 0
    assert signed_requests() == [] and fake_swaphunt.paid_log == []


def test_payto_allowlist_applies_to_dry_run(api):
    _, _, (res,) = mcp_run({"PAYTO_ALLOWLIST": OTHER_PAY_TO}, [("get_price", {})])
    assert "not in PAYTO_ALLOWLIST" in res["error"]


def test_payto_allowlist_allows_listed_address(api, key):
    # Mixed case and spaces: addresses are compared case-insensitively.
    allow = f" {OTHER_PAY_TO}, {fake_swaphunt.DEFAULT_PAY_TO.upper().replace('0X', '0x')} "
    _, _, (res,) = mcp_run({"X402_PAY": "1", "PRIVATE_KEY": key, "PAYTO_ALLOWLIST": allow}, [("get_price", {})])
    assert res["cost_usd"] == 0.001
    assert [p["to"].lower() for p in fake_swaphunt.paid_log] == [fake_swaphunt.DEFAULT_PAY_TO.lower()]


def test_payto_allowlist_rejects_bad_entry(api):
    r = run("-m", "swaphunt_mcp", "--version", env={"PAYTO_ALLOWLIST": "0x123,swaphunt.dev"})
    assert r.returncode == 1 and "PAYTO_ALLOWLIST has an entry that is not an address" in r.stderr


# --- Startup and key handling -----------------------------------------------

def test_version_and_help():
    r = run("-m", "swaphunt_mcp", "--version")
    assert r.returncode == 0 and r.stdout.strip() == f"swaphunt-mcp {VERSION}"
    r = run("-m", "swaphunt_mcp", "--help")
    assert r.returncode == 0 and "--check" in r.stdout and "PAYTO_ALLOWLIST" in r.stdout


def test_pay_without_key_refuses_to_start(api):
    r = run("-m", "swaphunt_mcp", env={"X402_PAY": "1"})
    assert r.returncode == 1 and "needs PRIVATE_KEY or PRIVATE_KEY_FILE" in r.stderr


@pytest.mark.skipif(os.name != "posix", reason="file modes are POSIX")
def test_key_file_must_be_private(api, key, tmp_path):
    f = tmp_path / "wallet.key"
    f.write_text(key)
    f.chmod(0o644)
    r = run("-m", "swaphunt_mcp", env={"X402_PAY": "1", "PRIVATE_KEY_FILE": str(f)})
    assert r.returncode == 1 and "readable by other users" in r.stderr
    f.chmod(0o600)
    _, _, (res,) = mcp_run({"X402_PAY": "1", "PRIVATE_KEY_FILE": str(f)}, [("get_price", {})])
    assert res["cost_usd"] == 0.001


def test_key_and_key_file_together_refused(api, key, tmp_path):
    f = tmp_path / "wallet.key"
    f.write_text(key)
    f.chmod(0o600)
    r = run("-m", "swaphunt_mcp", env={"X402_PAY": "1", "PRIVATE_KEY": key, "PRIVATE_KEY_FILE": str(f)})
    assert r.returncode == 1 and "not both" in r.stderr


# --- Package metadata -------------------------------------------------------

def test_server_json_matches_package():
    sj = json.loads((PKG / "server.json").read_text())
    pyproject = tomllib.loads((PKG / "pyproject.toml").read_text())
    assert sj["name"] == "io.github.swaphunt/swaphunt-mcp"
    assert 1 <= len(sj["description"]) <= 100  # registry schema limit
    assert sj["version"] == VERSION
    (pkg,) = sj["packages"]
    assert pkg["identifier"] == pyproject["project"]["name"] == "swaphunt-mcp"
    assert pkg["version"] == VERSION and pkg["transport"] == {"type": "stdio"}
    env_names = {e["name"] for e in pkg["environmentVariables"]}
    assert env_names == {"X402_PAY", "PRIVATE_KEY_FILE", "PRIVATE_KEY", "MAX_SPEND_USD", "PAYTO_ALLOWLIST"}
    assert all(e.get("isSecret") for e in pkg["environmentVariables"] if e["name"] == "PRIVATE_KEY")
    assert f"## {VERSION} " in (PKG / "CHANGELOG.md").read_text()


def test_readme_documents_settings_and_tools():
    readme = (PKG / "README.md").read_text()
    for name in ("X402_PAY", "PRIVATE_KEY_FILE", "MAX_SPEND_USD", "PAYTO_ALLOWLIST", "uvx swaphunt-mcp"):
        assert name in readme, name
    for e in CONTRACT:
        assert f"`{e['tool']}`" in readme, e["tool"]
    # PyPI renders the README without the repository, so links must be absolute.
    assert not re.search(r"\]\((?!https://|#)", readme)
