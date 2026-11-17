"""
محرك تقييم الأقاليم السحابية ومصفوفة قرار الاستضافة الموزونة (Cloud Region Benchmark & Hosting Decision Matrix).
المشروع: My Road to be Trilunair Dr.MaJoOoOoOoD — الإصدار v1.2.0-low-latency-cloudflare

يطبق هذا المحرك قواعد نزاهة القياس الصارمة (Measurement Integrity Rules):
1. لا يُصنّف أي قياس منفذ من بيئة التطوير (ANTIGRAVITY_DEV_SANDBOX_VM) على أنه قياس إقليمي لطوكيو أو سنغافورة أو فرانكفورت.
2. تُوسم القياسات الإقليمية غير المنفذة بعد بوضوح بـ NOT_MEASURED دون تلفيق أي أرقام كمون.
3. تُفصل المراجع الهندسية المنشورة عن البنية العامة لـ AWS/CloudFront عن القياسات الفعلية المباشرة.
4. تُطبق بوابة التأهيل الدنيا أولاً (استبعاد الاستضافة المجانية النائمة أو قواعد البيانات منتهية الصلاحية)،
   ثم تُحسب الأوزان المعتمدة (35% كمون بينانس، 20% استمرارية التشغيل، 15% العزل والأمان، 15% التكلفة الشهرية،
   10% متانة PostgreSQL، 5% بساطة النشر والصيانة).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


DECISION_WEIGHTS: dict[str, float] = {
    "binanceLatencyAndStability": 0.35,
    "continuousRuntimeReliability": 0.20,
    "securityAndIsolation": 0.15,
    "monthlyOperatingCost": 0.15,
    "postgresqlCompatibilityAndDurability": 0.10,
    "deploymentAndMaintenanceSimplicity": 0.05,
}

# كتالوج المرشحين الإقليميين وخيارات البنية التحتية (2026 Verified Specifications)
HOSTING_CANDIDATES_CATALOG: list[dict[str, Any]] = [
    {
        "optionId": "tokyo-oci-always-free-payg-guarded",
        "regionCode": "ap-tokyo-1",
        "regionNameEn": "Tokyo, Japan (Primary Candidate)",
        "regionNameAr": "طوكيو، اليابان (المرشح الأول المفضل)",
        "provider": "Oracle Cloud Infrastructure (OCI Always Free + PAYG Idle-Reclaim Guard) + Cloudflare Free",
        "computeSpec": "Ampere A1 ARM (VM.Standard.A1.Flex: 2 OCPU, 12 GB RAM, 200 GB Block Storage, 10 TB egress)",
        "databaseSpec": "Co-located Native PostgreSQL 16 on 127.0.0.1:5432 (<0.3ms loopback, encrypted daily backups)",
        "monthlyCostUsd": 0.00,
        "sleepsOnInactivity": False,
        "ephemeralDatabase": False,
        "publicInboundPortsOpen": False,
        "preliminaryExternalRefNoteEn": (
            "External AWS/CloudFront public infrastructure reference places Binance Spot Asia-Pacific market-data "
            "distribution hubs in Tokyo (ap-northeast-1); actual VM probe remains REQUIRED before final lock."
        ),
        "operationalCaveatEn": (
            "OCI Free Tier carries no formal SLA and Tokyo ARM capacity is often constrained unless account is "
            "upgraded to PAYG (remaining $0/mo within Always Free 2 OCPU / 12 GB limits) or failed over to Osaka (ap-osaka-1)."
        ),
        "staticCriterionScores": {
            "binanceLatencyAndStability_preliminary": 96.0,
            "continuousRuntimeReliability": 84.0,  # PAYG-guarded 24/7 VM, slightly below paid SLA tier due to no formal Free SLA
            "securityAndIsolation": 97.0,          # Isolated tenancy + Cloudflared outbound-only tunnel + loopback PG16
            "monthlyOperatingCost": 100.0,         # $0.00/month
            "postgresqlCompatibilityAndDurability": 94.0,  # 200 GB Block Volume + native PG16 + local/offsite encrypted dump
            "deploymentAndMaintenanceSimplicity": 86.0,    # Native systemd + uv + cloudflared; OCI ARM capacity check needed
        },
    },
    {
        "optionId": "tokyo-aws-lightsail-2gb-sla",
        "regionCode": "ap-northeast-1",
        "regionNameEn": "Tokyo, Japan (Deterministic Paid SLA Tier)",
        "regionNameAr": "طوكيو، اليابان (طبقة SLA مدفوعة منخفضة التكلفة)",
        "provider": "AWS Lightsail Tokyo (ap-northeast-1) + Cloudflare Free Pages/Zero Trust",
        "computeSpec": "Linux 2 vCPU, 2 GB RAM, 60 GB NVMe SSD, 3 TB transfer (same AWS region family as Tokyo CloudFront/API edge)",
        "databaseSpec": "Co-located Native PostgreSQL 16 on 127.0.0.1:5432 + Lightsail automated disk snapshots",
        "monthlyCostUsd": 12.00,
        "sleepsOnInactivity": False,
        "ephemeralDatabase": False,
        "publicInboundPortsOpen": False,
        "preliminaryExternalRefNoteEn": (
            "Direct intra-region AWS ap-northeast-1 connectivity to CloudFront/API edge in Tokyo; instant capacity availability."
        ),
        "operationalCaveatEn": (
            "Costs $12.00/month ($5.00/mo 1 GB plan exists, but 2 GB RAM is recommended for FastAPI + PostgreSQL 16 safety margin)."
        ),
        "staticCriterionScores": {
            "binanceLatencyAndStability_preliminary": 98.0,
            "continuousRuntimeReliability": 96.0,
            "securityAndIsolation": 97.0,
            "monthlyOperatingCost": 84.0,          # $12.00/mo low-cost predictable flat rate
            "postgresqlCompatibilityAndDurability": 95.0,
            "deploymentAndMaintenanceSimplicity": 96.0,    # Instant provisioning, zero ARM capacity wait
        },
    },
    {
        "optionId": "osaka-oci-always-free-japan-alt",
        "regionCode": "ap-osaka-1",
        "regionNameEn": "Osaka, Japan (Japan Capacity Fallback)",
        "regionNameAr": "أوساكا، اليابان (البديل الياباني المباشر عند امتلاء طوكيو)",
        "provider": "Oracle Cloud Always Free (ap-osaka-1) + Cloudflare Free",
        "computeSpec": "Ampere A1 ARM (2 OCPU, 12 GB RAM, 200 GB Block Storage)",
        "databaseSpec": "Co-located Native PostgreSQL 16 on 127.0.0.1:5432",
        "monthlyCostUsd": 0.00,
        "sleepsOnInactivity": False,
        "ephemeralDatabase": False,
        "publicInboundPortsOpen": False,
        "preliminaryExternalRefNoteEn": (
            "Located ~400 km from Tokyo (~7–11 ms optical fiber RTT to Tokyo edge) with higher OCI Free ARM availability."
        ),
        "operationalCaveatEn": "Slightly higher RTT to Tokyo edge than ap-tokyo-1; requires PAYG upgrade to prevent idle reclamation.",
        "staticCriterionScores": {
            "binanceLatencyAndStability_preliminary": 91.0,
            "continuousRuntimeReliability": 85.0,
            "securityAndIsolation": 97.0,
            "monthlyOperatingCost": 100.0,
            "postgresqlCompatibilityAndDurability": 94.0,
            "deploymentAndMaintenanceSimplicity": 90.0,
        },
    },
    {
        "optionId": "singapore-oci-or-lightsail",
        "regionCode": "ap-southeast-1",
        "regionNameEn": "Singapore (Secondary APAC Candidate)",
        "regionNameAr": "سنغافورة (المرشح الآسيوي الثانوي)",
        "provider": "AWS Lightsail Singapore ($12/mo) / Vultr SGP ($12/mo) / OCI ap-singapore-1 ($0/mo)",
        "computeSpec": "2 vCPU, 2 GB RAM Linux VPS (or OCI 2 OCPU / 12 GB ARM)",
        "databaseSpec": "Co-located Native PostgreSQL 16 on 127.0.0.1:5432",
        "monthlyCostUsd": 12.00,
        "sleepsOnInactivity": False,
        "ephemeralDatabase": False,
        "publicInboundPortsOpen": False,
        "preliminaryExternalRefNoteEn": (
            "Major APAC crypto routing hub, but submarine cable path to Tokyo adds ~65–75 ms round-trip vs Tokyo."
        ),
        "operationalCaveatEn": "Higher RTT to Tokyo-hosted Spot infrastructure than Japan regions; verify empirically via probe.",
        "staticCriterionScores": {
            "binanceLatencyAndStability_preliminary": 78.0,
            "continuousRuntimeReliability": 95.0,
            "securityAndIsolation": 96.0,
            "monthlyOperatingCost": 84.0,
            "postgresqlCompatibilityAndDurability": 95.0,
            "deploymentAndMaintenanceSimplicity": 95.0,
        },
    },
    {
        "optionId": "frankfurt-hetzner-arm-eu",
        "regionCode": "eu-central-1",
        "regionNameEn": "Frankfurt / Nuremberg, Germany (European Candidate)",
        "regionNameAr": "فرانكفورت، ألمانيا (المرشح الأوروبي للأقرب جغرافياً للشرق الأوسط)",
        "provider": "Hetzner Cloud Germany (CAX11 ARM / CX23 ~€5.49/mo) + Cloudflare Free",
        "computeSpec": "2 vCPU Ampere ARM / x86, 4 GB RAM, 40 GB NVMe SSD, 20 TB EU traffic",
        "databaseSpec": "Co-located Native PostgreSQL 16 on 127.0.0.1:5432",
        "monthlyCostUsd": 6.00,
        "sleepsOnInactivity": False,
        "ephemeralDatabase": False,
        "publicInboundPortsOpen": False,
        "preliminaryExternalRefNoteEn": (
            "Strong EU hardware value and closer browser RTT to Riyadh (~65–80 ms), but Cloudflare Pages already serves UI "
            "from Riyadh edge while Frankfurt->Tokyo Binance path incurs ~165–225 ms RTT."
        ),
        "operationalCaveatEn": "Hetzner has no Tokyo region; long-haul Europe-Asia path increases market-data staleness window.",
        "staticCriterionScores": {
            "binanceLatencyAndStability_preliminary": 58.0,
            "continuousRuntimeReliability": 96.0,
            "securityAndIsolation": 96.0,
            "monthlyOperatingCost": 92.0,
            "postgresqlCompatibilityAndDurability": 96.0,
            "deploymentAndMaintenanceSimplicity": 95.0,
        },
    },
    {
        "optionId": "sleeping-ephemeral-free-paas",
        "regionCode": "us-or-eu-shared",
        "regionNameEn": "Generic Sleeping Free PaaS (Render Free / Ephemeral DB)",
        "regionNameAr": "منصات الاستضافة المجانية النائمة (مرفوضة هندسياً)",
        "provider": "Render Free Web Service + 30-Day Expiring Free Postgres",
        "computeSpec": "0.1 shared CPU, 512 MB RAM, sleeps after 15 minutes idle",
        "databaseSpec": "Free PostgreSQL deleted/expired after 30 days (1 GB cap)",
        "monthlyCostUsd": 0.00,
        "sleepsOnInactivity": True,
        "ephemeralDatabase": True,
        "publicInboundPortsOpen": True,
        "preliminaryExternalRefNoteEn": "Fails mandatory 24/7 WebSocket & audit-log durability requirements.",
        "operationalCaveatEn": "DISQUALIFIED: Cold-start spin-down breaks Binance WS supervisor and 30-day DB expiry destroys financial audit logs.",
        "staticCriterionScores": {
            "binanceLatencyAndStability_preliminary": 20.0,
            "continuousRuntimeReliability": 10.0,
            "securityAndIsolation": 45.0,
            "monthlyOperatingCost": 100.0,
            "postgresqlCompatibilityAndDurability": 10.0,
            "deploymentAndMaintenanceSimplicity": 80.0,
        },
    },
]


def score_empirical_probe_latency(probe: dict[str, Any]) -> float:
    """
    Convert an actual CLOUD_REGIONAL_VM probe report into a 0..100 score for the 35%
    Binance Latency & Stability criterion.
    """
    rest = probe.get("restMetrics", {})
    warm = rest.get("warmRestKeepAlive", {})
    rel = rest.get("reliability", {})
    ws_map = probe.get("webSocketMetrics", {})
    ws_primary = ws_map.get("binance_vision_ws_stream", {})

    p50 = float(warm.get("p50Ms", 999.0) or 999.0)
    p99 = float(warm.get("p99Ms", 999.0) or 999.0)
    err_pct = float(rel.get("errorRatePct", 100.0))
    ws_ok = bool(ws_primary.get("connected", False))
    reconnects = int(ws_primary.get("reconnectCount", 0))

    # Latency curve: 1-5ms -> ~99, 15ms -> ~94, 50ms -> ~82, 100ms -> ~68, 200ms -> ~48
    p50_score = max(10.0, 100.0 - (p50 * 0.26))
    p99_penalty = min(25.0, max(0.0, (p99 - p50) * 0.12))
    err_penalty = min(50.0, err_pct * 5.0)
    ws_bonus = 4.0 if (ws_ok and reconnects == 0) else (-15.0 if not ws_ok else -4.0 * reconnects)
    return round(max(0.0, min(100.0, p50_score - p99_penalty - err_penalty + ws_bonus)), 2)


def _default_probes_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "data" / "regional_probes"


def _default_sandbox_probe_file() -> Path:
    return Path(__file__).resolve().parents[1] / "data" / "sandbox_probe_evidence.json"


def load_probe_artifacts(probes_dir: Path | None = None) -> tuple[dict[str, dict[str, Any]], dict[str, Any] | None]:
    """
    Load verified regional cloud probes (strictly requiring countsAsRegionalCloudEvidence == True)
    separately from any local ANTIGRAVITY_DEV_SANDBOX_VM probe.
    """
    p_dir = probes_dir or _default_probes_dir()
    regional_by_code: dict[str, dict[str, Any]] = {}
    sandbox_probe: dict[str, Any] | None = None

    sandbox_file = _default_sandbox_probe_file()
    if sandbox_file.is_file():
        try:
            sandbox_probe = json.loads(sandbox_file.read_text(encoding="utf-8"))
        except Exception:
            sandbox_probe = None

    if p_dir.is_dir():
        for path in sorted(p_dir.glob("*.json")):
            try:
                doc = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            env = doc.get("environment", {})
            if bool(env.get("countsAsRegionalCloudEvidence")):
                reg = str(env.get("claimedRegion", "")).strip()
                if reg:
                    regional_by_code[reg] = doc
            elif sandbox_probe is None:
                sandbox_probe = doc

    return regional_by_code, sandbox_probe


def evaluate_hosting_decision_matrix(probes_dir: Path | None = None) -> dict[str, Any]:
    """
    Compute the complete Phase 3 Weighted Hosting Decision Matrix while strictly enforcing
    Phase 2 & Phase 8 Measurement Integrity Rules.
    """
    regional_probes, sandbox_probe = load_probe_artifacts(probes_dir=probes_dir)

    region_aliases: dict[str, list[str]] = {
        "ap-tokyo-1": ["ap-tokyo-1", "ap-northeast-1", "tokyo", "nrt"],
        "ap-northeast-1": ["ap-northeast-1", "ap-tokyo-1", "tokyo", "nrt"],
        "ap-osaka-1": ["ap-osaka-1", "ap-northeast-3", "osaka", "kix"],
        "ap-southeast-1": ["ap-southeast-1", "ap-singapore-1", "singapore", "sin", "sgp"],
        "eu-central-1": ["eu-central-1", "eu-frankfurt-1", "frankfurt", "fra", "fsn1"],
    }

    evaluated_options: list[dict[str, Any]] = []
    measured_region_count = 0

    for item in HOSTING_CANDIDATES_CATALOG:
        qualified = (
            not item["sleepsOnInactivity"]
            and not item["ephemeralDatabase"]
            and not item["publicInboundPortsOpen"]
        )
        disqualification_reasons: list[str] = []
        if item["sleepsOnInactivity"]:
            disqualification_reasons.append("Sleeps on inactivity (breaks 24/7 WebSocket & market freshness supervisor)")
        if item["ephemeralDatabase"]:
            disqualification_reasons.append("Ephemeral/expiring database (violates immutable financial audit durability)")
        if item["publicInboundPortsOpen"]:
            disqualification_reasons.append("Exposes public inbound ports without Cloudflare Tunnel isolation")

        matched_probe: dict[str, Any] | None = None
        for alias in region_aliases.get(item["regionCode"], [item["regionCode"]]):
            if alias in regional_probes:
                matched_probe = regional_probes[alias]
                break

        scores = dict(item["staticCriterionScores"])
        if matched_probe is not None:
            measured_region_count += 1
            latency_score = score_empirical_probe_latency(matched_probe)
            measurement_status = "MEASURED_ON_REGIONAL_CLOUD_VM"
            warm = matched_probe.get("restMetrics", {}).get("warmRestKeepAlive", {})
            ws_main = matched_probe.get("webSocketMetrics", {}).get("binance_vision_ws_stream", {})
            measured_summary: dict[str, Any] = {
                "status": "MEASURED",
                "restP50Ms": warm.get("p50Ms"),
                "restP95Ms": warm.get("p95Ms"),
                "restP99Ms": warm.get("p99Ms"),
                "wsConnectMs": ws_main.get("wsConnectMs"),
                "wsMessagesReceived": ws_main.get("messagesReceived"),
                "cloudFrontPops": matched_probe.get("restMetrics", {}).get("routing", {}).get("cloudFrontPops", []),
                "evidenceSha256": matched_probe.get("evidenceSha256"),
            }
        else:
            latency_score = float(scores["binanceLatencyAndStability_preliminary"])
            measurement_status = "NOT_MEASURED"
            measured_summary = {
                "status": "NOT_MEASURED",
                "restP50Ms": None,
                "restP95Ms": None,
                "restP99Ms": None,
                "wsConnectMs": None,
                "noteEn": (
                    "NOT MEASURED from a live VM in this region yet. Run "
                    f"`python3 scripts/benchmark_region_probe.py --region-label {item['regionCode']} "
                    "--environment-override CLOUD_REGIONAL_VM` on a candidate VM to lock empirical numbers."
                ),
            }

        criterion_breakdown = {
            "binanceLatencyAndStability": latency_score,
            "continuousRuntimeReliability": float(scores["continuousRuntimeReliability"]),
            "securityAndIsolation": float(scores["securityAndIsolation"]),
            "monthlyOperatingCost": float(scores["monthlyOperatingCost"]),
            "postgresqlCompatibilityAndDurability": float(scores["postgresqlCompatibilityAndDurability"]),
            "deploymentAndMaintenanceSimplicity": float(scores["deploymentAndMaintenanceSimplicity"]),
        }

        weighted_total = round(
            sum(criterion_breakdown[k] * DECISION_WEIGHTS[k] for k in DECISION_WEIGHTS),
            2,
        )

        evaluated_options.append(
            {
                "optionId": item["optionId"],
                "regionCode": item["regionCode"],
                "regionNameEn": item["regionNameEn"],
                "regionNameAr": item["regionNameAr"],
                "provider": item["provider"],
                "computeSpec": item["computeSpec"],
                "databaseSpec": item["databaseSpec"],
                "monthlyCostUsd": item["monthlyCostUsd"],
                "qualified": qualified,
                "disqualificationReasons": disqualification_reasons,
                "regionalMeasurementStatus": measurement_status,
                "measuredProbeSummary": measured_summary,
                "preliminaryExternalRefNoteEn": item["preliminaryExternalRefNoteEn"],
                "operationalCaveatEn": item["operationalCaveatEn"],
                "criterionScores": criterion_breakdown,
                "weightedScore": weighted_total if qualified else 0.0,
            }
        )

    qualified_ranked = sorted(
        [opt for opt in evaluated_options if opt["qualified"]],
        key=lambda x: x["weightedScore"],
        reverse=True,
    )
    disqualified = [opt for opt in evaluated_options if not opt["qualified"]]
    all_empirically_measured = len(regional_probes) >= 3

    primary_pick = qualified_ranked[0]
    paid_sla_fallback = next(
        (opt for opt in qualified_ranked if opt["optionId"] == "tokyo-aws-lightsail-2gb-sla"),
        qualified_ranked[1] if len(qualified_ranked) > 1 else primary_pick,
    )

    sandbox_summary: dict[str, Any] | None = None
    if sandbox_probe is not None:
        s_warm = sandbox_probe.get("restMetrics", {}).get("warmRestKeepAlive", {})
        s_dns = sandbox_probe.get("restMetrics", {}).get("dnsResolution", {})
        s_tcp = sandbox_probe.get("restMetrics", {}).get("tcpConnect", {})
        s_tls = sandbox_probe.get("restMetrics", {}).get("tlsHandshake", {})
        s_rel = sandbox_probe.get("restMetrics", {}).get("reliability", {})
        s_ws = sandbox_probe.get("webSocketMetrics", {}).get("binance_vision_ws_stream", {})
        sandbox_summary = {
            "probeEnvironment": sandbox_probe.get("environment", {}).get(
                "probeEnvironment", "ANTIGRAVITY_DEV_SANDBOX_VM"
            ),
            "countsAsRegionalCloudEvidence": False,
            "networkEgressMode": sandbox_probe.get("environment", {}).get("networkEgressMode"),
            "startedAtUtc": sandbox_probe.get("startedAtUtc"),
            "dnsP50Ms": s_dns.get("p50Ms"),
            "tcpConnectP50Ms": s_tcp.get("p50Ms"),
            "tlsHandshakeP50Ms": s_tls.get("p50Ms"),
            "warmRestP50Ms": s_warm.get("p50Ms"),
            "warmRestP95Ms": s_warm.get("p95Ms"),
            "warmRestP99Ms": s_warm.get("p99Ms"),
            "errorRatePct": s_rel.get("errorRatePct"),
            "sustainedAvailabilityPct": s_rel.get("sustainedAvailabilityPct"),
            "cloudFrontPops": sandbox_probe.get("restMetrics", {}).get("routing", {}).get("cloudFrontPops", []),
            "wsConnected": s_ws.get("connected"),
            "wsConnectMs": s_ws.get("wsConnectMs"),
            "wsMessagesReceived": s_ws.get("messagesReceived"),
            "evidenceSha256": sandbox_probe.get("evidenceSha256"),
            "integrityDisclaimerEn": (
                "Measured live from the Antigravity development sandbox VM through agy-plugin-proxy to verify probe "
                "tooling and live Binance Spot public reachability. Strictly EXCLUDED from Tokyo/Singapore/Frankfurt regional claims."
            ),
        }

    return {
        "schemaVersion": "1.2.0-low-latency-cloudflare",
        "targetDomain": os.getenv("TRILUNAIR_PRIMARY_DOMAIN", "trilunair.medinsup.com"),
        "isolatedMedicalDomain": "medinsup.com",
        "weights": DECISION_WEIGHTS,
        "selectionStatus": (
            "EMPIRICALLY_CONFIRMED_BY_REGIONAL_PROBES"
            if all_empirically_measured
            else "PROVISIONAL_PENDING_REGIONAL_CLOUD_PROBES"
        ),
        "regionalProbesIngestedCount": len(regional_probes),
        "recommendedPrimaryOption": primary_pick,
        "recommendedPaidSlaFallbackOption": paid_sla_fallback,
        "rankedQualifiedOptions": qualified_ranked,
        "disqualifiedOptions": disqualified,
        "localSandboxVerificationRun": sandbox_summary,
        "measurementIntegrityPolicy": {
            "sandboxRunsExcludedFromRegionalClaims": True,
            "unmeasuredRegionsMarkedExplicitly": True,
            "matchingEngineInternalLocationAssumed": False,
            "publicMarketDataEquatedToOrderExecution": False,
            "paidCloudResourcesProvisionedWithoutApproval": False,
        },
    }
