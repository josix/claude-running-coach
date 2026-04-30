#!/bin/bash
# plan-integrity-check.sh — PostToolUse hook for running-coach plugin
# Validates storage/plan.json after any Write or Edit operation targeting that file.
# Exit 0 silently if valid; exit 1 with error message on stderr if invalid.

# Claude Code provides tool input as JSON on stdin for PostToolUse hooks
# Parse the file_path from the tool input to determine if plan.json was written
TOOL_INPUT=$(cat)

TARGET_PATH=$(echo "$TOOL_INPUT" | python3 -c "
import json, sys
try:
  data = json.load(sys.stdin)
  inp = data.get('tool_input', {})
  print(inp.get('file_path', ''))
except Exception:
  print('')
" 2>/dev/null)

# Only validate if the file is plan.json
if [[ "$TARGET_PATH" != *"plan.json" ]]; then
  exit 0
fi

[[ "$TARGET_PATH" == *.example.json ]] && exit 0

PLAN_FILE="$TARGET_PATH"

if [ ! -f "$PLAN_FILE" ]; then
  exit 0
fi

python3 - "$PLAN_FILE" <<'PYEOF'
import json, sys

plan_path = sys.argv[1]

try:
  with open(plan_path) as f:
    plan = json.load(f)
except json.JSONDecodeError as e:
  print(f"plan-integrity-check: FAIL — plan.json is not valid JSON: {e}", file=sys.stderr)
  sys.exit(1)
except Exception as e:
  print(f"plan-integrity-check: FAIL — cannot read plan.json: {e}", file=sys.stderr)
  sys.exit(1)

# Check required top-level keys
required_keys = ["version", "goal", "methodology", "macrocycle", "weeks", "last_modified_at"]
missing = [k for k in required_keys if k not in plan]
if missing:
  print(f"plan-integrity-check: FAIL — missing required keys: {missing}", file=sys.stderr)
  sys.exit(1)

# Check macrocycle.total_weeks matches len(weeks)
macrocycle = plan["macrocycle"]
total_weeks = macrocycle.get("total_weeks")
actual_weeks = len(plan["weeks"])
if total_weeks != actual_weeks:
  print(
    f"plan-integrity-check: FAIL — macrocycle.total_weeks ({total_weeks}) "
    f"does not match len(weeks) ({actual_weeks})",
    file=sys.stderr
  )
  sys.exit(1)

# Check phase boundaries are monotonic (start_week values increase)
phases = macrocycle.get("phases", [])
prev_start = -1
for phase in phases:
  start = phase.get("start_week", 0)
  if start <= prev_start:
    print(
      f"plan-integrity-check: FAIL — phase start_week values are not monotonically increasing "
      f"(got {start} after {prev_start})",
      file=sys.stderr
    )
    sys.exit(1)
  prev_start = start

# Check each week has week_number matching its index + 1
for i, week in enumerate(plan["weeks"]):
  expected = i + 1
  actual = week.get("week_number")
  if actual != expected:
    print(
      f"plan-integrity-check: FAIL — week at index {i} has week_number={actual}, expected {expected}",
      file=sys.stderr
    )
    sys.exit(1)

sys.exit(0)
PYEOF
