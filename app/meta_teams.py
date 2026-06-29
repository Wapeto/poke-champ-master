"""
Reshape scraped Game8 team guides into clean, displayable meta teams.

The raw scrape stores article titles ("Best Rain Team Regulation M-B: Builds
and How to Play Guide") and flat member builds. This module derives a concise
archetype label, drops non-team articles, and enriches each member with the
type / tier / artwork already in the roster so the UI can render real cards.
"""

from __future__ import annotations

import re
from typing import Any

# Stripped from raw article titles to recover the archetype label.
_NOISE = re.compile(
    r"""
      ^Best\s+                                   # leading "Best "
    | \s*[:\-]?\s*Builds\s+and\s+How.*$          # trailing guide boilerplate
    | \s*[:\-]?\s*Complete\s+Roster.*$           # roster/schedule articles
    | \s+Regulation\s+[\w-]+                      # "Regulation M-B" (keep the colon)
    | \s+\b(Teams?|Comps?|Compositions?)\b       # generic "Team(s)" noun
    """,
    re.IGNORECASE | re.VERBOSE,
)


def _clean_name(raw: str) -> str:
    label = _NOISE.sub("", raw).strip(" -:")
    label = re.sub(r"\s{2,}", " ", label)
    return label or raw.strip()


def _member(member: dict, roster: dict[str, dict]) -> dict[str, Any]:
    name = member.get("pokemon", "")
    poke = roster.get(name.lower(), {})
    return {
        "pokemon": name,
        "image_url": poke.get("image_url"),
        "types": poke.get("types", []),
        "tier": poke.get("tier", ""),
        "nature": member.get("nature"),
        "ability": member.get("ability"),
        "held_item": member.get("held_item"),
        "moves": [mv["name"] for mv in member.get("moves", []) if mv.get("name")],
        "ev_spread": member.get("ev_spread"),
    }


def build_meta_teams(teams: list[dict], roster: dict[str, dict]) -> list[dict[str, Any]]:
    """Clean, enriched meta teams with a full 6-member roster only."""
    result: list[dict[str, Any]] = []
    for team in teams:
        members = team.get("members", [])
        if len(members) < 6:
            continue
        result.append({
            "name": _clean_name(team.get("name", "")),
            "raw_name": team.get("name", ""),
            "strategy": team.get("strategy"),
            "source_url": team.get("source_url", ""),
            "members": [_member(m, roster) for m in members],
        })
    return result
