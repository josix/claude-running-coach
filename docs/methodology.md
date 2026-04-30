# Methodology

`running-coach` is grounded in modern, evidence-based endurance training. This document explains the principles encoded in the plugin and cites the literature.

## VDOT — the fitness number

Jack Daniels' VDOT is a single number that summarizes running fitness, derived from any recent race result. From VDOT, the plugin computes five training paces:

| Zone | Daniels label | % VDOT | Purpose |
|---|---|---|---|
| Easy | E | ~70% | Aerobic base, mitochondrial density, fat oxidation |
| Marathon | M | ~84% | Race-specific endurance, fueling rehearsal |
| Threshold | T | ~88% | Lactate clearance |
| Interval | I | ~98% | VO2max ceiling |
| Repetition | R | ~110% | Running economy, neuromuscular speed |

The plugin's VDOT table is anchored to Jack Daniels' published values (sourced from a verbatim PDF reproduction); pace columns and race-time predictions for missing rows are filled using Daniels' VO2 and fraction-of-VO2max regression formulas:

```
VO2(v) = -4.60 + 0.182258 v + 0.000104 v²
f(t)   = 0.8 + 0.1894393·e^(-0.012778·t) + 0.2989558·e^(-0.1932605·t)
VDOT   = VO2(d/t) / f(t)
```

## Polarized 80/20 intensity distribution

Stephen Seiler's research on world-class endurance athletes shows a consistent pattern: ~80% of training time at low intensity (Easy / Long), ~20% at high intensity (Threshold / Interval / Repetition), with little time in the moderate "junk mile" zone. A 2025 Nature *Scientific Reports* study on personalized training (cite link) found polarized produced ~30% greater marathon improvement than pyramidal in responder clusters.

`running-coach` defaults to polarized 80/20. A pyramidal toggle is planned for v2 to handle the ~32% of runners who respond better to a slightly less polarized distribution.

## Macrocycle structure

A marathon macrocycle is split into four phases:

| Phase | Proportion | Focus |
|---|---|---|
| Base | ~50% | Aerobic volume + strides; build the engine |
| Build | ~25% | Threshold + interval development |
| Peak | ~15% | Marathon-specific quality (long runs with M-pace, race-pace tempo) |
| Taper | ~10% (2-3 weeks) | Volume cut, intensity preservation |

Plans are 8 to 24 weeks long, anchored to the race date.

## Weekly progression — 3-up-1-down

The "10% rule" is folklore (JOSPT 2014 review found no evidence supporting it). `running-coach` uses a 3-up-1-down progression: weeks 1/2/3 increase volume ~10–15%, week 4 cuts ~20% to allow consolidation. This pattern has stronger empirical backing and matches what most successful sub-elite plans actually use (PMC quantitative analysis of 92 plans, 2024).

## Adaptive iteration — strike rules

Coaches don't change plans after one bad workout — they monitor. They do change after a pattern emerges. `running-coach` encodes that judgment:

- **1 miss** — monitor; humans have bad days
- **2 misses** — reduce intensity; the prescription may be slightly too aggressive
- **3 misses** — insert a recovery week; the body needs absorption time
- **3 on-target** — bump VDOT; you've adapted, paces should tighten

Aborted workouts with high HR drift + high RPE flag fatigue. Two such flags in 14 days trigger a recovery week.

## Tapering

Per Bosquet et al.'s 2007 meta-analysis of 27 taper studies and Smyth & Lawlor (2021): a marathon taper should be 2–3 weeks long, cutting volume ~40–60% by race week while preserving intensity. Expected gain: 2–3% (3–6 minutes for a 3-hour marathoner). The plugin's `taper-protocol` skill applies this curve automatically.

## Time-based prescription

Workouts are prescribed in **minutes**, not kilometers. This is a deliberate choice grounded in:
1. Body adapts to time-on-feet, not arbitrary distance markers
2. Terrain, weather, and footing make distance unreliable as a load proxy
3. Distance prescription invites mid-run pace-policing, which produces surge/sag oscillation and erodes the meditative quality of easy running

A distance toggle exists for runners who think in kilometers (`users.preferences.workout_unit: "distance"`), but the default is time.

## Rest is sacred

The plugin treats rest days as load-bearing, not gaps. The strike-rule engine never schedules make-up workouts on rest days. Easy days stay easy (30–40 minutes default); the urge to extend them is a common amateur mistake.

## Sources

- Daniels, Jack. *Daniels' Running Formula*. Human Kinetics, 4th ed., 2021.
- Pfitzinger, Pete. *Advanced Marathoning*. Human Kinetics.
- Seiler, Stephen. "What is Best Practice for Training Intensity and Duration Distribution in Endurance Athletes?" *International Journal of Sports Physiology and Performance*, 2010.
- Bosquet, L., Montpetit, J., Arvisais, D., Mujika, I. (2007). "Effects of tapering on performance: a meta-analysis." *Medicine and Science in Sports and Exercise*.
- Smyth, B., Lawlor, A. "Longer disciplined tapers improve marathon performance." *Frontiers in Physiology*, 2021.
- Nature *Scientific Reports* 2025 — "Machine learning-based personalized training: pyramidal vs polarized" (https://www.nature.com/articles/s41598-025-25369-7)
- JOSPT 2014 review of the "10% rule"

For implementation details and the strike-rule pseudocode, see `DESIGN.md` §4.
