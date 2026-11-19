from __future__ import annotations

import os
import socket
import uuid
import pytest
from fastapi.testclient import TestClient

from app.database import db_session, reset_db_init_cache
from app.main import app
from app.quant_core import (
    BetaWinRate,
    ClockSyncGuard,
    ConsensusEngine,
    IsotonicCalibrator,
    NormalGamma,
    RiskState,
    compute_calibration_table,
    compute_hwm_bots20_transfer,
    deflated_sharpe,
    detect_market_regime,
    evaluate_daily_drawdown_breaker,
    graduated_exit_plan,
    iceberg_visible_qty,
    make_idempotent_client_order_id,
    size_position,
    thompson_allocate,
    twap_slices,
    validate_spot_signal,
)
from app.security import hash_admin_secret, verify_admin_secret_path_safe


def test_consensus_only_predictors_and_isotonic_calibration() -> None:
    with pytest.raises(ValueError):
        ConsensusEngine(["AI1", "AI2", "AI4"])

    ce = ConsensusEngine(["AI1", "AI2", "AI3"])
    assert set(ce.stats.keys()) == {"AI1", "AI2", "AI3"}
    for _ in range(120):
        ce.update({"AI1": 0.92, "AI2": 0.50, "AI3": 0.25}, 1)
    assert ce.stats["AI1"].weight > ce.stats["AI2"].weight > ce.stats["AI3"].weight

    cal = IsotonicCalibrator().fit([0.1, 0.4, 0.35, 0.8, 0.9], [0, 0, 1, 1, 1])
    assert 0.0 <= cal(0.85) <= 1.0
    assert cal(0.2) <= cal(0.5) <= cal(0.95)


def test_spot_long_only_and_hwm_net_of_fees() -> None:
    naked_sell = validate_spot_signal("SELL", holding_qty=0.0, step=0.001)
    assert naked_sell["executable"] is False
    assert naked_sell["action"] == "STAY_FLAT_NO_SHORT"

    close_owned = validate_spot_signal("SELL", holding_qty=10.5, step=0.001)
    assert close_owned["executable"] is True
    assert close_owned["action"] == "EXIT_OWNED_SPOT"
    assert close_owned["qty_cap"] == 10.5

    loss_day = compute_hwm_bots20_transfer(-500.0, notional_usd=10_000.0, equity_before_trade=100_000.0, high_water_mark=100_000.0)
    assert loss_day["bots_20_usd"] == 0.0
    assert loss_day["new_hwm"] == 100_000.0

    below_hwm = compute_hwm_bots20_transfer(300.0, notional_usd=10_000.0, equity_before_trade=loss_day["new_equity"], high_water_mark=loss_day["new_hwm"])
    assert below_hwm["bots_20_usd"] == 0.0

    above_hwm = compute_hwm_bots20_transfer(500.0, notional_usd=10_000.0, equity_before_trade=below_hwm["new_equity"], high_water_mark=below_hwm["new_hwm"])
    assert above_hwm["above_hwm_gain"] > 0
    assert above_hwm["bots_20_usd"] == round(above_hwm["above_hwm_gain"] * 0.20, 2)


def test_three_tier_daily_drawdown_circuit_breaker_unit() -> None:
    """
    Phase 1 Rule #6 Unit Test:
    - < 1.5% DD  -> Full Kelly size (1.0x)
    - 1.5% - 2.5% -> Cut size in half (0.5x)
    - 2.5% - 3.0% -> Stop new trades (approved=False, close_all_positions=False)
    - >= 3.0%     -> Close everything & halt (approved=False, close_all_positions=True)
    """
    wr = BetaWinRate(30, 10)

    # 1. Normal (< 1.5% DD)
    rs_normal = RiskState(equity=99_200.0, day_start_equity=100_000.0, open_risk_usd=0.0)
    b_norm = evaluate_daily_drawdown_breaker(rs_normal)
    assert b_norm["tier"] == "NORMAL"
    assert b_norm["size_multiplier"] == 1.0
    sz_norm = size_position(0.90, wr, 2.2, 100.0, 1.5, 0.01, rs_normal, "SOLUSDT", "crypto")
    assert sz_norm["approved"] is True
    assert sz_norm["size_multiplier"] == 1.0

    # 2. 1.5% <= DD < 2.5% -> Half Size (0.5x)
    rs_half = RiskState(equity=98_200.0, day_start_equity=100_000.0, open_risk_usd=0.0)  # 1.8% DD
    b_half = evaluate_daily_drawdown_breaker(rs_half)
    assert b_half["tier"] == "DD_1_5_HALF_SIZE"
    assert b_half["size_multiplier"] == 0.5
    assert b_half["allow_new_trades"] is True
    assert b_half["close_all_positions"] is False
    sz_half = size_position(0.90, wr, 2.2, 100.0, 1.5, 0.01, rs_half, "SOLUSDT", "crypto")
    assert sz_half["approved"] is True
    assert sz_half["size_multiplier"] == 0.5
    # Accounting for 98.2k vs 99.2k equity (~0.99 ratio), half-size qty is ~0.495x of normal qty
    assert 0.48 <= (sz_half["qty"] / sz_norm["qty"]) <= 0.51

    # 3. 2.5% <= DD < 3.0% -> Stop New Trades (keep existing managed, close_all=False)
    rs_stop = RiskState(equity=97_300.0, day_start_equity=100_000.0, open_risk_usd=0.0)  # 2.7% DD
    b_stop = evaluate_daily_drawdown_breaker(rs_stop)
    assert b_stop["tier"] == "DD_2_5_STOP_NEW"
    assert b_stop["allow_new_trades"] is False
    assert b_stop["close_all_positions"] is False
    sz_stop = size_position(0.95, wr, 2.2, 100.0, 1.5, 0.01, rs_stop, "SOLUSDT", "crypto")
    assert sz_stop["approved"] is False
    assert sz_stop["veto_by"] == "AI4_DAILY_DD_2_5_STOP_NEW"
    assert sz_stop["close_all_positions"] is False

    # 4. >= 3.0% DD -> Close Everything & Halt (close_all=True)
    rs_close = RiskState(equity=96_800.0, day_start_equity=100_000.0, open_risk_usd=0.0)  # 3.2% DD
    b_close = evaluate_daily_drawdown_breaker(rs_close)
    assert b_close["tier"] == "DD_3_0_CLOSE_ALL"
    assert b_close["allow_new_trades"] is False
    assert b_close["close_all_positions"] is True
    sz_close = size_position(0.95, wr, 2.2, 100.0, 1.5, 0.01, rs_close, "SOLUSDT", "crypto")
    assert sz_close["approved"] is False
    assert sz_close["veto_by"] == "AI4_DAILY_DD_VETO"
    assert sz_close["close_all_positions"] is True


def test_argon2id_idempotency_clock_sync_and_calibration_bins_unit() -> None:
    # Rule #8: Argon2id hashing in security.py
    h = hash_admin_secret("Sovereign#Majed2026")
    assert h.startswith("$argon2id$v=19$m=65536,t=3,p=2$")
    assert verify_admin_secret_path_safe("Sovereign#Majed2026", h) is True
    assert verify_admin_secret_path_safe("Wrong#Password", h) is False

    # Rule #9: Deterministic idempotent clientOrderId + ClockSyncGuard (recvWindow)
    cid1 = make_idempotent_client_order_id("SOLUSDT", "BUY", "sig-2026-11-19T12:00")
    cid2 = make_idempotent_client_order_id("SOLUSDT", "BUY", "sig-2026-11-19T12:00")
    cid3 = make_idempotent_client_order_id("SOLUSDT", "BUY", "sig-2026-11-19T12:05")
    assert cid1 == cid2
    assert cid1 != cid3
    assert len(cid1) <= 36

    clk = ClockSyncGuard(recv_window_ms=5000, max_allowed_drift_ms=1000)
    sync_ok = clk.sync_with_server_time(1_700_000_000_050, local_send_ms=1_700_000_000_000, local_recv_ms=1_700_000_000_004)
    assert sync_ok["withinDriftLimit"] is True
    assert clk.build_signed_timing_params(1_700_000_000_100)["recvWindow"] == 5000

    clk.sync_with_server_time(1_700_000_005_000, local_send_ms=1_700_000_000_000, local_recv_ms=1_700_000_000_002)
    with pytest.raises(ValueError):
        clk.build_signed_timing_params(1_700_000_000_100)

    # Rule #11: 4-bin calibration table (75-80%, 80-85%, 85-90%, 90%+)
    cal_tbl = compute_calibration_table([
        {"calibrated_prob": 0.77, "won": True, "net_pnl_usd": 120.0},
        {"calibrated_prob": 0.82, "won": True, "net_pnl_usd": 180.0},
        {"calibrated_prob": 0.87, "won": True, "net_pnl_usd": 220.0},
        {"calibrated_prob": 0.94, "won": True, "net_pnl_usd": 310.0},
    ])
    assert [b["bin"] for b in cal_tbl["bins"]] == ["75-80%", "80-85%", "85-90%", "90%+"]


def test_postgresql_orders_fills_kill_switch_cfo_gate_and_14day_testnet_lock(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    End-to-end API & PostgreSQL Persistence Test:
    - Connects to Native PostgreSQL (127.0.0.1:5432) if running so orders & fills are proven in PostgreSQL!
    - Verifies idempotent order submission, working order cancellation via Kill Switch,
      14-day Testnet lock against LIVE_PRODUCTION trade keys, and Personal CFO login protection (401 -> 200).
    """
    pg_up = False
    try:
        with socket.create_connection(("127.0.0.1", 5432), timeout=0.5):
            pg_up = True
    except OSError:
        pg_up = False

    if pg_up:
        monkeypatch.setenv("DATABASE_URL", "postgresql://trilunair@127.0.0.1:5432/trilunair")
        reset_db_init_cache()

    monkeypatch.setenv("TRILUNAIR_REQUIRE_CFO_LOGIN", "1")

    with TestClient(app) as client:
        # Ensure Kill Switch starts disarmed
        client.post("/api/executive/kill-switch", json={"active": False, "reason": "TEST_INIT"})

        # 1. Rule #10: Personal CFO (/cfo & /api/wealth/overview) MUST reject unauthenticated public access!
        assert client.get("/cfo").status_code == 401
        assert client.get("/api/wealth/overview").status_code == 401

        # 2. Rule #8 & #10: Approve Argon2id password -> issues session cookie -> unlocks /api/wealth/overview!
        r_app = client.post("/api/executive/auth/approve-password", json={"email": "majed@trillionaire.sa", "password": "Majed#Strong2026"})
        assert r_app.status_code == 200
        assert "Argon2id" in r_app.json()["kdf"]
        assert client.get("/api/wealth/overview").status_code == 200

        # 3. Rule #7 & #11: Testnet keys accepted, LIVE_PRODUCTION keys strictly blocked before 14 days!
        r_test_keys = client.post(
            "/api/executive/vault/validate-keys",
            json={
                "readOnlyKey": "TESTNET_RO_KEY_111",
                "tradeOnlyKey": "TESTNET_TR_KEY_222",
                "withdrawalsDisabled": True,
                "staticIpWhitelisted": True,
                "environment": "SPOT_TESTNET",
            },
        )
        assert r_test_keys.json()["approved"] is True

        r_live_blocked = client.post(
            "/api/executive/vault/validate-keys",
            json={
                "readOnlyKey": "LIVE_RO_KEY_111",
                "tradeOnlyKey": "LIVE_TR_KEY_222",
                "withdrawalsDisabled": True,
                "staticIpWhitelisted": True,
                "environment": "LIVE_PRODUCTION",
            },
        )
        assert r_live_blocked.json()["approved"] is False
        assert r_live_blocked.json()["blockedBy14DayTestnetLock"] is True

        # 4. Rule #9: Sync clock (recvWindow=5000) + Submit idempotent filled order & verify PostgreSQL row + fill!
        r_clk = client.post("/api/executive/clock/sync", json={"recvWindowMs": 5000})
        assert r_clk.json()["recvWindowMs"] == 5000

        unique_sig = f"sig-{uuid.uuid4().hex[:8]}"
        r_ord1 = client.post(
            "/api/executive/orders/submit",
            json={
                "symbol": "SOLUSDT",
                "side": "BUY",
                "signalKey": unique_sig,
                "qty": 2.5,
                "price": 214.8,
                "calibratedProb": 0.94,
                "orderType": "LIMIT_MAKER",
                "simulateImmediateFill": True,
            },
        )
        assert r_ord1.status_code == 200
        b1 = r_ord1.json()
        assert b1["idempotentReplay"] is False
        assert b1["fillsCount"] == 1
        if pg_up:
            assert b1["storageEngine"] == "PostgreSQL"

        # Submitting identical signalKey MUST NOT duplicate order or fill!
        r_ord2 = client.post(
            "/api/executive/orders/submit",
            json={
                "symbol": "SOLUSDT",
                "side": "BUY",
                "signalKey": unique_sig,
                "qty": 2.5,
                "price": 214.8,
                "calibratedProb": 0.94,
                "orderType": "LIMIT_MAKER",
                "simulateImmediateFill": True,
            },
        )
        assert r_ord2.status_code == 200
        assert r_ord2.json()["idempotentReplay"] is True
        assert r_ord2.json()["clientOrderId"] == b1["clientOrderId"]

        # 5. Rule #5: Submit an OPEN working order, then fire Kill Switch -> cancels open order & halts bots!
        open_sig = f"open-{uuid.uuid4().hex[:8]}"
        r_open = client.post(
            "/api/executive/orders/submit",
            json={
                "symbol": "BTCUSDT",
                "side": "BUY",
                "signalKey": open_sig,
                "qty": 0.05,
                "price": 96500.0,
                "calibratedProb": 0.93,
                "orderType": "WORKING_LIMIT",
                "simulateImmediateFill": False,
            },
        )
        open_cid = r_open.json()["clientOrderId"]
        assert r_open.json()["status"] == "OPEN"

        r_ks = client.post("/api/executive/kill-switch", json={"active": True, "reason": "E2E_EMERGENCY_TEST"})
        assert r_ks.status_code == 200
        ks_body = r_ks.json()
        assert ks_body["killSwitch"] is True
        assert ks_body["botsHalted"] is True
        assert ks_body["canceledOpenOrdersCount"] >= 1
        assert open_cid in ks_body["canceledClientOrderIds"]

        # New order while Kill Switch active MUST be blocked (HTTP 409)
        r_blocked_ord = client.post(
            "/api/executive/orders/submit",
            json={"symbol": "ETHUSDT", "side": "BUY", "signalKey": "after-ks", "qty": 1.0, "price": 3400.0},
        )
        assert r_blocked_ord.status_code == 409

        # Disarm Kill Switch after test
        client.post("/api/executive/kill-switch", json={"active": False, "reason": "TEST_CLEANUP"})

        # 6. Rule #11: Verify 14-day Binance Spot Testnet Calibration Table endpoint
        r_cal = client.get("/api/executive/testnet-calibration")
        assert r_cal.status_code == 200
        cal_json = r_cal.json()
        assert cal_json["mode"] == "BINANCE_SPOT_TESTNET_PAPER_SHADOW"
        assert cal_json["requiredDays"] == 14
        assert cal_json["liveTradingKeyForbidden"] is True
        assert [b["bin"] for b in cal_json["calibrationReport"]["bins"]] == ["75-80%", "80-85%", "85-90%", "90%+"]
