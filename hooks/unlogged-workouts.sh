#!/bin/bash
# unlogged-workouts.sh — SessionStart hook for running-coach plugin
# Reminds the runner if there are unlogged workouts since their last log entry.
# Exit 0 always (informational only, never blocking).

PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
DAILY_STATE="${PLUGIN_ROOT}/storage/daily_state.json"
PLAN_FILE="${PLUGIN_ROOT}/storage/plan.json"

# If plugin not initialized, exit silently
if [ ! -f "$DAILY_STATE" ] || [ ! -f "$PLAN_FILE" ]; then
  exit 0
fi

# Parse as_of_date from daily_state.json
AS_OF=$(python3 -c "
import json, sys
try:
  data = json.load(open('$DAILY_STATE'))
  print(data.get('as_of_date', ''))
except Exception:
  print('')
")

if [ -z "$AS_OF" ]; then
  exit 0
fi

TODAY=$(python3 -c "from datetime import date; print(date.today().isoformat())")

if [ "$AS_OF" = "$TODAY" ]; then
  exit 0
fi

# Count prescribed training days (non-Rest) between as_of_date (exclusive) and today (inclusive)
COUNT=$(python3 -c "
import json, sys
from datetime import date, timedelta

try:
  with open('$DAILY_STATE') as f:
    state = json.load(f)
  with open('$PLAN_FILE') as f:
    plan = json.load(f)

  as_of = date.fromisoformat('$AS_OF')
  today = date.fromisoformat('$TODAY')

  # Build set of dates in the gap (as_of exclusive, today inclusive)
  gap_dates = set()
  d = as_of + timedelta(days=1)
  while d <= today:
    gap_dates.add(d.isoformat())
    d += timedelta(days=1)

  # Count non-Rest days in plan that fall in the gap
  count = 0
  for week in plan.get('weeks', []):
    for day in week.get('days', []):
      if day.get('date') in gap_dates and day.get('type', 'Rest') != 'Rest':
        count += 1

  print(count)
except Exception as e:
  print(0)
")

if [ "$COUNT" -gt 0 ] 2>/dev/null; then
  echo "📅 You have ${COUNT} unlogged workout(s) since ${AS_OF}. Run /run-log <date> to catch up."
fi

exit 0
