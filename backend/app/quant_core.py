"""
quant_core.py — Pure Standard-Library Quantitative Core for HOW TO BE A TRILLIONAIRE
=====================================================================================
Zero external dependencies (Python 3.10+ stdlib only: math, random, time, uuid, dataclasses).

Implements all 8 modules of the Quantitative Engineering Upgrade Plan (v1.0):
1. Strict Role-Separated Consensus Engine (AI-1, AI-2, AI-3 predictors ONLY; online log-loss Hedge weights)
2. Isotonic Probability Calibrator (Pool-Adjacent-Violators Algorithm - PAVA, AI-5 >= 0.90 Gate)
3. Market Regime & Microstructure Shock Filter (Volatility / Spread / Choppiness Veto)
4. Bayesian Win-Rate (BetaWinRate) + Fractional Kelly & ATR Position Sizer + Risk Veto (AI-4)
5. Spot Long-Only Validator, High-Water-Mark (HWM) Net-of-Fees 20% Pool & Graduated Exit (Chandelier ATR)
6. Conjugate Normal-Gamma Thompson Sampling Bandit Allocator for the 20% Bot Pool
7. Deflated Sharpe Ratio (Bailey & López de Prado multiple-testing & non-Normality adjustment)
8. Tokyo Low-Latency Smart Execution (Post-Only LIMIT_MAKER -> IOC chaser, TWAP jitter slices, Iceberg)
"""

from __future__ import annotations

import hashlib
import math
import random
import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Protocol, Sequence, Tuple


# ----------------------------------------------------------------------------- utilities
def clip(x: float, lo: float, hi: float) -> float:
    """Clamp x into [lo, hi]."""
    return lo if x < lo else (hi if x > hi else x)


def round_step(qty: float, step: float) -> float:
    """Round quantity/price down to exchange LOT_SIZE / PRICE_FILTER step without float drift."""
    if step <= 0:
        return max(0.0, qty)
    if qty <= 0:
        return 0.0
    decimals = max(0, int(round(-math.log10(step))) + 2) if step < 1 else 0
    floored = math.floor((qty + 1e-12) / step) * step
    return round(max(0.0, floored), decimals if decimals > 0 else 8)


def new_client_order_id(prefix: str = "HTB") -> str:
    """Deterministic-format unique clientOrderId compatible with Binance ^[a-zA-Z0-9-_]{1,36}$."""
    ts_ms = int(time.time() * 1000) % 10_000_000_000
    rand_hex = uuid.uuid4().hex[:10]
    return f"{prefix}-{ts_ms}-{rand_hex}"[:36]


def _logit(p: float) -> float:
    pc = clip(p, 1e-6, 1.0 - 1e-6)
    return math.log(pc / (1.0 - pc))


def _sigmoid(z: float) -> float:
    if z >= 0:
        ez = math.exp(-min(z, 60.0))
        return 1.0 / (1.0 + ez)
    ez = math.exp(max(z, -60.0))
    return ez / (1.0 + ez)


def _norm_cdf(z: float) -> float:
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def _norm_ppf(p: float) -> float:
    """Rational Beasley-Springer-Moro / Acklam approximation for standard normal inverse CDF."""
    pc = clip(p, 1e-12, 1.0 - 1e-12)
    a = [-3.969683028665376e01, 2.209460984245205e02, -2.759285104469687e02,
         1.383577518672690e02, -3.066479806614716e01, 2.506628277459239e00]
    b = [-5.447609879822406e01, 1.615858368580409e02, -1.556989798598866e02,
         6.680131188771972e01, -1.328068155288572e01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e00,
         -2.549732539343734e00, 4.374664141464968e00, 2.938163982698783e00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e00,
         3.754408661907416e00]
    plow = 0.02425
    phigh = 1.0 - plow
    if pc < plow:
        q = math.sqrt(-2.0 * math.log(pc))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
               ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0)
    if pc <= phigh:
        q = pc - 0.5
        r = q * q
        return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / \
               (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1.0)
    q = math.sqrt(-2.0 * math.log(1.0 - pc))
    return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
            ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0)


# ----------------------------------------------------------------------------- 1. ConsensusEngine (AI-1..AI-3 ONLY)
@dataclass
class AgentStat:
    weight: float = 1.0
    cum_loss: float = 0.0
    brier_ema: float = 0.25
    samples: int = 0


class ConsensusEngine:
    """
    Combines ONLY true price-direction predictors (AI1: Orderbook/Delta, AI2: Multi-TF Price/Vol,
    AI3: Whale/Smart-Money Flow). AI4 (Risk Sizer & Veto) and AI5 (Calibrator & >=0.90 Gate) are
    strictly excluded from signal generation to prevent artificial confidence inflation.
    """

    def __init__(self, agent_ids: Sequence[str] = ("AI1", "AI2", "AI3"), eta: float = 0.12, decay: float = 0.992):
        if not agent_ids:
            raise ValueError("ConsensusEngine requires at least one predictor agent")
        for aid in agent_ids:
            if aid.upper().replace("-", "") in ("AI4", "AI5"):
                raise ValueError(f"{aid} is a Risk/Gate module and MUST NOT be included as a signal predictor")
        self.agent_ids: Tuple[str, ...] = tuple(agent_ids)
        self.eta = eta
        self.decay = decay
        w0 = 1.0 / len(self.agent_ids)
        self.stats: Dict[str, AgentStat] = {k: AgentStat(weight=w0) for k in self.agent_ids}

    def predict(self, probs: Dict[str, float]) -> float:
        """Log-odds (supra-Bayesian) weighted pooling of predictor probabilities."""
        total_w = 0.0
        z_sum = 0.0
        for k in self.agent_ids:
            if k in probs:
                w = self.stats[k].weight
                z_sum += w * _logit(probs[k])
                total_w += w
        if total_w <= 0:
            return 0.5
        return _sigmoid(z_sum / total_w)

    def update(self, probs: Dict[str, float], outcome: int) -> None:
        """Online multiplicative-weights (Hedge) update using proper Brier/Log scoring rule."""
        y = 1.0 if int(outcome) == 1 else 0.0
        raw_weights: Dict[str, float] = {}
        for k in self.agent_ids:
            st = self.stats[k]
            p = clip(probs.get(k, 0.5), 1e-4, 1.0 - 1e-4)
            brier = (p - y) ** 2
            logloss = -(y * math.log(p) + (1.0 - y) * math.log(1.0 - p))
            st.cum_loss = st.cum_loss * self.decay + (0.5 * brier + 0.5 * logloss)
            st.brier_ema = 0.95 * st.brier_ema + 0.05 * brier
            st.samples += 1
            raw_weights[k] = math.exp(-self.eta * st.cum_loss)
        s = sum(raw_weights.values()) or 1.0
        # Keep a 5% exploration floor per predictor so no agent permanently dies
        floor = 0.05 / len(self.agent_ids)
        normed = {k: max(floor, raw_weights[k] / s) for k in self.agent_ids}
        s2 = sum(normed.values())
        for k in self.agent_ids:
            self.stats[k].weight = normed[k] / s2


# ----------------------------------------------------------------------------- 2. IsotonicCalibrator (PAVA — AI-5)
class IsotonicCalibrator:
    """
    Out-of-sample monotonic probability calibrator via Pool-Adjacent-Violators Algorithm (PAVA).
    Ensures a model score mapped to >= 0.90 corresponds to ~90% empirical realization rate.
    """

    def __init__(self) -> None:
        self._xs: List[float] = [0.0, 1.0]
        self._ys: List[float] = [0.0, 1.0]
        self._fitted: bool = False

    def fit(self, probs: Sequence[float], outcomes: Sequence[int]) -> "IsotonicCalibrator":
        if len(probs) != len(outcomes) or len(probs) == 0:
            return self
        pairs = sorted((clip(float(p), 0.0, 1.0), float(int(y))) for p, y in zip(probs, outcomes))
        # Each block: [sum_y, weight_n, min_x, max_x]
        blocks: List[List[float]] = [[y, 1.0, x, x] for x, y in pairs]
        i = 0
        while i < len(blocks) - 1:
            mean_i = blocks[i][0] / blocks[i][1]
            mean_next = blocks[i + 1][0] / blocks[i + 1][1]
            if mean_i > mean_next + 1e-12:
                blocks[i][0] += blocks[i + 1][0]
                blocks[i][1] += blocks[i + 1][1]
                blocks[i][3] = blocks[i + 1][3]
                blocks.pop(i + 1)
                if i > 0:
                    i -= 1
            else:
                i += 1
        xs: List[float] = []
        ys: List[float] = []
        for sum_y, cnt, x_lo, x_hi in blocks:
            xs.append(0.5 * (x_lo + x_hi))
            # Laplace-smoothed block probability to prevent degenerate 1.000 on tiny N
            ys.append(clip((sum_y + 0.5) / (cnt + 1.0) if len(pairs) < 30 else sum_y / cnt, 0.01, 0.99))
        self._xs = xs
        self._ys = ys
        self._fitted = True
        return self

    def __call__(self, p: float) -> float:
        x = clip(float(p), 0.0, 1.0)
        if not self._fitted or not self._xs:
            return x
        if x <= self._xs[0]:
            return self._ys[0]
        if x >= self._xs[-1]:
            return self._ys[-1]
        for i in range(len(self._xs) - 1):
            x0, x1 = self._xs[i], self._xs[i + 1]
            if x0 <= x <= x1:
                if abs(x1 - x0) < 1e-12:
                    return self._ys[i]
                t = (x - x0) / (x1 - x0)
                return self._ys[i] + t * (self._ys[i + 1] - self._ys[i])
        return self._ys[-1]


# ----------------------------------------------------------------------------- 3. Regime Filter
@dataclass
class RegimeAssessment:
    tradable: bool
    regime: str  # "TREND_OK" | "CHOP_BLOCKED" | "VOL_SHOCK_BLOCKED" | "SPREAD_BLOCKED"
    reason: str
    efficiency_ratio: float


def detect_market_regime(
    closes: Sequence[float],
    spread_bps: float = 2.0,
    atr_pct: float = 0.012,
    max_spread_bps: float = 12.0,
    max_atr_pct: float = 0.055,
    min_efficiency: float = 0.24,
) -> RegimeAssessment:
    """Kaufman Efficiency Ratio + spread/volatility shock filter."""
    if spread_bps > max_spread_bps:
        return RegimeAssessment(False, "SPREAD_BLOCKED", f"Spread {spread_bps:.1f}bps > {max_spread_bps}bps", 0.0)
    if atr_pct > max_atr_pct:
        return RegimeAssessment(False, "VOL_SHOCK_BLOCKED", f"ATR shock {atr_pct*100:.2f}% > {max_atr_pct*100:.1f}%", 0.0)
    if len(closes) < 4:
        return RegimeAssessment(True, "TREND_OK", "Nominal liquidity regime", 0.5)
    net_move = abs(closes[-1] - closes[0])
    path_move = sum(abs(closes[i] - closes[i - 1]) for i in range(1, len(closes))) or 1e-9
    er = clip(net_move / path_move, 0.0, 1.0)
    if er < min_efficiency:
        return RegimeAssessment(False, "CHOP_BLOCKED", f"Choppy regime (ER={er:.2f} < {min_efficiency})", er)
    return RegimeAssessment(True, "TREND_OK", f"Clean directional regime (ER={er:.2f})", er)


# ----------------------------------------------------------------------------- 4. BetaWinRate, RiskState & Position Sizer (AI-4 Veto + AI-5 Gate)
@dataclass
class BetaWinRate:
    alpha: float = 30.0
    beta: float = 10.0

    @property
    def mean(self) -> float:
        return self.alpha / (self.alpha + self.beta)

    @property
    def conservative_p(self) -> float:
        """1-sigma conservative lower confidence bound on empirical win rate."""
        a, b = self.alpha, self.beta
        tot = a + b
        var = (a * b) / ((tot * tot) * (tot + 1.0))
        return clip(self.mean - math.sqrt(var), 0.05, 0.98)

    def update(self, won: bool) -> None:
        if won:
            self.alpha += 1.0
        else:
            self.beta += 1.0


@dataclass
class RiskState:
    equity: float
    day_start_equity: float
    open_risk_usd: float = 0.0
    high_water_mark: float = 0.0
    kill_switch: bool = False
    dd_half_size_threshold: float = 0.015    # 1.5% daily drawdown -> cut position size in half (0.5x)
    dd_stop_new_threshold: float = 0.025     # 2.5% daily drawdown -> stop all new trade entries
    max_daily_dd: float = 0.03               # 3.0% daily drawdown -> close everything & halt
    max_open_heat: float = 0.045             # Max 4.5% simultaneous open risk across all positions
    max_single_notional_pct: float = 0.08    # Hard cap per position (8% of equity)

    def __post_init__(self) -> None:
        if self.high_water_mark <= 0:
            self.high_water_mark = max(self.equity, self.day_start_equity)

    @property
    def daily_drawdown_pct(self) -> float:
        if self.day_start_equity <= 0:
            return 0.0
        return max(0.0, (self.day_start_equity - self.equity) / self.day_start_equity)


def evaluate_daily_drawdown_breaker(risk_state: RiskState) -> Dict[str, Any]:
    """
    3-Tier Daily Drawdown Circuit Breaker (Phase 1 Mandatory Rule #6):
    - dd < 1.5%        : NORMAL (1.0x position size, new trades allowed, close_all=False)
    - 1.5% <= dd < 2.5%: DD_1_5_HALF_SIZE (0.5x position size, new trades allowed, close_all=False)
    - 2.5% <= dd < 3.0%: DD_2_5_STOP_NEW (0.0x size, new trades blocked, close_all=False)
    - dd >= 3.0%       : DD_3_0_CLOSE_ALL (0.0x size, new trades blocked, close_all=True — liquidate all!)
    """
    if risk_state.kill_switch:
        return {
            "tier": "KILL_SWITCH_ACTIVE",
            "drawdown_pct": round(risk_state.daily_drawdown_pct * 100.0, 3),
            "size_multiplier": 0.0,
            "allow_new_trades": False,
            "close_all_positions": True,
            "reason": "Emergency Kill Switch is active — all open orders canceled & bots halted",
        }
    dd = risk_state.daily_drawdown_pct
    if dd >= risk_state.max_daily_dd - 1e-9:
        return {
            "tier": "DD_3_0_CLOSE_ALL",
            "drawdown_pct": round(dd * 100.0, 3),
            "size_multiplier": 0.0,
            "allow_new_trades": False,
            "close_all_positions": True,
            "reason": f"Daily drawdown {dd*100:.2f}% >= {risk_state.max_daily_dd*100:.1f}%: CLOSE ALL POSITIONS & HALT",
        }
    if dd >= risk_state.dd_stop_new_threshold - 1e-9:
        return {
            "tier": "DD_2_5_STOP_NEW",
            "drawdown_pct": round(dd * 100.0, 3),
            "size_multiplier": 0.0,
            "allow_new_trades": False,
            "close_all_positions": False,
            "reason": f"Daily drawdown {dd*100:.2f}% >= {risk_state.dd_stop_new_threshold*100:.1f}%: STOP NEW TRADES",
        }
    if dd >= risk_state.dd_half_size_threshold - 1e-9:
        return {
            "tier": "DD_1_5_HALF_SIZE",
            "drawdown_pct": round(dd * 100.0, 3),
            "size_multiplier": 0.5,
            "allow_new_trades": True,
            "close_all_positions": False,
            "reason": f"Daily drawdown {dd*100:.2f}% >= {risk_state.dd_half_size_threshold*100:.1f}%: HALF POSITION SIZE (0.5x)",
        }
    return {
        "tier": "NORMAL",
        "drawdown_pct": round(dd * 100.0, 3),
        "size_multiplier": 1.0,
        "allow_new_trades": True,
        "close_all_positions": False,
        "reason": "Nominal daily drawdown (<1.5%)",
    }


def size_position(
    cal_prob: float,
    win_rate: BetaWinRate,
    reward_risk: float,
    price: float,
    atr: float,
    step: float,
    risk_state: RiskState,
    symbol: str,
    asset_class: str = "crypto",
    min_calibrated_gate: float = 0.75,
    kelly_fraction_cap: float = 0.25,
    atr_stop_mult: float = 1.8,
    fee_bps_roundtrip: float = 15.0,
) -> Dict[str, Any]:
    """
    AI-4 Risk Sizer & Veto + AI-5 >=0.75 (75%) Calibrated Confidence Gate + 3-Tier Daily Drawdown Breaker.
    - 1.5% DD -> 0.5x size
    - 2.5% DD -> stop new trades
    - 3.0% DD -> close all positions & halt
    """
    dd_breaker = evaluate_daily_drawdown_breaker(risk_state)
    if risk_state.kill_switch:
        return {
            "approved": False,
            "veto_by": "KILL_SWITCH",
            "dd_tier": dd_breaker["tier"],
            "close_all_positions": True,
            "size_multiplier": 0.0,
            "reason": dd_breaker["reason"],
            "qty": 0.0,
            "notional_usd": 0.0,
        }
    if not dd_breaker["allow_new_trades"]:
        veto_code = "AI4_DAILY_DD_VETO" if dd_breaker["close_all_positions"] else "AI4_DAILY_DD_2_5_STOP_NEW"
        return {
            "approved": False,
            "veto_by": veto_code,
            "dd_tier": dd_breaker["tier"],
            "close_all_positions": dd_breaker["close_all_positions"],
            "size_multiplier": 0.0,
            "reason": dd_breaker["reason"],
            "qty": 0.0,
            "notional_usd": 0.0,
        }
    if cal_prob < min_calibrated_gate:
        return {
            "approved": False,
            "veto_by": "AI5_CONFIDENCE_GATE",
            "dd_tier": dd_breaker["tier"],
            "close_all_positions": False,
            "size_multiplier": dd_breaker["size_multiplier"],
            "reason": f"Calibrated confidence {cal_prob*100:.1f}% < {min_calibrated_gate*100:.0f}% gate",
            "qty": 0.0,
            "notional_usd": 0.0,
        }
    if price <= 0 or atr <= 0 or reward_risk <= 0:
        return {"approved": False, "veto_by": "AI4_INVALID_INPUT", "dd_tier": dd_breaker["tier"], "close_all_positions": False, "size_multiplier": 0.0, "reason": "Non-positive price/ATR/RR", "qty": 0.0, "notional_usd": 0.0}

    # Blend calibrated signal probability with conservative empirical Beta posterior
    p_eff = clip(0.65 * cal_prob + 0.35 * win_rate.conservative_p, 0.01, 0.99)
    # Net reward-to-risk after roundtrip Maker/Taker fees
    stop_dist = atr * atr_stop_mult
    stop_pct = stop_dist / price
    fee_pct = fee_bps_roundtrip / 10_000.0
    b_net = max(0.1, (reward_risk * stop_pct - fee_pct) / (stop_pct + fee_pct))

    full_kelly = p_eff - (1.0 - p_eff) / b_net
    if full_kelly <= 0:
        return {"approved": False, "veto_by": "AI4_NEGATIVE_EDGE", "dd_tier": dd_breaker["tier"], "close_all_positions": False, "size_multiplier": 0.0, "reason": "Net-of-fee Kelly edge <= 0", "qty": 0.0, "notional_usd": 0.0}

    # Fractional Kelly risk budget (capped at 1.25% equity risk per trade & remaining portfolio heat)
    rem_heat = max(0.0, risk_state.max_open_heat * risk_state.equity - risk_state.open_risk_usd)
    if rem_heat <= 10.0:
        return {"approved": False, "veto_by": "AI4_HEAT_CAP", "dd_tier": dd_breaker["tier"], "close_all_positions": False, "size_multiplier": 0.0, "reason": "Max open portfolio risk heat reached", "qty": 0.0, "notional_usd": 0.0}

    frac_kelly_risk_pct = clip(full_kelly * kelly_fraction_cap * 0.04, 0.002, 0.0125)
    risk_budget_usd = min(risk_state.equity * frac_kelly_risk_pct, rem_heat)

    raw_notional = risk_budget_usd / max(stop_pct + fee_pct, 1e-4)
    asset_cap = risk_state.max_single_notional_pct if asset_class == "crypto" else risk_state.max_single_notional_pct * 0.85
    base_capped_notional = min(raw_notional, risk_state.equity * asset_cap)
    # Apply 3-Tier Daily Drawdown multiplier (1.0x normal, 0.5x when 1.5% <= DD < 2.5%)
    sized_notional = base_capped_notional * dd_breaker["size_multiplier"]
    qty = round_step(sized_notional / price, step)
    notional_usd = round(qty * price, 2)

    if qty <= 0 or notional_usd < 10.0:
        return {"approved": False, "veto_by": "AI4_MIN_NOTIONAL", "dd_tier": dd_breaker["tier"], "close_all_positions": False, "size_multiplier": dd_breaker["size_multiplier"], "reason": "Position below exchange minNotional", "qty": 0.0, "notional_usd": 0.0}

    actual_risk_usd = round(notional_usd * (stop_pct + fee_pct), 2)
    dec = 4 if price < 10 else 2
    return {
        "approved": True,
        "veto_by": None,
        "dd_tier": dd_breaker["tier"],
        "close_all_positions": False,
        "size_multiplier": dd_breaker["size_multiplier"],
        "symbol": symbol,
        "asset_class": asset_class,
        "qty": qty,
        "notional_usd": notional_usd,
        "portfolio_pct": round((notional_usd / risk_state.equity) * 100.0, 2),
        "risk_usd": actual_risk_usd,
        "kelly_fraction": round(full_kelly * kelly_fraction_cap * dd_breaker["size_multiplier"], 4),
        "stop_price": round(price - stop_dist, dec),
        "tp1_price": round(price + stop_dist * 1.2, dec),
        "tp2_price": round(price + stop_dist * reward_risk, dec),
        "chandelier_atr_mult": 2.2,
    }


# ----------------------------------------------------------------------------- 5. Spot Long-Only, HWM 20% Pool & Graduated Exits
def validate_spot_signal(side: str, holding_qty: float, step: float = 1e-6) -> Dict[str, Any]:
    """
    Mandatory Fix #3: Binance Spot is strictly Long-Only (no naked shorting).
    A SELL signal means EXIT owned Spot inventory if holding_qty > 0, otherwise STAY_FLAT.
    """
    s = side.upper()
    if s == "BUY":
        return {"executable": True, "action": "OPEN_SPOT_LONG", "qty_cap": None, "reason": "Spot Long entry permitted"}
    if s == "SELL":
        avail = round_step(holding_qty, step)
        if avail > 0:
            return {"executable": True, "action": "EXIT_OWNED_SPOT", "qty_cap": avail, "reason": "Closing owned Spot inventory"}
        return {
            "executable": False,
            "action": "STAY_FLAT_NO_SHORT",
            "qty_cap": 0.0,
            "reason": "Spot market is Long-Only: no owned inventory to exit; naked shorting prohibited.",
        }
    return {"executable": False, "action": "HOLD", "qty_cap": 0.0, "reason": "Neutral signal"}


def compute_hwm_bots20_transfer(
    gross_pnl_usd: float,
    notional_usd: float,
    equity_before_trade: float,
    high_water_mark: float,
    fee_rate: float = 0.00075,
    bots_share: float = 0.20,
) -> Dict[str, float]:
    """
    Mandatory Fix #6: 20% autonomous bot allocation is computed ONLY on realized net profit
    AFTER exchange fees AND strictly above the daily High-Water-Mark (zero transfer on losing days
    or while recovering below HWM).
    """
    fees_usd = round(abs(notional_usd) * 2.0 * fee_rate, 2)  # Entry + Exit roundtrip fee reserve
    net_pnl_usd = round(gross_pnl_usd - fees_usd, 2)
    equity_after_net = round(equity_before_trade + net_pnl_usd, 2)

    hwm_prev = max(high_water_mark, 0.0)
    above_hwm_gain = max(0.0, equity_after_net - hwm_prev)
    bots_20_usd = round(above_hwm_gain * bots_share, 2) if net_pnl_usd > 0 and above_hwm_gain > 0 else 0.0
    owner_net_usd = round(net_pnl_usd - bots_20_usd, 2)
    new_equity = round(equity_before_trade + owner_net_usd, 2)
    new_hwm = max(hwm_prev, new_equity)
    return {
        "gross_pnl_usd": round(gross_pnl_usd, 2),
        "fees_usd": fees_usd,
        "net_pnl_usd": net_pnl_usd,
        "above_hwm_gain": round(above_hwm_gain, 2),
        "bots_20_usd": bots_20_usd,
        "owner_net_usd": owner_net_usd,
        "new_equity": new_equity,
        "new_hwm": round(new_hwm, 2),
    }


def graduated_exit_plan(entry_price: float, qty: float, atr: float, step: float, highest_since_entry: Optional[float] = None) -> Dict[str, Any]:
    """3-tranche Partial Take-Profit + Chandelier ATR Trailing Stop."""
    q1 = round_step(qty * 0.40, step)
    q2 = round_step(qty * 0.35, step)
    q3 = round_step(max(0.0, qty - q1 - q2), step)
    stop_dist = 1.8 * atr
    peak = max(entry_price, highest_since_entry or entry_price)
    chandelier_sl = peak - 2.2 * atr
    dec = 4 if entry_price < 10 else 2
    return {
        "tp1": {"qty": q1, "share": "40%", "price": round(entry_price + 1.2 * stop_dist, dec), "rule": "Move SL to Breakeven + Fees"},
        "tp2": {"qty": q2, "share": "35%", "price": round(entry_price + 2.2 * stop_dist, dec), "rule": "Lock +1.0R Profit"},
        "runner": {"qty": q3, "share": "25%", "chandelier_stop": round(chandelier_sl, dec), "rule": "Chandelier 2.2x ATR Trail"},
    }


# ----------------------------------------------------------------------------- 6. NormalGamma & Thompson Sampling Bandit (20% Pool)
@dataclass
class NormalGamma:
    """Conjugate Normal-Gamma posterior for unknown mean mu and precision tau of bot returns."""
    mu0: float = 0.0
    kappa0: float = 1.0
    alpha0: float = 2.0
    beta0: float = 1e-4

    def update(self, x: float) -> None:
        val = float(x)
        k_new = self.kappa0 + 1.0
        mu_new = (self.kappa0 * self.mu0 + val) / k_new
        a_new = self.alpha0 + 0.5
        b_new = self.beta0 + 0.5 * (self.kappa0 / k_new) * ((val - self.mu0) ** 2)
        self.mu0, self.kappa0, self.alpha0, self.beta0 = mu_new, k_new, a_new, max(b_new, 1e-12)

    def sample_sharpe_like(self, rng: random.Random) -> float:
        """Draw (mu, tau) from Normal-Gamma posterior and return risk-adjusted drift mu * sqrt(tau)."""
        tau = rng.gammavariate(self.alpha0, 1.0 / self.beta0)
        tau = max(tau, 1e-12)
        sigma_mu = 1.0 / math.sqrt(self.kappa0 * tau)
        mu_draw = rng.gauss(self.mu0, sigma_mu)
        return mu_draw * math.sqrt(tau)


def thompson_allocate(
    posteriors: Dict[str, NormalGamma],
    bounds: Optional[Dict[str, Tuple[float, float]]] = None,
    seed: Optional[int] = None,
    n_draws: int = 250,
    min_floor: float = 0.05,
    max_cap: float = 0.55,
) -> Dict[str, float]:
    """
    Monte-Carlo Thompson Sampling allocation across autonomous bots in the 20% pool.
    Automatically shifts capital from slower/noisy bots to highest risk-adjusted performers.
    """
    keys = list(posteriors.keys())
    if not keys:
        return {}
    rng = random.Random(seed)
    wins = {k: 0.0 for k in keys}
    for _ in range(max(1, n_draws)):
        scores = {k: posteriors[k].sample_sharpe_like(rng) for k in keys}
        winner = max(keys, key=lambda k: scores[k])
        wins[winner] += 1.0

    raw = {k: wins[k] / n_draws for k in keys}
    bmap = bounds or {}
    clipped: Dict[str, float] = {}
    for k in keys:
        lo, hi = bmap.get(k, (min_floor, max_cap))
        clipped[k] = clip(raw[k], lo, hi)
    total = sum(clipped.values()) or 1.0
    return {k: clipped[k] / total for k in keys}


# ----------------------------------------------------------------------------- 7. Deflated Sharpe Ratio (Bailey & López de Prado)
def deflated_sharpe(sr: float, n_obs: int, skew: float, kurt: float, n_trials: int, sr_var: float) -> float:
    """
    Deflated Sharpe Ratio (DSR): probability in [0, 1] that observed Sharpe `sr` is statistically
    genuine after adjusting for sample length `n_obs`, skewness `skew`, kurtosis `kurt` (3=Normal),
    and selection bias across `n_trials` backtested configurations with cross-trial variance `sr_var`.
    """
    if n_obs <= 2:
        return 0.0
    euler_gamma = 0.5772156649015329
    trials = max(1, int(n_trials))
    if trials == 1 or sr_var <= 0:
        sr_star = 0.0
    else:
        z1 = _norm_ppf(1.0 - 1.0 / trials)
        z2 = _norm_ppf(1.0 - 1.0 / (trials * math.e))
        sr_star = math.sqrt(max(0.0, sr_var)) * ((1.0 - euler_gamma) * z1 + euler_gamma * z2)

    denom_sq = 1.0 - skew * sr + ((kurt - 1.0) / 4.0) * (sr * sr)
    denom = math.sqrt(max(1e-9, denom_sq))
    z_dsr = ((sr - sr_star) * math.sqrt(n_obs - 1.0)) / denom
    return clip(_norm_cdf(z_dsr), 0.0, 1.0)


# ----------------------------------------------------------------------------- 8. Tokyo Low-Latency Smart Execution (Maker Chaser, TWAP, Iceberg)
class AsyncOrderClient(Protocol):
    async def new_order(self, **kwargs: Any) -> Dict[str, Any]: ...
    async def get_order(self, **kwargs: Any) -> Dict[str, Any]: ...
    async def cancel_order(self, **kwargs: Any) -> Dict[str, Any]: ...
    async def best_bid_ask(self, symbol: str) -> Tuple[float, float]: ...


async def execute_maker_chaser(
    cli: AsyncOrderClient,
    symbol: str,
    side: str,
    qty: float,
    limit_price: float,
    step: float,
    tick_size: float = 0.01,
    max_chase: int = 3,
    allow_ioc_sweep: bool = True,
) -> Dict[str, Any]:
    """
    Tokyo (~1.5ms) zero-slippage execution loop:
    1. Posts LIMIT_MAKER (Post-Only) at top-of-book to capture 0% / low maker fee and zero spread cost.
    2. Re-pegs up to `max_chase` times if book moves away without crossing limit_price.
    3. Sweeps any unfilled remainder via bounded LIMIT IOC at `limit_price` if `allow_ioc_sweep`.
    """
    s = side.upper()
    filled = 0.0
    cid = new_client_order_id()
    for _ in range(max(1, max_chase)):
        rem = round_step(qty - filled, step)
        if rem <= 0:
            return {"status": "FILLED_MAKER", "qty": filled, "cid": cid}
        bid, ask = await cli.best_bid_ask(symbol)
        peg = min(limit_price, ask - tick_size) if s == "BUY" else max(limit_price, bid + tick_size)
        peg = round_step(peg, tick_size)
        cid = new_client_order_id()
        try:
            res = await cli.new_order(
                symbol=symbol,
                side=s,
                type="LIMIT_MAKER",
                quantity=rem,
                price=peg,
                newClientOrderId=cid,
            )
            exec_q = float(res.get("executedQty", 0.0))
            filled = round_step(filled + exec_q, step)
            if filled >= round_step(qty, step):
                return {"status": "FILLED_MAKER", "qty": filled, "cid": cid}
            await cli.cancel_order(symbol=symbol, origClientOrderId=cid)
        except Exception:
            # LIMIT_MAKER rejected because book crossed -> proceed to next peg or bounded IOC
            pass

    if allow_ioc_sweep and filled < round_step(qty, step):
        rest = round_step(qty - filled, step)
        await cli.new_order(symbol=symbol, side=s, type="LIMIT", timeInForce="IOC",
                            quantity=rest, price=limit_price, newClientOrderId=new_client_order_id())
    return {"status": "PARTIAL_OR_DONE", "qty": filled, "cid": cid}


def twap_slices(total_qty: float, n: int, step: float, jitter: float = 0.2, seed: Optional[int] = None) -> List[float]:
    rng = random.Random(seed)
    raw = [1 + rng.uniform(-jitter, jitter) for _ in range(n)]
    s = sum(raw)
    sl = [round_step(total_qty * r / s, step) for r in raw]
    sl[-1] = round_step(total_qty - sum(sl[:-1]), step)
    return sl


def iceberg_visible_qty(total_qty: float, parts_limit: int, step: float, min_parts: int = 5) -> float:
    """Binance ICEBERG_PARTS filter: ceil(qty/icebergQty) <= parts_limit (read from exchangeInfo)."""
    parts = clip(min_parts, 1, parts_limit)
    return max(step, round_step(total_qty / parts, step))


# ----------------------------------------------------------------------------- 9. Idempotent clientOrderId, Clock Sync (recvWindow) & 14-Day Calibration Table
def make_idempotent_client_order_id(symbol: str, side: str, signal_key: str, prefix: str = "htb") -> str:
    """
    Phase 1 Rule #9: Deterministic idempotent newClientOrderId (<= 36 chars, ^[A-Za-z0-9-_]+$).
    Submitting the same (symbol, side, signal_key) twice always generates the exact same ID,
    preventing duplicate fills on network retries.
    """
    sym_clean = re.sub(r"[^A-Z0-9]", "", symbol.upper())[:8] or "ASSET"
    s_clean = "B" if side.upper() == "BUY" else "S"
    digest = hashlib.sha256(f"{sym_clean}:{side.upper()}:{signal_key.strip()}".encode("utf-8")).hexdigest()[:18]
    cid = f"{prefix}-{sym_clean}-{s_clean}-{digest}"
    return cid[:36]


@dataclass
class ClockSyncGuard:
    """
    Phase 1 Rule #9: Synchronizes local monotonic/wall clock against Binance `/api/v3/time`
    and enforces strict `recvWindow` (default 5000ms, max 10000ms) and drift bounds.
    """
    recv_window_ms: int = 5000
    max_allowed_drift_ms: int = 1000
    offset_ms: int = 0
    last_sync_epoch_ms: int = 0
    last_rtt_ms: float = 1.5

    def sync_with_server_time(self, server_time_ms: int, local_send_ms: Optional[int] = None, local_recv_ms: Optional[int] = None) -> Dict[str, Any]:
        now_ms = int(time.time() * 1000)
        send_ms = local_send_ms if local_send_ms is not None else now_ms
        recv_ms = local_recv_ms if local_recv_ms is not None else now_ms
        rtt = max(0, recv_ms - send_ms)
        midpoint = send_ms + (rtt // 2)
        self.offset_ms = int(server_time_ms - midpoint)
        self.last_sync_epoch_ms = recv_ms
        self.last_rtt_ms = float(rtt)
        return {
            "offsetMs": self.offset_ms,
            "rttMs": self.last_rtt_ms,
            "recvWindowMs": self._sanitized_recv_window(),
            "withinDriftLimit": abs(self.offset_ms) <= self.max_allowed_drift_ms,
        }

    def _sanitized_recv_window(self) -> int:
        return int(clip(self.recv_window_ms, 1000, 10000))

    def build_signed_timing_params(self, local_now_ms: Optional[int] = None) -> Dict[str, Any]:
        now_ms = int(time.time() * 1000) if local_now_ms is None else int(local_now_ms)
        drift_ok = abs(self.offset_ms) <= self.max_allowed_drift_ms
        if not drift_ok:
            raise ValueError(f"Clock drift {self.offset_ms}ms exceeds safety limit ±{self.max_allowed_drift_ms}ms")
        return {
            "timestamp": now_ms + self.offset_ms,
            "recvWindow": self._sanitized_recv_window(),
            "clockOffsetMs": self.offset_ms,
        }


CALIBRATION_BINS_SPEC: Tuple[Tuple[str, float, float], ...] = (
    ("75-80%", 0.75, 0.80),
    ("80-85%", 0.80, 0.85),
    ("85-90%", 0.85, 0.90),
    ("90%+", 0.90, 1.0001),
)


def compute_calibration_table(records: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Phase 3 Rule #11: Evaluates 14-day Binance Spot Testnet Paper/Shadow outcomes across
    the 4 required confidence bins: (75-80%, 80-85%, 85-90%, 90%+), comparing expected
    calibrated confidence against empirical win rate and computing Expected Calibration Error (ECE).
    """
    rows: List[Dict[str, Any]] = []
    total_n = 0
    weighted_gap = 0.0

    for label, lo, hi in CALIBRATION_BINS_SPEC:
        bucket = [
            r for r in records
            if lo <= float(r.get("calibrated_prob", 0.0)) < hi
        ]
        n = len(bucket)
        if n > 0:
            exp_pct = round((sum(float(r["calibrated_prob"]) for r in bucket) / n) * 100.0, 2)
            wins = sum(1 for r in bucket if bool(r.get("won")))
            act_pct = round((wins / n) * 100.0, 2)
            gap_pct = round(act_pct - exp_pct, 2)
            net_pnl = round(sum(float(r.get("net_pnl_usd", 0.0)) for r in bucket), 2)
            aligned = abs(gap_pct) <= 8.0
            total_n += n
            weighted_gap += n * abs(gap_pct)
        else:
            exp_pct = round(((lo + min(hi, 1.0)) / 2.0) * 100.0, 2)
            wins = 0
            act_pct = 0.0
            gap_pct = 0.0
            net_pnl = 0.0
            aligned = True

        rows.append({
            "bin": label,
            "rangeMinPct": round(lo * 100.0, 1),
            "rangeMaxPct": round(min(hi, 1.0) * 100.0, 1),
            "tradesCount": n,
            "winsCount": wins,
            "expectedConfidencePct": exp_pct,
            "actualWinRatePct": act_pct,
            "calibrationGapPct": gap_pct,
            "netPnlUsd": net_pnl,
            "status": "ALIGNED" if aligned else "RECALIBRATE_REQUIRED",
        })

    ece_pct = round(weighted_gap / total_n, 2) if total_n > 0 else 0.0
    return {
        "totalEvaluatedTrades": total_n,
        "expectedCalibrationErrorPct": ece_pct,
        "bins": rows,
    }


# ----------------------------------------------------------------------------- self-test
if __name__ == "__main__":
    ce = ConsensusEngine(["AI1", "AI2", "AI3"])
    rng = random.Random(1)
    for _ in range(500):
        y = int(rng.random() < 0.55)
        ce.update({"AI1": clip(0.5 + (0.2 if y else -0.2) + rng.gauss(0, .2), .01, .99),
                   "AI2": rng.random(), "AI3": 0.5}, y)
    print("weights", {k: round(v.weight, 3) for k, v in ce.stats.items()})
    cal = IsotonicCalibrator().fit([0.1, 0.4, 0.35, 0.8, 0.9], [0, 0, 1, 1, 1])
    print("cal(0.85)=", round(cal(0.85), 3))
    rs = RiskState(equity=100_000, day_start_equity=100_000, open_risk_usd=0)
    print("size", size_position(0.92, BetaWinRate(30, 10), 2.0, 100.0, 1.2, 0.5, rs, "SOLUSDT", "crypto"))
    posts = {f"AI{i}": NormalGamma() for i in range(1, 6)}
    for _ in range(100):
        for i, k in enumerate(posts):
            posts[k].update(rng.gauss(0.001 * i, 0.01))
    print("alloc", {k: round(v, 3) for k, v in thompson_allocate(posts, {}, seed=7).items()})
    print("DSR", round(deflated_sharpe(0.15, 500, -0.3, 5.0, 20, 0.002), 3))
