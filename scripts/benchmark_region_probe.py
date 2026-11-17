#!/usr/bin/env python3
"""
QUANTUM TRILUNAIR — Portable Cloud Region Latency & Stability Benchmark Probe
Release: v1.2.0-low-latency-cloudflare

Zero-lock-in, portable Python 3 stdlib probe script designed to run identically on:
  1. Candidate Cloud VMs in Tokyo (ap-northeast-1 / ap-tokyo-1), Osaka (ap-osaka-1),
     Singapore (ap-southeast-1 / ap-singapore-1), and Frankfurt (eu-central-1 / eu-frankfurt-1)
     using pure Python 3.10+ standard library (zero pip packages required).
  2. Local / Sandbox verification environments (explicitly tagged ANTIGRAVITY_DEV_SANDBOX_VM
     so non-regional runs are NEVER misrepresented as cloud region measurements).

Safety Guarantee:
  - Queries ONLY official unauthenticated Binance Spot public market-data endpoints:
      * https://data-api.binance.vision
      * https://api.binance.com
      * wss://data-stream.binance.vision
      * wss://stream.binance.com:9443
  - Never uses API keys, never touches account or order endpoints, never places orders.
"""

from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
import hashlib
import http.client
import json
import math
import os
import platform
import socket
import ssl
import statistics
import struct
import time
from typing import Any
from urllib.parse import urlparse


OFFICIAL_REST_TARGETS: list[dict[str, str]] = [
    {
        "id": "binance_vision_ping",
        "host": "data-api.binance.vision",
        "path": "/api/v3/ping",
        "purpose": "Pure HTTP RTT baseline",
    },
    {
        "id": "binance_vision_time",
        "host": "data-api.binance.vision",
        "path": "/api/v3/time",
        "purpose": "Exchange server clock delta & freshness",
    },
    {
        "id": "binance_vision_book_ticker",
        "host": "data-api.binance.vision",
        "path": "/api/v3/ticker/bookTicker?symbol=BTCUSDT",
        "purpose": "Top-of-book quote & spread snapshot",
    },
    {
        "id": "binance_vision_depth5",
        "host": "data-api.binance.vision",
        "path": "/api/v3/depth?symbol=BTCUSDT&limit=5",
        "purpose": "Orderbook L2 depth payload transfer",
    },
    {
        "id": "binance_api_primary_ping",
        "host": "api.binance.com",
        "path": "/api/v3/ping",
        "purpose": "Primary api.binance.com edge comparison",
    },
]

OFFICIAL_WS_TARGETS: list[dict[str, Any]] = [
    {
        "id": "binance_vision_ws_stream",
        "host": "data-stream.binance.vision",
        "port": 443,
        "path": "/stream?streams=btcusdt@bookTicker/btcusdt@trade",
    },
    {
        "id": "binance_primary_ws_9443",
        "host": "stream.binance.com",
        "port": 9443,
        "path": "/ws/btcusdt@bookTicker",
    },
]


def percentile(values: list[float], pct: float) -> float:
    """Compute exact linear-interpolated percentile (P50, P95, P99)."""
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return round(ordered[0], 3)
    rank = (pct / 100.0) * (len(ordered) - 1)
    low = int(math.floor(rank))
    high = int(math.ceil(rank))
    if low == high:
        return round(ordered[low], 3)
    weight = rank - low
    return round(ordered[low] * (1.0 - weight) + ordered[high] * weight, 3)


def summarize_series(values: list[float]) -> dict[str, float | int]:
    if not values:
        return {
            "count": 0,
            "minMs": 0.0,
            "meanMs": 0.0,
            "stdevMs": 0.0,
            "p50Ms": 0.0,
            "p95Ms": 0.0,
            "p99Ms": 0.0,
            "maxMs": 0.0,
        }
    return {
        "count": len(values),
        "minMs": round(min(values), 3),
        "meanMs": round(statistics.fmean(values), 3),
        "stdevMs": round(statistics.pstdev(values), 3) if len(values) > 1 else 0.0,
        "p50Ms": percentile(values, 50.0),
        "p95Ms": percentile(values, 95.0),
        "p99Ms": percentile(values, 99.0),
        "maxMs": round(max(values), 3),
    }


def build_ssl_context() -> ssl.SSLContext:
    for env_key in ("SSL_CERT_FILE", "REQUESTS_CA_BUNDLE", "CURL_CA_BUNDLE"):
        ca_path = os.getenv(env_key, "").strip()
        if ca_path and os.path.exists(ca_path):
            return ssl.create_default_context(cafile=ca_path)
    if os.path.exists("/etc/ssl/certs/ca-certificates.crt"):
        return ssl.create_default_context(cafile="/etc/ssl/certs/ca-certificates.crt")
    return ssl.create_default_context()


def detect_execution_environment(explicit_env: str | None, explicit_region: str | None) -> dict[str, Any]:
    proxy_url = (
        os.getenv("HTTPS_PROXY", "").strip()
        or os.getenv("https_proxy", "").strip()
        or os.getenv("HTTP_PROXY", "").strip()
        or os.getenv("http_proxy", "").strip()
    )
    hostname = socket.gethostname()
    is_antigravity_sandbox = (
        os.path.exists("/opt/antigravity")
        or os.getenv("USER", "") == "antigravity"
        or "agy-plugin-proxy" in proxy_url
    )

    if explicit_env:
        env_kind = explicit_env
    elif is_antigravity_sandbox:
        env_kind = "ANTIGRAVITY_DEV_SANDBOX_VM"
    else:
        env_kind = "CLOUD_REGIONAL_VM"

    region_id = explicit_region or (
        "sandbox-non-regional" if env_kind == "ANTIGRAVITY_DEV_SANDBOX_VM" else "unspecified-cloud-region"
    )
    return {
        "probeEnvironment": env_kind,
        "claimedRegion": region_id,
        "countsAsRegionalCloudEvidence": env_kind == "CLOUD_REGIONAL_VM" and not bool(proxy_url),
        "networkEgressMode": "HTTP_CONNECT_PROXY" if proxy_url else "DIRECT_REGIONAL_EGRESS",
        "proxyConfigured": bool(proxy_url),
        "hostname": hostname,
        "platform": platform.platform(),
        "pythonVersion": platform.python_version(),
    }


def open_tls_socket(
    host: str,
    port: int,
    ssl_ctx: ssl.SSLContext,
    timeout_sec: float,
) -> tuple[ssl.SSLSocket, dict[str, Any]]:
    """
    Establish TCP + TLS connection (directly on cloud VMs, or via HTTP CONNECT tunnel
    when HTTPS_PROXY is set in sandboxed environments) while timing each phase in nanoseconds.
    """
    proxy_raw = (
        os.getenv("HTTPS_PROXY", "").strip()
        or os.getenv("https_proxy", "").strip()
        or os.getenv("HTTP_PROXY", "").strip()
        or os.getenv("http_proxy", "").strip()
    )
    timings: dict[str, Any] = {
        "dnsResolutionMs": 0.0,
        "tcpConnectMs": 0.0,
        "tlsHandshakeMs": 0.0,
        "resolvedIp": "",
        "tlsVersion": "",
        "cipher": "",
    }

    if not proxy_raw:
        t0 = time.perf_counter_ns()
        addr_info = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
        t1 = time.perf_counter_ns()
        timings["dnsResolutionMs"] = round((t1 - t0) / 1_000_000.0, 3)
        family, socktype, proto, _, sockaddr = addr_info[0]
        timings["resolvedIp"] = str(sockaddr[0])

        raw_sock = socket.socket(family, socktype, proto)
        raw_sock.settimeout(timeout_sec)
        t2 = time.perf_counter_ns()
        raw_sock.connect(sockaddr)
        t3 = time.perf_counter_ns()
        timings["tcpConnectMs"] = round((t3 - t2) / 1_000_000.0, 3)
    else:
        parsed_proxy = urlparse(proxy_raw if "://" in proxy_raw else f"http://{proxy_raw}")
        p_host = parsed_proxy.hostname or "127.0.0.1"
        p_port = parsed_proxy.port or 8080

        # Still measure DNS resolution if local resolver answers, without failing if proxy-only DNS
        t0 = time.perf_counter_ns()
        try:
            infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
            timings["resolvedIp"] = str(infos[0][4][0])
        except Exception:
            timings["resolvedIp"] = f"proxy-resolved:{host}"
        t1 = time.perf_counter_ns()
        timings["dnsResolutionMs"] = round((t1 - t0) / 1_000_000.0, 3)

        raw_sock = socket.create_connection((p_host, p_port), timeout=timeout_sec)
        t2 = time.perf_counter_ns()
        connect_req = (
            f"CONNECT {host}:{port} HTTP/1.1\r\n"
            f"Host: {host}:{port}\r\n"
            f"Proxy-Connection: Keep-Alive\r\n\r\n"
        ).encode("ascii")
        raw_sock.sendall(connect_req)
        resp_buf = b""
        while b"\r\n\r\n" not in resp_buf:
            chunk = raw_sock.recv(4096)
            if not chunk:
                raw_sock.close()
                raise ConnectionError(f"Proxy closed socket during CONNECT to {host}:{port}")
            resp_buf += chunk
        status_line = resp_buf.split(b"\r\n", 1)[0].decode("latin1", errors="replace")
        if " 200 " not in status_line:
            raw_sock.close()
            raise ConnectionError(f"Proxy CONNECT rejected for {host}:{port}: {status_line}")
        t3 = time.perf_counter_ns()
        timings["tcpConnectMs"] = round((t3 - t2) / 1_000_000.0, 3)

    t4 = time.perf_counter_ns()
    tls_sock = ssl_ctx.wrap_socket(raw_sock, server_hostname=host, do_handshake_on_connect=False)
    tls_sock.do_handshake()
    t5 = time.perf_counter_ns()
    timings["tlsHandshakeMs"] = round((t5 - t4) / 1_000_000.0, 3)
    timings["tlsVersion"] = tls_sock.version() or ""
    cipher_info = tls_sock.cipher()
    timings["cipher"] = cipher_info[0] if cipher_info else ""
    return tls_sock, timings


def probe_rest_endpoints(
    samples: int,
    timeout_sec: float,
    ssl_ctx: ssl.SSLContext,
) -> dict[str, Any]:
    """Run cold-handshake and warm-keepalive REST measurements against official Binance endpoints."""
    dns_ms: list[float] = []
    tcp_ms: list[float] = []
    tls_ms: list[float] = []
    cold_rest_ms: list[float] = []
    warm_rest_ms: list[float] = []
    clock_deltas_ms: list[float] = []
    spreads_bps: list[float] = []
    resolved_ips: set[str] = set()
    cf_pops: set[str] = set()
    tls_versions: set[str] = set()

    total_attempts = 0
    error_count = 0
    timeout_count = 0
    rate_limit_429_count = 0
    endpoint_summaries: dict[str, dict[str, Any]] = {}

    # 1. Cold connection handshake probes (DNS + TCP + TLS + HTTP GET /api/v3/ping)
    cold_runs = max(3, min(samples, 6))
    for _ in range(cold_runs):
        total_attempts += 1
        tls_sock = None
        try:
            tls_sock, hs = open_tls_socket("data-api.binance.vision", 443, ssl_ctx, timeout_sec)
            dns_ms.append(float(hs["dnsResolutionMs"]))
            tcp_ms.append(float(hs["tcpConnectMs"]))
            tls_ms.append(float(hs["tlsHandshakeMs"]))
            if hs["resolvedIp"]:
                resolved_ips.add(str(hs["resolvedIp"]))
            if hs["tlsVersion"]:
                tls_versions.add(str(hs["tlsVersion"]))

            cold_conn = http.client.HTTPSConnection("data-api.binance.vision", 443, timeout=timeout_sec, context=ssl_ctx)
            cold_conn.sock = tls_sock
            r0 = time.perf_counter_ns()
            cold_conn.request(
                "GET",
                "/api/v3/ping",
                headers={
                    "Host": "data-api.binance.vision",
                    "User-Agent": "Trilunair-Region-Benchmark/1.2",
                    "Accept": "application/json",
                    "Connection": "close",
                },
            )
            c_resp = cold_conn.getresponse()
            _ = c_resp.read()
            r1 = time.perf_counter_ns()
            if c_resp.status == 200:
                cold_rest_ms.append(round((r1 - r0) / 1_000_000.0, 3))
            else:
                error_count += 1
            pop_hdr = c_resp.getheader("X-Amz-Cf-Pop")
            if pop_hdr:
                cf_pops.add(pop_hdr.strip())
            cold_conn.close()
        except socket.timeout:
            timeout_count += 1
            error_count += 1
        except Exception:
            error_count += 1
        finally:
            if tls_sock is not None:
                try:
                    tls_sock.close()
                except Exception:
                    pass

    # 2. Warm HTTP/1.1 Keep-Alive probes across all official REST targets
    for target in OFFICIAL_REST_TARGETS:
        t_latencies: list[float] = []
        t_errors = 0
        host = target["host"]
        path = target["path"]
        tls_sock = None
        try:
            tls_sock, hs = open_tls_socket(host, 443, ssl_ctx, timeout_sec)
            if hs["resolvedIp"]:
                resolved_ips.add(str(hs["resolvedIp"]))

            conn = http.client.HTTPSConnection(host, 443, timeout=timeout_sec, context=ssl_ctx)
            conn.sock = tls_sock

            per_target_samples = samples if target["id"] == "binance_vision_ping" else max(4, samples // 2)
            for _ in range(per_target_samples):
                total_attempts += 1
                local_before_ms = time.time() * 1000.0
                s0 = time.perf_counter_ns()
                conn.request(
                    "GET",
                    path,
                    headers={
                        "Host": host,
                        "User-Agent": "Trilunair-Region-Benchmark/1.2",
                        "Accept": "application/json",
                        "Connection": "keep-alive",
                    },
                )
                resp = conn.getresponse()
                body = resp.read()
                s1 = time.perf_counter_ns()
                local_after_ms = time.time() * 1000.0
                rtt_ms = round((s1 - s0) / 1_000_000.0, 3)

                pop = resp.getheader("X-Amz-Cf-Pop")
                if pop:
                    cf_pops.add(pop.strip())

                if resp.status in (429, 418):
                    rate_limit_429_count += 1
                    t_errors += 1
                    error_count += 1
                    break
                if resp.status != 200:
                    t_errors += 1
                    error_count += 1
                    continue

                t_latencies.append(rtt_ms)
                if host == "data-api.binance.vision":
                    warm_rest_ms.append(rtt_ms)

                if target["id"] == "binance_vision_time":
                    parsed = json.loads(body.decode("utf-8"))
                    server_time_ms = float(parsed.get("serverTime", 0.0))
                    if server_time_ms > 0:
                        midpoint_ms = (local_before_ms + local_after_ms) / 2.0
                        clock_deltas_ms.append(round(abs(midpoint_ms - server_time_ms), 3))
                elif target["id"] == "binance_vision_book_ticker":
                    parsed = json.loads(body.decode("utf-8"))
                    bid = float(parsed.get("bidPrice", 0.0))
                    ask = float(parsed.get("askPrice", 0.0))
                    if bid > 0 and ask >= bid:
                        mid = (bid + ask) / 2.0
                        spreads_bps.append(round(((ask - bid) / mid) * 10_000.0, 4))

                time.sleep(0.05)
            conn.close()
        except socket.timeout:
            timeout_count += 1
            error_count += 1
            t_errors += 1
        except Exception as exc:
            error_count += 1
            t_errors += 1
            endpoint_summaries[target["id"]] = {
                "host": host,
                "path": path,
                "reachable": False,
                "error": str(exc)[:180],
                "latency": summarize_series(t_latencies),
            }
            continue
        finally:
            if tls_sock is not None:
                try:
                    tls_sock.close()
                except Exception:
                    pass

        endpoint_summaries[target["id"]] = {
            "host": host,
            "path": path,
            "reachable": len(t_latencies) > 0,
            "errors": t_errors,
            "latency": summarize_series(t_latencies),
        }

    return {
        "dnsResolution": summarize_series(dns_ms),
        "tcpConnect": summarize_series(tcp_ms),
        "tlsHandshake": summarize_series(tls_ms),
        "coldRestPing": summarize_series(cold_rest_ms),
        "warmRestKeepAlive": summarize_series(warm_rest_ms),
        "marketDataClockDeltaMs": summarize_series(clock_deltas_ms),
        "observedBtcUsdtSpreadBps": summarize_series(spreads_bps),
        "routing": {
            "resolvedIps": sorted(resolved_ips),
            "ipCount": len(resolved_ips),
            "cloudFrontPops": sorted(cf_pops),
            "tlsVersions": sorted(tls_versions),
        },
        "reliability": {
            "totalRestAttempts": total_attempts,
            "errorCount": error_count,
            "timeoutCount": timeout_count,
            "rateLimit429Count": rate_limit_429_count,
            "errorRatePct": round((error_count / max(1, total_attempts)) * 100.0, 3),
            "timeoutRatePct": round((timeout_count / max(1, total_attempts)) * 100.0, 3),
            "sustainedAvailabilityPct": round(
                ((total_attempts - error_count) / max(1, total_attempts)) * 100.0, 3
            ),
        },
        "endpoints": endpoint_summaries,
    }


def _ws_read_exact(sock: ssl.SSLSocket, n: int) -> bytes:
    buf = bytearray()
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise EOFError("WebSocket stream closed")
        buf.extend(chunk)
    return bytes(buf)


def _ws_send_masked_frame(sock: ssl.SSLSocket, opcode: int, payload: bytes) -> None:
    mask_key = os.urandom(4)
    header = bytearray([0x80 | (opcode & 0x0F)])
    length = len(payload)
    if length < 126:
        header.append(0x80 | length)
    elif length < 65536:
        header.append(0x80 | 126)
        header.extend(struct.pack("!H", length))
    else:
        header.append(0x80 | 127)
        header.extend(struct.pack("!Q", length))
    header.extend(mask_key)
    masked = bytes(b ^ mask_key[i % 4] for i, b in enumerate(payload))
    sock.sendall(bytes(header) + masked)


def _ws_recv_frame(sock: ssl.SSLSocket) -> tuple[int, bytes]:
    first_two = _ws_read_exact(sock, 2)
    opcode = first_two[0] & 0x0F
    masked = bool(first_two[1] & 0x80)
    length = first_two[1] & 0x7F
    if length == 126:
        length = struct.unpack("!H", _ws_read_exact(sock, 2))[0]
    elif length == 127:
        length = struct.unpack("!Q", _ws_read_exact(sock, 8))[0]
    mask_key = _ws_read_exact(sock, 4) if masked else b""
    payload = _ws_read_exact(sock, length) if length > 0 else b""
    if masked:
        payload = bytes(b ^ mask_key[i % 4] for i, b in enumerate(payload))
    return opcode, payload


def probe_websocket_stream(
    duration_sec: float,
    timeout_sec: float,
    ssl_ctx: ssl.SSLContext,
) -> dict[str, Any]:
    """
    RFC 6455 TLS WebSocket probe against official Binance Spot public market streams.
    Measures WS handshake latency, message inter-arrival intervals, event freshness,
    micro-volatility trade burst rate, and reconnect count.
    """
    results: dict[str, Any] = {}
    for target in OFFICIAL_WS_TARGETS:
        host = str(target["host"])
        port = int(target["port"])
        path = str(target["path"])
        target_id = str(target["id"])

        ws_connect_ms = 0.0
        inter_arrival_ms: list[float] = []
        event_freshness_ms: list[float] = []
        trade_prices: list[float] = []
        messages_received = 0
        reconnects = 0
        connected = False
        error_msg: str | None = None

        deadline = time.monotonic() + (
            duration_sec if target_id == "binance_vision_ws_stream" else min(4.0, duration_sec)
        )
        attempts = 0

        while time.monotonic() < deadline and attempts < 3:
            attempts += 1
            tls_sock = None
            try:
                w0 = time.perf_counter_ns()
                tls_sock, _ = open_tls_socket(host, port, ssl_ctx, timeout_sec)
                ws_key = base64.b64encode(os.urandom(16)).decode("ascii")
                upgrade_req = (
                    f"GET {path} HTTP/1.1\r\n"
                    f"Host: {host}:{port}\r\n"
                    f"Upgrade: websocket\r\n"
                    f"Connection: Upgrade\r\n"
                    f"Sec-WebSocket-Key: {ws_key}\r\n"
                    f"Sec-WebSocket-Version: 13\r\n"
                    f"User-Agent: Trilunair-Region-Benchmark/1.2\r\n\r\n"
                ).encode("ascii")
                tls_sock.sendall(upgrade_req)

                resp_hdr = b""
                while b"\r\n\r\n" not in resp_hdr:
                    chunk = tls_sock.recv(4096)
                    if not chunk:
                        raise ConnectionError("EOF during WebSocket HTTP 101 upgrade")
                    resp_hdr += chunk
                w1 = time.perf_counter_ns()

                status_line = resp_hdr.split(b"\r\n", 1)[0].decode("latin1", errors="replace")
                if "101" not in status_line:
                    raise ConnectionError(f"WebSocket upgrade rejected: {status_line}")

                ws_connect_ms = round((w1 - w0) / 1_000_000.0, 3)
                connected = True
                if attempts > 1:
                    reconnects += 1

                tls_sock.settimeout(min(3.0, max(1.0, deadline - time.monotonic())))
                last_arrival_ns: int | None = None

                while time.monotonic() < deadline:
                    opcode, payload = _ws_recv_frame(tls_sock)
                    now_ns = time.perf_counter_ns()
                    now_epoch_ms = time.time() * 1000.0
                    if opcode == 0x9:  # PING -> PONG
                        _ws_send_masked_frame(tls_sock, 0xA, payload)
                        continue
                    if opcode == 0x8:  # CLOSE
                        break
                    if opcode == 0x1:  # TEXT JSON
                        messages_received += 1
                        if last_arrival_ns is not None:
                            inter_arrival_ms.append(round((now_ns - last_arrival_ns) / 1_000_000.0, 3))
                        last_arrival_ns = now_ns

                        try:
                            msg = json.loads(payload.decode("utf-8"))
                            data = msg.get("data", msg) if isinstance(msg, dict) else {}
                            event_ts = float(data.get("E", 0.0))
                            if event_ts > 0:
                                event_freshness_ms.append(round(max(0.0, now_epoch_ms - event_ts), 3))
                            if "p" in data:
                                trade_prices.append(float(data["p"]))
                        except Exception:
                            pass
                _ws_send_masked_frame(tls_sock, 0x8, b"")
                break
            except socket.timeout:
                # Normal if stream was quiet near deadline
                if messages_received > 0:
                    break
                error_msg = "WebSocket frame read timed out"
            except Exception as exc:
                error_msg = str(exc)[:180]
                time.sleep(0.25)
            finally:
                if tls_sock is not None:
                    try:
                        tls_sock.close()
                    except Exception:
                        pass

        micro_vol_bps = 0.0
        if len(trade_prices) >= 2 and min(trade_prices) > 0:
            micro_vol_bps = round(
                ((max(trade_prices) - min(trade_prices)) / statistics.fmean(trade_prices)) * 10_000.0,
                4,
            )

        results[target_id] = {
            "endpoint": f"wss://{host}:{port}{path}",
            "connected": connected,
            "wsConnectMs": ws_connect_ms,
            "messagesReceived": messages_received,
            "reconnectCount": reconnects,
            "interArrivalMs": summarize_series(inter_arrival_ms),
            "eventFreshnessAgeMs": summarize_series(event_freshness_ms),
            "volatilityObservation": {
                "tradePrintCount": len(trade_prices),
                "tradeRatePerSec": round(len(trade_prices) / max(0.5, duration_sec), 2),
                "realizedMicroRangeBps": micro_vol_bps,
            },
            "error": error_msg if not connected else None,
        }
    return results


def run_benchmark(
    region_label: str | None = None,
    provider_label: str = "unspecified",
    monthly_cost_usd: float = 0.0,
    samples: int = 16,
    ws_duration_sec: float = 8.0,
    timeout_sec: float = 6.0,
    explicit_env: str | None = None,
) -> dict[str, Any]:
    started_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    t_start = time.perf_counter()
    ssl_ctx = build_ssl_context()
    env_meta = detect_execution_environment(explicit_env=explicit_env, explicit_region=region_label)

    rest_report = probe_rest_endpoints(samples=samples, timeout_sec=timeout_sec, ssl_ctx=ssl_ctx)
    ws_report = probe_websocket_stream(duration_sec=ws_duration_sec, timeout_sec=timeout_sec, ssl_ctx=ssl_ctx)
    elapsed_sec = round(time.perf_counter() - t_start, 3)

    payload: dict[str, Any] = {
        "schemaVersion": "1.2.0",
        "startedAtUtc": started_iso,
        "completedAtUtc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "durationSeconds": elapsed_sec,
        "providerLabel": provider_label,
        "monthlyHostingCostUsd": round(monthly_cost_usd, 2),
        "environment": env_meta,
        "safetyStatement": (
            "Public unauthenticated Binance Spot market-data probe only. "
            "Zero API keys used; zero orders submitted; matching-engine internal topology not assumed."
        ),
        "restMetrics": rest_report,
        "webSocketMetrics": ws_report,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    payload["evidenceSha256"] = hashlib.sha256(canonical).hexdigest()
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(
        description="QUANTUM TRILUNAIR — Portable Binance Spot Public Region Latency Probe"
    )
    parser.add_argument("--region-label", default=None, help="e.g. ap-tokyo-1, ap-singapore-1, eu-frankfurt-1")
    parser.add_argument("--provider-label", default="local-verification", help="e.g. oci-always-free, aws-lightsail")
    parser.add_argument("--monthly-cost-usd", type=float, default=0.0, help="Monthly VM cost in USD")
    parser.add_argument("--samples", type=int, default=12, help="Number of warm REST samples (default: 12)")
    parser.add_argument("--ws-duration", type=float, default=6.0, help="WebSocket stream window in seconds")
    parser.add_argument("--timeout", type=float, default=6.0, help="Socket timeout in seconds")
    parser.add_argument("--environment-override", default=None, choices=["ANTIGRAVITY_DEV_SANDBOX_VM", "CLOUD_REGIONAL_VM"])
    parser.add_argument("--output", default="", help="Optional path to save JSON report")
    args = parser.parse_args()

    report = run_benchmark(
        region_label=args.region_label,
        provider_label=args.provider_label,
        monthly_cost_usd=args.monthly_cost_usd,
        samples=max(3, args.samples),
        ws_duration_sec=max(1.5, args.ws_duration),
        timeout_sec=max(2.0, args.timeout),
        explicit_env=args.environment_override,
    )

    encoded = json.dumps(report, indent=2, ensure_ascii=False)
    if args.output:
        out_dir = os.path.dirname(os.path.abspath(args.output))
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(encoded + "\n")
    print(encoded)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
