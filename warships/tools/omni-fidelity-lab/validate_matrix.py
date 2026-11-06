#!/usr/bin/env python3
"""Omni Fidelity Lab — validation de la matrice de fidélité (CI).

Vérifie : champs obligatoires, ids uniques, statuts autorisés, critère
mesurable présent pour CHAQUE entrée (défense anti "score de fidélité"
sans mesure), sources citées, aucun secret. Exit 1 si problème.
"""
import json
import re
import sys
from pathlib import Path

REQUIRED = ["id", "category", "reference", "description", "observable",
            "reproduction", "measurable", "status", "tests", "gaps"]
STATUSES = {"planned", "dev", "implemented", "tested"}
SECRET = re.compile(r"(ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{16,}|sk-[A-Za-z0-9]{8,}|AKIA[0-9A-Z]{16}")


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    path = root / "docs" / "fidelity" / "fidelity-matrix.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    problems = []
    entries = data.get("entries", [])
    if not entries:
        problems.append("matrice vide")
    ids = [e.get("id") for e in entries]
    if len(ids) != len(set(ids)):
        problems.append("ids dupliqués")
    for e in entries:
        for field in REQUIRED:
            if field not in e:
                problems.append(f"{e.get('id', '?')}: champ manquant {field}")
        if e.get("status") not in STATUSES:
            problems.append(f"{e.get('id', '?')}: statut inconnu {e.get('status')!r}")
        m = e.get("measurable")
        if not (isinstance(m, dict) and m.get("metric") and m.get("target") and m.get("method")):
            problems.append(f"{e.get('id', '?')}: critère mesurable incomplet")
        if not isinstance(e.get("tests"), list):
            problems.append(f"{e.get('id', '?')}: tests doit être une liste")
    if not data.get("sources"):
        problems.append("sources absentes")
    raw = path.read_text(encoding="utf-8")
    if SECRET.search(raw):
        problems.append("motif de secret détecté")
    if problems:
        for p in problems:
            print(f"ERREUR: {p}")
        return 1
    tested = sum(1 for e in entries if e["status"] == "tested")
    print(f"OK: {len(entries)} entrées, {tested} testées, critères mesurables complets.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
