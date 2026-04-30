# Post-Race Recovery Protocol — Reference

## The 4+3 Protocol

**Source**: User's training knowledge base highlight + corroborated by standard coaching literature.

> "Post-race: minimum 4 days complete rest, then return with 30-40 min easy jog."

This maps to the `recovery-protocol` implementation:
- **Days 1-4**: Complete rest. No running, no cross-training. Sleep and nutrition priority.
- **Days 5-7**: Recovery jogs at 30-40 min, Easy pace, RPE ≤ 4. Stop immediately if any pain.
- **Day 8+**: Resume normal training at the appropriate plan week.

## Rationale

### Why 4 days of complete rest?

Marathon and half-marathon racing causes significant musculoskeletal stress beyond what training loads produce. Key physiological markers:

- **Muscle fiber damage**: Eccentric loading during downhill sections causes sarcomere disruption detectable by biopsy for 7-14 days post-race.
- **Inflammatory markers**: CK (creatine kinase) and IL-6 peak at 24-48h; return to baseline in 3-5 days for half-marathon, 5-7 days for marathon.
- **Immune suppression**: The "open window" hypothesis — immune function is depressed for 3-72h after intense effort, increasing infection risk.

Even when the runner "feels fine" at day 2, cellular repair is ongoing. The 4-day floor reflects the minimum time for the acute inflammatory phase to resolve.

### Why only 30-40 min easy on the return?

The return-to-run volume is deliberately conservative:
- Easy pace ensures no glycolytic demand on still-depleted muscle glycogen stores.
- 30-40 min is long enough to assess readiness without creating additional stress.
- RPE ≤ 4 as a hard ceiling: if the run requires more effort than "conversational", stop.

### Shorter races (5K, 10K)

For races shorter than a half-marathon, the protocol can be compressed:
- 5K: 1-2 days rest, then easy running resumed.
- 10K: 2-3 days rest, then easy running.
- Half-marathon: 3-4 days rest (use the full 4-day floor to be safe).
- Marathon: use the full 4+3 protocol.

The `recovery-protocol` skill currently applies the full protocol regardless of race distance. Future versions may parameterize based on race distance.

## References

1. **Cheung, K., Hume, P., Maxwell, L. (2003)** — Delayed onset muscle soreness: Treatment strategies and performance factors. *Sports Medicine* 33(2):145-164.
2. **Pedersen, B.K., Ullum, H. (1994)** — NK cell response to physical activity: possible mechanisms of action. *Medicine & Science in Sports & Exercise*.
3. **Pfitzinger, P., Douglas, S. (2009)** — *Advanced Marathoning, 2nd Ed.* Chapter on recovery. Human Kinetics.
4. **Daniels, J. (2014)** — *Daniels' Running Formula, 3rd Ed.* Recovery guidelines post-competition. Human Kinetics.

## Plugin implementation note

The `recovery-protocol` skill hardcodes the 4+3 split. If the user's training philosophy differs (e.g., they follow a more aggressive return protocol), Coach should surface the default and ask for confirmation before applying. The user's knowledge-base preference ("minimum 4 days complete rest") is canonical for this plugin.
