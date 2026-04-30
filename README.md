# running-coach

Adaptive running training plugin for Claude Code. Generates a personalized macrocycle from your race goal, prescribes daily workouts using Daniels' VDOT pacing, and iterates the plan after every workout based on actual performance.

## What it does

- Set a race goal with target date and current fitness baseline
- Get a complete training plan (base → build → peak → taper) generated from Daniels' VDOT methodology and polarized 80/20 intensity distribution
- See today's workout card with target paces, RPE expectations, and warm-up cues
- Log each workout (manual entry; Strava integration in v2)
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
| `/run-today` | Show today's workout card |
| `/run-log [date]` | Log a completed workout (triggers adaptive iteration) |
| `/run-sync [--days N]` | Pull recent activities from Strava (v2) |
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

## Components

- **3 agents**: Coach (opus, head coach), WorkoutLogger (sonnet, captures runs), DataFetcher (sonnet, Strava — v2)
- **9 commands** (above)
- **11 skills** (compute-vdot, build-training-plan, generate-daily-workout, log-workout, analyze-workout, adapt-plan, weekly-review, fetch-strava-activity, research-methodology, taper-protocol, recovery-protocol)
- **2 hooks**: SessionStart (unlogged-workout reminder), PostToolUse (plan.json integrity check)
- **Static data**: VDOT pace table (VDOT 30–85), workout templates (~30 entries across base/build/peak/taper)
- **Storage**: 5 mutable per-user JSON files (users, plan, daily_state, workouts, progress)

## Status

v0.1 ships:
- Manual logging path (`/run-log`) end-to-end
- Daniels VDOT + polarized 80/20
- 24-week max macrocycle, 8-week min
- Single primary race target (multi-race in v2)

Out of scope for v1: nutrition, strength, injury rehab, multi-sport, Garmin write-back, Strava sync (v2), social features.

## Methodology citations

Plugin grounding sources:
- Jack Daniels, *Daniels' Running Formula* (Human Kinetics) — VDOT pacing, periodization
- Stephen Seiler — polarized 80/20 intensity distribution
- Bosquet et al. (2007) — taper meta-analysis
- See `docs/methodology.md` for the full reading list.

## License

MIT
