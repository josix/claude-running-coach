# running-coach Hooks

This directory contains the two lifecycle hooks for the `running-coach` plugin.

---

## Hooks Overview

### `unlogged-workouts.sh` — SessionStart

**Trigger**: Every time a Claude Code session starts while the `running-coach` plugin is loaded.

**Purpose**: Reminds the runner if there are prescribed training days that have not yet been logged since the last `as_of_date` in `storage/daily_state.json`.

**Logic**:
1. If `storage/daily_state.json` or `storage/plan.json` does not exist (plugin not yet initialized), exit silently.
2. Parse `as_of_date` from `daily_state.json`.
3. If today equals `as_of_date`, nothing to remind — exit silently.
4. Count non-Rest days in `plan.json` that fall between `as_of_date` (exclusive) and today (inclusive).
5. If count > 0, emit: `📅 You have N unlogged workout(s) since YYYY-MM-DD. Run /run-log <date> to catch up.`

**Exit semantics**: Always exits 0. This hook is informational only — it never blocks the session.

---

### `plan-integrity-check.sh` — PostToolUse (Write | Edit)

**Trigger**: After any `Write` or `Edit` tool call that targets `storage/plan.json`.

**Purpose**: Validates `plan.json` after every write to catch structural corruption before it affects the adaptive loop.

**Checks performed**:
1. File parses as valid JSON.
2. Required top-level keys are present: `version`, `goal`, `methodology`, `macrocycle`, `weeks`, `last_modified_at`.
3. `macrocycle.total_weeks` equals `len(weeks)`.
4. Phase `start_week` values are monotonically increasing.
5. Each week's `week_number` matches its array index + 1.

**Exit semantics**: Exits 0 silently if all checks pass. Exits 1 with a descriptive error message on stderr if any check fails — Claude Code surfaces this to the user and the session is halted until the issue is resolved.

---

## Activating the Hooks (Manifest Wiring)

Both hooks are declared in `hooks/hooks.json`. To activate them, the plugin manifest (`.claude-plugin/plugin.json`) must reference this file via the `hooks` field:

```json
{
  "hooks": "${CLAUDE_PLUGIN_ROOT}/hooks/hooks.json"
}
```

**This wiring is not yet applied** — the manifest is managed by the orchestrator and will be patched in a final integration pass after all parallel plugin build tasks complete. The `hooks/hooks.json` file is ready and valid.

---

## Dependencies

Both scripts use only:
- `/bin/bash` (standard shell)
- `python3` with stdlib only (`json`, `datetime`) — no `jq` or external tools required

The `${CLAUDE_PLUGIN_ROOT}` environment variable is set by Claude Code when the plugin is loaded.
