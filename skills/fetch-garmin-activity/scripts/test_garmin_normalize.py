"""
test_garmin_normalize.py — pytest test suite for garmin_normalize.py.

Run with: python -m pytest skills/fetch-garmin-activity/scripts/test_garmin_normalize.py -v
"""

from garmin_normalize import (
    extract_display_name,
    is_duplicate,
    normalize_activity,
    upsert_workout,
)


# ---------------------------------------------------------------------------
# Fixtures — shape matches `garmin_activity_detail` MCP response
# ---------------------------------------------------------------------------


def make_run_detail(activity_overrides=None, splits=None):
    """Return a minimal valid garmin_activity_detail-style dict.

    Mirrors the response from `mcp__garmin__garmin_activity_detail` in
    nrvim/garmin-givemydata.
    """
    activity = {
        "activity_id": 22721734357,
        "activity_name": "Easy Run",
        "activity_type": "running",
        "start_time_local": "2026-05-01 15:05:39",
        "duration_min": 40.0,
        "distance_km": 8.0,
        "calories": 405.0,
        "avg_hr": 152.4,
        "max_hr": 168.0,
        "elevation_gain_m": 8.0,
        "avg_power_w": 220.0,
        "training_load": 49.1,
        "avg_cadence": 175.0,
        "location_name": "Test Park",
    }
    if activity_overrides:
        activity.update(activity_overrides)
    return {
        "activity": activity,
        "splits": splits if splits is not None else [],
        "hr_zones": {},
        "weather": {},
        "exercise_sets": [],
        "running_dynamics": {},
    }


# ---------------------------------------------------------------------------
# normalize_activity — happy path
# ---------------------------------------------------------------------------


def test_normalize_happy_path():
    detail = make_run_detail()
    result = normalize_activity(detail)
    assert result is not None
    assert result["duration_min"] == 40
    assert result["distance_km"] == 8.0
    # 40 min over 8 km = 300 s/km
    assert result["avg_pace_per_km_s"] == 300
    assert result["avg_hr"] == 152
    assert result["max_hr"] == 168
    assert result["rpe"] is None
    assert result["notes"] == ""
    assert result["splits"] == []
    assert result["garmin_activity_id"] == "22721734357"


# ---------------------------------------------------------------------------
# normalize_activity — sport type filter
# ---------------------------------------------------------------------------


def test_normalize_running_accepted():
    assert normalize_activity(make_run_detail({"activity_type": "running"})) is not None


def test_normalize_track_running_accepted():
    """track_running is a real activity_type seen in the wild."""
    assert normalize_activity(make_run_detail({"activity_type": "track_running"})) is not None


def test_normalize_trail_running_accepted():
    assert normalize_activity(make_run_detail({"activity_type": "trail_running"})) is not None


def test_normalize_treadmill_running_accepted():
    assert normalize_activity(make_run_detail({"activity_type": "treadmill_running"})) is not None


def test_normalize_virtual_run_accepted():
    assert normalize_activity(make_run_detail({"activity_type": "virtual_run"})) is not None


def test_normalize_indoor_running_accepted():
    assert normalize_activity(make_run_detail({"activity_type": "indoor_running"})) is not None


def test_normalize_walking_rejected():
    assert normalize_activity(make_run_detail({"activity_type": "walking"})) is None


def test_normalize_cycling_rejected():
    assert normalize_activity(make_run_detail({"activity_type": "cycling"})) is None


def test_normalize_hiking_rejected():
    assert normalize_activity(make_run_detail({"activity_type": "hiking"})) is None


def test_normalize_activity_type_empty():
    assert normalize_activity(make_run_detail({"activity_type": ""})) is None


def test_normalize_activity_block_missing():
    """If detail has no activity key, refuse."""
    assert normalize_activity({"splits": []}) is None


def test_normalize_detail_none():
    assert normalize_activity(None) is None


# ---------------------------------------------------------------------------
# normalize_activity — duration filter
# ---------------------------------------------------------------------------


def test_normalize_duration_too_short():
    assert normalize_activity(make_run_detail({"duration_min": 4.9})) is None


def test_normalize_duration_exactly_min():
    assert normalize_activity(make_run_detail({"duration_min": 5.0})) is not None


def test_normalize_duration_missing():
    assert normalize_activity(make_run_detail({"duration_min": None})) is None


# ---------------------------------------------------------------------------
# normalize_activity — distance filter
# ---------------------------------------------------------------------------


def test_normalize_distance_zero():
    assert normalize_activity(make_run_detail({"distance_km": 0})) is None


def test_normalize_distance_missing():
    assert normalize_activity(make_run_detail({"distance_km": None})) is None


# ---------------------------------------------------------------------------
# normalize_activity — HR
# ---------------------------------------------------------------------------


def test_normalize_hr_missing():
    detail = make_run_detail({"avg_hr": None, "max_hr": None})
    result = normalize_activity(detail)
    assert result is not None
    assert result["avg_hr"] is None
    assert result["max_hr"] is None


def test_normalize_hr_only_avg_present():
    detail = make_run_detail({"avg_hr": 145.0, "max_hr": None})
    result = normalize_activity(detail)
    assert result is not None
    assert result["avg_hr"] == 145
    assert result["max_hr"] is None


# ---------------------------------------------------------------------------
# normalize_activity — activity_id required for dedup
# ---------------------------------------------------------------------------


def test_normalize_missing_activity_id_rejected():
    """No activity_id ⇒ cannot dedupe ⇒ refuse."""
    assert normalize_activity(make_run_detail({"activity_id": None})) is None


# ---------------------------------------------------------------------------
# normalize_activity — splits
# ---------------------------------------------------------------------------


def test_normalize_splits_empty():
    result = normalize_activity(make_run_detail(splits=[]))
    assert result["splits"] == []


def test_normalize_splits_realistic():
    """3 km splits from real garmin-givemydata shape."""
    splits = [
        {"split_number": 1, "distance_m": 1000.0, "duration_sec": 300.0,
         "avg_speed": 3.33, "avg_hr": 145, "max_hr": 152, "elev_gain": 0, "avg_cadence": 175},
        {"split_number": 2, "distance_m": 1000.0, "duration_sec": 310.0,
         "avg_speed": 3.23, "avg_hr": 150, "max_hr": 155, "elev_gain": 1, "avg_cadence": 174},
        {"split_number": 3, "distance_m": 1000.0, "duration_sec": 290.0,
         "avg_speed": 3.45, "avg_hr": 155, "max_hr": 160, "elev_gain": 0, "avg_cadence": 176},
    ]
    result = normalize_activity(make_run_detail(splits=splits))
    assert len(result["splits"]) == 3
    assert result["splits"][0] == {"km": 1, "pace_per_km_s": 300}
    assert result["splits"][1] == {"km": 2, "pace_per_km_s": 310}
    assert result["splits"][2] == {"km": 3, "pace_per_km_s": 290}


def test_normalize_splits_drops_trailing_partial():
    """Garmin emits a tiny trailing split (e.g. 5m / 1s) for the last few meters of overshoot.
    That should be dropped — keeping it produces nonsense paces (~3 m/s = 333 s/km on noise)."""
    splits = [
        {"split_number": 1, "distance_m": 1000.0, "duration_sec": 300.0},
        {"split_number": 2, "distance_m": 5.0, "duration_sec": 1.0},  # trailing overshoot
    ]
    result = normalize_activity(make_run_detail(splits=splits))
    assert len(result["splits"]) == 1
    assert result["splits"][0] == {"km": 1, "pace_per_km_s": 300}


def test_normalize_splits_handles_zero_duration():
    splits = [{"split_number": 1, "distance_m": 1000.0, "duration_sec": 0}]
    result = normalize_activity(make_run_detail(splits=splits))
    assert len(result["splits"]) == 1
    assert result["splits"][0]["pace_per_km_s"] is None


# ---------------------------------------------------------------------------
# extract_display_name
# ---------------------------------------------------------------------------


def test_extract_display_name_prefers_full_name():
    profile = {"social_profile": {"fullName": "Wilson Wang", "displayName": "wwang_42"}}
    assert extract_display_name(profile) == "Wilson Wang"


def test_extract_display_name_skips_uuid_displayname():
    """When displayName is a UUID (modern Garmin default), skip it."""
    profile = {
        "social_profile": {
            "displayName": "c6e6b45b-4699-423e-8ac4-56ce3b5a2740",
            "userName": "wilson@example.com",
        }
    }
    assert extract_display_name(profile) == "wilson@example.com"


def test_extract_display_name_uses_first_last_from_base():
    profile = {
        "social_profile": {},
        "user_profile_base": {"firstName": "Wilson", "lastName": "Wang"},
    }
    assert extract_display_name(profile) == "Wilson Wang"


def test_extract_display_name_first_only_when_no_last():
    profile = {
        "social_profile": {},
        "user_profile_base": {"firstName": "Wilson"},
    }
    assert extract_display_name(profile) == "Wilson"


def test_extract_display_name_real_garmin_shape():
    """Real shape captured from a live garmin-givemydata response."""
    profile = {
        "social_profile": {
            "displayName": "c6e6b45b-4699-423e-8ac4-56ce3b5a2740",  # UUID
            "fullName": "Wilson",
            "userProfileFullName": "Wilson",
            "userName": "wilson8507@gmail.com",
            "profileId": 120203587,
        },
        "user_profile_base": {
            "firstName": "Wilson",
            "lastName": None,
        },
    }
    assert extract_display_name(profile) == "Wilson"


def test_extract_display_name_none_when_empty():
    assert extract_display_name({}) is None
    assert extract_display_name({"social_profile": {}, "user_profile_base": {}}) is None


def test_extract_display_name_handles_none_input():
    assert extract_display_name(None) is None


# ---------------------------------------------------------------------------
# is_duplicate
# ---------------------------------------------------------------------------


def _make_workout(garmin_activity_id="999", source="garmin", date="2026-05-01", wkt_id="wkt-001"):
    return {
        "id": wkt_id,
        "date": date,
        "source": source,
        "actual": {
            "garmin_activity_id": garmin_activity_id,
        },
    }


def test_is_duplicate_hit():
    workouts = [_make_workout(garmin_activity_id="999")]
    assert is_duplicate(workouts, "garmin", "999") is True


def test_is_duplicate_miss_different_id():
    workouts = [_make_workout(garmin_activity_id="888")]
    assert is_duplicate(workouts, "garmin", "999") is False


def test_is_duplicate_empty_list():
    assert is_duplicate([], "garmin", "999") is False


def test_is_duplicate_different_source():
    workouts = [_make_workout(garmin_activity_id="999", source="garmin")]
    assert is_duplicate(workouts, "strava", "999") is False


# ---------------------------------------------------------------------------
# upsert_workout
# ---------------------------------------------------------------------------


def _make_full_workout(wkt_id, date, source, activity_id=None):
    actual = {}
    if activity_id is not None:
        actual[f"{source}_activity_id"] = str(activity_id)
    return {
        "id": wkt_id,
        "date": date,
        "source": source,
        "actual": actual,
    }


def test_upsert_new_workout_appended():
    new_workout = _make_full_workout("wkt-001", "2026-05-01", "garmin", 12345)
    result, action = upsert_workout([], new_workout, "garmin")
    assert action == "appended"
    assert len(result) == 1


def test_upsert_skipped_dup():
    existing = _make_full_workout("wkt-001", "2026-05-01", "garmin", 999)
    new_workout = _make_full_workout("wkt-002", "2026-05-01", "garmin", 999)
    result, action = upsert_workout([existing], new_workout, "garmin")
    assert action == "skipped_dup"
    assert len(result) == 1


def test_upsert_manual_replaced_by_garmin():
    existing_manual = _make_full_workout("wkt-manual-001", "2026-05-01", "manual", None)
    new_garmin = _make_full_workout("wkt-garmin-001", "2026-05-01", "garmin", 777)
    result, action = upsert_workout([existing_manual], new_garmin, "garmin")
    assert action == "replaced_lower_priority"
    assert len(result) == 2
    manual_entry = next(w for w in result if w["id"] == "wkt-manual-001")
    assert manual_entry.get("superseded_by") == "wkt-garmin-001"


def test_upsert_skipped_lower_priority():
    existing_garmin = _make_full_workout("wkt-garmin-001", "2026-05-01", "garmin", 888)
    new_manual = _make_full_workout("wkt-manual-002", "2026-05-01", "manual", None)
    result, action = upsert_workout([existing_garmin], new_manual, "garmin")
    assert action == "skipped_lower_priority"
    assert len(result) == 1


def test_upsert_no_mutation():
    existing = _make_full_workout("wkt-001", "2026-05-01", "manual", None)
    original_workouts = [existing]
    original_copy = list(original_workouts)
    new_workout = _make_full_workout("wkt-002", "2026-05-02", "manual", None)
    result, _ = upsert_workout(original_workouts, new_workout, "manual")
    assert result is not original_workouts
    assert original_workouts == original_copy


def test_upsert_different_dates_both_kept():
    existing = _make_full_workout("wkt-garmin-001", "2026-05-01", "garmin", 111)
    new_workout = _make_full_workout("wkt-garmin-002", "2026-05-02", "garmin", 222)
    result, action = upsert_workout([existing], new_workout, "garmin")
    assert action == "appended"
    assert len(result) == 2


def test_upsert_double_session_same_day():
    am_run = {
        "id": "wkt-2026-04-29-001",
        "date": "2026-04-29",
        "source": "garmin",
        "actual": {"garmin_activity_id": "111"},
    }
    pm_run = {
        "id": "wkt-2026-04-29-002",
        "date": "2026-04-29",
        "source": "garmin",
        "actual": {"garmin_activity_id": "222"},
    }
    workouts, action1 = upsert_workout([], am_run, preferred_source="garmin")
    workouts, action2 = upsert_workout(workouts, pm_run, preferred_source="garmin")
    assert action1 == "appended"
    assert action2 == "appended"
    assert len(workouts) == 2
    assert not workouts[0].get("superseded_by")
    assert not workouts[1].get("superseded_by")


def test_upsert_cross_provider_garmin_replaces_strava():
    existing_strava = _make_full_workout("wkt-strava-001", "2026-05-01", "strava", "S-555")
    new_garmin = _make_full_workout("wkt-garmin-001", "2026-05-01", "garmin", "G-999")
    result, action = upsert_workout([existing_strava], new_garmin, "garmin")
    assert action == "replaced_lower_priority"
    assert len(result) == 2
    strava_entry = next(w for w in result if w["id"] == "wkt-strava-001")
    assert strava_entry.get("superseded_by") == "wkt-garmin-001"
