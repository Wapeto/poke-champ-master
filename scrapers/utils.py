import json
import re
from pathlib import Path
from typing import Any


STAT_ALIASES: dict[str, str] = {
    "hp": "hp", "h": "hp",
    "atk": "atk", "attack": "atk", "at": "atk",
    "def": "def", "defense": "def", "defence": "def",
    "spa": "spa", "spatk": "spa", "sp.atk": "spa", "sp.a": "spa",
    "spd": "spd", "spdef": "spd", "sp.def": "spd", "sp.d": "spd",
    "spe": "spe", "speed": "spe",
}


def normalize_stat(name: str) -> str | None:
    key = name.strip().lower().replace(" ", "").replace(".", "")
    return STAT_ALIASES.get(key)


def empty_evs() -> dict[str, int]:
    return {"hp": 0, "atk": 0, "def": 0, "spa": 0, "spd": 0, "spe": 0}


def parse_ev_text(text: str) -> dict[str, int]:
    """Parse EV/stat spread from strings like '252 Atk / 4 Def / 252 Spe' or 'HP 2 | SpA 32 | Spe 32'."""
    evs = empty_evs()
    # "252 Atk" pattern
    for m in re.finditer(r"(\d+)\s+([A-Za-z][A-Za-z\. ]*?)(?=\s*[\d/|,]|\s*$)", text):
        key = normalize_stat(m.group(2))
        if key:
            evs[key] = int(m.group(1))
    # "Atk 252" or "Atk: 252" pattern
    for m in re.finditer(r"([A-Za-z][A-Za-z\. ]*?)\s*:?\s*(\d+)(?=\s*[/|,]|\s*$)", text):
        key = normalize_stat(m.group(1))
        if key:
            evs[key] = int(m.group(2))
    return evs


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower().strip()).strip("_")


def save_json(data: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
