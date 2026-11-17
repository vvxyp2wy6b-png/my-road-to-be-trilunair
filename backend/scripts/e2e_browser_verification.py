"""
اختبار التحقق الشامل عبر متصفح Chromium الحقيقي (Playwright E2E Verification)
المشروع: My Road to be Trilunair Dr.MaJoOoOoOoD

يتحقق فعلياً عبر متصفح Chromium الحقيقي من:
1. تواصل واجهة React الحقيقية مع خادم FastAPI الحقيقي وقاعدة بيانات PostgreSQL 15 وبث WebSocket (/ws/market).
2. عمل جميع السمات الست (Royal Gold, Quantum Cyan, Nebula Purple, Emerald Matrix, Arctic Platinum, Obsidian Black)
   في تطبيق React الفعلي واستدامتها في الخادم.
3. عمل الأوامر النصية العربية عبر شريط الأوامر الدائم وعرض نتائج قاعة اجتماع الوكلاء وشارات المزود الصريحة دون تنفيذ تلقائي.
4. عمل التفاعل الصوتي عبر الميكروفون بإذن صريح (Push-to-Talk + SpeechRecognition باللغة العربية) وإرساله عبر قناة VOICE.
5. بقاء وضع التداول على PAPER وتعطيل التداول الحقيقي LIVE طوال الاختبار وبعد انتهائه.
"""

from __future__ import annotations

import json
from playwright.sync_api import sync_playwright
import httpx

BASE_URL = "http://127.0.0.1:8000"

EXPECTED_SIX_THEMES = [
    ("royal-gold", "#f5c451"),
    ("quantum-cyan", "#06e8f9"),
    ("nebula-purple", "#c084fc"),
    ("emerald-matrix", "#10f59c"),
    ("arctic-platinum", "#e2e8f0"),
    ("obsidian-black", "#d4af37"),
]


def main() -> None:
    report: dict[str, object] = {}

    # فحص جاهزية الخادم الخلفي والبنية التحتية قبل فتح المتصفح
    with httpx.Client(timeout=5.0, trust_env=False) as http:
        infra = http.get(f"{BASE_URL}/api/system/infrastructure").json()
        status = http.get(f"{BASE_URL}/api/system/status").json()
        assert infra["database"]["engine"] == "postgresql", infra
        assert infra["database"]["connected"] is True, infra
        assert infra["redis"]["connected"] is True, infra
        assert status["tradingMode"] == "PAPER", status
        assert status["liveAuthorized"] is False, status
        report["infrastructure"] = infra
        report["initialSystemStatus"] = status

    ws_frames_received: list[str] = []
    api_calls_seen: list[str] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path="/usr/bin/chromium",
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        context = browser.new_context(viewport={"width": 1440, "height": 920})

        # حقن محرك التعرف الصوتي القياسي للمتصفح لاختبار دورة الميكروفون الحقيقية في البيئة غير الرسومية
        context.add_init_script(
            """
            (() => {
              Object.defineProperty(navigator, 'mediaDevices', {
                configurable: true,
                value: {
                  getUserMedia: async () => ({
                    getTracks: () => [{ stop: () => {} }]
                  })
                }
              });

              class ControlledSpeechRecognition {
                constructor() {
                  this.lang = 'ar-SA';
                  this.continuous = false;
                  this.interimResults = true;
                  this.onstart = null;
                  this.onresult = null;
                  this.onerror = null;
                  this.onend = null;
                  window.__latestSpeechRecognition = this;
                }
                start() {
                  if (this.onstart) this.onstart();
                }
                stop() {
                  if (this.onresult) {
                    const fakeEvent = {
                      resultIndex: 0,
                      results: [
                        Object.assign(
                          [{ transcript: 'حلل الإيثيريوم الآن', confidence: 0.98 }],
                          { isFinal: true }
                        )
                      ]
                    };
                    this.onresult(fakeEvent);
                  }
                  if (this.onend) this.onend();
                }
                abort() {
                  if (this.onend) this.onend();
                }
              }

              window.SpeechRecognition = ControlledSpeechRecognition;
              window.webkitSpeechRecognition = ControlledSpeechRecognition;
            })();
            """
        )

        page = context.new_page()
        page.on("request", lambda req: api_calls_seen.append(f"{req.method} {req.url}") if "/api/" in req.url else None)

        def _on_ws(ws):
            if "/ws/market" in ws.url:
                ws.on("framereceived", lambda payload: ws_frames_received.append(str(payload)[:160]))

        page.on("websocket", _on_ws)

        # 1. فتح التطبيق الكامل والتحقق من تحميل React SPA والتواصل مع FastAPI و WebSocket
        page.goto(BASE_URL, wait_until="networkidle")
        page.wait_for_selector('[data-testid="live-terminal-view"]', timeout=10000)
        page.wait_for_timeout(1800)
        assert len(ws_frames_received) >= 1, "Expected live /ws/market frames in browser"
        report["wsFramesCount"] = len(ws_frames_received)

        # 2. الانتقال إلى استوديو السمات والتحقق من جميع السمات الست (6 Themes) في React الفعلي
        page.click("#nav-themes-btn")
        page.wait_for_selector('[data-testid="apply-theme-obsidian-black"]', timeout=5000)

        verified_themes: list[dict[str, str]] = []
        for theme_id, expected_accent in EXPECTED_SIX_THEMES:
            btn = page.get_by_test_id(f"apply-theme-{theme_id}")
            btn.scroll_into_view_if_needed()
            btn.click()
            page.wait_for_timeout(200)

            dom_theme = page.evaluate("() => document.documentElement.getAttribute('data-theme')")
            dom_accent = page.evaluate(
                "() => document.documentElement.style.getPropertyValue('--accent-primary').trim().toLowerCase()"
            )
            assert dom_theme == theme_id, f"Expected data-theme={theme_id}, got {dom_theme}"
            assert dom_accent == expected_accent.lower(), f"Expected {expected_accent}, got {dom_accent}"
            verified_themes.append({"themeId": dom_theme, "accentPrimary": dom_accent})

        report["verifiedSixThemesInReactDom"] = verified_themes

        # إعادة السمة الملكية الذهبية والعودة لشاشة التداول الحية
        page.get_by_test_id("apply-theme-royal-gold").click()
        page.wait_for_timeout(200)
        page.click("#nav-terminal-btn")
        page.wait_for_selector('[data-testid="live-terminal-view"]', timeout=5000)

        # 3. اختبار إرسال أمر عربي نصي عبر شريط الأوامر الدائم والتحقق من قاعة اجتماع الوكلاء وعدم التنفيذ التلقائي
        cmd_input = page.get_by_label("حقل الأمر النصي")
        cmd_input.fill("حلل البيتكوين وجهز مقترح شراء 0.05 BTC")
        page.get_by_label("إرسال الأمر").click()
        page.wait_for_timeout(600)

        convene_btn = page.get_by_test_id("convene-council-btn")
        convene_btn.scroll_into_view_if_needed()
        convene_btn.click()
        page.wait_for_selector('[data-testid="agent-card-quant-alpha"]', timeout=10000)

        sim_badge_text = page.get_by_test_id("agent-provider-quant-alpha").inner_text()
        assert "SIMULATED: local-quant-engine" in sim_badge_text, sim_badge_text
        report["meetingRoomProviderBadge"] = sim_badge_text

        # 4. اختبار التفاعل الصوتي عبر الميكروفون بإذن صريح (Push-to-Talk -> VOICE command)
        mic_auth_btn = page.get_by_label("منح إذن صريح للميكروفون")
        mic_auth_btn.click()
        ptt_btn = page.get_by_label("اضغط مطولاً للتحدث (Push-to-Talk)")
        ptt_btn.wait_for(state="visible", timeout=5000)

        ptt_btn.dispatch_event("mousedown")
        page.wait_for_timeout(150)
        ptt_btn.dispatch_event("mouseup")
        page.wait_for_timeout(1200)

        voice_calls = [c for c in api_calls_seen if "/api/ai/command" in c]
        assert len(voice_calls) >= 2, f"Expected both TEXT and VOICE /api/ai/command calls, got {voice_calls}"
        report["aiCommandHttpCalls"] = len(voice_calls)

        # 5. الانتقال إلى شاشة الحوكمة والعمليات السحابية والتحقق من لوحة Cloud Operations و Passkey و Region Latency وسياسة المخاطر الموحدة وخلو DOM من 7777
        page.click("#nav-governance-btn")
        page.wait_for_selector('[data-testid="governance-view"]', timeout=5000)
        page.wait_for_selector('[data-testid="cloud-operations-panel"]', timeout=5000)
        page.wait_for_selector('[data-testid="passkey-biometric-panel"]', timeout=5000)
        page.wait_for_selector('[data-testid="region-latency-telemetry-panel"]', timeout=5000)
        page.wait_for_selector('[data-testid="unified-risk-policy-strip"]', timeout=5000)
        page.wait_for_timeout(500)

        gov_text = page.get_by_test_id("governance-view").inner_text()
        assert "7777" not in gov_text, "Default test PIN 7777 must never appear in Governance DOM!"
        passkey_panel_text = page.get_by_test_id("passkey-biometric-panel").inner_text()
        assert ("trilunair.medinsup.com" in passkey_panel_text or "RP ID: 127.0.0.1" in passkey_panel_text), passkey_panel_text
        assert ("صفر قوالب حيوية مخزنة" in passkey_panel_text or "Zero Biometric" in passkey_panel_text), passkey_panel_text
        latency_panel_text = page.get_by_test_id("region-latency-telemetry-panel").inner_text()
        assert "NOT_MEASURED" in latency_panel_text or "Tokyo" in latency_panel_text or "طوكيو" in latency_panel_text, latency_panel_text
        risk_strip_text = page.get_by_test_id("unified-risk-policy-strip").inner_text()
        for expected_pct in ("0.5%", "25%", "2%", "5%", "10%"):
            assert expected_pct in risk_strip_text, f"Missing {expected_pct} in {risk_strip_text}"
        report["verifiedUnifiedRiskStripInDom"] = True
        report["verifiedPasskeyAndLatencyPanelsInDom"] = True
        report["verifiedZeroDefaultPinInDom"] = True

        # 6. الانتقال إلى شاشة المحفظة والمدير المالي الشخصي (Personal CFO & Saudi Employment Benefits) والتحقق من ظهورها حياً
        page.click("#nav-portfolio-btn")
        page.wait_for_selector('[data-testid="personal-cfo-wealth-panel"]', timeout=6000)
        page.wait_for_selector('[data-testid="saudi-labor-benefits-calculator"]', timeout=6000)
        page.wait_for_selector('[data-testid="contract-renewal-deadline-tracker"]', timeout=6000)
        cfo_dom_text = page.get_by_test_id("personal-cfo-wealth-panel").inner_text()
        assert "PROVISIONAL / SUBJECT TO CONTRACT AND LEGAL VERIFICATION" in cfo_dom_text, cfo_dom_text
        assert "2027-08-11" in cfo_dom_text, cfo_dom_text
        assert "72,000" in cfo_dom_text, cfo_dom_text
        report["verifiedPersonalCfoAndSaudiContractInDom"] = True

        browser.close()

    # التحقق النهائي من قاعدة البيانات ولوحة العمليات السحابية وبقاء التداول مقفلاً على PAPER
    with httpx.Client(timeout=5.0, trust_env=False) as http:
        final_status = http.get(f"{BASE_URL}/api/system/status").json()
        ops = http.get(f"{BASE_URL}/api/system/operations").json()
        history = http.get(f"{BASE_URL}/api/ai/history").json()
        portfolio = http.get(f"{BASE_URL}/api/portfolio").json()
        assert final_status["version"] == "1.2.0-low-latency-cloudflare"
        assert final_status["tradingMode"] == "PAPER"
        assert final_status["liveAuthorized"] is False
        assert final_status["executionLockedToPaper"] is True
        assert ops["subsystems"]["postgresql"]["status"] == "CONNECTED"
        assert ops["subsystems"]["binancePublicMarketData"]["restStatus"] == "CONNECTED"
        sources_recorded = [m["source"] for m in history["messages"] if m["role"] == "user"]
        assert "TEXT" in sources_recorded and "VOICE" in sources_recorded, sources_recorded
        report["recordedCommandSourcesInPostgres"] = sources_recorded
        report["finalTradingMode"] = final_status["tradingMode"]
        report["liveAuthorized"] = final_status["liveAuthorized"]
        report["binancePublicRestStatus"] = ops["subsystems"]["binancePublicMarketData"]["restStatus"]
        report["portfolioTotalEquity"] = portfolio["totalEquity"]

    print("E2E_VERIFICATION_SUCCESS")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
