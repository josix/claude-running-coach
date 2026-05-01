---
name: probe-strava-connection
description: Verify Strava MCP connectivity and capture athlete identity before flipping the integrations.strava.connected flag. Returns ok+athlete_id on success, classified error on failure.
---

# Probe Strava Connection

Checks whether the Strava MCP server is available, calls `mcp__strava__check-strava-connection` to verify OAuth state, then `mcp__strava__get-athlete-profile` to capture athlete identity. Returns a structured result used by `/run-init --connect strava` to decide whether to flip `users.json.integrations.strava.connected` to `true`.

## When to use

- Called by Coach when the user runs `/run-init --connect strava`.
- Must be called before writing `connected: true` to `users.json` — no optimistic connection.

## Outputs

Returns a dict in one of two shapes:

**Success:**
```json
{ "ok": true, "athlete_id": 12345678, "username": "jrunner", "firstname": "Jordan" }
```

**Failure:**
```json
{ "ok": false, "error_code": "<code>", "user_message": "<human-readable instructions>" }
```

See `body.md` for the full decision tree and user-facing messages for each failure mode.
