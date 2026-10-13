import json

from scripts.update_placements import CANDIDATES_PATH, OVERRIDES_PATH, build_placements


def test_current_candidates_have_placement_records():
    candidates = json.loads(CANDIDATES_PATH.read_text(encoding="utf-8"))
    overrides = json.loads(OVERRIDES_PATH.read_text(encoding="utf-8"))

    output = build_placements(candidates, overrides)

    assert output["total_candidates"] == len(candidates["candidates"])
    assert output["confirmed_count"] + output["pending_count"] == output["total_candidates"]
    assert output["stale_overrides"] == sorted(
        set(overrides["placements"]) - {item["name"] for item in candidates["candidates"]}
    )
    assert {item["candidate_id"] for item in output["placements"]} == {
        item["id"] for item in candidates["candidates"]
    }


def test_confirmed_placements_have_sources():
    candidates = json.loads(CANDIDATES_PATH.read_text(encoding="utf-8"))
    overrides = json.loads(OVERRIDES_PATH.read_text(encoding="utf-8"))

    output = build_placements(candidates, overrides)
    confirmed = [item for item in output["placements"] if item["status"] == "confirmed"]

    assert {item["name"] for item in confirmed} == {
        item["name"] for item in candidates["candidates"] if item["name"] in overrides["placements"]
    }
    assert all(item["destination"] and item["source_url"] for item in confirmed)


def test_departed_candidates_are_excluded_and_new_candidates_are_pending():
    template = {"institution": "Example University", "country": "US", "rank": 1, "fields": ["Macroeconomics"], "paper_url": "https://example.edu/paper.pdf", "profile_url": "https://example.edu/profile"}
    candidates = {"candidates": [dict(template, id="current", name="Current Economist"), dict(template, id="new", name="New Economist")]}
    placement = {"destination": "Example University", "source_url": "https://example.edu/placements"}
    overrides = {"placements": {"Current Economist": placement, "Departed Economist": placement}}

    output = build_placements(candidates, overrides)

    assert output["total_candidates"] == 2
    assert output["confirmed_count"] == 1
    assert output["pending_count"] == 1
    assert output["stale_overrides"] == ["Departed Economist"]
    assert [(item["name"], item["status"]) for item in output["placements"]] == [("Current Economist", "confirmed"), ("New Economist", "pending")]
