#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OMNI UNITY BRIDGE — synchronisation noyau -> couche Unity.

Recopie OCTET PAR OCTET les 19 fichiers du noyau C# (warships/core) et les
7 specs de navires (warships/data/ships) vers warships/unity/Assets/OmniWarships.
A executer apres toute modification du noyau, puis valider :

    python3 warships/tools/omni-unity-bridge/sync_core.py
    python3 warships/tools/omni-unity-bridge/validate_unity_layer.py

La CI refuse toute copie divergente (comparaison octet par octet) : le
noyau reste l'unique source de verite.
"""
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SRC_CORE = ROOT / "warships" / "core" / "OmniWarships.Core"
DST_CORE = ROOT / "warships" / "unity" / "Assets" / "OmniWarships" / "Core"
SRC_SHIPS = ROOT / "warships" / "data" / "ships"
DST_SHIPS = DST_CORE.parent / "Resources" / "Ships"

CORE_FILES = [
    "AI/TacticalAI.cs",
    "AI/ThreatBoard.cs",
    "Common/Rng.cs",
    "Common/Vec2.cs",
    "Replay/ReplayRecorder.cs",
    "Simulation/BallisticsModel.cs",
    "Simulation/BattleSim.cs",
    "Simulation/CiwsModel.cs",
    "Simulation/DamageModel.cs",
    "Simulation/FloodingModel.cs",
    "Simulation/NavalMovementModel.cs",
    "Simulation/OceanModel.cs",
    "Simulation/SensorModel.cs",
    "Simulation/ShipState.cs",
    "Spec/Compartments.cs",
    "Spec/Enums.cs",
    "Spec/ShipSpec.cs",
    "Spec/SpecLoader.cs",
    "Spec/Weapons.cs",
]

SHIP_FILES = [
    "ws-battleship-01.ship.txt",
    "ws-carrier-01.ship.txt",
    "ws-corvette-01.ship.txt",
    "ws-cruiser-01.ship.txt",
    "ws-destroyer-01.ship.txt",
    "ws-frigate-01.ship.txt",
    "ws-submarine-01.ship.txt",
]


def main():
    copied = 0
    for rel in CORE_FILES:
        src = SRC_CORE / rel
        if not src.is_file():
            sys.exit("sync_core : source absente : " + str(src))
        dst = DST_CORE / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        copied += 1
    for name in SHIP_FILES:
        src = SRC_SHIPS / name
        if not src.is_file():
            sys.exit("sync_core : spec absente : " + str(src))
        dst = DST_SHIPS / name
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        copied += 1
    print("sync_core : " + str(copied) + " fichiers copies (19 noyau + 7 specs).")
    print("Verifier ensuite : python3 warships/tools/omni-unity-bridge/validate_unity_layer.py")


if __name__ == "__main__":
    main()
