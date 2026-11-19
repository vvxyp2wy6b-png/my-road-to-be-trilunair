from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.quant_core import (
    BetaWinRate,
    ConsensusEngine,
    IsotonicCalibrator,
    NormalGamma,
    RiskState,
    compute_hwm_bots20_transfer,
    deflated_sharpe,
    detect_market_regime,
    graduated_exit_plan,
    iceberg_visible_qty,
    size_position,
    thompson_allocate,
    twap_slices,
    validate_spot_signal,
)


def test_consensus_only_predictors_and_isotonic_calibration() -> None:
    # Fix #2: AI4 and AI5 MUST be rejected if passed as predictors
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
    # Fix #3: Naked short in Spot is strictly blocked
    naked_sell = validate_spot_signal("SELL", holding_qty=0.0, step=0.001)
    assert naked_sell["executable"] is False
    assert naked_sell["action"] == "STAY_FLAT_NO_SHORT"

    # Closing owned inventory in Spot is allowed
    close_owned = validate_spot_signal("SELL", holding_qty=10.5, step=0.001)
    assert close_owned["executable"] is True
    assert close_owned["action"] == "EXIT_OWNED_SPOT"
    assert close_owned["qty_cap"] == 10.5

    # Fix #6: 20% bot cut ONLY net of fees AND strictly above High-Water-Mark
    loss_day = compute_hwm_bots20_transfer(-500.0, notional_usd=10_000.0, equity_before_trade=100_000.0, high_water_mark=100_000.0)
    assert loss_day["bots_20_usd"] == 0.0
    assert loss_day["new_hwm"] == 100_000.0

    # Recovery still below HWM -> zero 20% fee!
    below_hwm = compute_hwm_bots20_transfer(300.0, notional_usd=10_000.0, equity_before_trade=loss_day["new_equity"], high_water_mark=loss_day["new_hwm"])
    assert below_hwm["bots_20_usd"] == 0.0

    # New gain exceeding HWM -> 20% only on the portion above HWM!
    above_hwm = compute_hwm_bots20_transfer(500.0, notional_usd=10_000.0, equity_before_trade=below_hwm["new_equity"], high_water_mark=below_hwm["new_hwm"])
    assert above_hwm["above_hwm_gain"] > 0
    assert above_hwm["bots_20_usd"] == round(above_hwm["above_hwm_gain"] * 0.20, 2)


def test_kelly_veto_graduated_exits_thompson_and_dsr() -> None:
    rs_ok = RiskState(equity=100_000.0, day_start_equity=100_000.0, open_risk_usd=0.0)
    vetoed_low_conf = size_position(0.84, BetaWinRate(30, 10), 2.2, 100.0, 1.2, 0.01, rs_ok, "SOLUSDT", "crypto")
    assert vetoed_low_conf["approved"] is False
    assert vetoed_low_conf["veto_by"] == "AI5_CONFIDENCE_GATE"

    approved = size_position(0.93, BetaWinRate(30, 10), 2.2, 100.0, 1.2, 0.01, rs_ok, "SOLUSDT", "crypto")
    assert approved["approved"] is True
    assert approved["qty"] > 0

    rs_dd = RiskState(equity=96_500.0, day_start_equity=100_000.0, open_risk_usd=0.0)
    vetoed_dd = size_position(0.95, BetaWinRate(30, 10), 2.2, 100.0, 1.2, 0.01, rs_dd, "SOLUSDT", "crypto")
    assert vetoed_dd["approved"] is False
    assert vetoed_dd["veto_by"] == "AI4_DAILY_DD_VETO"

    exits = graduated_exit_plan(100.0, 10.0, 1.5, 0.01)
    assert round(exits["tp1"]["qty"] + exits["tp2"]["qty"] + exits["runner"]["qty"], 2) == 10.0

    bots = {f"AI{i}": NormalGamma() for i in range(1, 6)}
    for _ in range(40):
        bots["AI5"].update(0.01)
        bots["AI1"].update(-0.002)
    alloc = thompson_allocate(bots, seed=7)
    assert abs(sum(alloc.values()) - 1.0) < 1e-3
    assert alloc["AI5"] > alloc["AI1"]

    dsr = deflated_sharpe(sr=2.1, n_obs=120, skew=-0.2, kurt=3.5, n_trials=12, sr_var=0.25)
    assert 0.0 <= dsr <= 1.0

    reg = detect_market_regime([100 + i * 0.8 for i in range(25)], spread_bps=2.5, atr_pct=0.012)
    assert reg.tradable is True
    assert len(twap_slices(10.0, 4, 0.01, seed=1)) == 4
    assert iceberg_visible_qty(10.0, 10, 0.01) == 2.0


def test_executive_argon2id_and_separated_keys_endpoints() -> None:
    client = TestClient(app)
    r_app = client.post("/api/executive/auth/approve-password", json={"email": "test@trillionaire.sa", "password": "Strong#Pass99"})
    assert r_app.status_code == 200
    assert "Argon2id" in r_app.json()["kdf"]

    r_ok = client.post("/api/executive/auth/verify-password", json={"email": "test@trillionaire.sa", "password": "Strong#Pass99"})
    assert r_ok.json()["verified"] is True

    r_bad = client.post("/api/executive/auth/verify-password", json={"email": "test@trillionaire.sa", "password": "Wrong#Pass00"})
    assert r_bad.json()["verified"] is False

    r_same = client.post(
        "/api/executive/vault/validate-keys",
        json={"readOnlyKey": "SAME_KEY_12345", "tradeOnlyKey": "SAME_KEY_12345", "withdrawalsDisabled": True, "staticIpWhitelisted": True},
    )
    assert r_same.json()["approved"] is False

    r_sep = client.post(
        "/api/executive/vault/validate-keys",
        json={"readOnlyKey": "READ_KEY_12345", "tradeOnlyKey": "TRADE_KEY_67890", "withdrawalsDisabled": True, "staticIpWhitelisted": True},
    )
    assert r_sep.json()["approved"] is True

    r_qe = client.get("/api/executive/quant-engine")
    assert r_qe.status_code == 200
    assert len(r_qe.json()["evaluatedCandidates"]) == 6
