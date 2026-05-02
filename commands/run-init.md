---
description: One-time onboarding — interview the runner about goal, fitness, training days, lifestyle. Generates users.json + plan.json. Optionally connect Strava with --connect strava.
argument-hint: "[--connect strava|garmin]"
---

# /run-init

## Purpose

Set up a brand-new runner profile and generate a personalized training plan. This command collects your race goal, current fitness level, and lifestyle constraints, then builds a full macrocycle tailored to your target date.

Run this once when starting the plugin for the first time. You can also re-run it with `--connect strava` or `--connect garmin` to probe and connect an activity source.

## Action

Delegate to **Coach**. Coach will:

1. **Interview the runner** — one question at a time — collecting:
   - Goal race (marathon, half, 10K, 5K, or custom distance)
   - Target finish time
   - Race date
   - Recent race result or time-trial result (used to seed VDOT — if none, Coach will offer a time-trial plan)
   - Available training days per week (which days of the week)
   - Lifestyle context (typical sleep hours, stress level, prior weekly mileage, injury history)
   - Methodology preference (polarized default; pyramidal available)
   - Unit preference (time default; distance available)

2. **Call `compute-vdot`** — translates the race result into a VDOT score and full E/M/T/I/R pace table.

3. **Call `build-training-plan`** — constructs the full macrocycle (base → build → peak → taper) from today through the race date, respecting the 8-week minimum and 24-week maximum. Selects weekly templates from `data/workout-templates.json`.

4. **Write `storage/users.json`** — saves the full user profile including fitness baseline and preferences.

5. **Write `storage/plan.json`** — saves the generated macrocycle with all weeks and days.

### If `--connect strava` is supplied

After writing the initial `users.json`, Coach will attempt to connect Strava via the `probe-strava-connection` skill:

1. **Call `probe-strava-connection`** — checks MCP availability, calls `mcp__strava__check-strava-connection`, then `mcp__strava__get-athlete-profile` to capture identity.

2. **If probe returns `ok: true`**:
   - Write `users.json.integrations.strava`:
     ```json
     {
       "connected": true,
       "athlete_id": <athlete_id from probe>,
       "connected_at": "<now ISO 8601>",
       "last_sync_at": null,
       "last_sync_status": null
     }
     ```
   - Set `users.json.integrations.preferred_source = "strava"`.
   - Confirm to the user: "Connected as @{username}. `/run-sync` will pull your recent runs."

3. **If probe returns `ok: false`**:
   - Leave `users.json.integrations.strava.connected = false` and `preferred_source = "manual"`.
   - Surface the probe's `message` verbatim so the user knows what to fix.
   - Onboarding still completes the manual path — the runner has a working plan immediately.

### If `--connect garmin` is supplied

After writing the initial `users.json`, Coach will attempt to connect Garmin Connect via the `probe-garmin-connection` skill. The plugin targets the `nrvim/garmin-givemydata` MCP server (a SQLite-backed Garmin client that bypasses Cloudflare via SeleniumBase UC mode); the older `garth`-based `Taxuspt/garmin_mcp` server stopped working in March 2026 when Garmin deployed Cloudflare bot detection.

1. **Call `probe-garmin-connection`** — checks MCP availability, calls `mcp__garmin__garmin_user_profile`, and verifies the local SQLite database has been seeded with profile rows.

2. **If probe returns `ok: true`**:
   - Write `users.json.integrations.garmin`:
     ```json
     {
       "connected": true,
       "garmin_user_id": "<garmin_user_id from probe>",
       "email": "<email from probe, or null>",
       "display_name": "<display_name from probe, or null>",
       "connected_at": "<now ISO 8601>",
       "last_sync_at": null,
       "last_sync_status": null,
       "last_sync_imported": null,
       "last_sync_enriched": null,
       "data_freshness_date": null
     }
     ```
   - Set `users.json.integrations.preferred_source = "garmin"`.
   - Confirm to the user: "Connected Garmin Connect (garmin_user_id: {garmin_user_id}{, display name: {display_name} if present}). `/run-sync` will pull your recent runs."

3. **If probe returns `ok: false`**:
   - Leave `users.json.integrations.garmin.connected = false` and `preferred_source = "manual"`.
   - Surface the probe's `message` verbatim so the user knows what to fix. The probe distinguishes three failure modes: `mcp_unavailable` (install the MCP server), `db_empty` (run `garmin-givemydata` once to populate the local DB), and `unknown` (verbatim error + diagnosis hint).
   - Onboarding still completes the manual path — the runner has a working plan immediately.

## Prerequisites for `--connect strava`

Before running `/run-init --connect strava`, set up the Strava MCP server:

1. **Install the MCP server**: https://github.com/r-huijts/strava-mcp
2. **Create a Strava API app**: https://www.strava.com/settings/api
3. **Set environment variables** in your Claude Code MCP server configuration:
   - `STRAVA_CLIENT_ID` — your Strava API app client ID
   - `STRAVA_CLIENT_SECRET` — your Strava API app client secret
   - `STRAVA_REFRESH_TOKEN` — a valid refresh token (obtained via the OAuth flow documented in the MCP server README)
4. **Add to MCP config**: follow https://docs.anthropic.com/en/docs/claude-code/mcp to register the server in your Claude Code configuration.
5. Restart Claude Code so the new MCP server is loaded, then run `/run-init --connect strava`.

If setup is not complete, the probe will return `mcp_unavailable` or `auth` and the onboarding will fall back to manual logging. You can re-run `/run-init --connect strava` at any time once setup is complete.

## Prerequisites for `--connect garmin`

Before running `/run-init --connect garmin`, set up the `nrvim/garmin-givemydata` MCP server. (The older `garth`-based `Taxuspt/garmin_mcp` is no longer supported by this plugin — Garmin's March 2026 Cloudflare deployment broke `garth` and every server built on it.)

### Why this server

`garmin-givemydata` uses SeleniumBase UC mode (undetected Chrome) to log in through Garmin's regular web flow, capturing a `cf_clearance` cookie that satisfies Cloudflare's bot detection. It dumps everything to a local SQLite database and exposes 44 read-only MCP tools that query that DB. The MCP server only contacts Garmin live when you call `garmin_sync` — every other tool is a fast local read. See https://github.com/nrvim/garmin-givemydata for the full feature matrix.

### Steps

1. **Install Google Chrome** (required by SeleniumBase). Download from https://www.google.com/chrome/ if you don't already have it.

2. **Install `garmin-givemydata`** with `uv` or `pipx` (do not use `brew` — the plugin tracks the PyPI release for predictable versioning). Both tools install into an isolated environment and put `garmin-givemydata` and `garmin-mcp` on PATH.
   ```
   # Option A — uv (recommended)
   uv tool install garmin-givemydata

   # Option B — pipx
   pipx install garmin-givemydata
   ```
   Requires Python 3.10+. `uv` will fetch a suitable Python automatically; `pipx` uses your system Python.

3. **Run the initial sync** in a terminal — this is the slow step:
   ```
   garmin-givemydata
   ```
   On first run it prompts for your Garmin Connect email, password, and MFA code (if MFA is enabled), launches a headless Chrome window to complete login, then pulls your full history. Plan for ~30 minutes for ~10 years of data; pass `--days 90` if you only want recent data, or `--profile activities` to skip health metrics. Subsequent runs are incremental and take seconds.

4. **Confirm the data location.** Both `uv tool install` and `pipx install` write the SQLite DB to `~/.garmin-givemydata/garmin.db` by default. Override with the `GARMIN_DATA_DIR` env var if you want it elsewhere.

5. **Register `garmin-mcp` in your Claude Code MCP config** under namespace `garmin` (the plugin's `mcp__garmin__*` tool prefix depends on this namespace). After `uv tool install` or `pipx install`, the entry point is on PATH:
   ```json
   {
     "mcpServers": {
       "garmin": {
         "command": "garmin-mcp"
       }
     }
   }
   ```
   If `garmin-mcp` is not on Claude Code's PATH (common with `uv tool` on macOS), use the absolute path emitted by `uv tool list` or `pipx list` — for example `~/.local/bin/garmin-mcp` for pipx, or `~/.local/share/uv/tools/garmin-givemydata/bin/garmin-mcp` for uv. If you set a custom `GARMIN_DATA_DIR`, mirror it in the MCP config:
   ```json
   {
     "mcpServers": {
       "garmin": {
         "command": "/absolute/path/to/garmin-mcp",
         "env": { "GARMIN_DATA_DIR": "/absolute/path/to/data/dir" }
       }
     }
   }
   ```
   See https://docs.anthropic.com/en/docs/claude-code/mcp for full MCP config docs.

6. Restart Claude Code so the new MCP server is loaded, then run `/run-init --connect garmin`.

### Caveats

- **Cloudflare session is IP-bound.** The `cf_clearance` cookie expires when your egress IP changes. On a stable home/office IP it lasts weeks; on a laptop that hops networks or a VPN that rotates exits, expect to re-run `garmin-givemydata` (and re-prompt for credentials) more often. Re-auth happens automatically on next run.
- **Live syncs still go through Cloudflare.** When `/run-sync` calls `garmin_sync(refresh=true)`, it triggers the headless-browser flow under the hood. If Garmin's bot detection tightens further, that path can break independently of the read tools — read tools keep working from the local DB regardless.
- **First-run cost is real.** The 10-year bulk fetch is ~30 minutes; nothing the plugin does will speed it up. If you only care about recent training data, use `garmin-givemydata --days 90` for the first run.
- **Probe scope.** `/run-init`'s probe only verifies that the local DB has profile rows — it cannot detect a stale Cloudflare session, since profile reads don't touch Garmin. Auth/Cloudflare failures surface at `/run-sync` time with their own error classification.

If setup is incomplete, the probe will return `mcp_unavailable` (server not registered) or `db_empty` (registered but no `garmin-givemydata` run yet) and onboarding falls back to manual logging. You can re-run `/run-init --connect garmin` at any time once setup is complete.

## Output

After completion, display:
- A welcome message with the runner's name and goal
- VDOT score and the five training paces (Easy, Marathon, Threshold, Interval, Repetition)
- A macrocycle overview: phase names, week ranges, and focus areas
- Today's first prescribed workout (so the runner knows what to expect immediately)
- If Strava connected: confirmation with athlete username and instructions to use `/run-sync`
- If Garmin connected: confirmation with garmin_user_id and instructions to use `/run-sync`
- A prompt to run `/run-today` to see today's full workout card

## Notes

If `storage/users.json` already exists, ask the runner whether to overwrite or start fresh. Preserving the existing file and running `/run-replan` instead is often the better choice after a mid-cycle event.
