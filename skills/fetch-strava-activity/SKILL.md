---
name: fetch-strava-activity
description: "Pulls recent run activities from the Strava MCP server, normalizes them to the workouts.json schema, and deduplicates by strava_activity_id. Use for /run-sync. Requires users.integrations.strava.connected = true. v1 stub: returns a polite redirect to /run-log."
---

# Fetch Strava Activity

Intended to connect to the Strava MCP server, retrieve recent run activities, normalize each to the internal workout schema, deduplicate against existing `workouts.json` entries, and run the same `analyze-workout` + `adapt-plan` pipeline as manual logging. In v1 this skill is a stub that politely redirects the user to `/run-log` and explains that full Strava integration is coming in v2.

## When to use

- The user runs `/run-sync` after a Strava-connected session.
- DataFetcher agent is invoked and `users.json.integrations.strava.connected == true` (v2+).

## Outputs

In v2: normalized workout records appended to `storage/workouts.json`, analysis and adapt-plan signals applied.
In v1: a stub message informing the user that Strava sync is not yet available.

See `body.md` for the full v2 field mapping and the v1 stub behavior.
