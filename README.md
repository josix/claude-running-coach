# running-coach

Adaptive running training plugin for Claude Code. Generates a personalized macrocycle from your race goal, prescribes daily workouts using Daniels' VDOT pacing, and iterates the plan after every workout based on actual performance.

## What it does

- Set a race goal with target date and current fitness baseline
- Get a complete training plan (base → build → peak → taper) generated from Daniels' VDOT methodology and polarized 80/20 intensity distribution
- See today's workout card with target paces, RPE expectations, and warm-up cues
- Log each workout manually or sync automatically from Strava (optional)
- The plan adapts after every workout: 2 missed targets → reduce next quality session; 3 misses → recovery week; 3 on-target → VDOT bump
- Weekly review surfaces fatigue trends and recommends hold / advance / recovery

## Quick start

```bash
# 1. Install (drop the directory into your plugins folder)
# 2. Open Claude Code in any working directory
# 3. Run the onboarding interview
/run-init

# 4. Each morning
/run-today

# 5. Each evening after running
/run-log

# 6. Each Sunday
/run-week
```

## Commands

| Command | What it does |
|---|---|
| `/run-init` | One-time onboarding: goal, fitness, training days, lifestyle |
| `/run-init --connect strava\|garmin` | Onboarding + probe and connect Strava or Garmin Connect account |
| `/run-today` | Show today's workout card |
| `/run-log [date]` | Log a completed workout (triggers adaptive iteration) |
| `/run-sync [--days N]` | Pull recent Strava or Garmin Connect activities (requires `/run-init --connect strava\|garmin`) |
| `/run-week` | Weekly rollup + recovery decision |
| `/run-replan [--reason "..."]` | Force full plan regeneration |
| `/run-plan` | Show current macrocycle (read-only) |
| `/run-race-recap` | Post-race log + VDOT update + 4-day rest protocol |
| `/run-research "question"` | Web-search-backed coaching Q&A |

## How adaptive iteration works

After each workout, `analyze-workout` computes the delta between actual and prescribed: completion %, pace delta %, RPE delta, intra-session HR drift. The verdict (`on-target` / `under` / `over` / `aborted`) drives a strike-rule engine:

- **1 missed target** — monitor, no plan change
- **2 consecutive misses** — next quality session intensity reduced one step
- **3 consecutive misses** — recovery week inserted (volume −30%, drop one quality)
- **3 consecutive ahead-of-target** — VDOT bumped, remaining plan paces regenerated
- **Aborted with high HR drift + high RPE** — fatigue red flag; second occurrence in 14 days triggers recovery week

See `docs/methodology.md` for the full coaching rationale and `DESIGN.md` for architecture details.

---

## Connecting an activity source (optional)

Activity source integration lets `/run-sync` automatically import your runs without manual entry. Manual logging via `/run-log` works perfectly without it — both Strava and Garmin are opt-in and the plugin remains fully usable with no MCP configured.

> **`preferred_source` semantics**: The most-recently-connected provider becomes preferred. On same-date duplicates, the preferred source wins and the other entry is kept but marked `superseded_by` the winning entry's ID.

### Strava

When connected, `/run-sync` fetches your recent Strava activities, normalizes fields (pace, HR, splits, RPE from description), deduplicates against existing log entries, and runs the same analysis and adaptation pipeline as manual logging.

**Setup steps:**

1. **Install the Strava MCP server**
   Follow the instructions at https://github.com/r-huijts/strava-mcp to install `r-huijts/strava-mcp`.

2. **Create a Strava API app**
   Go to https://www.strava.com/settings/api, create an app, and note the **Client ID** and **Client Secret**. Follow the OAuth flow in the MCP server README to generate a **Refresh Token**.

3. **Set environment variables in your MCP config**
   Add the following to your Claude Code MCP server configuration (see https://docs.anthropic.com/en/docs/claude-code/mcp):
   - `STRAVA_CLIENT_ID`
   - `STRAVA_CLIENT_SECRET`
   - `STRAVA_REFRESH_TOKEN`

4. **Probe and connect**
   Restart Claude Code (so the MCP server loads), then run:
   ```
   /run-init --connect strava
   ```
   The plugin probes the MCP server and your credentials before writing anything. On success you'll see: "Connected as @{username}."

**Troubleshooting:**

| Error message | `error` | What to do |
|---|---|---|
| "The Strava MCP server is not connected." | `mcp_unavailable` | Install r-huijts/strava-mcp, add to MCP config, restart Claude Code |
| "Strava authentication failed." | `auth` | Check `STRAVA_CLIENT_ID`, `STRAVA_CLIENT_SECRET`, `STRAVA_REFRESH_TOKEN` are set and valid |
| "Strava rate limit reached — retry in 15 minutes." | `rate_limit` | Wait 15 minutes and re-run `/run-sync` |
| "Strava auth expired — re-run /run-init --connect strava." | `auth` | Re-run the probe to refresh the connection |
| "Strava MCP server not available — check MCP config." | `mcp_unavailable` | Verify MCP configuration and restart Claude Code |
| Verbatim API error | `unknown` | Investigate the error; file an issue if it persists |

### Garmin Connect

When connected, `/run-sync` triggers a live sync of your Garmin Connect data into a local SQLite database, then reads recent runs from that DB, normalizes fields (pace, HR, splits, running dynamics), deduplicates against existing log entries, and runs the same analysis and adaptation pipeline as manual logging. Note: RPE is not parsed from Garmin activities (no description field in the activity summary).

The plugin targets the `nrvim/garmin-givemydata` MCP server. The older `garth`-based `Taxuspt/garmin_mcp` is no longer supported — Garmin's March 2026 Cloudflare deployment broke `garth` and every server built on it. `garmin-givemydata` works around the bot detection by driving an undetected Chrome session via SeleniumBase.

**Setup steps:**

1. **Install Google Chrome** (required by SeleniumBase). Download from https://www.google.com/chrome/.

2. **Install `garmin-givemydata`** with `uv` or `pipx` — do **not** use `brew`. Both install into an isolated environment and put `garmin-givemydata` and `garmin-mcp` on PATH.
   ```
   # Option A — uv (recommended)
   uv tool install garmin-givemydata

   # Option B — pipx
   pipx install garmin-givemydata
   ```
   Requires Python 3.10+.

3. **Run the initial sync** in a terminal (this is the slow step — ~30 minutes for ~10 years of history; pass `--days 90` for a fast first run):
   ```
   garmin-givemydata
   ```
   You will be prompted for Garmin Connect email, password, and MFA code (if MFA is enabled). On success, the local SQLite is populated at `~/.garmin-givemydata/garmin.db` (override with `GARMIN_DATA_DIR`).

4. **Register `garmin-mcp` in your Claude Code MCP config** under namespace `garmin` (the plugin's `mcp__garmin__*` tool prefix depends on this namespace):
   ```json
   {
     "mcpServers": {
       "garmin": {
         "command": "garmin-mcp"
       }
     }
   }
   ```
   If `garmin-mcp` is not on Claude Code's PATH, use the absolute path from `uv tool list` or `pipx list`. See https://docs.anthropic.com/en/docs/claude-code/mcp for full MCP config docs.

5. Restart Claude Code so the new MCP server is loaded, then run `/run-init --connect garmin`.

**Caveats:**

- The `cf_clearance` cookie used to bypass Cloudflare is bound to your egress IP. On a stable network it lasts weeks; on rotating VPNs or laptops that hop networks, expect to re-run `garmin-givemydata` periodically. Re-auth is automatic on next run.
- The 30-minute first-run cost is unavoidable — Garmin doesn't provide a public API; the data has to be scraped through the web UI.
- All Garmin live access happens during `garmin_sync`. Read tools (`garmin_query`, `garmin_activity_detail`, etc.) only hit the local SQLite, so `/run-today`-style reads keep working even if Garmin is unreachable.

**Troubleshooting:**

| Error message | `error` | What to do |
|---|---|---|
| "The garmin-givemydata MCP server is not connected." | `mcp_unavailable` | Install via `uv tool install garmin-givemydata` (or pipx), register `garmin-mcp` under namespace `garmin` in your Claude Code MCP config, restart |
| "garmin-givemydata MCP is connected, but the local database has not been populated yet." | `db_empty` | Run `garmin-givemydata` once in a terminal to populate the SQLite (~30 min for full history; `--days 90` for a fast first run) |
| "Garmin authentication failed or MFA needed." | `auth` (during `/run-sync`) | Run `garmin-givemydata` in a terminal to re-prompt for credentials/MFA |
| "Garmin Cloudflare check failed." | `auth` (during `/run-sync`) | Run `garmin-givemydata` from your normal egress IP — `cf_clearance` is IP-bound |
| Verbatim API/SQLite error | `unknown` | Investigate; `garmin-givemydata --status` shows DB contents |

> **Migrating from `Taxuspt/garmin_mcp`?** Remove that server from your Claude Code MCP config (or any other `garth`-based Garmin MCP — they're all broken by Cloudflare as of March 2026), then follow the install steps above. The plugin's `users.json.integrations.garmin` schema is unchanged — re-run `/run-init --connect garmin` to refresh it after switching servers.

### Daily use (either provider)

```bash
# Sync yesterday's run
/run-sync

# Sync the last 3 days
/run-sync --days 3
```

---

## Components

- **3 agents**: Coach (opus, head coach), WorkoutLogger (sonnet, captures manual runs), DataFetcher (sonnet, Strava + Garmin sync)
- **9 commands** (above)
- **14 skills** (compute-vdot, build-training-plan, generate-daily-workout, log-workout, analyze-workout, adapt-plan, weekly-review, fetch-strava-activity, probe-strava-connection, fetch-garmin-activity, probe-garmin-connection, research-methodology, taper-protocol, recovery-protocol)
- **2 hooks**: SessionStart (unlogged-workout reminder), PostToolUse (plan.json integrity check)
- **Static data**: VDOT pace table (VDOT 30–85), workout templates (~30 entries across base/build/peak/taper)
- **Storage**: 5 mutable per-user JSON files (users, plan, daily_state, workouts, progress)

## Status

v0.3.0 ships:
- Manual logging path (`/run-log`) end-to-end
- Daniels VDOT + polarized 80/20
- 24-week max macrocycle, 8-week min
- Single primary race target (multi-race in v2)
- **Strava read** (soft, opt-in via `/run-init --connect strava`); probe-based connection; `preferred_source` dedup tiebreaker
- **Garmin Connect read** (soft, opt-in via `/run-init --connect garmin`); probe-based connection; MFA interactive at first setup
- Cross-provider start-time-window dedup: deferred to v0.4.0 (v0.3.0 ships single-provider-at-a-time)

Out of scope: nutrition, strength, injury rehab, multi-sport, Garmin write-back, social features.

## Methodology citations

Plugin grounding sources:
- Jack Daniels, *Daniels' Running Formula* (Human Kinetics) — VDOT pacing, periodization
- Stephen Seiler — polarized 80/20 intensity distribution
- Bosquet et al. (2007) — taper meta-analysis
- See `docs/methodology.md` for the full reading list.

## License

MIT
