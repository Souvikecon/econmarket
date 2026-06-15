from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANDIDATES_PATH = ROOT / "data" / "candidates.json"
OVERRIDES_PATH = ROOT / "data" / "placement_overrides.json"
OUTPUT_PATH = ROOT / "data" / "placements.json"


def build_placements(candidates_payload: dict, overrides_payload: dict) -> dict:
    overrides = overrides_payload.get("placements", {})
    candidates = candidates_payload.get("candidates", [])
    current_names = {candidate["name"] for candidate in candidates}
    unknown_names = sorted(set(overrides) - current_names)

    placements = []
    confirmed_count = 0
    for candidate in candidates:
        placement = overrides.get(candidate["name"])
        confirmed = placement is not None
        confirmed_count += int(confirmed)
        placements.append(
            {
                "candidate_id": candidate["id"],
                "name": candidate["name"],
                "institution": candidate["institution"],
                "country": candidate["country"],
                "rank": candidate["rank"],
                "fields": candidate["fields"],
                "paper_url": candidate["paper_url"],
                "profile_url": candidate["profile_url"],
                "status": "confirmed" if confirmed else "pending",
                "destination": placement["destination"] if confirmed else "",
                "position": placement.get("position", "") if confirmed else "",
                "timing": placement.get("timing", "") if confirmed else "",
                "source_url": placement["source_url"] if confirmed else "",
                "source_label": placement.get("source_label", "Placement source") if confirmed else "",
            }
        )

    return {
        "generated_at": candidates_payload.get("generated_at"),
        "reviewed_at": overrides_payload.get("reviewed_at"),
        "total_candidates": len(placements),
        "confirmed_count": confirmed_count,
        "pending_count": len(placements) - confirmed_count,
        "stale_overrides": unknown_names,
        "placements": placements,
    }


def main() -> None:
    candidates_payload = json.loads(CANDIDATES_PATH.read_text(encoding="utf-8"))
    overrides_payload = json.loads(OVERRIDES_PATH.read_text(encoding="utf-8"))
    output = build_placements(candidates_payload, overrides_payload)
    OUTPUT_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if output["stale_overrides"]:
        print(f"Skipped placement overrides not on the current roster: {', '.join(output['stale_overrides'])}")
    print(
        f"Wrote {output['total_candidates']} placement record(s) to {OUTPUT_PATH} "
        f"({output['confirmed_count']} confirmed, {output['pending_count']} pending)"
    )


if __name__ == "__main__":
    main()
