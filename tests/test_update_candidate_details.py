import json

from scripts.update_candidate_details import (
    ABSTRACTS_PATH,
    CANDIDATES_PATH,
    PLACEMENTS_PATH,
    build_candidate_details,
    placement_types,
    research_topics,
)


def detail_output():
    candidates = json.loads(CANDIDATES_PATH.read_text(encoding="utf-8"))
    placements = json.loads(PLACEMENTS_PATH.read_text(encoding="utf-8"))
    abstracts = json.loads(ABSTRACTS_PATH.read_text(encoding="utf-8"))
    return build_candidate_details(candidates, placements, abstracts)


def test_all_candidates_have_summaries_and_topics():
    candidates = json.loads(CANDIDATES_PATH.read_text(encoding="utf-8"))["candidates"]
    summaries = json.loads(ABSTRACTS_PATH.read_text(encoding="utf-8"))["summaries"]
    output = detail_output()

    assert output["total_candidates"] == len(candidates)
    assert {item["id"] for item in output["candidates"]} == {item["id"] for item in candidates}
    assert output["summaries_available"] == sum(bool(summaries.get(item["name"])) for item in candidates)
    assert output["stale_summaries"] == sorted(set(summaries) - {item["name"] for item in candidates})
    assert all(item["abstract_summary"] == summaries.get(item["name"], "") for item in output["candidates"])
    assert all(item["research_topics"] for item in output["candidates"])


def test_requested_placement_types_are_available():
    for destination, expected in [
        ("Example University", "University / research"),
        ("Federal Reserve", "Central bank"),
        ("International Monetary Fund", "International organization"),
        ("Cornerstone Research", "Private sector"),
    ]:
        assert expected in placement_types({"status": "confirmed", "destination": destination, "position": ""})


def test_requested_research_topics_are_available():
    topics = research_topics({"paper_title": "Monetary Policy, Credit and Employment", "fields": ["Macroeconomics"]}, "")

    assert {"Monetary economics", "Macro-finance", "Labor macro"} <= set(topics)


def test_roster_change_preserves_new_candidates_and_reports_departed_summaries():
    candidates = {"candidates": [{"id": "new", "name": "New Economist", "paper_title": "Monetary Policy", "fields": ["Macroeconomics"], "paper_url": "https://example.edu/paper.pdf"}]}
    output = build_candidate_details(candidates, {"placements": []}, {"summaries": {"Departed Economist": "Reviewed summary"}})

    assert output["total_candidates"] == 1
    assert output["summaries_available"] == 0
    assert output["stale_summaries"] == ["Departed Economist"]
    assert output["candidates"][0]["abstract_summary"] == ""
    assert output["candidates"][0]["placement_types"] == ["Not announced"]
