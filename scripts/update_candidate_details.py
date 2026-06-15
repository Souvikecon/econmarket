from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANDIDATES_PATH = ROOT / "data" / "candidates.json"
PLACEMENTS_PATH = ROOT / "data" / "placements.json"
ABSTRACTS_PATH = ROOT / "data" / "abstract_overrides.json"
OUTPUT_PATH = ROOT / "data" / "candidate_details.json"


TOPIC_RULES = {
    "Monetary economics": r"monetary|inflation|interest rate|central bank|federal reserve|phillips curve|bond market",
    "Macro-finance": r"finance|financial|bank|credit|borrowing|debt|asset pric|capital allocation|venture capital|bond|stock market|insurance|bailout|collateral",
    "Labor macro": r"labor|labour|worker|employment|unemployment|occupation|caregiving|human capital",
    "International macro": r"international|exchange rate|currency|trade|export|import|sovereign|cross-border|global",
    "Growth and innovation": r"growth|innovation|technology|productivity|r&d|structural change|development|rural|agricultur",
    "Environmental macro": r"climate|environment|carbon|deforestation|storm|drought|natural disaster",
    "Public and fiscal": r"fiscal|public|government|tax|redistribution|medicaid|subsid|regulation|price control|political economy",
}

PLACEMENT_RULES = {
    "Central bank": r"federal reserve|central bank|bank of korea|bank of portugal|banco de españa|european central bank",
    "International organization": r"international monetary fund|\bimf\b|european commission",
    "Private sector": r"cornerstone research",
    "University / research": r"university|université|universitat|universidad|college|\bschool\b|nber|cemfi|institute|bocconi|bilkent|uquam",
    "Public sector / policy": r"international trade commission|penn wharton budget model",
}


def research_topics(candidate: dict, summary: str) -> list[str]:
    haystack = " ".join([candidate["paper_title"], *candidate["fields"], summary]).lower()
    topics = [label for label, pattern in TOPIC_RULES.items() if re.search(pattern, haystack, re.IGNORECASE)]
    return topics or ["Other macroeconomics"]


def placement_types(placement: dict | None) -> list[str]:
    if not placement or placement["status"] == "pending":
        return ["Not announced"]
    haystack = f"{placement['destination']} {placement['position']}".lower()
    types = [label for label, pattern in PLACEMENT_RULES.items() if re.search(pattern, haystack, re.IGNORECASE)]
    return types or ["Other placement"]


def build_candidate_details(candidates_payload: dict, placements_payload: dict, abstracts_payload: dict) -> dict:
    placements = {item["candidate_id"]: item for item in placements_payload.get("placements", [])}
    summaries = abstracts_payload.get("summaries", {})
    current_names = {candidate["name"] for candidate in candidates_payload.get("candidates", [])}
    stale_summaries = sorted(set(summaries) - current_names)
    details = []
    for candidate in candidates_payload.get("candidates", []):
        summary = summaries.get(candidate["name"], "")
        placement = placements.get(candidate["id"])
        details.append(
            {
                **candidate,
                "abstract_summary": summary,
                "abstract_source_url": candidate["paper_url"],
                "research_topics": research_topics(candidate, summary),
                "placement_status": placement["status"] if placement else "pending",
                "placement_types": placement_types(placement),
                "placement_destination": placement["destination"] if placement else "",
            }
        )
    return {
        "generated_at": candidates_payload.get("generated_at"),
        "reviewed_at": abstracts_payload.get("reviewed_at"),
        "total_candidates": len(details),
        "summaries_available": sum(bool(item["abstract_summary"]) for item in details),
        "stale_summaries": stale_summaries,
        "candidates": details,
    }


def main() -> None:
    candidates_payload = json.loads(CANDIDATES_PATH.read_text(encoding="utf-8"))
    placements_payload = json.loads(PLACEMENTS_PATH.read_text(encoding="utf-8"))
    abstracts_payload = json.loads(ABSTRACTS_PATH.read_text(encoding="utf-8"))
    output = build_candidate_details(candidates_payload, placements_payload, abstracts_payload)
    OUTPUT_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if output["stale_summaries"]:
        print(f"Skipped summaries not on the current roster: {', '.join(output['stale_summaries'])}")
    print(
        f"Wrote {output['total_candidates']} candidate detail record(s) to {OUTPUT_PATH} "
        f"({output['summaries_available']} summaries)"
    )


if __name__ == "__main__":
    main()
