# Research Methodology — Instructions

## Inputs

- Free-form question string from the user (via `/run-research "question"` or in-conversation).
- Context from `storage/users.json` (VDOT, current phase, training days) — include as background when relevant to the search.

## Steps

1. Parse the question and identify the core coaching topic (e.g., "heat adaptation", "return from illness", "downhill pacing").
2. Generate 2-3 search query variants. Bias toward evidence-based or peer-reviewed sources. Example variants for "running in heat":
   - `"heat acclimation running protocol research"`
   - `"running performance hot weather training adaptation Stacy Sims"`
   - `"heat training VO2max impact running Daniels"`
3. Run WebSearch for each variant. Review results for relevance and source quality (prefer sources from `references/sources.md`).
4. WebFetch the top 2-3 most relevant pages. Extract key claims, numbers, and recommendations.
5. Synthesize: write a 200-400 word answer that:
   - States the key finding upfront
   - Provides actionable numbers where available (e.g., "10-14 days of heat exposure before an event")
   - Acknowledges uncertainty or individual variation
   - Cites 2-3 sources inline (URL or author + title)
   - If the answer surfaces jargon not in `references/glossary.md`, invents a brief plain-English gloss in the same one-sentence shape (≤ 12 words) so research-mode output stays accessible to all runners.
6. If the answer implies a training modification:
   - State it explicitly as a proposal: "Based on this, I'd suggest [specific change]. Should I apply it to your plan?"
   - Do NOT call `adapt-plan` or write any file until the user confirms.
7. If no useful results are found, say so clearly and offer to rephrase the question.

## Output

Markdown answer block in the conversation:

```markdown
## Research: {question}

{200-400 word answer}

**Sources:**
1. {Source 1 — title + URL}
2. {Source 2 — title + URL}
3. {Source 3 — optional}

---
**Plan modification proposal (optional):**
> {Specific suggestion}. Should I apply this to your current plan?
```

## Examples

**Question: "How do I run a hilly marathon course?"**
→ Search: "hilly marathon pacing strategy", "uphill running economy", "Pfitzinger hill strategy"
→ Answer covers: effort-based pacing on uphills, controlled descent technique, example pace adjustments
→ No plan modification needed; purely informational

**Question: "I have a cold — when can I run again?"**
→ Search: "returning to running after illness research", "above neck below neck rule running"
→ Answer: "above-the-neck rule" — light symptoms OK; systemic/fever → full rest until 24h symptom-free
→ Proposal: "Insert 3 rest days starting today and push back this week's quality session. Confirm?"

## Edge cases

- **No search results**: tell the user, offer to rephrase.
- **Conflicting sources**: present both perspectives; note the disagreement.
- **Question is about injury treatment**: do NOT prescribe. Provide general information and recommend a physio or sports medicine doctor.
- **Question has a clear answer in VDOT methodology**: answer from knowledge directly without searching. Reserve WebSearch for genuinely novel questions to avoid unnecessary tool calls.
