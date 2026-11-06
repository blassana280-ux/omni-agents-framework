#!/usr/bin/env python3
"""Omni Asset Factory / Battle Sandbox — validation des specs de navires.

Parse les fichiers .ship.txt (format ligne-clé : clé valeurs...), commun
au lecteur C# (SpecLoader, embarqué dans l'assemblage) et à la CI.
Vérifie les invariants de la matrice de fidélité. Exit 1 si problème.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SHIPS = ROOT / "data" / "ships"
CLASSES = {"Corvette", "Frigate", "Destroyer", "Cruiser", "Battleship", "Carrier", "Submarine"}
WEAPON_KINDS = {"Gun", "Ssm", "Sam", "Torpedo", "Ciws", "Rocket", "DepthCharge"}
GUIDANCE = {"none", "pn", "straight", "auto"}
SENSOR_KINDS = {"Radar", "Sonar"}
SYSTEMS = {"Propulsion", "Steering", "Radar", "Sonar", "Gunnery", "Missiles", "Hangar", "Comms"}
SCALARS = [
    ("length_m", 20, 350, float), ("beam_m", 5, 60, float), ("draft_m", 1, 15, float),
    ("displacement_t", 200, 80000, float), ("max_speed_kn", 5, 45, float),
    ("accel_kn_s", 0.01, 0.5, float), ("turn_deg_s", 0.5, 5.0, float),
    ("rcs_m2", 50, 100000, float), ("acoustic", 0.05, 1.0, float),
]


def parse(path):
    data = {"compartments": [], "weapons": [], "sensors": []}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        parts = line.split()
        key, rest = parts[0], parts[1:]
        if key == "compartment":
            data["compartments"].append({
                "id": rest[0], "center": float(rest[1]), "half": float(rest[2]),
                "hp": float(rest[3]), "armor": float(rest[4]), "systems": set(rest[5].split(",")),
            })
        elif key == "weapon":
            data["weapons"].append({
                "id": rest[0], "kind": rest[1], "damage": float(rest[2]), "range_m": float(rest[3]),
                "speed": float(rest[4]), "reload": float(rest[5]), "salvo": int(rest[6]),
                "ammo": int(rest[7]), "guidance": rest[8],
            })
        elif key == "sensor":
            data["sensors"].append({"id": rest[0], "kind": rest[1], "range_m": float(rest[2]), "ref": float(rest[3])})
        else:
            data[key] = " ".join(rest) if key in ("id", "name", "class") else rest[0]
    return data


def main() -> int:
    problems = []
    files = sorted(SHIPS.glob("*.ship.txt"))
    if not files:
        print("ERREUR: aucun fichier .ship.txt")
        return 1
    speeds = {}
    for path in files:
        sid = path.stem
        d = parse(path)
        if d.get("id") != sid:
            problems.append(f"{sid}: id de fichier != id de spec")
        if d.get("class") not in CLASSES:
            problems.append(f"{sid}: classe inconnue {d.get('class')!r}")
        for key, lo, hi, conv in SCALARS:
            if key not in d:
                problems.append(f"{sid}: champ manquant {key}")
            else:
                v = float(d[key])
                if not (lo <= v <= hi):
                    problems.append(f"{sid}: {key}={v} hors bornes [{lo},{hi}]")
        if not d["compartments"]:
            problems.append(f"{sid}: aucun compartiment")
        comps = sorted(d["compartments"], key=lambda c: c["center"])
        for c in comps:
            if not (0.0 < c["center"] < 1.0) or not (0.02 <= c["half"] <= 0.30):
                problems.append(f"{sid}: compartiment {c['id']} mal placé")
            if not c["systems"] or not c["systems"] <= SYSTEMS:
                problems.append(f"{sid}: compartiment {c['id']} systèmes invalides")
            if c["hp"] <= 0 or not (0.8 <= c["armor"] <= 2.0):
                problems.append(f"{sid}: compartiment {c['id']} hp/armure invalides")
        if comps and comps[0]["center"] - comps[0]["half"] > 0.15:
            problems.append(f"{sid}: proue non couverte")
        if comps and comps[-1]["center"] + comps[-1]["half"] < 0.85:
            problems.append(f"{sid}: poupe non couverte")
        for a, b in zip(comps, comps[1:]):
            if b["center"] - b["half"] - (a["center"] + a["half"]) > 0.10:
                problems.append(f"{sid}: trou de coque entre {a['id']} et {b['id']}")
        for w in d["weapons"]:
            if w["kind"] not in WEAPON_KINDS or w["guidance"] not in GUIDANCE:
                problems.append(f"{sid}: arme {w['id']} type/guidage invalide")
            if w["damage"] <= 0 or w["range_m"] <= 0 or w["reload"] <= 0 or w["salvo"] < 1 or w["ammo"] < 1:
                problems.append(f"{sid}: arme {w['id']} paramètres invalides")
            if w["kind"] == "Torpedo" and not (10 <= w["speed"] <= 40):
                problems.append(f"{sid}: torpille {w['id']} vitesse irréaliste")
        for s in d["sensors"]:
            if s["kind"] not in SENSOR_KINDS or s["range_m"] <= 0 or s["ref"] <= 0:
                problems.append(f"{sid}: capteur {s['id']} invalide")
        speeds[sid] = float(d.get("max_speed_kn", 0))
    ids = [p.stem for p in files]
    if len(ids) != len(set(ids)):
        problems.append("ids de navires dupliqués")
    # Critère mesurable de la matrice de fidélité : écart de vitesse >= 2.2x
    ratio = max(speeds.values()) / min(speeds.values())
    if ratio < 2.2:
        problems.append(f"écart de vitesse max/min = {ratio:.2f} < 2.2 (matrice de fidélité)")
    if problems:
        for p in problems:
            print(f"ERREUR: {p}")
        return 1
    print(f"OK: {len(files)} navires valides, écart de vitesse {ratio:.2f}x.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
