---
name: research-methodology
description: "Web-search-backed Q&A for novel coaching questions outside the plan's standard logic: heat acclimation, recovery from illness, pacing strategies for unique courses. Use for /run-research and when the Coach cannot answer from training data alone."
---

# Research Methodology

Uses WebSearch and WebFetch to answer novel running and coaching questions that fall outside the plugin's built-in logic. Synthesizes 2-3 reputable sources into a 200-400 word answer and cites them explicitly. If the answer implies a plan modification, it surfaces the suggestion for user confirmation before any change is applied.

## When to use

- The user runs `/run-research "question"` with a free-form coaching or physiology question.
- Coach is asked something it cannot answer reliably from its training data (e.g., heat acclimation timelines, altitude adjustment, post-illness return protocol).
- A question falls outside VDOT methodology or the polarized 80/20 framework.

## Outputs

A 200-400 word synthesized answer in the conversation, with 2-3 cited sources. If a plan modification is recommended, a clear proposal is surfaced — but NOT auto-applied. The user must confirm before any skill mutates `plan.json`.

See `body.md` for the full research and synthesis process and `references/sources.md` for preferred coaching sources.
