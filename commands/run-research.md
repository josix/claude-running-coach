---
description: Free-form coaching question, web-search backed.
argument-hint: "\"your question\""
---

# /run-research

## Purpose

Ask any running or coaching question and receive a synthesized, evidence-based answer backed by current web sources. Use this for topics not directly covered by your training plan — heat acclimation, altitude training, recovery from illness, fueling strategies, injury prevention, cross-training, or anything else.

## Inputs

- **question** (required): Your question as a quoted string. Examples:
  - `"How should I adjust my training in hot and humid weather?"`
  - `"What are the signs of overtraining syndrome?"`
  - `"How many days of easy running after a half marathon before resuming quality sessions?"`

## Action

Delegate to **Coach**. Coach will call `research-methodology`, which:

1. **Generates 2–3 query variants** from the question to maximize coverage (e.g., academic phrasing + practitioner phrasing + specific scenario phrasing).

2. **Runs WebSearch + WebFetch** on each variant, targeting peer-reviewed sources, established coaching resources (Jack Daniels, 80/20 Endurance, Pfitzinger, RunningPhysio), and recent sport-science literature.

3. **Synthesizes a 200–400 word answer** in the runner's preferred language, with:
   - Direct answer to the question
   - Key evidence or reasoning
   - Practical recommendations
   - 2–4 inline citations (source name + URL)

4. **Surfaces any plan-modification recommendation** if the research finding suggests a change to the current training plan (e.g., "Based on this, you may want to reduce intensity for the next 5 days"). This recommendation is **for user confirmation only** — Coach does NOT auto-apply changes from research. The runner must explicitly confirm before anything in `plan.json` is touched.

## Important Notes

- Research answers are advisory. They do not replace medical advice for injuries or illness.
- If the answer directly supports modifying the plan, Coach will describe the proposed change and ask "Shall I apply this to your plan?" before making any edits.
- For injury-related questions, Coach will always recommend consulting a physiotherapist or sports medicine professional alongside any general guidance.
