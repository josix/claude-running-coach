---
name: probe-garmin-connection
description: Verify Garmin Connect MCP connectivity and capture user identity before flipping the integrations.garmin.connected flag. Returns ok+garmin_user_id on success, classified error on failure.
---

# Probe Garmin Connection

Checks whether the `garmin-givemydata` MCP server is loaded and whether its local SQLite database has been seeded by an initial sync. Calls `mcp__garmin__garmin_user_profile` to verify the DB is populated and capture the runner's Garmin profile identity. Returns a structured result used by `/run-init --connect garmin` to decide whether to flip `users.json.integrations.garmin.connected` to `true`.

## When to use

- Called by Coach when the user runs `/run-init --connect garmin`.
- Must be called before writing `connected: true` to `users.json` — no optimistic connection.

## Outputs

Returns a dict in one of two shapes:

**Success:**
```json
{ "ok": true, "garmin_user_id": "123456789", "display_name": "Wilson Wang", "email": "wilson@example.com" }
```

**Failure:**
```json
{ "ok": false, "error": "mcp_unavailable" | "db_empty" | "unknown", "message": "<human-readable instructions>" }
```

See `body.md` for the full decision tree and user-facing messages for each failure mode.
