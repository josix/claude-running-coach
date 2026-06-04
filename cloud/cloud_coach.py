#!/usr/bin/env python3
"""
cloud_coach.py — Standalone cloud coaching script for GitHub Actions.

Triggered by Cloudflare Worker after each new Strava activity.
Does NOT require local storage files (plan.json, workouts.json, etc.).
Fetches Strava data directly via REST API, analyzes, sends Telegram coaching.

Goal: 2:50 Sydney Marathon — 2026/08/30
"""
from __future__ import annotations

import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ── Reuse existing normalize helper (pure functions, no I/O) ─────────
sys.path.insert(0, str(Path(__file__).parent.parent / "skills" / "fetch-strava-activity" / "scripts"))
from strava_normalize import normalize_activity  # noqa: E402

# ── Config ───────────────────────────────────────────────────────────
GOAL_DATE        = datetime(2026, 8, 30, tzinfo=timezone.utc)
GOAL_TIME_SEC    = 2 * 3600 + 50 * 60           # 2:50:00
GOAL_PACE_SEC_KM = GOAL_TIME_SEC / 42.195        # ≈ 242 s/km = 4:02/km

STRAVA_CLIENT_ID     = os.environ["STRAVA_CLIENT_ID"]
STRAVA_CLIENT_SECRET = os.environ["STRAVA_CLIENT_SECRET"]
STRAVA_REFRESH_TOKEN = os.environ["STRAVA_REFRESH_TOKEN"]
TELEGRAM_TOKEN       = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID     = os.environ["TELEGRAM_CHAT_ID"]
ACTIVITY_ID          = os.environ.get("ACTIVITY_ID", "").strip()

# ── Formatting helpers ────────────────────────────────────────────────
def fmt_pace(sec_per_km: float) -> str:
    m, s = divmod(int(sec_per_km), 60)
    return f"{m}:{s:02d}/km"

def fmt_duration(sec: int) -> str:
    h, rem = divmod(sec, 3600)
    m, s   = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"

def days_to_race() -> int:
    return max(0, (GOAL_DATE - datetime.now(timezone.utc)).days)

# ── Strava REST API ───────────────────────────────────────────────────
def get_access_token() -> str:
    data = urllib.parse.urlencode({
        "client_id":     STRAVA_CLIENT_ID,
        "client_secret": STRAVA_CLIENT_SECRET,
        "refresh_token": STRAVA_REFRESH_TOKEN,
        "grant_type":    "refresh_token",
    }).encode()
    req = urllib.request.Request(
        "https://www.strava.com/oauth/token", data=data, method="POST"
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())["access_token"]

def strava_get(token: str, path: str):
    req = urllib.request.Request(
        f"https://www.strava.com/api/v3{path}",
        headers={"Authorization": f"Bearer {token}"},
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())

# ── Workout classification ────────────────────────────────────────────
TRAIL_KW  = ["山", "縱走", "油坑", "劍", "陽明", "風櫃", "trail", "越野", "夸父", "步道"]
TEMPO_KW  = ["tempo", "threshold", "課表", "耕跑", "間歇", "interval", "速度", "地獄列車"]
LONG_KW   = ["long", "lsd", "長距", "長跑", "zone 2", "zone2"]
EASY_KW   = ["easy", "輕鬆", "緩", "暖身", "收操", "散步", "恢復", "recovery", "皮克敏"]
RACE_KW   = ["race", "賽", "比賽", "競賽"]

def classify(name: str, dist_km: float, pace_sec: float, hr: float) -> str:
    n = name.lower()
    for kw in RACE_KW:
        if kw in n: return "race"
    for kw in TRAIL_KW:
        if kw in n: return "trail"
    for kw in TEMPO_KW:
        if kw in n: return "tempo"
    for kw in LONG_KW:
        if kw in n: return "long"
    for kw in EASY_KW:
        if kw in n: return "easy"

    if dist_km >= 25:                              return "long"
    if dist_km >= 15 and pace_sec > 290:           return "long"
    if pace_sec < 255 and hr > 163:                return "tempo"
    if hr and hr < 148 and pace_sec > 290:         return "easy"
    return "moderate"

# ── Weekly volume (Mon–today) ─────────────────────────────────────────
def weekly_volume(recent: list) -> float:
    now   = datetime.now(timezone.utc)
    start = (now - timedelta(days=now.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    total = 0.0
    for a in recent:
        sport = a.get("sport_type") or a.get("type") or ""
        if sport not in {"Run", "TrailRun", "VirtualRun"}:
            continue
        dt = datetime.strptime(a["start_date"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        if dt >= start:
            total += a.get("distance", 0) / 1000
    return total

# ── Coaching message ──────────────────────────────────────────────────
TYPE_ICON = {
    "long":     "🏃 長跑",
    "tempo":    "⚡ 速度訓練",
    "easy":     "🌿 輕鬆跑",
    "trail":    "⛰️ 越野跑",
    "race":     "🏆 比賽",
    "moderate": "🔄 一般跑",
}

def coaching_message(raw_activity: dict, recent: list) -> str:
    norm  = normalize_activity(raw_activity)
    if norm is None:
        raise ValueError("normalize_activity returned None — not a qualifying run")

    dist  = raw_activity["distance"] / 1000
    dur   = raw_activity["moving_time"]
    pace  = norm.get("avg_pace_per_km_s") or (dur / raw_activity["distance"] * 1000)
    hr    = norm.get("avg_hr") or 0
    maxhr = norm.get("max_hr") or 0
    elev  = raw_activity.get("total_elevation_gain") or 0
    name  = raw_activity.get("name", "")
    wtype = classify(name, dist, pace, hr)
    days  = days_to_race()
    vol   = weekly_volume(recent)

    lines: list[str] = []
    lines.append(f"*{TYPE_ICON.get(wtype, '🏃 跑步')} 分析*")
    lines.append(f"📍 {name}")
    lines.append("")

    # ── Stats ──
    lines.append("📊 *基本數據*")
    lines.append(f"• 距離：{dist:.2f} km")
    lines.append(f"• 時間：{fmt_duration(dur)}")
    lines.append(f"• 配速：{fmt_pace(pace)}")
    if hr:
        hr_str = f"{hr} bpm"
        if maxhr:
            hr_str += f"（最高 {maxhr}）"
        lines.append(f"• 心率：{hr_str}")
    if elev >= 30:
        lines.append(f"• 爬升：{elev:.0f} m")
    lines.append("")

    # ── Coaching ──
    lines.append(f"🎯 *教練分析*（距雪梨馬 {days} 天）")

    if wtype == "long":
        if dist >= 28:
            lines.append("✅ 30K 級別長跑——馬拉松耐力基礎紮實！")
        elif dist >= 22:
            lines.append("✅ 良好長跑，繼續把距離推到 28-30K。")
        elif dist >= 18:
            lines.append("👍 中等長跑。備賽階段目標每週一次 25-30K。")
        else:
            lines.append("💡 長跑距離偏短，嘗試延伸到 20K 以上。")
        if hr:
            if hr < 158:
                lines.append(f"💚 心率控制佳（{hr} bpm），長跑應維持 Zone 2-3（140-160 bpm）。")
            elif hr > 168:
                lines.append(f"⚠️ 長跑心率偏高（{hr} bpm）——下次嘗試更慢但更長。")
        if 0 < pace < GOAL_PACE_SEC_KM + 65:
            lines.append(
                f"💡 長跑配速 {fmt_pace(pace)} 接近比賽配速。"
                f"長跑建議比目標慢 60-90 秒（目標配速 {fmt_pace(GOAL_PACE_SEC_KM)}）。"
            )

    elif wtype == "tempo":
        lo, hi = GOAL_PACE_SEC_KM - 10, GOAL_PACE_SEC_KM + 20   # 3:52–4:22
        if pace < lo:
            lines.append(f"🔥 超強！配速 {fmt_pace(pace)} 遠快於目標配速——注意充分恢復。")
        elif pace <= hi:
            lines.append(
                f"✅ 配速 {fmt_pace(pace)} 精準落在節奏跑區間，"
                f"目標配速 {fmt_pace(GOAL_PACE_SEC_KM)}——完美！"
            )
        else:
            lines.append(
                f"💡 節奏跑配速 {fmt_pace(pace)} 可以再快一些。"
                f"節奏跑目標：{fmt_pace(lo)}~{fmt_pace(hi)}。"
            )

    elif wtype == "easy":
        if pace > 330:
            lines.append(f"✅ 很好！輕鬆跑就該慢（{fmt_pace(pace)}）——身體在恢復。")
        elif pace < 280:
            lines.append(
                f"⚠️ 「輕鬆跑」配速 {fmt_pace(pace)} 其實不輕鬆。"
                "輕鬆跑建議 5:10-5:50/km，讓身體真正恢復。"
            )
        else:
            lines.append(f"✅ 配速合理（{fmt_pace(pace)}）。")

    elif wtype == "trail":
        lines.append(
            f"⛰️ 越野跑看強度不看配速。"
            f"爬升 {elev:.0f}m 訓練臀肌和大腿，對馬拉松後段維持姿勢很有幫助。"
        )
        lines.append("💡 越野後隔天建議輕鬆恢復或休息。")

    elif wtype == "race":
        lines.append(f"🏆 比賽配速 {fmt_pace(pace)}！")
        if pace < GOAL_PACE_SEC_KM:
            lines.append(f"✅ 比目標配速 {fmt_pace(GOAL_PACE_SEC_KM)} 還快——狀態很好！")
        else:
            lines.append(f"目標配速 {fmt_pace(GOAL_PACE_SEC_KM)}，繼續保持訓練！")

    else:
        lines.append(f"配速 {fmt_pace(pace)}，心率 {hr} bpm。穩定的有氧訓練。")

    # ── Weekly volume ──
    lines.append("")
    lines.append(f"📅 *本週累計：{vol:.1f} km*")
    if vol < 50:
        lines.append("⚠️ 週量偏低，目標 60-70km。")
    elif vol < 65:
        lines.append("👍 週量合理，繼續加油。")
    elif vol < 80:
        lines.append("✅ 本週量紮實！")
    else:
        lines.append("⚠️ 週量較高，注意睡眠和恢復。")

    # ── Phase guidance ──
    lines.append("")
    if days > 70:
        lines.append("🗓️ 現在：*基礎建量期* — 重點是週量穩定到 65-75km，長跑推到 28-30km。")
    elif days > 42:
        lines.append("🗓️ 現在：*質量期* — 每週一次 Tempo，長跑 26-30km，週量 65-75km。")
    elif days > 21:
        lines.append("🗓️ 現在：*磨練期* — 加入 MP 長跑，後半段壓到 4:05/km。")
    elif days > 14:
        lines.append("🗓️ 現在：*減量開始* — 週量降 20%，維持配速感覺。")
    else:
        lines.append("🗓️ 現在：*賽前調整* — 以輕鬆跑為主，儲存能量，大量休息！")

    return "\n".join(lines)

# ── Telegram ─────────────────────────────────────────────────────────
def send_telegram(text: str) -> None:
    data = json.dumps({
        "chat_id":    TELEGRAM_CHAT_ID,
        "text":       text,
        "parse_mode": "Markdown",
    }).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as r:
        resp = json.loads(r.read())
        if not resp.get("ok"):
            raise RuntimeError(f"Telegram error: {resp}")

# ── Main ─────────────────────────────────────────────────────────────
def main() -> None:
    if not ACTIVITY_ID:
        print("ERROR: ACTIVITY_ID not set", file=sys.stderr)
        sys.exit(1)
    if not ACTIVITY_ID.isdigit():
        print(f"ERROR: invalid ACTIVITY_ID '{ACTIVITY_ID}' — must be a positive integer", file=sys.stderr)
        sys.exit(1)

    print(f"Fetching Strava activity {ACTIVITY_ID}...")
    token    = get_access_token()
    activity = strava_get(token, f"/activities/{ACTIVITY_ID}")

    sport = activity.get("sport_type") or activity.get("type") or ""
    if sport not in {"Run", "TrailRun", "VirtualRun"}:
        print(f"Not a run (sport_type={sport!r}), skipping.")
        return

    # Recent 28 days for weekly volume context
    since   = int((datetime.now(timezone.utc) - timedelta(days=28)).timestamp())
    recent  = strava_get(token, f"/athlete/activities?after={since}&per_page=80")

    msg = coaching_message(activity, recent)
    print("── Coaching message ──")
    print(msg)
    print("─────────────────────")

    send_telegram(msg)
    print("✅ Sent to Telegram!")

if __name__ == "__main__":
    main()
