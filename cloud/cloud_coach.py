#!/usr/bin/env python3
"""
cloud_coach.py — AI-powered coaching via Claude API + repo context.

Flow:
  GitHub Actions (triggered by Cloudflare Worker after Strava webhook)
  → reads agents/coach.md + data/vdot-table.json from repo
  → fetches Strava activity + recent history
  → asks Claude for coaching analysis
  → sends to Telegram
"""
from __future__ import annotations

import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ── Env ──────────────────────────────────────────────────────────────
STRAVA_CLIENT_ID     = os.environ["STRAVA_CLIENT_ID"]
STRAVA_CLIENT_SECRET = os.environ["STRAVA_CLIENT_SECRET"]
STRAVA_REFRESH_TOKEN = os.environ["STRAVA_REFRESH_TOKEN"]
TELEGRAM_TOKEN       = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID     = os.environ["TELEGRAM_CHAT_ID"]
ANTHROPIC_API_KEY    = os.environ["ANTHROPIC_API_KEY"]
ACTIVITY_ID          = os.environ.get("ACTIVITY_ID", "").strip()
GITHUB_TOKEN         = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPO          = os.environ.get("GITHUB_REPO", "")
STRAVA_ATHLETE_ID    = 130655035  # Po-Han's athlete ID — reject activities from other athletes

EFFORT_NAME_MAP = {
    "5K":            "5k",
    "10K":           "10k",
    "Half-Marathon": "half",
    "Marathon":      "full",
}

REPO_ROOT = Path(__file__).parent.parent

# ── Formatting ────────────────────────────────────────────────────────
def fmt_pace(sec_per_km: float) -> str:
    m, s = divmod(int(sec_per_km), 60)
    return f"{m}:{s:02d}/km"

def fmt_duration(sec: int) -> str:
    h, rem = divmod(sec, 3600)
    m, s   = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"

def days_to_race() -> int:
    goal = datetime(2026, 8, 30, tzinfo=timezone.utc)
    return max(0, (goal - datetime.now(timezone.utc)).days)

# ── Strava ────────────────────────────────────────────────────────────
def get_access_token() -> str:
    data = urllib.parse.urlencode({
        "client_id":     STRAVA_CLIENT_ID,
        "client_secret": STRAVA_CLIENT_SECRET,
        "refresh_token": STRAVA_REFRESH_TOKEN,
        "grant_type":    "refresh_token",
    }).encode()

    import time
    for attempt in range(3):
        req = urllib.request.Request(
            "https://www.strava.com/oauth/token", data=data, method="POST"
        )
        try:
            with urllib.request.urlopen(req) as r:
                return json.loads(r.read())["access_token"]
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")
            print(f"Strava OAuth error {e.code} (attempt {attempt+1}/3): {body[:200]}", file=sys.stderr)
            if attempt < 2:
                time.sleep(5 * (attempt + 1))  # 5s, 10s
            else:
                raise

def strava_get(token: str, path: str):
    req = urllib.request.Request(
        f"https://www.strava.com/api/v3{path}",
        headers={"Authorization": f"Bearer {token}"},
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())

# ── Repo context ──────────────────────────────────────────────────────
def load_coach_context() -> str:
    path = REPO_ROOT / "cloud" / "coach_prompt.md"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""

def load_vdot_table() -> str:
    path = REPO_ROOT / "data" / "vdot-table.json"
    if not path.exists():
        return ""
    table = json.loads(path.read_text(encoding="utf-8"))
    rows = table.get("rows", [])
    # VDOT 48-58 relevant for this runner (current ~50, target ~57)
    relevant = [r for r in rows if isinstance(r, dict) and 48 <= r.get("vdot", 0) <= 58]
    return json.dumps(relevant, ensure_ascii=False)

def load_user_profile() -> str:
    path = REPO_ROOT / "storage" / "users.json"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return json.dumps({
        "name": "Po-Han",
        "current_fitness": {"vdot": 52},
        "race_goal": {
            "name": "Sydney Marathon",
            "target_time": "2:50:00",
            "race_date": "2026-08-30"
        },
        "preferences": {"language": "zh-TW"}
    }, ensure_ascii=False)

# ── Lap formatting ────────────────────────────────────────────────────
def format_laps(laps: list) -> str:
    if not laps:
        return "- 無 lap 資料"
    lines = []
    for lap in laps:
        d = lap.get("distance", 0)
        if d < 100:  # skip sub-100m splits
            continue
        dist_km = d / 1000
        pace    = lap.get("moving_time", 0) / d * 1000 if d else 0
        hr      = lap.get("average_heartrate") or 0
        idx     = lap.get("lap_index", len(lines) + 1)
        line    = f"  Lap {idx}: {dist_km:.2f}km @ {fmt_pace(pace)}"
        if hr:
            line += f"  HR {hr:.0f}"
        lines.append(line)
    return "\n".join(lines) if lines else "- 無 lap 資料"

def format_best_efforts(activity: dict) -> str:
    efforts = activity.get("best_efforts", [])
    if not efforts:
        return ""
    # Only show meaningful distances (≥1km)
    keep = {"1000m", "1 mile", "2 mile", "5k", "10k", "Half-Marathon", "Marathon"}
    lines = []
    for e in efforts:
        name = e.get("name", "")
        if name not in keep:
            continue
        elapsed  = e.get("elapsed_time", 0)
        pr_rank  = e.get("pr_rank")
        date_str = (e.get("start_date_local") or "")[:10]
        line     = f"  {name}: {fmt_duration(elapsed)}"
        if date_str:
            line += f"（{date_str}）"
        if pr_rank == 1:
            line += " 🏆 PR"
        lines.append(line)
    return "\n".join(lines)

# ── Activity summary ──────────────────────────────────────────────────
def build_activity_summary(activity: dict, recent: list, laps: list, pb: dict) -> str:
    dist  = activity["distance"] / 1000
    dur   = activity["moving_time"]
    pace  = dur / activity["distance"] * 1000 if activity["distance"] else 0
    hr    = activity.get("average_heartrate") or 0
    maxhr = activity.get("max_heartrate") or 0
    elev  = activity.get("total_elevation_gain") or 0
    name  = activity.get("name", "")
    date  = activity.get("start_date_local", "")[:10]

    now   = datetime.now(timezone.utc)
    start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    weekly_km = sum(
        a["distance"] / 1000 for a in recent
        if (a.get("sport_type") or a.get("type")) in {"Run", "TrailRun", "VirtualRun"}
        and datetime.strptime(a["start_date"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc) >= start
    )

    long_runs = [
        f"{a['start_date_local'][:10]}: {a['distance']/1000:.1f}km @ {fmt_pace(a['moving_time']/a['distance']*1000 if a['distance'] else 0)}"
        for a in recent
        if (a.get("sport_type") or a.get("type")) in {"Run", "TrailRun", "VirtualRun"}
        and a["distance"] >= 15000
    ][-5:]

    # All activities in the last 120 days, newest first, skip current activity
    current_id = activity.get("id")
    run_types   = {"Run", "TrailRun", "VirtualRun"}
    cross_types = {"WeightTraining", "Hike", "Mountaineering", "Swim", "Swimming"}
    recent_all  = [
        a for a in recent
        if a.get("id") != current_id
        and (a.get("sport_type") or a.get("type")) in (run_types | cross_types)
    ]
    recent_all.sort(key=lambda a: a["start_date"], reverse=True)

    def fmt_recent(a: dict) -> str:
        sport  = a.get("sport_type") or a.get("type") or ""
        d      = a.get("distance", 0) / 1000
        t      = a.get("moving_time", 0)
        hr_avg = a.get("average_heartrate") or 0
        label  = f"{a['start_date_local'][:10]} [{sport}]"
        if d > 0.1:
            pace_str = f" {d:.1f}km @ {fmt_pace(t / a['distance'] * 1000 if a['distance'] else 0)}"
        else:
            pace_str = f" {fmt_duration(t)}"
        hr_str = f" HR {hr_avg:.0f}" if hr_avg else ""
        return f"- {label}{pace_str}{hr_str}"

    recent_lines = [fmt_recent(a) for a in recent_all[:30]]

    lines = [
        "## 活動資料",
        f"- 日期：{date}",
        f"- 名稱：{name}",
        f"- 距離：{dist:.2f} km",
        f"- 時間：{fmt_duration(dur)}",
        f"- 配速：{fmt_pace(pace)}",
    ]
    if hr:
        lines.append(f"- 平均心率：{hr:.0f} bpm（最高 {maxhr:.0f}）" if maxhr else f"- 平均心率：{hr:.0f} bpm")
    if elev >= 20:
        lines.append(f"- 爬升：{elev:.0f} m")

    # Lap breakdown
    if laps:
        lines += ["", "## Lap 明細"]
        lines.append(format_laps(laps))

    # Best efforts in this activity (PR tracking)
    best = format_best_efforts(activity)
    if best:
        lines += ["", "## 本次最佳成績（各距離）", best]

    lines += [
        "",
        "## 本週訓練",
        f"- 本週累計：{weekly_km:.1f} km",
        "",
        "## 近期長跑（≥15km）",
    ]
    lines += [f"- {r}" for r in long_runs] if long_runs else ["- 近期無長跑記錄"]

    lines += [
        "",
        "## 近四個月活動紀錄（最近 30 筆）",
    ]
    lines += recent_lines if recent_lines else ["- 無近期紀錄"]

    lines += ["", "## 全時個人最佳（PB）"]
    lines.append(format_pb(pb))

    lines += [
        "",
        "## 比賽目標",
        "- 目標：2:50 雪梨馬拉松（2026/08/30）",
        f"- 距比賽：{days_to_race()} 天",
        "- 目標配速：4:02/km",
    ]

    return "\n".join(lines)

# ── PB tracking ──────────────────────────────────────────────────────
def load_pb() -> dict:
    raw = os.environ.get("PB_JSON", "").strip()
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}

def format_pb(pb: dict) -> str:
    if not pb:
        return "- 尚無記錄"
    lines = []
    labels = {"5k": "5K", "10k": "10K", "half": "半馬", "full": "全馬"}
    for key in ["5k", "10k", "half", "full"]:
        if key not in pb:
            continue
        s = pb[key]["time_sec"]
        h, rem = divmod(s, 3600)
        m, sec = divmod(rem, 60)
        t = f"{h}:{m:02d}:{sec:02d}" if h else f"{m}:{sec:02d}"
        lines.append(f"- {labels[key]}: {t}（{pb[key]['date']}）")
    return "\n".join(lines) if lines else "- 尚無記錄"

def update_pb_variable(pb: dict) -> None:
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return
    payload = json.dumps({"name": "PB_JSON", "value": json.dumps(pb, ensure_ascii=False)}).encode()
    req = urllib.request.Request(
        f"https://api.github.com/repos/{GITHUB_REPO}/actions/variables/PB_JSON",
        data=payload,
        headers={
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
        },
        method="PATCH",
    )
    try:
        with urllib.request.urlopen(req) as r:
            r.read()
        print("PB_JSON variable updated.")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            # Variable doesn't exist yet — create it
            req2 = urllib.request.Request(
                f"https://api.github.com/repos/{GITHUB_REPO}/actions/variables",
                data=payload,
                headers={
                    "Authorization": f"Bearer {GITHUB_TOKEN}",
                    "Accept": "application/vnd.github+json",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            with urllib.request.urlopen(req2) as r:
                r.read()
            print("PB_JSON variable created.")
        else:
            print(f"Warning: could not update PB_JSON: {e}", file=sys.stderr)

def check_and_update_pb(activity: dict, pb: dict) -> tuple[dict, list[str]]:
    """Check best_efforts for new PRs. Returns updated pb and list of PR descriptions."""
    efforts = activity.get("best_efforts", [])
    new_prs: list[str] = []
    updated = False

    for effort in efforts:
        name    = effort.get("name", "")
        key     = EFFORT_NAME_MAP.get(name)
        pr_rank = effort.get("pr_rank")
        elapsed = effort.get("elapsed_time", 0)
        date    = (effort.get("start_date_local") or activity.get("start_date_local", ""))[:10]

        if not key or not elapsed:
            continue

        is_new_pb = (key not in pb or elapsed < pb[key]["time_sec"])
        if pr_rank == 1 or is_new_pb:
            pb[key] = {"time_sec": elapsed, "date": date, "activity_id": activity.get("id")}
            h, rem = divmod(elapsed, 3600)
            m, sec = divmod(rem, 60)
            t = f"{h}:{m:02d}:{sec:02d}" if h else f"{m}:{sec:02d}"
            labels = {"5k": "5K", "10k": "10K", "half": "半馬", "full": "全馬"}
            new_prs.append(f"{labels[key]} PB：{t}")
            updated = True

    if updated:
        update_pb_variable(pb)

    return pb, new_prs

# ── Claude API ────────────────────────────────────────────────────────
def ask_claude(system_prompt: str, user_message: str) -> str:
    payload = json.dumps({
        "model":      "claude-sonnet-4-5",
        "max_tokens": 1024,
        "system":     system_prompt,
        "messages":   [{"role": "user", "content": user_message}],
    }).encode()

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "x-api-key":         ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type":      "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req) as r:
        resp = json.loads(r.read())
        return resp["content"][0]["text"]

# ── Telegram ─────────────────────────────────────────────────────────
def send_telegram(text: str) -> None:
    if len(text) > 4096:
        text = text[:4090] + "…"
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
            # Retry without Markdown if parse error
            data2 = json.dumps({
                "chat_id": TELEGRAM_CHAT_ID,
                "text":    text,
            }).encode()
            req2 = urllib.request.Request(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                data=data2,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            urllib.request.urlopen(req2)

# ── Main ─────────────────────────────────────────────────────────────
def main() -> None:
    if not ACTIVITY_ID:
        print("ERROR: ACTIVITY_ID not set", file=sys.stderr)
        sys.exit(1)
    if not ACTIVITY_ID.isdigit():
        print(f"ERROR: invalid ACTIVITY_ID '{ACTIVITY_ID}'", file=sys.stderr)
        sys.exit(1)

    print(f"Fetching Strava activity {ACTIVITY_ID}...")
    token    = get_access_token()
    activity = strava_get(token, f"/activities/{ACTIVITY_ID}")

    # Verify activity belongs to the expected athlete (reject spoofed activity IDs)
    athlete_id = activity.get("athlete", {}).get("id")
    if athlete_id != STRAVA_ATHLETE_ID:
        print(f"Activity athlete {athlete_id} != expected {STRAVA_ATHLETE_ID}, skipping.")
        return

    sport = activity.get("sport_type") or activity.get("type") or ""
    is_run = sport in {"Run", "TrailRun", "VirtualRun"}
    is_cross = sport in {"WeightTraining", "Hike", "Mountaineering", "Swim", "Swimming"}

    if not is_run and not is_cross:
        print(f"Activity type {sport!r} not in scope, skipping.")
        return

    since  = int((datetime.now(timezone.utc) - timedelta(days=120)).timestamp())
    recent: list = []
    page = 1
    while True:
        batch = strava_get(token, f"/athlete/activities?after={since}&per_page=200&page={page}")
        if not batch:
            break
        recent.extend(batch)
        if len(batch) < 200:
            break
        page += 1
    print(f"[DEBUG] Strava returned {len(recent)} activities total ({page} page(s), last 120 days)")

    # Fetch lap data (runs only — cross-training laps are not useful)
    laps: list = []
    if is_run:
        try:
            laps = strava_get(token, f"/activities/{ACTIVITY_ID}/laps")
        except Exception as e:
            print(f"Warning: could not fetch laps: {e}", file=sys.stderr)

    coach_md        = load_coach_context()
    vdot_table      = load_vdot_table()
    user_profile    = load_user_profile()
    pb              = load_pb()

    # Check for PRs and update PB_JSON variable if needed (runs only)
    new_prs: list[str] = []
    if is_run:
        pb, new_prs = check_and_update_pb(activity, pb)

    activity_summary = build_activity_summary(activity, recent, laps, pb)

    if is_run:
        system_prompt = f"""{coach_md}

## VDOT 配速表（VDOT 48-58）
{vdot_table}

## 跑者個人資料
{user_profile}"""
    else:
        system_prompt = f"""{coach_md}

## 跑者個人資料
{user_profile}

這次是交叉訓練活動（{sport}），請從馬拉松備賽角度分析其幫助與意義。"""

    if is_run:
        user_message = f"""請分析以下跑步活動，給出教練回饋：

{activity_summary}

請依序包含：
1. **近期訓練脈絡**（先從四個月活動紀錄判斷）：
   - 本週目前跑量 vs 前三週平均週跑量，是否突增 >10%？
   - 最近 14 天質量課（T/I/R）次數，是否超過 80/20 原則？
   - 這次活動前 48 小時有無高強度課？連續疲勞風險？
2. **訓練類型判定**（根據 lap 配速分布推斷）：
   - 輕鬆跑、節奏跑、間歇、長跑、馬拉松配速跑
3. **依訓練類型對症分析**：
   - 間歇 → 快速段是否達目標配速？恢復段心率是否降下來？
   - 節奏跑 → 配速是否維持在目標區間？後段崩速了嗎？
   - 輕鬆跑 → 心率是否控制在 Zone 2 以內？
4. 根據本次或近期最佳成績，估算目前 VDOT（標明依據距離/時間）
5. 距離 2:50 雪梨馬拉松目標的差距評估
6. 一個具體的下次訓練建議"""
    else:
        user_message = f"""請分析以下交叉訓練活動，從馬拉松備賽的角度給出回饋：

{activity_summary}

請包含：
1. 這次交叉訓練對跑步體能的幫助（肌力、心肺、恢復等）
2. 強度是否合適
3. 建議的恢復方式或下一步"""

    print("Asking Claude for analysis...")
    analysis = ask_claude(system_prompt, user_message)

    print("── Analysis ──")
    print(analysis)
    print("─────────────")

    name = activity.get("name", "活動")
    dist = activity.get("distance", 0) / 1000
    icon = "🏃" if is_run else "💪"
    pr_banner = ("\n\n🏆 *新 PB！* " + "、".join(new_prs)) if new_prs else ""
    msg  = f"{icon} *{name}*" + (f" ({dist:.1f}km)" if dist > 0 else "") + pr_banner + f"\n\n{analysis}"

    send_telegram(msg)
    print("✅ Sent to Telegram!")

if __name__ == "__main__":
    main()
