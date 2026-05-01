# DESIGN.md — `running-coach` Claude Code Plugin

**Status**: DRAFT v1 — pending user approval before any implementation
**Author**: Senku (Planner Agent), via /agent-flow:orchestrate
**Date**: 2026-04-30
**Reference plugin**: `jp-learner` (same author, same orchestration patterns)

---

## 1. Plugin Overview & User-Facing Flow

`running-coach` is a Claude Code plugin that turns a runner's race goal + current fitness + lifestyle constraints into a personalized, adaptive training plan grounded in modern coaching science (Jack Daniels VDOT + polarized 80/20). The plugin generates daily workouts, ingests post-workout data (manual or via Strava), and iterates the plan based on adherence and performance signals.

### Primary user (persona)
A runner with a target race date and current performance baseline, training 3–5 days/week, who wants a coach-quality plan that respects rest as sacred and adapts to real life.

### Happy path

```
                         ONE-TIME SETUP
                         ──────────────
   /run-init  ─────►  Coach (opus) interview:
                       • Goal race + target time + date
                       • Current fitness (recent race / time-trial)
                       • Available training days
                       • Lifestyle (sleep, stress, prior mileage)
                       • Methodology preference (polarized default)
                       • Unit preference (time default)
                              │
                              ▼
                    skills: compute-vdot
                            build-training-plan
                              │
                              ▼
              storage/users.json + storage/plan.json
              (macrocycle: base → build → peak → taper)


                         DAILY LOOP
                         ──────────
                          Morning
   /run-today  ─────►  Coach reads plan.json + daily_state.json
                       Emits today's workout card:
                         • Type (E/L/T/I/R/M/Recovery/Rest)
                         • Duration (or distance if user prefers)
                         • Target paces / HR zones / RPE
                         • Warm-up cue (carry-forward from yesterday)

                          Evening
   /run-log    ─────►  WorkoutLogger (sonnet) prompts for:
                         • Actual duration / distance
                         • Avg HR / RPE
                         • Splits (optional)
                         • Free-text notes
                       OR
   /run-sync   ─────►  DataFetcher (sonnet) calls Strava MCP
                       to fetch most recent activity.
                              │
                              ▼
              skills: analyze-workout → adapt-plan
                              │
                              ▼
              storage/workouts.json (append)
              storage/progress.json (rolling stats)
              storage/daily_state.json (carry-forward)
              storage/plan.json (modified if strike rules fire)


                         WEEKLY RITUAL
                         ─────────────
   /run-week   ─────►  Coach: 7-day rollup
                         • Completed vs prescribed mileage
                         • Quality session adherence
                         • Fatigue indicators (HR drift, RPE creep)
                         • Decision: hold / advance / recovery week
                       writes weekly summary to progress.json


                         RACE DAY
                         ────────
   plan.json taper phase auto-engages T-2 or T-3 weeks
   Race-week workouts: shakeouts, opener, race day
   /run-race-recap (post) → triggers 4-day rest + jog protocol
```

---

## 2. Component Inventory

### 2.1 Commands (`/run-*`)

All commands live under `commands/` as `.md` files with YAML front-matter (name, description, argument-hint).

| Command | Argument hint | Triggers | Owning agent | Calls skills |
|---|---|---|---|---|
| `/run-init` | `[--connect strava]` | One-time onboarding interview; produces `users.json` + initial `plan.json` | Coach | `compute-vdot`, `build-training-plan` |
| `/run-today` | (none) | Renders today's workout card from `plan.json` + `daily_state.json` | Coach | `generate-daily-workout` |
| `/run-log` | `[date]` (defaults today) | Manual workout entry interview; appends to `workouts.json`; triggers analyze+adapt | WorkoutLogger | `log-workout`, `analyze-workout`, `adapt-plan` |
| `/run-sync` | `[--days N]` (default 1) | Fetches recent Strava activities, normalizes, runs same analyze+adapt pipeline | DataFetcher | `fetch-strava-activity`, `analyze-workout`, `adapt-plan` |
| `/run-week` | `[--week N]` (default current) | Weekly rollup + recovery-week decision | Coach | `weekly-review` |
| `/run-replan` | `[--reason "..."]` | User-initiated full replan (injury, life event, race change) | Coach | `build-training-plan` |
| `/run-plan` | (none) | Shows current macrocycle view (read-only summary of `plan.json`) | Coach | (no skills, just read) |
| `/run-race-recap` | (post-race) | Writes race result to `progress.json`; computes new VDOT; sets 4-day rest + jog protocol | Coach | `compute-vdot`, `adapt-plan` |
| `/run-research` | `"question"` | Free-form coaching question; web-search backed | Coach | `research-methodology` |

**Justification for additions beyond minimum**:
- `/run-plan` — read-only view is essential UX (users want to see the macrocycle without re-rendering today)
- `/run-race-recap` — race day is a load-bearing event that changes everything; deserves a first-class command
- `/run-research` — escape hatch for novel questions; uses web search per user story ("if web search is needed, the subagent should delegate to it")

### 2.2 Agents

Three specialist agents under `agents/`. Each is a `.md` file with YAML front-matter: `name`, `description`, `model`, `color`, `tools`, `skills`.

#### Coach (`agents/coach.md`)
- **Model**: opus
- **Color**: red
- **Tools**: Read, Write, Edit, Grep, Glob, Bash, WebSearch, WebFetch, `mcp__strava__check-strava-connection`, `mcp__strava__get-athlete-profile` (probe only)
- **Owned skills**: `compute-vdot`, `build-training-plan`, `generate-daily-workout`, `adapt-plan`, `weekly-review`, `research-methodology`, `taper-protocol`, `recovery-protocol`, `probe-strava-connection`
- **Single-writer responsibility**: `users.json`, `plan.json`, `progress.json` (the strategic state)
- **Invoked when**: `/run-init`, `/run-today`, `/run-week`, `/run-replan`, `/run-plan`, `/run-race-recap`, `/run-research`
- **Description**: The head coach. Owns macrocycle design, daily prescription, weekly assessment, and methodology research. Reasoning-heavy → opus. Also performs a one-shot probe at `/run-init` time to verify Strava connectivity via `probe-strava-connection` before setting `connected: true`.

#### WorkoutLogger (`agents/workout-logger.md`)
- **Model**: sonnet
- **Color**: green
- **Tools**: Read, Write, Edit, Grep, Glob, Bash
- **Owned skills**: `log-workout`, `analyze-workout`
- **Single-writer responsibility**: `workouts.json`, `daily_state.json`
- **Invoked when**: `/run-log`
- **Description**: Captures one workout via interview, normalizes to schema, writes to workouts.json, and triggers analyze + adapt. Conversational, fast → sonnet.

#### DataFetcher (`agents/data-fetcher.md`)
- **Model**: sonnet
- **Color**: blue
- **Tools**: Read, Write, Edit, Grep, Glob, Bash, mcp__strava__*
- **Owned skills**: `fetch-strava-activity`; calls `analyze-workout` (shared)
- **Single-writer responsibility**: same files as WorkoutLogger when sourced from Strava (`workouts.json`, `daily_state.json`)
- **Invoked when**: `/run-sync`
- **Description**: Pulls recent activity from Strava MCP, maps to internal workout schema, dedupes against existing entries (by activity_id), then runs the same analyze + adapt path as manual logging.

**Single-writer enforcement note**: WorkoutLogger and DataFetcher both write to `workouts.json` but never simultaneously — the orchestrator routes to exactly one based on the command (`/run-log` vs `/run-sync`). The read-modify-write protocol from jp-learner is preserved: read whole file, mutate in memory, write whole file.

### 2.3 Skills

12 skills under `skills/<kebab-name>/SKILL.md`. Skills with deterministic math get a Python helper (per user preference: code-over-tokens for math).

| # | Skill | Owner | 2-line description | Code? |
|---|---|---|---|---|
| 1 | `compute-vdot` | Coach | Translates one race result (distance + time) into VDOT score and full E/M/T/I/R pace table. Deterministic — runs `scripts/vdot.py`. | Yes (`scripts/vdot.py`) |
| 2 | `build-training-plan` | Coach | Constructs full macrocycle (base/build/peak/taper) from goal + target date + available days. Emits `plan.json` with weekly templates. | Yes (`scripts/macrocycle.py` for date math + phase split) |
| 3 | `generate-daily-workout` | Coach | Picks today's prescription from current plan week + applies daily_state carry-forwards (warm-up notes, fatigue flags). Pure Markdown output. | No |
| 4 | `log-workout` | WorkoutLogger | Conversational capture of duration, distance, RPE, HR, splits, notes. Writes normalized record. | No |
| 5 | `analyze-workout` | WorkoutLogger / DataFetcher | Computes adherence delta vs prescribed: pace deviation %, completion %, HR drift, RPE delta. Returns structured signal dict. | Yes (`scripts/analyze.py`) |
| 6 | `adapt-plan` | Coach | Applies the 1/2/3-strike rules: monitor → reduce intensity → recovery week. Mutates `plan.json` only when thresholds fire. | Yes (`scripts/adapt.py` — pure rule engine) |
| 7 | `weekly-review` | Coach | Aggregates last 7 days: mileage, quality adherence, fatigue trend. Decides: hold / advance / recovery. Writes weekly summary. | Yes (`scripts/weekly.py`) |
| 8 | `fetch-strava-activity` | DataFetcher | Calls Strava MCP `get-recent-activities`, maps fields to internal schema, dedupes by `strava_activity_id`. | No (just MCP plumbing) |
| 9 | `research-methodology` | Coach | Web-search-backed Q&A for novel coaching questions (heat acclimation, altitude, recovery from illness). Cites sources. | No |
| 10 | `taper-protocol` | Coach | Specialized logic for race-week taper: −20%/−40%/−60% volume curve, intensity preservation, race-day shakeout. Called by `build-training-plan` and `adapt-plan` when within 3 weeks of race. | Yes (`scripts/taper.py`) |
| 11 | `recovery-protocol` | Coach | Post-race + injury-flag protocols: 4 days rest, then 30–40 min jog (per user KB). Inserts recovery block into plan. | No |
| 12 | `probe-strava-connection` | Coach | Verifies Strava MCP connectivity via `mcp__strava__check-strava-connection` + `mcp__strava__get-athlete-profile`; returns ok+athlete_id on success or classified error otherwise. Gates `--connect strava` from setting a false-positive `connected:true`. | No |

**Skill structure** (each follows progressive disclosure):
```
skills/<name>/
├── SKILL.md           # entry point + description (front-matter)
├── body.md            # full instructions (loaded on demand)
├── references/        # supporting docs (e.g., vdot-explainer.md)
└── scripts/           # Python helpers (when applicable)
```

### 2.4 Hooks

Modest. Only what enforces invariants the design demands.

| Hook | Trigger | Purpose |
|---|---|---|
| `SessionStart` → `unlogged-workouts.sh` | Session start | Reads `daily_state.json`; if last completed workout date < today AND there's a prescribed workout for that date with no entry in `workouts.json`, emits a one-line reminder: "You have an unlogged workout from {date}. Run `/run-log {date}`." |
| `PostToolUse` (Write/Edit on `plan.json`) → `plan-integrity-check.sh` | After any write to `plan.json` | Validates JSON parses, required fields present, week count matches macrocycle dates. Aborts and rolls back if invalid. (Mirrors jp-learner's invariant style.) |

**Skipped hooks (intentionally)**:
- No `UserPromptSubmit` hook — Coach handles intent classification natively
- No `PreToolUse` hook — file writes are infrequent and small; full validation in PostToolUse is sufficient
- No telemetry hook — out of scope v1

### 2.5 MCPs

| MCP server | Tier | Status | Auth | Purpose | Soft/Hard |
|---|---|---|---|---|---|
| `r-huijts/strava-mcp` | v1 | active | OAuth2 (user-side setup) | Read activities, splits, HR, laps | **Soft** — manual logging is the default; user opts in via `/run-init --connect strava` |
| `Nicolasvegam/garmin-connect-mcp` (read) | v2 | planned | Garmin Connect creds | Direct Garmin pull (alt to Strava) | Soft |
| `st3v/garmin-workouts-mcp` (write) | v2 | planned | Garmin Connect creds | Push generated workouts to watch | Soft |
| Strava webhook (server) | v3 | planned | n/a (push) | Auto-trigger plan iteration on activity completion | n/a — defer to v3 |
| WebSearch (built-in) | v1 | active | n/a | `research-methodology` skill | Hard (always available) |

**Manifest impact**: `.claude-plugin/plugin.json` declares no MCP as required; documentation in README explains opt-in setup for Strava.

**Integration schema fields** (all stored under `users.json.integrations`):
- `preferred_source` (`"manual" | "strava" | "garmin"`) — tiebreaker for same-date workouts from multiple sources. Defaults to `"manual"`; flips to `"strava"` only after a successful probe during `/run-init --connect strava`.
- `connected_at` — ISO 8601 timestamp when the connection was established; `null` until first successful probe.
- `last_sync_at` — ISO 8601 timestamp of the most recent sync attempt; `null` until first `/run-sync`.
- `last_sync_status` — `null | "ok" | "error:<code>"` where codes are: `auth`, `rate_limit`, `mcp_unavailable`, `network`, `unknown`.

---

## 3. Data Model

All persistent state lives under `storage/` (mutable, per-user) or `data/` (read-only, plugin-distributed).

### 3.1 `storage/users.json`

**Single writer**: Coach
**Purpose**: User profile, preferences, current fitness baseline.

```json
{
  "version": 1,
  "user_id": "default",
  "created_at": "2026-04-30T10:00:00Z",
  "profile": {
    "name": "Wilson",
    "age": 38,
    "sex": "M",
    "weight_kg": 68
  },
  "current_fitness": {
    "vdot": 47,
    "vdot_source": "5K time-trial",
    "vdot_source_date": "2026-04-15",
    "vdot_source_result": { "distance_m": 5000, "time_s": 1440 },
    "paces": {
      "easy_per_km_s":     324,
      "marathon_per_km_s": 282,
      "threshold_per_km_s": 264,
      "interval_per_km_s": 240,
      "repetition_per_km_s": 222
    },
    "weekly_mileage_baseline_km": 35
  },
  "preferences": {
    "workout_unit": "time",
    "methodology": "polarized",
    "training_days": ["Tue", "Thu", "Sat", "Sun"],
    "rest_days_sacred": true,
    "long_run_day": "Sun",
    "quality_days": ["Tue", "Sat"],
    "language": "zh-TW"
  },
  "lifestyle": {
    "typical_sleep_hours": 7,
    "stress_level": "moderate",
    "injury_history": [],
    "constraints_notes": "no running on weekday mornings"
  },
  "integrations": {
    "preferred_source": "manual",
    "strava": {
      "connected": false,
      "athlete_id": null,
      "connected_at": null,
      "last_sync_at": null,
      "last_sync_status": null
    },
    "garmin": {
      "connected": false,
      "user_id": null,
      "connected_at": null,
      "last_sync_at": null,
      "last_sync_status": null
    }
  }
}
```

**Field notes**:
- `vdot` is the canonical fitness number; paces are derived (cached for quick reads).
- `workout_unit` toggles whether `/run-today` cards show `45 min @ E pace` vs `8 km @ E pace`. Default `time` per user KB preference.
- `quality_days` are the days where T/I/R workouts can land. Logic enforces no back-to-back quality days.
- `rest_days_sacred: true` blocks the adapter from inserting "make-up" workouts on rest days.
- `preferred_source` (`"manual" | "strava" | "garmin"`) — default `"manual"`. Flips to `"strava"` only after a successful probe via `/run-init --connect strava`. Acts as a tiebreaker: when the same date has workouts from multiple sources, the entry from `preferred_source` wins; the other entry is kept but marked `superseded_by: <winning_id>`.
- `connected_at` / `last_sync_at` / `last_sync_status` — populated at connection time and after each `/run-sync`. `last_sync_status` is `null | "ok" | "error:<code>"` (codes: `auth`, `rate_limit`, `mcp_unavailable`, `network`, `unknown`). The Garmin schema slot is reserved for v2 forward-compatibility.

### 3.2 `storage/plan.json`

**Single writer**: Coach
**Purpose**: The full macrocycle. ~24 weeks for a marathon goal. Structured as phases → weeks → days.

```json
{
  "version": 1,
  "goal": {
    "race": "marathon",
    "target_time_s": 14400,
    "race_date": "2026-10-15",
    "race_name": "Taipei Marathon 2026"
  },
  "methodology": "polarized",
  "macrocycle": {
    "start_date": "2026-04-30",
    "end_date": "2026-10-15",
    "total_weeks": 24,
    "phases": [
      { "name": "base",  "start_week": 1,  "end_week": 10, "focus": "aerobic volume + strides" },
      { "name": "build", "start_week": 11, "end_week": 18, "focus": "T + I development" },
      { "name": "peak",  "start_week": 19, "end_week": 22, "focus": "marathon-specific T + M" },
      { "name": "taper", "start_week": 23, "end_week": 24, "focus": "volume cut, intensity preserve" }
    ]
  },
  "weeks": [
    {
      "week_number": 1,
      "phase": "base",
      "target_volume_min": 240,
      "target_long_run_min": 80,
      "days": [
        { "date": "2026-04-28", "dow": "Tue", "type": "E",     "duration_min": 35, "target_pace": "easy",    "notes": "include 4x20s strides" },
        { "date": "2026-04-30", "dow": "Thu", "type": "E",     "duration_min": 35, "target_pace": "easy",    "notes": "" },
        { "date": "2026-05-02", "dow": "Sat", "type": "E",     "duration_min": 40, "target_pace": "easy",    "notes": "" },
        { "date": "2026-05-03", "dow": "Sun", "type": "L",     "duration_min": 80, "target_pace": "easy",    "notes": "RPE-driven, do not check pace" },
        { "date": "2026-04-29", "dow": "Wed", "type": "Rest",  "duration_min": 0,  "target_pace": null,      "notes": "" },
        { "date": "2026-05-01", "dow": "Fri", "type": "Rest",  "duration_min": 0,  "target_pace": null,      "notes": "" },
        { "date": "2026-04-27", "dow": "Mon", "type": "Rest",  "duration_min": 0,  "target_pace": null,      "notes": "" }
      ]
    }
    /* ... 23 more weeks ... */
  ],
  "last_modified_at": "2026-04-30T10:00:00Z",
  "last_modified_reason": "initial generation"
}
```

**Field notes**:
- `target_pace` is a key into `users.json.current_fitness.paces` (not duplicated — single source of truth). Re-resolved at render time.
- `type` enum: `E`, `L`, `T`, `I`, `R`, `M`, `Strides`, `Recovery`, `Rest`.
- `duration_min` is canonical; if the user prefers distance, the renderer converts using current paces.
- The 3-up-1-down progression: weeks 1/2/3 increase volume, week 4 cuts ~20%. Encoded in `target_volume_min` per week.

### 3.3 `storage/daily_state.json`

**Single writer**: WorkoutLogger / DataFetcher (whoever logs the most recent workout)
**Purpose**: Tomorrow's seed. Carry-forwards from yesterday.

```json
{
  "version": 1,
  "as_of_date": "2026-04-30",
  "carry_forward": {
    "warm_up_cue": "calves felt tight last session — extend dynamic warm-up by 5 min",
    "fatigue_flag": "none",
    "recurring_red_flags": []
  },
  "consecutive_misses": 0,
  "consecutive_ahead": 0,
  "last_workout_id": "wkt-2026-04-29-001",
  "last_workout_quality": "on-target"
}
```

### 3.4 `storage/workouts.json`

**Single writer**: WorkoutLogger / DataFetcher (per command)
**Purpose**: Append-only log of completed workouts.

```json
{
  "version": 1,
  "workouts": [
    {
      "id": "wkt-2026-04-29-001",
      "date": "2026-04-29",
      "source": "manual",
      "strava_activity_id": null,
      "prescribed": {
        "type": "T",
        "duration_min": 40,
        "target_pace_per_km_s": 264,
        "notes": "20 min @ T after 10 min easy warm-up"
      },
      "actual": {
        "duration_min": 38,
        "distance_km": 7.8,
        "avg_pace_per_km_s": 270,
        "avg_hr": 168,
        "max_hr": 178,
        "rpe": 7,
        "splits": [
          { "km": 1, "pace_per_km_s": 320 },
          { "km": 2, "pace_per_km_s": 268 }
        ],
        "notes": "windy on the back stretch"
      },
      "analysis": {
        "completion_pct": 95,
        "pace_delta_pct": 2.3,
        "rpe_delta": 1,
        "hr_drift_bpm": 4,
        "verdict": "on-target"
      }
    }
  ]
}
```

**Field notes**:
- `id` format: `wkt-YYYY-MM-DD-NNN` (NNN handles multi-session days).
- `analysis` is computed by `analyze-workout` skill at log time, then frozen.
- `verdict` enum: `on-target`, `under` (missed), `over` (ahead), `aborted`.

### 3.5 `storage/progress.json`

**Single writer**: Coach (during weekly review and adapt-plan)
**Purpose**: Rolling stats and longitudinal trends. Kept small.

```json
{
  "version": 1,
  "rolling_7d": {
    "mileage_km": 32,
    "duration_min": 215,
    "avg_rpe": 5.2,
    "quality_sessions_completed": 1,
    "quality_sessions_prescribed": 2
  },
  "rolling_28d": {
    "mileage_km": 130,
    "vdot_trend": "+0.3",
    "avg_resting_signal": "stable"
  },
  "weekly_summaries": [
    {
      "week_number": 1,
      "completed_volume_min": 230,
      "prescribed_volume_min": 240,
      "verdict": "hold",
      "notes": "good week, advance to week 2 as planned"
    }
  ],
  "vdot_history": [
    { "date": "2026-04-15", "vdot": 47, "trigger": "5K time-trial" }
  ],
  "race_results": [],
  "last_updated_at": "2026-04-30T10:00:00Z"
}
```

### 3.6 `data/vdot-table.json` (read-only, plugin-distributed)

Static lookup table, VDOT 30–85 → paces (per Daniels' Running Formula tables). Loaded by `compute-vdot` Python helper. ~55 rows × 6 pace columns. Schema documented in `data/vdot-table-schema.md`.

### 3.7 `data/workout-templates.json` (read-only)

Library of reusable workout patterns by phase + type. Example entries:

```json
{
  "templates": [
    {
      "id": "base-E-35",
      "phase": "base",
      "type": "E",
      "duration_min": 35,
      "structure": "easy throughout",
      "notes_template": ""
    },
    {
      "id": "build-T-40",
      "phase": "build",
      "type": "T",
      "duration_min": 40,
      "structure": "10 min easy WU, 20 min @ T, 10 min easy CD",
      "notes_template": "RPE should plateau at 7"
    },
    {
      "id": "peak-I-vo2",
      "phase": "peak",
      "type": "I",
      "duration_min": 50,
      "structure": "10 min WU, 5x3 min @ I (3 min jog rec), 10 min CD",
      "notes_template": "if last interval feels like first, you ran too easy"
    }
  ]
}
```

`build-training-plan` composes weeks by selecting templates from this library.

---

## 4. Adaptive Iteration Loop — Pseudocode

The core loop fires whenever a workout is logged (manual or Strava-sourced). It is the heart of the plugin.

```
function on_workout_logged(workout):
    # ── 1. Compute the analysis ────────────────────────────
    prescribed = lookup_prescribed_workout(workout.date)
    delta = analyze_workout(workout.actual, prescribed)
    # delta = {
    #   completion_pct,
    #   pace_delta_pct,        # signed; +ve = slower than target
    #   rpe_delta,             # signed; +ve = harder than expected
    #   hr_drift_bpm,          # within-session drift
    #   verdict                # 'on-target' | 'under' | 'over' | 'aborted'
    # }

    # ── 2. Persist ─────────────────────────────────────────
    workouts.json.append({...workout, analysis: delta})

    # ── 3. Update rolling progress ─────────────────────────
    progress.rolling_7d = recompute_rolling(workouts, days=7)
    progress.rolling_28d = recompute_rolling(workouts, days=28)

    # ── 4. Strike rules ───────────────────────────────────
    state = read(daily_state.json)

    if delta.verdict == 'under':
        state.consecutive_misses += 1
        state.consecutive_ahead = 0

        if state.consecutive_misses == 1:
            action = 'monitor'                          # no plan change
        elif state.consecutive_misses == 2:
            action = 'reduce_next_quality'              # cut next quality session intensity by 1 step
            adapt_plan(plan, rule='reduce_intensity', target='next_quality')
        elif state.consecutive_misses >= 3:
            action = 'recovery_week'                    # cut volume 30–40%, drop one quality
            adapt_plan(plan, rule='insert_recovery_week', start='next_week')
            state.consecutive_misses = 0                # reset after intervention

    elif delta.verdict == 'over':
        state.consecutive_ahead += 1
        state.consecutive_misses = 0

        if state.consecutive_ahead >= 3:
            new_vdot = users.current_fitness.vdot + 1
            users.current_fitness.vdot = new_vdot
            users.current_fitness.paces = recompute_paces(new_vdot)
            adapt_plan(plan, rule='regenerate_remaining_paces')
            state.consecutive_ahead = 0

    elif delta.verdict == 'on-target':
        state.consecutive_misses = 0
        state.consecutive_ahead = 0
        # no plan change

    elif delta.verdict == 'aborted':
        state.consecutive_misses += 1                   # treated as a miss
        # check fatigue signals: if hr_drift_bpm > 8 AND rpe_delta >= 2,
        # promote to recurring_red_flag
        if delta.hr_drift_bpm > 8 and delta.rpe_delta >= 2:
            state.carry_forward.recurring_red_flags.append({
                date: today,
                signal: 'high_drift_high_rpe'
            })
            if count(recurring_red_flags, last_14_days) >= 2:
                adapt_plan(plan, rule='insert_recovery_week', start='next_week')

    # ── 5. Carry-forward seeding ──────────────────────────
    state.last_workout_id = workout.id
    state.last_workout_quality = delta.verdict
    state.carry_forward.warm_up_cue = derive_warm_up_cue(workout, delta)
    state.as_of_date = workout.date

    # ── 6. Persist state ──────────────────────────────────
    write(daily_state.json, state)
    write(progress.json, progress)
    if plan_was_modified:
        write(plan.json, plan)        # PostToolUse hook validates integrity
```

### Threshold definitions (calibrated, conservative)

| Signal | Threshold for "under" verdict | Threshold for "over" verdict |
|---|---|---|
| `completion_pct` | < 80% | — |
| `pace_delta_pct` | > +5% (slower) | < -3% (faster) AND `rpe_delta <= 0` |
| `rpe_delta` | > +2 | — (no rpe-only trigger; v0.2) |
| `hr_drift_bpm` (intra-session) | > 8 ⇒ promote to red flag | n/a |

A workout is "under" if **any two** of: completion, pace, RPE thresholds are exceeded. "Over" requires **both** faster-than-prescribed pace AND non-elevated RPE — i.e., a genuine over-fitness signal must include actual faster pace, not just a low RPE on a self-paced slow run.

**v0.2 change** — the prior `rpe_delta < -1` solo trigger for "over" was removed after dogfooding on 2026-05-01: a runner who self-paces slower than prescribed and reports correspondingly low RPE was being falsely flagged as ahead-of-fitness. Real over-fitness shows up as faster pace at lower RPE, not lower RPE alone.

---

## 5. Decisions on Open Questions

### Q1: Plan length — target-date driven or fixed templates?
**Decision**: Target-date driven, with **min 8-week guard** and **max 24-week cap**.
**Reasoning**: User explicitly said "I can set a goal that I want to achieve at a target date." Fixed templates ignore date math. The 8-week minimum prevents unsafe ramping for races scheduled too close. The 24-week cap matches Daniels' standard marathon block; longer plans suffer from compliance drift and life-event noise. If the race is >24 weeks out, we generate a 24-week block ending at race date and label the pre-block period as "general fitness — replan when within 24 weeks."

### Q2: Multi-race vs single-race?
**Decision**: **Single primary target** in v1, with `goal.tune_up_races[]` as optional sub-array (max 2).
**Reasoning**: Multi-race stacks add significant complexity (priority management, recovery between races, peaking conflicts) for marginal v1 value. Most runners have one big goal. Tune-up races (e.g., a 10K six weeks out) are common and easy to model as fixed dates that swap one quality session for race-week mini-taper. Full multi-race orchestration deferred to v2.

### Q3: Strava MCP soft vs hard dependency?
**Decision**: **Soft**, per Riko's recommendation.
**Reasoning**: Hard dependency creates an install cliff (OAuth setup before any value). Manual logging via `/run-log` is a complete, working flow on its own. Strava connection is opt-in via `/run-init --connect strava` or post-hoc `/run-init --connect strava` re-run. The `integrations.strava.connected` flag in `users.json` gates `/run-sync` availability.

### Q4: Time vs distance prescription?
**Decision**: **Time default**, distance toggle available.
**Reasoning**: User KB explicitly says "Train by TIME, not distance — body remembers work-time." This is also methodologically sound (different terrain/conditions make distance unreliable as a load proxy). Toggle exists in `users.preferences.workout_unit` for users who think in distance. Renderer in `generate-daily-workout` adapts. Internally, all storage is in minutes (canonical).

---

## 6. Out of Scope for v1

Explicit non-goals:

1. **Nutrition / fueling guidance** — separate domain, deserves its own plugin
2. **Strength training prescription** — supplementary, complex programming, leave to user
3. **Injury rehab guidance** — liability + needs PT context; v1 only flags red flags and recommends rest
4. **Multi-sport (cycling/swimming) cross-training** — running-only focus by name and scope
5. **Garmin write-back** (push workout to watch) — v2; requires `st3v/garmin-workouts-mcp` integration
6. **Strava webhook auto-sync** — v3; needs server infra
7. **Social features** (sharing plans, leaderboards) — out of scope entirely
8. **Heat/altitude acclimation programming** — v2; addressable via `research-methodology` ad-hoc in v1
9. **Multi-user / team coaching** — single-user plugin

---

## 7. v1 → v2 → v3 Milestones

### v1 (MVP) — 4–6 weeks of build
**Ships**:
- All 9 commands (manual-logging path complete)
- All 12 skills (with Python helpers for VDOT, macrocycle, analysis, adaptation, weekly review, taper)
- Coach + WorkoutLogger + DataFetcher agents (fully wired — no stubs)
- All storage schemas
- `data/vdot-table.json` + `data/workout-templates.json` populated
- 2 hooks (SessionStart reminder + plan-integrity)
- README with onboarding walkthrough
- End-to-end happy path: `/run-init` → `/run-today` → `/run-log` → `/run-week`
- Strava read (soft, opt-in via `/run-init --connect strava`); manual remains the default. Probe-based connection (no false positives). Dedup + multi-source coexistence via `preferred_source` tiebreaker.

### v2 — Garmin read + tune-up races
**Ships**:
- Optional Garmin Connect read (alternate to Strava; schema slot reserved in v0.2.0 users.json)
- Cross-provider dedup (Strava + Garmin)
- `goal.tune_up_races[]` support
- Methodology toggle: pyramidal in addition to polarized

### v3 — Closed loop + automation
**Ships**:
- Garmin workout write-back (push to watch via `st3v/garmin-workouts-mcp`)
- Strava webhook server companion → auto-trigger `/run-sync` on new activity
- Heat/altitude acclimation modules
- Multi-race orchestration (priority-A, priority-B with peaking conflict resolution)

---

## 8. Acceptance Criteria for This Design

The design is "good enough to start building" when the user can affirm all of the following:

1. **Component inventory is complete**: Every command, agent, skill, hook, and MCP integration is named with a clear owner and purpose. No "TBD" on critical-path items.
2. **Data model is concrete**: All five storage files have JSON examples with realistic values; every field has a single, named writer; no ambiguity about who mutates what.
3. **Adaptive loop is precise**: The 1/2/3-strike rules have exact thresholds (not "if behind"); pseudocode runs end-to-end without hand-waving.
4. **Methodology grounding is verifiable**: VDOT, polarized 80/20, 3-up-1-down progression, taper curve are all referenced by name in skill descriptions and tied to specific files (`scripts/vdot.py`, `data/vdot-table.json`, etc.).
5. **User KB preferences honored**: Time-default, rest-days-sacred, easy-runs-short, RPE-driven long runs all show up as concrete defaults in `users.json` schema or skill logic.
6. **Open questions resolved**: All four open questions have decisions with stated reasoning.
7. **Scope discipline visible**: At least 5 explicit non-goals listed; v1/v2/v3 milestone split makes MVP tight.
8. **Build is sequenceable**: Implementation order (next section) lets day-1 work begin productively without blocking on later decisions.

If any of these fail user review, iterate the design before implementation begins.

---

## 9. Implementation Order

Optimized so the day-1 build hits a working `/run-init` → `/run-today` flow with manual logging only. Strava/Garmin integration deferred.

### Phase 1 — Skeleton (day 1)
1. Create `.claude-plugin/plugin.json` (name, version 0.0.1, description, author)
2. Create directory tree: `agents/`, `commands/`, `skills/`, `data/`, `storage/`, `hooks/`
3. Create empty `storage/*.example.json` templates for all 5 storage files (committed as examples; real files written at `/run-init` time)
4. Create `data/*-schema.md` docs for vdot-table and workout-templates

### Phase 2 — Static data (day 1–2)
5. Populate `data/vdot-table.json` from Daniels' Running Formula tables (VDOT 30–85)
6. Populate `data/workout-templates.json` with ~30 templates covering base/build/peak/taper × E/L/T/I/R/M

### Phase 3 — Deterministic helpers (day 2–3)
7. Write `skills/compute-vdot/scripts/vdot.py` — race time → VDOT (lookup + interpolation), VDOT → pace table
8. Write `skills/build-training-plan/scripts/macrocycle.py` — date math, phase split, week generation
9. Write `skills/analyze-workout/scripts/analyze.py` — delta computation
10. Write `skills/adapt-plan/scripts/adapt.py` — strike-rule engine
11. Write `skills/weekly-review/scripts/weekly.py` — rollups + recovery decision
12. Write `skills/taper-protocol/scripts/taper.py` — taper curve generator
13. Unit tests for each Python helper (pytest, run via Bash)

### Phase 4 — Skills as Markdown (day 3–4)
14. Write SKILL.md + body.md for all 12 skills, referencing scripts where applicable
15. Skills follow progressive disclosure (front-matter description short; body loaded on demand)

### Phase 5 — Agents (day 4)
16. Write `agents/coach.md` (opus, full toolset, owns 8 skills)
17. Write `agents/workout-logger.md` (sonnet, owns log-workout + analyze-workout)
18. Write `agents/data-fetcher.md` (sonnet, owns fetch-strava-activity; wired to Strava MCP in Phase 11)

### Phase 6 — Commands (day 4–5)
19. Write all 9 `/run-*` command files with argument hints and agent routing
20. Smoke test: invoke each command, confirm correct agent activation

### Phase 7 — Hooks (day 5)
21. Write `hooks/session-start.sh` (unlogged-workout reminder)
22. Write `hooks/plan-integrity-check.sh` (PostToolUse on plan.json writes)
23. Wire hooks in `.claude-plugin/plugin.json`

### Phase 8 — End-to-end test (day 5–6)
24. Run `/run-init` with synthetic test data (sub-4 marathon, 5K=24:00, Tue/Thu/Sat/Sun)
25. Verify `users.json` and `plan.json` produced correctly
26. Run `/run-today` — confirm card renders
27. Run `/run-log` with on-target workout → verify analysis + state update
28. Run `/run-log` 3× with under-target workouts → verify recovery week inserts
29. Run `/run-week` → verify rollup + verdict
30. Run `/run-replan --reason "schedule change"` → verify regeneration

### Phase 9 — Documentation (day 6)
31. Write top-level `README.md` with install, onboarding walkthrough, command reference
32. Write `docs/methodology.md` explaining VDOT, polarized 80/20, strike rules

### Phase 10 — v1 release
33. Tag plugin v0.1.0
34. User dogfood for 1–2 training weeks
35. Iterate based on real-use feedback; Strava read wiring follows in Phase 11

### Phase 11 — Strava read wiring (post-v0.1 patch)
36. **Schema patches** — update `storage/users.example.json` with new `integrations` block (`preferred_source`, `connected_at`, `last_sync_at`, `last_sync_status`) and patch DESIGN.md to resolve §2.5 vs §7 contradiction in favor of v1 Strava.
37. **Python helper + tests** — create `skills/fetch-strava-activity/scripts/strava_normalize.py` with pure functions (`normalize_activity`, `parse_rpe_from_notes`, `is_duplicate`, `upsert_workout`) and matching pytest suite; all tests must be green before any wiring proceeds.
38. **`probe-strava-connection` skill** — new skill that checks MCP availability, calls `mcp__strava__check-strava-connection` + `mcp__strava__get-athlete-profile`, and returns structured `{ok, athlete_id}` or classified error (`mcp_unavailable`, `auth`, `unknown`).
39. **Agent updates** — add `mcp__strava__check-strava-connection` + `mcp__strava__get-athlete-profile` + `probe-strava-connection` to Coach; add `mcp__strava__*` namespace to DataFetcher and replace v1 stub body with the real read flow.
40. **Command updates** — update `run-init.md` to invoke the probe skill when `--connect strava` is supplied and surface the result; update `run-sync.md` to drop v1 framing and document failure modes.
41. **README + version bump** — add "Connecting Strava (optional)" section, update status block, bump `plugin.json` version to `0.2.0`.

**Critical-path observation**: Steps 1–13 unblock all downstream work. Steps 14–22 can partially parallelize (skills and agents are independent files). Phase 8 is the gate that proves MVP integrity.

---

**Awaiting user approval before any implementation begins.**
