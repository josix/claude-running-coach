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
| `/run-init --connect strava` | Onboarding + probe and connect Strava account |
| `/run-today` | Show today's workout card |
| `/run-log [date]` | Log a completed workout (triggers adaptive iteration) |
| `/run-sync [--days N]` | Pull recent Strava activities (requires connection) |
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

## Connecting Strava (optional)

Strava integration lets `/run-sync` automatically import your runs without manual entry. Manual logging via `/run-log` works perfectly without it — Strava is opt-in and the plugin remains fully usable with no MCP configured.

### What it does and why

When connected, `/run-sync` fetches your recent Strava activities, normalizes fields (pace, HR, splits, RPE from description), deduplicates against existing log entries, and runs the same analysis and adaptation pipeline as manual logging. Your `preferred_source` setting (set to `"strava"` on connection) acts as a tiebreaker: if the same date has both a Strava-synced entry and a manually logged entry, the Strava entry wins and the manual one is kept but marked as superseded.

### Setup steps

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

### Daily use

```bash
# Sync yesterday's run
/run-sync

# Sync the last 3 days
/run-sync --days 3
```

### Troubleshooting

| Error message | `error_code` | What to do |
|---|---|---|
| "The Strava MCP server is not connected." | `mcp_unavailable` | Install r-huijts/strava-mcp, add to MCP config, restart Claude Code |
| "Strava authentication failed." | `auth` | Check `STRAVA_CLIENT_ID`, `STRAVA_CLIENT_SECRET`, `STRAVA_REFRESH_TOKEN` are set and valid |
| "Strava rate limit reached — retry in 15 minutes." | `rate_limit` | Wait 15 minutes and re-run `/run-sync` |
| "Strava auth expired — re-run /run-init --connect strava." | `auth` | Re-run the probe to refresh the connection |
| "Strava MCP server not available — check MCP config." | `mcp_unavailable` | Verify MCP configuration and restart Claude Code |
| Verbatim API error | `unknown` | Investigate the error; file an issue if it persists |

### Garmin Connect

Garmin Connect read is coming in v2 (the `garmin` schema slot is reserved in `users.json` for forward-compatibility). There is no Garmin setup to do in v0.2.0.

---

## Components

- **3 agents**: Coach (opus, head coach), WorkoutLogger (sonnet, captures manual runs), DataFetcher (sonnet, Strava sync)
- **9 commands** (above)
- **12 skills** (compute-vdot, build-training-plan, generate-daily-workout, log-workout, analyze-workout, adapt-plan, weekly-review, fetch-strava-activity, probe-strava-connection, research-methodology, taper-protocol, recovery-protocol)
- **2 hooks**: SessionStart (unlogged-workout reminder), PostToolUse (plan.json integrity check)
- **Static data**: VDOT pace table (VDOT 30–85), workout templates (~30 entries across base/build/peak/taper)
- **Storage**: 5 mutable per-user JSON files (users, plan, daily_state, workouts, progress)

## Status

v0.2.0 ships:
- Manual logging path (`/run-log`) end-to-end
- Daniels VDOT + polarized 80/20
- 24-week max macrocycle, 8-week min
- Single primary race target (multi-race in v2)
- **Strava read** (soft, opt-in via `/run-init --connect strava`); probe-based connection; `preferred_source` dedup tiebreaker

Out of scope: nutrition, strength, injury rehab, multi-sport, Garmin write-back, Garmin read (v2), social features.

## Methodology citations

Plugin grounding sources:
- Jack Daniels, *Daniels' Running Formula* (Human Kinetics) — VDOT pacing, periodization
- Stephen Seiler — polarized 80/20 intensity distribution
- Bosquet et al. (2007) — taper meta-analysis
- See `docs/methodology.md` for the full reading list.

## License

MIT
