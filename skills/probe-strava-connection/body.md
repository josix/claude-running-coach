# Probe Strava Connection — Instructions

This skill verifies the Strava MCP server is available and the user's credentials are valid. It must complete successfully before the caller writes `connected: true` to `users.json`. Do not make any writes to storage — return a structured result dict only.

The MCP server (`r-huijts/strava-mcp`, registered as `strava`) exposes a purpose-built connectivity check (`mcp__strava__check-strava-connection`) and a profile read (`mcp__strava__get-athlete-profile`). This skill uses the connection-check first, then profile read for athlete identity.

---

## Step 1 — Check MCP availability

Attempt to determine whether `mcp__strava__check-strava-connection` and `mcp__strava__get-athlete-profile` are available in your current tool list.

If either tool is **not available** (not present in the tool list, or the MCP server is not loaded):

Return:
```json
{
  "ok": false,
  "error_code": "mcp_unavailable",
  "user_message": "The Strava MCP server is not connected. To install it:\n1. Install the r-huijts/strava-mcp server: https://github.com/r-huijts/strava-mcp\n2. Add it to your Claude Code MCP configuration (see https://docs.anthropic.com/en/docs/claude-code/mcp)\n3. Set the required environment variables (see Step 2 prerequisites below)\n4. Restart Claude Code and re-run /run-init --connect strava"
}
```

Stop and return this result.

---

## Step 2 — Call `mcp__strava__check-strava-connection`

Call the tool with no arguments. It returns a structured connectivity status (whether OAuth tokens are present and valid).

### If the response indicates "not connected" or missing tokens

Return the `auth` error (see "On error — credentials" section below).

### If the response indicates "connected"

Proceed to Step 3.

---

## Step 3 — Call `mcp__strava__get-athlete-profile`

Call the tool with no arguments (it uses the OAuth token from the environment).

### On success

The tool returns an athlete profile object. Before extracting fields, check that the `id` field is present.

If the response is missing the `id` field (degraded MCP response), return:
```json
{
  "ok": false,
  "error_code": "unknown",
  "user_message": "Strava MCP responded but did not include athlete id. Try again, or check that your Strava API app has the required scopes (read,activity:read_all)."
}
```

Otherwise extract:
- `athlete_id` — the integer value of `id`
- `username` — the `username` field (may be empty string or absent; use `""` as fallback)
- `firstname` — the `firstname` field (may be absent; use `""` as fallback)

Return:
```json
{
  "ok": true,
  "athlete_id": 12345678,
  "username": "jrunner",
  "firstname": "Jordan"
}
```

### On error — credentials / auth problem

If the error message contains any of: `"client_id"`, `"client_secret"`, `"token"`, `"unauthorized"`, `"401"`, `"invalid_token"`, `"access_token"`, `"not connected"`, `"connect-strava"`:

Return:
```json
{
  "ok": false,
  "error_code": "auth",
  "user_message": "Strava authentication failed or no account is connected. To connect:\n\n1. Run the MCP's OAuth flow by calling mcp__strava__connect-strava (the server will guide you through Strava's OAuth consent).\n\nOr if you've already done that, verify these environment variables are set correctly in your MCP server config:\n- STRAVA_CLIENT_ID — your Strava API app client ID\n- STRAVA_CLIENT_SECRET — your Strava API app client secret\n- STRAVA_REFRESH_TOKEN — a valid refresh token for your Strava account\n\nTo obtain these:\n1. Create a Strava API app at https://www.strava.com/settings/api\n2. Use mcp__strava__connect-strava or the manual OAuth flow to generate a refresh token\n3. Add the variables to your Claude Code MCP server configuration\n\nAfter connecting, restart Claude Code and re-run /run-init --connect strava."
}
```

### On any other error

Return:
```json
{
  "ok": false,
  "error_code": "unknown",
  "user_message": "<verbatim error message from the MCP tool call>"
}
```

---

## Failure mode summary

| error_code | When it fires | What to tell the user |
|---|---|---|
| `mcp_unavailable` | Either probe tool not in tool list | Install r-huijts/strava-mcp and add to MCP config |
| `auth` | check-strava-connection reports not-connected, OR profile call returns credential-related error | Run `mcp__strava__connect-strava` to OAuth, or check env vars |
| `unknown` | Any other error from the MCP calls | Surface the verbatim error so the user can diagnose |

---

## Important

- Do **not** write anything to `users.json` — that is the caller's responsibility.
- Do **not** retry on failure — return the classified error immediately.
- Do **not** swallow errors silently — an `ok: false` result is still a result.
