"""
test_strava_normalize.py — pytest test suite for strava_normalize.py.

Run with: python -m pytest skills/fetch-strava-activity/scripts/test_strava_normalize.py -v
"""

from strava_normalize import (
    is_duplicate,
    normalize_activity,
    parse_rpe_from_notes,
    upsert_workout,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def make_run_activity(**overrides):
    """Return a minimal valid Strava run activity dict."""
    base = {
        "id": 12345678,
        "sport_type": "Run",
        "moving_time": 2400,  # 40 min
        "distance": 8000.0,   # 8 km
        "average_speed": 3.33,  # ~5:00/km
        "average_heartrate": 152.4,
        "max_heartrate": 168.0,
        "description": "Easy aerobic run. RPE: 5",
        "splits_metric": [
            {"average_speed": 3.20},
            {"average_speed": 3.33},
            {"average_speed": 3.40},
        ],
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# normalize_activity tests
# ---------------------------------------------------------------------------


def test_normalize_happy_path():
    activity = make_run_activity()
    result = normalize_activity(activity)
    assert result is not None
    assert result["duration_min"] == 40
    assert result["distance_km"] == 8.0
    assert result["avg_pace_per_km_s"] == round(1000 / 3.33)
    assert result["avg_hr"] == 152
    assert result["max_hr"] == 168
    assert result["rpe"] == 5
    assert len(result["splits"]) == 3
    assert result["splits"][0]["km"] == 1
    assert result["splits"][0]["pace_per_km_s"] == round(1000 / 3.20)
    assert result["notes"] == "Easy aerobic run. RPE: 5"
    assert result["strava_activity_id"] == "12345678"


def test_normalize_walks_filtered():
    activity = make_run_activity(sport_type="Walk")
    result = normalize_activity(activity)
    assert result is None


def test_normalize_hike_filtered():
    activity = make_run_activity(sport_type="Hike")
    result = normalize_activity(activity)
    assert result is None


def test_normalize_trail_run_accepted():
    activity = make_run_activity(sport_type="TrailRun")
    result = normalize_activity(activity)
    assert result is not None


def test_normalize_virtual_run_accepted():
    activity = make_run_activity(sport_type="VirtualRun")
    result = normalize_activity(activity)
    assert result is not None


def test_normalize_short_filtered():
    activity = make_run_activity(moving_time=120)  # 2 min — too short
    result = normalize_activity(activity)
    assert result is None


def test_normalize_exactly_min_duration_accepted():
    activity = make_run_activity(moving_time=300)  # exactly 5 min
    result = normalize_activity(activity)
    assert result is not None


def test_normalize_missing_hr():
    activity = make_run_activity()
    del activity["average_heartrate"]
    del activity["max_heartrate"]
    result = normalize_activity(activity)
    assert result is not None
    assert result["avg_hr"] is None
    assert result["max_hr"] is None
    # Other fields still populated
    assert result["duration_min"] == 40
    assert result["distance_km"] == 8.0


def test_normalize_zero_speed():
    activity = make_run_activity(average_speed=0)
    result = normalize_activity(activity)
    assert result is not None
    assert result["avg_pace_per_km_s"] is None


def test_normalize_missing_splits():
    activity = make_run_activity()
    del activity["splits_metric"]
    result = normalize_activity(activity)
    assert result is not None
    assert result["splits"] == []


def test_normalize_zero_distance_filtered():
    activity = make_run_activity(distance=0)
    result = normalize_activity(activity)
    assert result is None


def test_normalize_legacy_type_field():
    """Strava activities with 'type' instead of 'sport_type' should work."""
    activity = make_run_activity()
    del activity["sport_type"]
    activity["type"] = "Run"
    result = normalize_activity(activity)
    assert result is not None


# ---------------------------------------------------------------------------
# parse_rpe_from_notes tests
# ---------------------------------------------------------------------------


def test_parse_rpe_variants():
    assert parse_rpe_from_notes("RPE: 7") == 7
    assert parse_rpe_from_notes("rpe 8") == 8
    assert parse_rpe_from_notes("feeling 6/10") == 6
    assert parse_rpe_from_notes("feeling: 9/10") == 9
    assert parse_rpe_from_notes("no rpe here") is None


def test_parse_rpe_equals_sign():
    assert parse_rpe_from_notes("RPE=4") == 4


def test_parse_rpe_out_of_range():
    assert parse_rpe_from_notes("RPE: 15") is None
    assert parse_rpe_from_notes("RPE: 0") is None


def test_parse_rpe_none_input():
    assert parse_rpe_from_notes(None) is None


def test_parse_rpe_empty_string():
    assert parse_rpe_from_notes("") is None


def test_parse_rpe_case_insensitive():
    assert parse_rpe_from_notes("rpe: 3") == 3
    assert parse_rpe_from_notes("RPE: 3") == 3
    assert parse_rpe_from_notes("Rpe: 3") == 3
    assert parse_rpe_from_notes("FEELING: 7/10") == 7


# ---------------------------------------------------------------------------
# is_duplicate tests
# ---------------------------------------------------------------------------


def _make_workout(strava_activity_id="999", source="strava", date="2026-05-01", wkt_id="wkt-001"):
    return {
        "id": wkt_id,
        "date": date,
        "source": source,
        "actual": {
            "strava_activity_id": strava_activity_id,
        },
    }


def test_is_duplicate_hit():
    workouts = [_make_workout(strava_activity_id="999")]
    assert is_duplicate(workouts, "strava", "999") is True


def test_is_duplicate_miss():
    workouts = [_make_workout(strava_activity_id="888")]
    assert is_duplicate(workouts, "strava", "999") is False


def test_is_duplicate_empty_list():
    assert is_duplicate([], "strava", "999") is False


def test_is_duplicate_different_source():
    workouts = [_make_workout(strava_activity_id="999")]
    # garmin_activity_id not present → miss
    assert is_duplicate(workouts, "garmin", "999") is False


# ---------------------------------------------------------------------------
# upsert_workout tests
# ---------------------------------------------------------------------------


def _make_full_workout(
    wkt_id,
    date,
    source,
    activity_id=None,
):
    actual = {}
    if activity_id is not None:
        actual[f"{source}_activity_id"] = str(activity_id)
    return {
        "id": wkt_id,
        "date": date,
        "source": source,
        "actual": actual,
    }


def test_upsert_appended():
    workouts = []
    new_workout = _make_full_workout("wkt-001", "2026-05-01", "manual", None)
    result, action = upsert_workout(workouts, new_workout, "manual")
    assert action == "appended"
    assert len(result) == 1
    assert result[0]["id"] == "wkt-001"


def test_upsert_skipped_dup():
    existing = _make_full_workout("wkt-001", "2026-05-01", "strava", "555")
    workouts = [existing]
    new_workout = _make_full_workout("wkt-002", "2026-05-01", "strava", "555")
    result, action = upsert_workout(workouts, new_workout, "strava")
    assert action == "skipped_dup"
    assert len(result) == 1  # list unchanged


def test_upsert_replaced_lower_priority():
    """Existing manual workout on same date; incoming strava is preferred_source=strava."""
    existing_manual = _make_full_workout("wkt-manual-001", "2026-05-01", "manual", None)
    workouts = [existing_manual]
    new_strava = _make_full_workout("wkt-strava-001", "2026-05-01", "strava", "777")
    result, action = upsert_workout(workouts, new_strava, "strava")
    assert action == "replaced_lower_priority"
    assert len(result) == 2  # both kept
    # The manual entry is marked superseded
    manual_entry = next(w for w in result if w["id"] == "wkt-manual-001")
    assert manual_entry.get("superseded_by") == "wkt-strava-001"
    # The strava entry is present
    assert any(w["id"] == "wkt-strava-001" for w in result)


def test_upsert_skipped_lower_priority():
    """Existing strava workout on same date; incoming manual with preferred_source=strava."""
    existing_strava = _make_full_workout("wkt-strava-001", "2026-05-01", "strava", "888")
    workouts = [existing_strava]
    new_manual = _make_full_workout("wkt-manual-002", "2026-05-01", "manual", None)
    result, action = upsert_workout(workouts, new_manual, "strava")
    assert action == "skipped_lower_priority"
    assert len(result) == 1  # manual NOT appended


def test_upsert_no_mutation():
    """Verify that the input list is not modified in place."""
    existing = _make_full_workout("wkt-001", "2026-05-01", "manual", None)
    original_workouts = [existing]
    original_copy = list(original_workouts)

    new_workout = _make_full_workout("wkt-002", "2026-05-02", "manual", None)
    result, action = upsert_workout(original_workouts, new_workout, "manual")

    # The returned list is new
    assert result is not original_workouts
    # The original list is unchanged
    assert original_workouts == original_copy
    assert len(original_workouts) == 1


def test_upsert_different_dates_both_appended():
    """Two workouts on different dates should both be appended regardless of source."""
    existing = _make_full_workout("wkt-strava-001", "2026-05-01", "strava", "111")
    workouts = [existing]
    new_workout = _make_full_workout("wkt-strava-002", "2026-05-02", "strava", "222")
    result, action = upsert_workout(workouts, new_workout, "strava")
    assert action == "appended"
    assert len(result) == 2


def test_upsert_preferred_source_no_conflict():
    """Same source as preferred on a date with no existing workout → appended."""
    workouts = []
    new_workout = _make_full_workout("wkt-strava-001", "2026-05-01", "strava", "333")
    result, action = upsert_workout(workouts, new_workout, "strava")
    assert action == "appended"
    assert len(result) == 1


def test_upsert_double_session_same_day():
    """Two Strava runs on the same date should both append (different ids).
    This is a real scenario: AM easy + PM workout. Neither should be marked superseded."""
    workouts = []
    am_run = {
        "id": "wkt-2026-04-29-001",
        "date": "2026-04-29",
        "source": "strava",
        "actual": {"strava_activity_id": "111"},
    }
    pm_run = {
        "id": "wkt-2026-04-29-002",
        "date": "2026-04-29",
        "source": "strava",
        "actual": {"strava_activity_id": "222"},
    }
    workouts, action1 = upsert_workout(workouts, am_run, preferred_source="strava")
    assert action1 == "appended"
    workouts, action2 = upsert_workout(workouts, pm_run, preferred_source="strava")
    assert action2 == "appended"
    assert len(workouts) == 2
    # Neither entry should have superseded_by set
    assert not workouts[0].get("superseded_by")
    assert not workouts[1].get("superseded_by")
