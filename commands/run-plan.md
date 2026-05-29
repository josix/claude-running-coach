---
description: Show the current macrocycle (read-only summary).
argument-hint: ""
---

# /run-plan

## Purpose

Display a bird's-eye view of your entire training plan — all phases, weekly volumes, and key workouts — so you can see the full arc from today to race day. This command is read-only; it makes no changes to any storage file.

## Action

Delegate to **Coach**. Coach reads `storage/plan.json` and renders a phase-by-phase Markdown summary.

## Output Format

```
Current Training Plan — Taipei Marathon 2026 (Oct 15)
Total: 24 weeks | Today: Week 3 of Base Phase

Phase definitions (first use):
  Base  — pile up easy miles to build aerobic foundation before adding intensity.
  Build — add quality sessions on top of the aerobic base.
  Peak  — race-specific work at highest volume and intensity; brief and demanding.
  Taper — cut volume before race day while maintaining intensity.

Pace codes (first use):
  E — Easy: conversational pace; you can chat in full sentences.
  M — Marathon: pace you'd hold for a full marathon; comfortably steady.
  T — Threshold: comfortably hard; speak a few words, not a full sentence.
  I — Interval: hard reps of 3–5 min at roughly 5K race effort.
  R — Repetition: short, fast strides at roughly mile race effort.
  L — Long run: the week's longest run, usually at Easy pace.

Phase    | Weeks   | Focus                          | Volume/wk | Key Workouts
---------|---------|--------------------------------|-----------|----------------------
Base     | 1–10    | Aerobic volume + strides       | 240 min   | E, L, Strides
Build    | 11–18   | Threshold + Interval dev       | 280 min   | T, I, L
Peak     | 19–22   | Marathon-specific T + M        | 300 min   | M, T, L (long)
Taper    | 23–24   | Volume cut, intensity preserve | 160 min   | E, T (short), Shakeout

▶ Current week (Week 3):
  Tue  E  35 min
  Thu  E  35 min
  Sat  E  40 min (include 4x20s strides)
  Sun  L  80 min (RPE-driven)
```

> For full definitions, see `references/glossary.md`.

Highlights the current week row with a ▶ indicator. If no plan exists, prompt the runner to run `/run-init`.
