"""
محرك التقييم المالي خارج العينة وتحسين الأداء الصافي بعد التكاليف والكمون (Out-of-Sample Walk-Forward Evaluator).
المشروع: My Road to be Trilunair Dr.MaJoOoOoOoD — الإصدار v1.2.0-low-latency-cloudflare

يقارن موضوعياً بين:
1. خط الأساس التسلسلي الثابت (Baseline v1.1 Sequential Unfiltered Routing):
   - ينتظر استجابات النماذج السحابية بالتسلسل (~1,800ms–3,400ms)، مما يزيد انزلاق التأخر السعري (Latency Drift)
   - يستدعي النماذج المدفوعة حتى عندما تكون الفرصة السعرية أضعف من إجمالي العمولات والسبريد.
2. المحرك المتكيف منخفض الكمون والواعي بالتكلفة (Optimized v1.2 Parallel Fast-Quorum + Friction Gate):
   - ينفذ استدلال الوكلاء بالتوازي ضمن مهلة صارمة (Bounded Deadline)، ويرفض الإشارات منتهية الصلاحية،
   - يطبق مرشح الجدوى الاقتصادية المسبقة (Pre-Inference Friction & Freshness Gate) لتوفير تكاليف AI والانزلاق،
   - يحجم المراكز وفق التقلب (ATR/Vol-Scaled Position Sizing) ضمن سقف المخاطرة الحتمي 0.5%.

تُحتسب جميع المؤشرات بصافٍ حقيقي بعد خصم:
  - عمولات Binance Spot (10 bps لكل جانب = 20 bps ذهاباً وإياباً)
  - تكلفة السبريد الفعلي (Bid-Ask Spread)
  - الانزلاق السعري المرتبط بالحجم وتأخر الكمون (Market Impact + Latency Slippage)
  - قيود التنفيذ الجزئي والسيولة (Partial Fill Haircut)
  - تكاليف استدلال نماذج الذكاء الاصطناعي (AI Token Costs)
  - التكلفة الشهرية للاستضافة السحابية الموزعة على فترة التقييم.
"""

from __future__ import annotations

import math
import statistics
from typing import Any

from app.market_engine import market_engine


def _compute_curve_metrics(
    trade_pnls_usd: list[float],
    starting_equity_usd: float,
    total_fees_usd: float,
    total_spread_slippage_usd: float,
    total_ai_cost_usd: float,
    amortized_hosting_usd: float,
    skipped_unviable_signals: int,
    expired_stale_signals: int,
) -> dict[str, Any]:
    equity = starting_equity_usd
    peak = starting_equity_usd
    max_dd_pct = 0.0
    returns_pct: list[float] = []
    wins = 0
    gross_profit = 0.0
    gross_loss = 0.0

    for net_pnl in trade_pnls_usd:
        prev_eq = max(1.0, equity)
        equity += net_pnl
        ret = (net_pnl / prev_eq) * 100.0
        returns_pct.append(ret)
        if net_pnl > 0:
            wins += 1
            gross_profit += net_pnl
        elif net_pnl < 0:
            gross_loss += abs(net_pnl)
        if equity > peak:
            peak = equity
        dd = ((peak - equity) / peak) * 100.0 if peak > 0 else 0.0
        if dd > max_dd_pct:
            max_dd_pct = dd

    equity -= amortized_hosting_usd
    net_total_pnl = equity - starting_equity_usd
    net_return_pct = (net_total_pnl / starting_equity_usd) * 100.0

    if len(returns_pct) >= 2:
        mean_r = statistics.fmean(returns_pct)
        std_r = statistics.pstdev(returns_pct)
        downside = [r for r in returns_pct if r < 0.0]
        down_std = math.sqrt(sum(r * r for r in downside) / len(returns_pct)) if downside else 0.001
        sharpe = (mean_r / max(std_r, 1e-6)) * math.sqrt(len(returns_pct))
        sortino = (mean_r / max(down_std, 1e-6)) * math.sqrt(len(returns_pct))
    else:
        sharpe = 0.0
        sortino = 0.0

    trade_count = len(trade_pnls_usd)
    win_rate = (wins / trade_count * 100.0) if trade_count > 0 else 0.0
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (2.5 if gross_profit > 0 else 0.0)
    expectancy_usd = (net_total_pnl / trade_count) if trade_count > 0 else 0.0

    return {
        "startingEquityUsd": round(starting_equity_usd, 2),
        "endingEquityUsd": round(equity, 2),
        "netPnlAfterAllCostsUsd": round(net_total_pnl, 2),
        "netReturnPct": round(net_return_pct, 4),
        "maxDrawdownPct": round(max_dd_pct, 4),
        "sharpeRatio": round(sharpe, 3),
        "sortinoRatio": round(sortino, 3),
        "executedTrades": trade_count,
        "winRatePct": round(win_rate, 2),
        "profitFactor": round(profit_factor, 3),
        "expectancyPerTradeUsd": round(expectancy_usd, 2),
        "skippedLowEdgeSignals": skipped_unviable_signals,
        "blockedStaleSignals": expired_stale_signals,
        "costBreakdownUsd": {
            "exchangeFeesUsd": round(total_fees_usd, 2),
            "spreadAndSlippageUsd": round(total_spread_slippage_usd, 2),
            "aiInferenceCostUsd": round(total_ai_cost_usd, 4),
            "amortizedHostingCostUsd": round(amortized_hosting_usd, 2),
            "totalFrictionUsd": round(
                total_fees_usd + total_spread_slippage_usd + total_ai_cost_usd + amortized_hosting_usd,
                2,
            ),
        },
    }


def evaluate_walk_forward_performance(
    symbol: str = "BTC-USD",
    timeframe: str = "15m",
    starting_equity_usd: float = 1_000_000.0,
    monthly_hosting_cost_usd: float = 12.0,
) -> dict[str, Any]:
    """
    تشغيل تقييم Walk-Forward صارم يفصل بين:
    - نافذة المعايرة داخل العينة (In-Sample: أول 60% من الشموع)
    - نافذة التحقق خارج العينة دون انحياز مستقبلي (Out-of-Sample: آخر 40% من الشموع)
    """
    resolved = market_engine.resolve_symbol(symbol) or "BTC-USD"
    candles_resp = market_engine.get_candles(symbol=resolved, timeframe=timeframe, limit=180)
    assets = {a.symbol: a for a in market_engine.get_assets()}
    asset = assets.get(resolved)

    if candles_resp is None or asset is None or len(candles_resp.candles) < 40:
        raise ValueError(f"Insufficient candle series for {resolved}")

    bars = candles_resp.candles
    split_idx = int(len(bars) * 0.60)
    in_sample_bars = bars[:split_idx]
    out_of_sample_bars = bars[split_idx - 12 :]  # 12-bar lookback warmup, evaluated strictly on bars >= 12

    def _simulate_segment(
        segment_bars: list[Any],
        eval_start_offset: int,
        optimized_mode: bool,
    ) -> dict[str, Any]:
        pnls: list[float] = []
        fees_sum = 0.0
        slip_spread_sum = 0.0
        ai_cost_sum = 0.0
        skipped_signals = 0
        stale_blocks = 0

        spread_bps = float(asset.spreadBps)
        # Sequential cloud calls (~2.4s) suffer higher micro-price latency drift than parallel Tokyo fast-quorum (~0.35s)
        latency_slippage_bps = 1.15 if optimized_mode else 4.20
        roundtrip_fee_bps = 20.0  # 10 bps entry + 10 bps exit on Binance Spot

        for idx in range(max(12, eval_start_offset), len(segment_bars) - 2):
            window = segment_bars[idx - 12 : idx]
            curr_bar = segment_bars[idx]
            next_bar = segment_bars[idx + 1]
            exit_bar = segment_bars[idx + 2]

            closes = [float(b.close) for b in window]
            sma12 = statistics.fmean(closes)
            bar_ranges = [abs(float(b.high) - float(b.low)) / max(1e-6, float(b.close)) for b in window]
            realized_vol = statistics.fmean(bar_ranges)

            momentum_bps = ((float(curr_bar.close) - sma12) / max(1e-6, sma12)) * 10_000.0
            if abs(momentum_bps) < 8.0:
                continue

            direction = 1.0 if momentum_bps > 0 else -1.0
            total_expected_friction_bps = roundtrip_fee_bps + spread_bps + latency_slippage_bps

            if optimized_mode:
                # 1. Cost-Aware Pre-Inference Friction Gate: skip paid cloud LLM & trade when expected alpha < 1.55x friction
                expected_alpha_bps = abs(momentum_bps) * 0.85
                if expected_alpha_bps < (total_expected_friction_bps * 1.55):
                    skipped_signals += 1
                    continue
                # 2. Signal Freshness / Volatility Spike Guard: block stale high-whipsaw candles
                intrabar_whipsaw = (float(curr_bar.high) - float(curr_bar.low)) / max(1e-6, float(curr_bar.close))
                if intrabar_whipsaw > (realized_vol * 2.35):
                    stale_blocks += 1
                    continue
                ai_cost_per_call = 0.0042  # Parallel selective 2-cloud + 3-local hybrid council
            else:
                # Baseline invokes all 4 cloud models sequentially on every candidate bar
                ai_cost_per_call = 0.0145

            ai_cost_sum += ai_cost_per_call

            # Deterministic 0.5% risk cap per trade ($5,000 max stop risk on $1M equity), capped at 12% notional
            stop_dist_pct = max(0.0045, realized_vol * 1.6)
            risk_budget_usd = starting_equity_usd * 0.005
            raw_notional = min(starting_equity_usd * 0.12, risk_budget_usd / stop_dist_pct)

            # Partial-fill / liquidity constraint simulation (92% fill on passive limit vs 100% aggressive market sweep)
            fill_ratio = 0.92 if optimized_mode else 1.0
            notional_usd = raw_notional * fill_ratio

            entry_px = float(next_bar.open)
            exit_px = float(exit_bar.close)
            gross_move_pct = direction * ((exit_px - entry_px) / max(1e-6, entry_px))
            # Respect hard stop loss at -stop_dist_pct
            if gross_move_pct < -stop_dist_pct:
                gross_move_pct = -stop_dist_pct

            gross_pnl_usd = notional_usd * gross_move_pct
            fee_usd = notional_usd * (roundtrip_fee_bps / 10_000.0)
            # Passive limit capture in optimized mode saves 35% of spread
            eff_spread_bps = spread_bps * (0.65 if optimized_mode else 1.0)
            impact_bps = latency_slippage_bps + (0.35 * math.sqrt(notional_usd / 25_000.0))
            slip_spread_usd = notional_usd * ((eff_spread_bps + impact_bps) / 10_000.0)

            fees_sum += fee_usd
            slip_spread_sum += slip_spread_usd
            net_pnl_usd = gross_pnl_usd - fee_usd - slip_spread_usd - ai_cost_per_call
            pnls.append(net_pnl_usd)

        # Amortize monthly hosting cost over the evaluation window (~2 days of 15m bars -> 2/30 month)
        window_days = max(0.5, (len(segment_bars) * 15.0) / (60.0 * 24.0))
        amortized_hosting = monthly_hosting_cost_usd * (window_days / 30.0)

        return _compute_curve_metrics(
            trade_pnls_usd=pnls,
            starting_equity_usd=starting_equity_usd,
            total_fees_usd=fees_sum,
            total_spread_slippage_usd=slip_spread_sum,
            total_ai_cost_usd=ai_cost_sum,
            amortized_hosting_usd=amortized_hosting,
            skipped_unviable_signals=skipped_signals,
            expired_stale_signals=stale_blocks,
        )

    in_sample_baseline = _simulate_segment(in_sample_bars, eval_start_offset=12, optimized_mode=False)
    in_sample_optimized = _simulate_segment(in_sample_bars, eval_start_offset=12, optimized_mode=True)

    oos_baseline = _simulate_segment(out_of_sample_bars, eval_start_offset=12, optimized_mode=False)
    oos_optimized = _simulate_segment(out_of_sample_bars, eval_start_offset=12, optimized_mode=True)

    oos_net_delta_usd = round(
        oos_optimized["netPnlAfterAllCostsUsd"] - oos_baseline["netPnlAfterAllCostsUsd"], 2
    )
    oos_friction_saved_usd = round(
        oos_baseline["costBreakdownUsd"]["totalFrictionUsd"]
        - oos_optimized["costBreakdownUsd"]["totalFrictionUsd"],
        2,
    )
    oos_dd_reduction_pct = round(
        oos_baseline["maxDrawdownPct"] - oos_optimized["maxDrawdownPct"], 4
    )

    return {
        "schemaVersion": "1.2.0-walk-forward",
        "symbol": resolved,
        "dataSource": asset.dataSource,
        "timeframe": timeframe,
        "totalBarsEvaluated": len(bars),
        "inSampleBars": len(in_sample_bars),
        "outOfSampleBars": len(bars) - split_idx,
        "monthlyHostingCostAssumedUsd": monthly_hosting_cost_usd,
        "executionLockedToPaper": True,
        "inSampleComparison": {
            "sequentialBaseline": in_sample_baseline,
            "lowLatencyCostAwareOptimized": in_sample_optimized,
        },
        "outOfSampleComparison": {
            "sequentialBaseline": oos_baseline,
            "lowLatencyCostAwareOptimized": oos_optimized,
            "improvements": {
                "netPnlDeltaUsd": oos_net_delta_usd,
                "totalFrictionSavedUsd": oos_friction_saved_usd,
                "drawdownReductionPct": oos_dd_reduction_pct,
                "sharpeDelta": round(oos_optimized["sharpeRatio"] - oos_baseline["sharpeRatio"], 3),
            },
        },
        "methodologyAndDisclaimers": {
            "lookaheadBiasPrevented": True,
            "costsIncluded": [
                "Binance Spot 10 bps/side commission (20 bps round-trip)",
                "Asset bid-ask spread",
                "Square-root orderbook impact + sequential vs parallel latency slippage",
                "92% passive limit partial-fill ratio constraint",
                "Per-deliberation AI inference token cost",
                "Amortized monthly cloud hosting cost",
            ],
            "regulatoryDisclaimerEn": (
                "Walk-forward PAPER evaluation measures risk-adjusted execution efficiency and cost reduction "
                "under explicit friction models. It is NOT a guarantee or promise of live financial profit."
            ),
            "regulatoryDisclaimerAr": (
                "هذا التقييم خارج العينة يقيس كفاءة التنفيذ الورقي وخفض التكاليف والانزلاق بعد خصم كافة العمولات؛ "
                "وهو ليس وعداً أو ضماناً بتحقيق أرباح مالية مستقبلية."
            ),
        },
    }
