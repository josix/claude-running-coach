# Probe Garmin Connection — Instructions

This skill verifies the `garmin-givemydata` MCP server is loaded and its local SQLite database has been seeded with the runner's profile. It must complete successfully before the caller writes `connected: true` to `users.json`. Do not make any writes to storage — return a structured result dict only.

## Why garmin-givemydata, not garth-based servers

As of March 2026, Garmin deployed Cloudflare bot detection that blocks every `garth`-based library (including `Taxuspt/garmin_mcp`). `garth` itself was deprecated on 2026-03-28. `nrvim/garmin-givemydata` works around this with SeleniumBase UC mode (undetected Chrome) and stores everything in a local SQLite database; the MCP server reads from that DB and only contacts Garmin when an explicit `garmin_sync` is requested. This means our probe verifies *DB readiness*, not live Garmin auth — auth-related failures only surface during `/run-sync`.

The MCP server exposes `mcp__garmin__garmin_user_profile`, which serves the dual purpose of MCP availability check and identity capture (the DB must have rows in the `user_profile` table for the probe to succeed).

---

## Step 1 — Check MCP availability

Attempt to determine whether `mcp__garmin__garmin_user_profile` is available in your current tool list.

If the tool is **not available** (not present in the tool list, or the MCP server is not loaded):

Return:
```json
{
  "ok": false,
  "error": "mcp_unavailable",
  "message": "The garmin-givemydata MCP server is not connected. To install it:\n1. Install via uv (recommended): uv tool install garmin-givemydata — or pipx: pipx install garmin-givemydata. Requires Python 3.10+ and Google Chrome (used by SeleniumBase for the Cloudflare-bypass login). Do not use brew.\n2. Run the initial sync once in a terminal: garmin-givemydata. You will be prompted for Garmin Connect email, password, and MFA code (if MFA is enabled). The first run launches a headless Chrome window, completes login, and pulls your full history (~30 minutes for ~10 years; pass --days 90 if you only want recent data). The cf_clearance cookie is bound to your egress IP and lasts ~weeks on a stable IP.\n3. Register garmin-givemydata in your Claude Code MCP config under namespace 'garmin' (the plugin's mcp__garmin__* tool prefix depends on this namespace). After uv tool install / pipx install, the entry point garmin-mcp is on PATH:\n   {\n     \"mcpServers\": {\n       \"garmin\": { \"command\": \"garmin-mcp\" }\n     }\n   }\n   If garmin-mcp is not on Claude Code's PATH, use the absolute path from `uv tool list` or `pipx list`. See https://docs.anthropic.com/en/docs/claude-code/mcp for full MCP config docs.\n4. Restart Claude Code and re-run /run-init --connect garmin."
}
```

Stop and return this result.

---

## Step 2 — Call `mcp__garmin__garmin_user_profile`

Call the tool with no arguments. The tool reads from the local SQLite DB (`~/.garmin-givemydata/garmin.db` by default, or `$GARMIN_DATA_DIR` if set). It does **not** make a live Garmin API call, so it cannot fail with auth errors at probe time.

The tool returns a JSON string. Parse it. The expected shape is a dict keyed by profile section:
```json
{
  "social_profile": { "profileId": 123456789, "displayName": "Wilson Wang", "userName": "wilson.wang", ... },
  "user_profile_base": { "userId": 123456789, ... },
  "personal_info": { ... },
  "user_settings": { ... }
}
```

### On empty result — DB not yet seeded

If the parsed dict is empty (`{}`), or both `social_profile` and `user_profile_base` are missing, the database has been initialized but no profile data has been synced yet. This means the user installed the MCP server but never ran `garmin-givemydata` to populate the DB.

Return:
```json
{
  "ok": false,
  "error": "db_empty",
  "message": "garmin-givemydata MCP is connected, but the local database has not been populated yet. Run the initial sync in a terminal: garmin-givemydata (pulls full history; pass --days 90 to limit). On first run you will be prompted for Garmin email, password, and MFA. The cf_clearance cookie is bound to your egress IP — if you switch networks frequently, expect the session to expire and re-prompt for credentials. Once the initial sync completes, re-run /run-init --connect garmin."
}
```

### On success — DB has profile rows

Extract identity in priority order:
1. `social_profile.profileId` (preferred) — coerce to string for `garmin_user_id`.
2. Fall back to `user_profile_base.userId` if `social_profile` is missing.

For the human-readable name (optional), prefer in this order:
1. `social_profile.fullName` — Garmin's actual display name (e.g., `"Wilson"`).
2. `social_profile.userProfileFullName` — usually the same as `fullName`.
3. `user_profile_base.firstName` (concatenated with `lastName` if present).
4. `social_profile.displayName` — **note**: in modern Garmin accounts this is often a synthetic UUID like `c6e6b45b-4699-423e-8ac4-56ce3b5a2740`, not a real name. Skip if it matches the UUID regex `^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$`.
5. `social_profile.userName` — typically the user's email address; fine as a last-resort identifier.
6. Fall back to `null` if none are present.

Optionally extract `email` from `social_profile.userName` (which holds the user's Garmin login email — e.g., `"wilson8507@gmail.com"`). Include in the success dict as `email` (string|null).

Return:
```json
{
  "ok": true,
  "garmin_user_id": "123456789",
  "display_name": "Wilson",
  "email": "wilson@example.com"
}
```

If both `profileId` and `userId` are missing despite a non-empty dict, return:
```json
{
  "ok": false,
  "error": "unknown",
  "message": "garmin-givemydata responded with profile data but no profileId or userId field. The local database may be partially seeded — try re-running garmin-givemydata to refresh. If the issue persists, file an issue at https://github.com/nrvim/garmin-givemydata/issues with the output of garmin-givemydata --status."
}
```

### On any other error from the tool call

The most common failure mode here is a SQLite "no such table" error (DB file does not exist) or a JSON parse error. Treat all unexpected errors as `unknown`:

```json
{
  "ok": false,
  "error": "unknown",
  "message": "<verbatim error message from the MCP tool call> — try running `garmin-givemydata --status` in a terminal to inspect the local database, then re-run /run-init --connect garmin."
}
```

If the verbatim error mentions `no such table`, append: " The DB schema has not been created yet. Run `garmin-givemydata` once to initialize it."

---

## Failure mode summary

| error | When it fires | What to tell the user |
|---|---|---|
| `mcp_unavailable` | `mcp__garmin__garmin_user_profile` not in tool list | Install nrvim/garmin-givemydata via `uv tool install garmin-givemydata` (or pipx), run `garmin-givemydata` once for initial sync, register the `garmin-mcp` server under namespace `garmin`, restart Claude Code |
| `db_empty` | Tool responds but `user_profile` table has no rows | Run `garmin-givemydata` to perform the initial sync (~30 min for full history) |
| `unknown` | SQLite error, JSON parse error, or unexpected response shape | Surface the verbatim error and suggest `garmin-givemydata --status` for diagnosis |

Note: there is no `auth` error class for this probe — Garmin authentication only happens during `garmin_sync` calls, which are triggered by `/run-sync`, not by `/run-init`. Auth or Cloudflare failures will surface there with the relevant error classification.

---

## Important

- Do **not** write anything to `users.json` — that is the caller's responsibility.
- Do **not** trigger a sync (`garmin_sync(refresh=true)`) from within this probe — that requires live Garmin access and can take minutes. Probes must be fast and read-only.
- Do **not** retry on failure — return the classified error immediately.
- Do **not** swallow errors silently — an `ok: false` result is still a result.
