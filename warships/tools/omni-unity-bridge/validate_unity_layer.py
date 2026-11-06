#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OMNI UNITY BRIDGE — validateur de la couche Unity (job CI).

Verifie, sans jamais simuler un statut :
  1. fichiers requis du projet Unity (structure minimale) ;
  2. manifest.json + asmdefs = JSON valides, URP dans le manifest,
     reference OmniWarships.Core dans l'asmdef Unity, plateforme Editor ;
  3. les 19 copies du noyau C# et les 7 specs sont IDENTIQUES OCTET
     PAR OCTET a leurs sources (warships/core, warships/data) ;
  4. equilibrage des accolades de tous les .cs (commentaires/chaines retires) ;
  5. aucune reference UnityEngine dans les copies du noyau ;
  6. scan de secrets sur la couche Unity et les outils ;
  7. coherence des docs (PROOF_STATUS / README) avec la realite du depot.

Sortie ::error:: GitHub Actions ; exit 1 si au moins une erreur.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CORE = ROOT / "warships" / "core" / "OmniWarships.Core"
DATA_SHIPS = ROOT / "warships" / "data" / "ships"
UNITY = ROOT / "warships" / "unity"
OMNI = UNITY / "Assets" / "OmniWarships"
UCORE = OMNI / "Core"
SHIPS = OMNI / "Resources" / "Ships"
DOCS = ROOT / "warships" / "docs"

errors = []


def err(msg):
    errors.append(msg)
    print("::error::" + msg.replace("\n", " | "))


# ---------------------------------------------------------------- fichiers

CORE_COPIES = [
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

SHIP_SPECS = [
    "ws-battleship-01.ship.txt",
    "ws-carrier-01.ship.txt",
    "ws-corvette-01.ship.txt",
    "ws-cruiser-01.ship.txt",
    "ws-destroyer-01.ship.txt",
    "ws-frigate-01.ship.txt",
    "ws-submarine-01.ship.txt",
]

UNITY_SCRIPTS = [
    "BattleBootstrap.cs", "BattleDirector.cs", "EffectsPool.cs",
    "HudController.cs", "OceanController.cs", "ProjectileView.cs",
    "QualityProfiles.cs", "ShipView.cs", "SpecSource.cs",
    "TouchInputController.cs", "WarshipCamera.cs",
]

UNITY_SHADERS = ["OmniFlash.shader", "OmniOcean.shader", "OmniSmoke.shader"]

REQUIRED_FILES = [
    UNITY / "Packages" / "manifest.json",
    UNITY / "ProjectSettings" / "ProjectVersion.txt",
    UNITY / "README-IMPORT.md",
    OMNI / "OmniWarships.Core.asmdef",
    OMNI / "OmniWarships.Unity.asmdef",
    OMNI / "Editor" / "OmniWarships.Unity.Editor.asmdef",
    OMNI / "Editor" / "OmniWarshipsMenu.cs",
] + [OMNI / "Scripts" / s for s in UNITY_SCRIPTS] \
  + [OMNI / "Shaders" / s for s in UNITY_SHADERS] \
  + [UCORE / c for c in CORE_COPIES] \
  + [SHIPS / s for s in SHIP_SPECS]


def check_required():
    for p in REQUIRED_FILES:
        if not p.is_file():
            err("fichier manquant : " + str(p.relative_to(ROOT)))


# ------------------------------------------------------------------- JSON

def load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        err("JSON invalide (" + str(path.relative_to(ROOT)) + ") : " + str(e))
        return None


def check_json():
    manifest = load_json(UNITY / "Packages" / "manifest.json")
    if manifest is not None:
        deps = manifest.get("dependencies", {})
        if "com.unity.render-pipelines.universal" not in deps:
            err("manifest.json : URP (com.unity.render-pipelines.universal) absent des dependances")

    core_asm = load_json(OMNI / "OmniWarships.Core.asmdef")
    if core_asm is not None:
        if core_asm.get("name") != "OmniWarships.Core":
            err("asmdef Core : name != OmniWarships.Core")
        if core_asm.get("references"):
            err("asmdef Core : le noyau ne doit referencer aucun assembly")

    unity_asm = load_json(OMNI / "OmniWarships.Unity.asmdef")
    if unity_asm is not None:
        refs = unity_asm.get("references", [])
        if "OmniWarships.Core" not in refs:
            err("asmdef Unity : reference OmniWarships.Core absente")
        if "Unity.RenderPipelines.Universal.Runtime" not in refs:
            err("asmdef Unity : reference URP runtime absente")

    editor_asm = load_json(OMNI / "Editor" / "OmniWarships.Unity.Editor.asmdef")
    if editor_asm is not None:
        if "Editor" not in editor_asm.get("includePlatforms", []):
            err("asmdef Editor : includePlatforms doit contenir Editor")
        if "OmniWarships.Core" not in editor_asm.get("references", []):
            err("asmdef Editor : reference OmniWarships.Core absente")

    version = UNITY / "ProjectSettings" / "ProjectVersion.txt"
    if version.is_file():
        if "2022.3" not in version.read_text(encoding="utf-8"):
            err("ProjectVersion.txt : version Unity inattendue (2022.3 attendu)")


# ------------------------------------------------- copies OCTET PAR OCTET

def check_copies():
    for rel in CORE_COPIES:
        src = CORE / rel
        dst = UCORE / rel
        if not src.is_file():
            err("source noyau absente : " + str(src.relative_to(ROOT)))
            continue
        if not dst.is_file():
            continue  # deja signale par check_required
        if src.read_bytes() != dst.read_bytes():
            err("copie noyau NON identique octet par octet : " + str(dst.relative_to(ROOT)))
    for name in SHIP_SPECS:
        src = DATA_SHIPS / name
        dst = SHIPS / name
        if not src.is_file():
            err("spec source absente : " + str(src.relative_to(ROOT)))
            continue
        if not dst.is_file():
            continue
        if src.read_bytes() != dst.read_bytes():
            err("copie spec NON identique octet par octet : " + str(dst.relative_to(ROOT)))


# -------------------------------------------------------- C# : accolades

def strip_csharp(text):
    out = []
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        nxt = text[i + 1] if i + 1 < n else ""
        if c == "/" and nxt == "/":
            while i < n and text[i] != "\n":
                i += 1
        elif c == "/" and nxt == "*":
            i += 2
            while i + 1 < n and not (text[i] == "*" and text[i + 1] == "/"):
                i += 1
            i += 2
        elif c == '"':
            i += 1
            while i < n and text[i] != '"':
                if text[i] == "\\":
                    i += 1
                i += 1
            i += 1
        elif c == "'":
            i += 1
            while i < n and text[i] != "'":
                if text[i] == "\\":
                    i += 1
                i += 1
            i += 1
        else:
            out.append(c)
            i += 1
    return "".join(out)


def check_braces():
    targets = [UCORE / c for c in CORE_COPIES] \
        + [OMNI / "Scripts" / s for s in UNITY_SCRIPTS] \
        + [OMNI / "Editor" / "OmniWarshipsMenu.cs"]
    for p in targets:
        if not p.is_file():
            continue
        stripped = strip_csharp(p.read_text(encoding="utf-8"))
        if stripped.count("{") != stripped.count("}"):
            err("accolades desequilibrees : " + str(p.relative_to(ROOT))
                + " ({=" + str(stripped.count("{")) + " }=" + str(stripped.count("}")) + ")")


# ------------------------------------------------ pas de UnityEngine noyau

def check_no_unityengine():
    for rel in CORE_COPIES:
        p = UCORE / rel
        if p.is_file() and "UnityEngine" in p.read_text(encoding="utf-8"):
            err("reference UnityEngine interdite dans la copie noyau : " + str(rel))


# ------------------------------------------------------------- secrets

SECRET_PATTERNS = [
    (re.compile(r"ghp_[A-Za-z0-9]{20,}"), "token GitHub classique"),
    (re.compile(r"github_pat_[A-Za-z0-9_]{20,}"), "token GitHub fine-grained"),
    (re.compile(r"AKIA[0-9A-Z]{16}"), "cle d'acces AWS"),
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "cle privee"),
    (re.compile(r"\bsk-[A-Za-z0-9]{20,}"), "cle API sk-"),
    (re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}"), "token Slack"),
]


def check_secrets():
    roots = [UNITY, ROOT / "warships" / "tools" / "omni-unity-bridge"]
    for root in roots:
        if not root.is_dir():
            continue
        for p in root.rglob("*"):
            if not p.is_file():
                continue
            try:
                text = p.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            for pat, label in SECRET_PATTERNS:
                m = pat.search(text)
                if m:
                    err("secret possible (" + label + ") dans " + str(p.relative_to(ROOT)))


# -------------------------------------------------------------------- docs

def check_docs():
    proof = DOCS / "PROOF_STATUS.md"
    if proof.is_file():
        text = proof.read_text(encoding="utf-8")
        if "validate_unity_layer" not in text:
            err("PROOF_STATUS.md : la ligne Couche Unity doit citer le validateur CI (validate_unity_layer)")
        if "warships/unity" not in text:
            err("PROOF_STATUS.md : la preuve de la couche Unity doit citer warships/unity")
    readme = ROOT / "warships" / "README.md"
    if readme.is_file():
        text = readme.read_text(encoding="utf-8")
        if "omni-unity-bridge" not in text:
            err("README.md : la structure doit lister tools/omni-unity-bridge (validateur CI)")
        if "omni-replay-debug" in text:
            err("README.md : tools/omni-replay-debug n'existe pas dans le depot (structure mensongere)")


def main():
    check_required()
    check_json()
    check_copies()
    check_braces()
    check_no_unityengine()
    check_secrets()
    check_docs()
    if errors:
        print("validate_unity_layer : " + str(len(errors)) + " erreur(s)")
        for e in errors:
            print("  - " + e)
        sys.exit(1)
    total = len(REQUIRED_FILES)
    print("validate_unity_layer : OK — " + str(total) + " fichiers requis, 19 copies noyau"
          + " et 7 specs identiques octet par octet, aucun secret, docs coherents.")


if __name__ == "__main__":
    main()
