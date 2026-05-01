---
description: One-time onboarding — interview the runner about goal, fitness, training days, lifestyle. Generates users.json + plan.json. Optionally connect Strava with --connect strava.
argument-hint: "[--connect strava]"
---

# /run-init

## Purpose

Set up a brand-new runner profile and generate a personalized training plan. This command collects your race goal, current fitness level, and lifestyle constraints, then builds a full macrocycle tailored to your target date.

Run this once when starting the plugin for the first time. You can also re-run it with `--connect strava` to probe and connect your Strava account.

## Action

Delegate to **Coach**. Coach will:

1. **Interview the runner** — one question at a time — collecting:
   - Goal race (marathon, half, 10K, 5K, or custom distance)
   - Target finish time
   - Race date
   - Recent race result or time-trial result (used to seed VDOT — if none, Coach will offer a time-trial plan)
   - Available training days per week (which days of the week)
   - Lifestyle context (typical sleep hours, stress level, prior weekly mileage, injury history)
   - Methodology preference (polarized default; pyramidal available)
   - Unit preference (time default; distance available)

2. **Call `compute-vdot`** — translates the race result into a VDOT score and full E/M/T/I/R pace table.

3. **Call `build-training-plan`** — constructs the full macrocycle (base → build → peak → taper) from today through the race date, respecting the 8-week minimum and 24-week maximum. Selects weekly templates from `data/workout-templates.json`.

4. **Write `storage/users.json`** — saves the full user profile including fitness baseline and preferences.

5. **Write `storage/plan.json`** — saves the generated macrocycle with all weeks and days.

### If `--connect strava` is supplied

After writing the initial `users.json`, Coach will attempt to connect Strava via the `probe-strava-connection` skill:

1. **Call `probe-strava-connection`** — checks MCP availability, calls `mcp__strava__check-strava-connection`, then `mcp__strava__get-athlete-profile` to capture identity.

2. **If probe returns `ok: true`**:
   - Write `users.json.integrations.strava`:
     ```json
     {
       "connected": true,
       "athlete_id": <athlete_id from probe>,
       "connected_at": "<now ISO 8601>",
       "last_sync_at": null,
       "last_sync_status": null
     }
     ```
   - Set `users.json.integrations.preferred_source = "strava"`.
   - Confirm to the user: "Connected as @{username}. `/run-sync` will pull your recent runs."

3. **If probe returns `ok: false`**:
   - Leave `users.json.integrations.strava.connected = false` and `preferred_source = "manual"`.
   - Surface the probe's `user_message` verbatim so the user knows what to fix.
   - Onboarding still completes the manual path — the runner has a working plan immediately.

## Prerequisites for `--connect strava`

Before running `/run-init --connect strava`, set up the Strava MCP server:

1. **Install the MCP server**: https://github.com/r-huijts/strava-mcp
2. **Create a Strava API app**: https://www.strava.com/settings/api
3. **Set environment variables** in your Claude Code MCP server configuration:
   - `STRAVA_CLIENT_ID` — your Strava API app client ID
   - `STRAVA_CLIENT_SECRET` — your Strava API app client secret
   - `STRAVA_REFRESH_TOKEN` — a valid refresh token (obtained via the OAuth flow documented in the MCP server README)
4. **Add to MCP config**: follow https://docs.anthropic.com/en/docs/claude-code/mcp to register the server in your Claude Code configuration.
5. Restart Claude Code so the new MCP server is loaded, then run `/run-init --connect strava`.

If setup is not complete, the probe will return `mcp_unavailable` or `auth` and the onboarding will fall back to manual logging. You can re-run `/run-init --connect strava` at any time once setup is complete.

## Output

After completion, display:
- A welcome message with the runner's name and goal
- VDOT score and the five training paces (Easy, Marathon, Threshold, Interval, Repetition)
- A macrocycle overview: phase names, week ranges, and focus areas
- Today's first prescribed workout (so the runner knows what to expect immediately)
- If Strava connected: confirmation with athlete username and instructions to use `/run-sync`
- A prompt to run `/run-today` to see today's full workout card

## Notes

If `storage/users.json` already exists, ask the runner whether to overwrite or start fresh. Preserving the existing file and running `/run-replan` instead is often the better choice after a mid-cycle event.
