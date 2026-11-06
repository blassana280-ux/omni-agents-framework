#!/usr/bin/env python3
"""Omni Battle Sandbox — validation des scénarios (CI). Exit 1 si problème."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[2]  # warships/
SCEN = HERE / "scenarios"
SPECS = {p.stem for p in (ROOT / "data" / "ships").glob("*.ship.txt")}


def main() -> int:
    problems = []
    files = sorted(SCEN.glob("*.json"))
    if not files:
        print("ERREUR: aucun scénario")
        return 1
    ids = []
    for path in files:
        d = json.loads(path.read_text(encoding="utf-8"))
        ids.append(d.get("id"))
        if d.get("id") != path.stem:
            problems.append(f"{path.name}: id != nom de fichier")
        env = d.get("environment", {})
        if not (0 <= env.get("sea_state", -1) <= 9):
            problems.append(f"{path.stem}: sea_state invalide")
        if not (0 <= env.get("wind_ms", -1) <= 40):
            problems.append(f"{path.stem}: wind_ms invalide")
        if not (0 <= env.get("fog", -1) <= 1):
            problems.append(f"{path.stem}: fog invalide")
        ships = d.get("ships", [])
        if len(ships) < 2:
            problems.append(f"{path.stem}: il faut au moins 2 navires")
        teams = set()
        for s in ships:
            teams.add(s.get("team"))
            if s.get("spec") not in SPECS:
                problems.append(f"{path.stem}: spec inconnue {s.get('spec')!r}")
            if not (0 <= s.get("heading_deg", -1) < 360):
                problems.append(f"{path.stem}: heading invalide")
        if len(teams) < 2:
            problems.append(f"{path.stem}: il faut au moins 2 équipes")
        if not (30 <= d.get("duration_s", 0) <= 900):
            problems.append(f"{path.stem}: duration_s hors bornes")
    if len(ids) != len(set(ids)):
        problems.append("ids de scénarios dupliqués")
    if problems:
        for p in problems:
            print(f"ERREUR: {p}")
        return 1
    print(f"OK: {len(files)} scénarios valides.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
