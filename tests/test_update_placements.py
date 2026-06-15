import json

from scripts.update_placements import CANDIDATES_PATH, OVERRIDES_PATH, build_placements


def test_current_candidates_have_placement_records():
    candidates = json.loads(CANDIDATES_PATH.read_text(encoding="utf-8"))
    overrides = json.loads(OVERRIDES_PATH.read_text(encoding="utf-8"))

    output = build_placements(candidates, overrides)

    assert output["total_candidates"] == len(candidates["candidates"])
    assert output["confirmed_count"] + output["pending_count"] == output["total_candidates"]
    assert output["stale_overrides"] == []
    assert {item["candidate_id"] for item in output["placements"]} == {
        item["id"] for item in candidates["candidates"]
    }


def test_confirmed_placements_have_sources():
    candidates = json.loads(CANDIDATES_PATH.read_text(encoding="utf-8"))
    overrides = json.loads(OVERRIDES_PATH.read_text(encoding="utf-8"))

    output = build_placements(candidates, overrides)
    confirmed = [item for item in output["placements"] if item["status"] == "confirmed"]

    assert len(confirmed) == 41
    assert all(item["destination"] and item["source_url"] for item in confirmed)
