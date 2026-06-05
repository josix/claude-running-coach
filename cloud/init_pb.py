#!/usr/bin/env python3
"""
init_pb.py — One-time scan of 2 years of Strava activities to initialize PB_JSON.

Fetches activity details for qualifying runs, extracts best_efforts,
and writes the all-time PB per distance to the GitHub Variable PB_JSON.

Run via: gh workflow run init-pb.yml -R pohanchi/claude-running-coach
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

STRAVA_CLIENT_ID     = os.environ["STRAVA_CLIENT_ID"]
STRAVA_CLIENT_SECRET = os.environ["STRAVA_CLIENT_SECRET"]
STRAVA_REFRESH_TOKEN = os.environ["STRAVA_REFRESH_TOKEN"]
GITHUB_TOKEN         = os.environ["GITHUB_TOKEN"]
GITHUB_REPO          = os.environ["GITHUB_REPO"]
STRAVA_ATHLETE_ID    = 130655035

# Distances that qualify for each PB category (in metres)
PB_THRESHOLDS = {
    "5k":   (4800,  6000),
    "10k":  (9500,  11000),
    "half": (20500, 22500),
    "full": (41500, 43500),
}

# best_efforts name → PB key mapping
EFFORT_NAME_MAP = {
    "5k":            "5k",
    "10k":           "10k",
    "Half-Marathon": "half",
    "Marathon":      "full",
}

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

def fetch_all_activities(token: str, since_ts: int) -> list:
    """Paginate through all activities since timestamp."""
    activities = []
    page = 1
    while True:
        batch = strava_get(token, f"/athlete/activities?after={since_ts}&per_page=200&page={page}")
        if not batch:
            break
        activities.extend(batch)
        print(f"  Fetched page {page}: {len(batch)} activities (total {len(activities)})")
        if len(batch) < 200:
            break
        page += 1
        time.sleep(1)  # be polite to Strava API
    return activities

def get_activity_detail(token: str, activity_id: int) -> dict | None:
    try:
        return strava_get(token, f"/activities/{activity_id}")
    except Exception as e:
        print(f"  Warning: could not fetch activity {activity_id}: {e}", file=sys.stderr)
        return None

def update_github_variable(name: str, value: str) -> None:
    data = json.dumps({"name": name, "value": value}).encode()
    req = urllib.request.Request(
        f"https://api.github.com/repos/{GITHUB_REPO}/actions/variables/{name}",
        data=data,
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
    except urllib.error.HTTPError as e:
        if e.code == 404:
            # Variable doesn't exist yet — create it
            req2 = urllib.request.Request(
                f"https://api.github.com/repos/{GITHUB_REPO}/actions/variables",
                data=data,
                headers={
                    "Authorization": f"Bearer {GITHUB_TOKEN}",
                    "Accept": "application/vnd.github+json",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            with urllib.request.urlopen(req2) as r:
                r.read()
        else:
            raise

def main() -> None:
    since = int((datetime.now(timezone.utc) - timedelta(days=730)).timestamp())
    print(f"Scanning Strava activities since {datetime.fromtimestamp(since).date()} (2 years)...")

    token = get_access_token()
    all_activities = fetch_all_activities(token, since)

    run_types = {"Run", "TrailRun", "VirtualRun"}
    runs = [
        a for a in all_activities
        if (a.get("sport_type") or a.get("type")) in run_types
        and a.get("athlete", {}).get("id") == STRAVA_ATHLETE_ID
    ]
    print(f"Found {len(runs)} run activities, checking for qualifying distances...")

    # Filter to runs that could qualify for any PB category
    min_qualifying = min(lo for lo, _ in PB_THRESHOLDS.values())
    qualifying = [a for a in runs if a.get("distance", 0) >= min_qualifying]
    print(f"{len(qualifying)} runs qualify for PB scan (≥{min_qualifying/1000:.0f}km)")

    # Scan each qualifying activity for best_efforts
    pb: dict[str, dict] = {}
    for i, a in enumerate(qualifying):
        act_id = a["id"]
        date   = a.get("start_date_local", "")[:10]
        dist   = a.get("distance", 0) / 1000
        print(f"  [{i+1}/{len(qualifying)}] {date} {dist:.1f}km (id={act_id})")

        detail = get_activity_detail(token, act_id)
        if not detail:
            continue

        efforts = detail.get("best_efforts", [])
        for effort in efforts:
            name = effort.get("name", "")
            key  = EFFORT_NAME_MAP.get(name)
            if not key:
                continue
            elapsed = effort.get("elapsed_time", 0)
            if elapsed <= 0:
                continue
            if key not in pb or elapsed < pb[key]["time_sec"]:
                pb[key] = {
                    "time_sec":   elapsed,
                    "date":       date,
                    "activity_id": act_id,
                }
                print(f"    New PB for {key}: {elapsed}s ({date})")

        time.sleep(0.5)  # ~2 req/sec, well under Strava's 100/15min limit

    # Print summary
    print("\n── PB Summary ──")
    for key in ["5k", "10k", "half", "full"]:
        if key in pb:
            s = pb[key]["time_sec"]
            h, rem = divmod(s, 3600)
            m, sec = divmod(rem, 60)
            t = f"{h}:{m:02d}:{sec:02d}" if h else f"{m}:{sec:02d}"
            print(f"  {key}: {t} ({pb[key]['date']})")
        else:
            print(f"  {key}: no data")

    print("\nWriting PB_JSON to GitHub Variable...")
    update_github_variable("PB_JSON", json.dumps(pb, ensure_ascii=False))
    print("✅ Done!")

if __name__ == "__main__":
    main()
