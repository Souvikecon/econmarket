import json

from scripts.update_candidate_details import (
    ABSTRACTS_PATH,
    CANDIDATES_PATH,
    PLACEMENTS_PATH,
    build_candidate_details,
)


def detail_output():
    candidates = json.loads(CANDIDATES_PATH.read_text(encoding="utf-8"))
    placements = json.loads(PLACEMENTS_PATH.read_text(encoding="utf-8"))
    abstracts = json.loads(ABSTRACTS_PATH.read_text(encoding="utf-8"))
    return build_candidate_details(candidates, placements, abstracts)


def test_all_candidates_have_summaries_and_topics():
    output = detail_output()

    assert output["total_candidates"] == 53
    assert output["summaries_available"] == 53
    assert output["stale_summaries"] == []
    assert all(item["abstract_summary"] for item in output["candidates"])
    assert all(item["research_topics"] for item in output["candidates"])


def test_requested_placement_types_are_available():
    output = detail_output()
    placement_types = {value for item in output["candidates"] for value in item["placement_types"]}

    assert {
        "University / research",
        "Central bank",
        "International organization",
        "Private sector",
    } <= placement_types


def test_requested_research_topics_are_available():
    output = detail_output()
    topics = {value for item in output["candidates"] for value in item["research_topics"]}

    assert {"Monetary economics", "Macro-finance", "Labor macro"} <= topics
