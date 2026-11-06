#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OMNI UNITY BRIDGE — validateur de la couche Unity (job CI).

Vérifie, sans jamais simuler un statut :
  1. fichiers requis du projet Unity (structure minimale) ;
  2. manifest.json + asmdefs = JSON valides, URP dans le manifest,
     référence OmniWarships.Core dans l asmdef Unity, plateforme Editor ;
  3. les 19 copies du noyau C# et les 7 specs sont IDENTIQUES OCTET
     PAR OCTET à leurs sources (warships/core, warships/data) ;
  4. équilibrage des accolades de tous les .cs (commentaires/chaînes retirés) ;
  5. aucune référence UnityEngine dans les copies du noyau ;
  6. syntaxe Python valide des 7 générateurs Blender (py_compile) ;
  7. scan de secrets sur la couche Unity et les outils ;
  8. cohérence des docs (PROOF_STATUS / README) avec la réalité du dépôt ;
  9. T-013.1 — garde-fou de la scène de bataille : chemin UNIQUE partagé
     (Assets/OmniWarships/Battle.unity), inclusion EXPLICITE dans
     BuildPlayerOptions.scenes, échec explicite si aucune scène valide.

Sortie ::error:: GitHub Actions ; exit 1 si au moins une erreur.
"""
import json
import os
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CORE = ROOT / "warships" / "core" / "OmniWarships.Core"
DATA_SHIPS = ROOT / "warships" / "data" / "ships"
UNITY = ROOT / "warships" / "unity"
OMNI = UNITY / "Assets" / "OmniWarships"
UCORE = OMNI / "Core"
SHIPS = OMNI / "Resources" / "Ships"
ASSET_FACTORY = ROOT / "warships" / "tools" / "omni-asset-factory"
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
    "BattleBootstrap.cs", "BattleDirector.cs", "CombatEffects.cs",
    "EffectsPool.cs", "GameEnvironment.cs", "HudController.cs",
    "OceanController.cs", "PauseMenu.cs", "ProjectileView.cs",
    "QualityProfiles.cs", "ShipDamageVisuals.cs", "ShipModelLibrary.cs",
    "ShipView.cs", "SpecSource.cs", "TouchInputController.cs",
    "WakeFoamController.cs", "WarshipCamera.cs", "WeatherDirector.cs",
]

UNITY_EDITOR_SCRIPTS = [
    "AndroidBuildConfig.cs",
    "BattleSceneGuard.cs",
    "OmniWarshipsMenu.cs",
    "WarshipsBuildScript.cs",
]

UNITY_SHADERS = [
    "OmniFlash.shader", "OmniFoam.shader", "OmniOcean.shader",
    "OmniSky.shader", "OmniSmoke.shader",
]

BLENDER_GENERATORS = [
    "omni_blender_common.py",
    "gen_destroyer_blender.py",
    "gen_frigate_blender.py",
    "gen_carrier_blender.py",
    "gen_submarine_blender.py",
    "gen_aircraft_blender.py",
    "gen_equipment_blender.py",
]

REQUIRED_FILES = [
    UNITY / "Packages" / "manifest.json",
    UNITY / "ProjectSettings" / "ProjectVersion.txt",
    UNITY / "README-IMPORT.md",
    UNITY / "ci" / "README-GAMECI.md",
    UNITY / "ci" / "gameci-example.yml",
    OMNI / "OmniWarships.Core.asmdef",
    OMNI / "OmniWarships.Unity.asmdef",
    OMNI / "Editor" / "OmniWarships.Unity.Editor.asmdef",
] + [OMNI / "Editor" / s for s in UNITY_EDITOR_SCRIPTS] \
  + [OMNI / "Scripts" / s for s in UNITY_SCRIPTS] \
  + [OMNI / "Shaders" / s for s in UNITY_SHADERS] \
  + [UCORE / c for c in CORE_COPIES] \
  + [SHIPS / s for s in SHIP_SPECS] \
  + [ASSET_FACTORY / g for g in BLENDER_GENERATORS]


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
            err("manifest.json : URP (com.unity.render-pipelines.universal) absent des dépendances")

    core_asm = load_json(OMNI / "OmniWarships.Core.asmdef")
    if core_asm is not None:
        if core_asm.get("name") != "OmniWarships.Core":
            err("asmdef Core : name != OmniWarships.Core")
        if core_asm.get("references"):
            err("asmdef Core : le noyau ne doit référencer aucun assembly")

    unity_asm = load_json(OMNI / "OmniWarships.Unity.asmdef")
    if unity_asm is not None:
        refs = unity_asm.get("references", [])
        if "OmniWarships.Core" not in refs:
            err("asmdef Unity : référence OmniWarships.Core absente")
        if "Unity.RenderPipelines.Universal.Runtime" not in refs:
            err("asmdef Unity : référence URP runtime absente")

    editor_asm = load_json(OMNI / "Editor" / "OmniWarships.Unity.Editor.asmdef")
    if editor_asm is not None:
        if "Editor" not in editor_asm.get("includePlatforms", []):
            err("asmdef Editor : includePlatforms doit contenir Editor")
        if "OmniWarships.Core" not in editor_asm.get("references", []):
            err("asmdef Editor : référence OmniWarships.Core absente")

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
            continue  # déjà signalé par check_required
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
        + [OMNI / "Editor" / s for s in UNITY_EDITOR_SCRIPTS]
    for p in targets:
        if not p.is_file():
            continue
        stripped = strip_csharp(p.read_text(encoding="utf-8"))
        if stripped.count("{") != stripped.count("}"):
            err("accolades déséquilibrées : " + str(p.relative_to(ROOT))
                + " ({=" + str(stripped.count("{")) + " }=" + str(stripped.count("}")) + ")")


# ------------------------------------------------ pas de UnityEngine noyau

def check_no_unityengine():
    for rel in CORE_COPIES:
        p = UCORE / rel
        if p.is_file() and "UnityEngine" in p.read_text(encoding="utf-8"):
            err("référence UnityEngine interdite dans la copie noyau : " + str(rel))


# --------------------------------------------- syntaxe des générateurs 3D

def check_python_syntax():
    """Compile (sans exécuter) chaque générateur Blender : attrape les
    erreurs de syntaxe avant qu'un exécuteur Blender réel ne les rencontre."""
    try:
        import py_compile
    except ImportError:
        return
    tmpdir = tempfile.gettempdir()
    for name in BLENDER_GENERATORS:
        p = ASSET_FACTORY / name
        if not p.is_file():
            continue  # déjà signalé par check_required
        cfile = os.path.join(tmpdir, "omni_" + name + ".pyc")
        try:
            py_compile.compile(str(p), cfile=cfile, doraise=True)
        except Exception as e:
            err("syntaxe Python invalide (" + name + ") : " + str(e))


# ------------------------------------------------------------- secrets

SECRET_PATTERNS = [
    (re.compile(r"ghp_[A-Za-z0-9]{20,}"), "token GitHub classique"),
    (re.compile(r"github_pat_[A-Za-z0-9_]{20,}"), "token GitHub fine-grained"),
    (re.compile(r"AKIA[0-9A-Z]{16}"), "clé d'accès AWS"),
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "clé privée"),
    (re.compile(r"\bsk-[A-Za-z0-9]{20,}"), "clé API sk-"),
    (re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}"), "token Slack"),
]


def check_secrets():
    roots = [UNITY, ROOT / "warships" / "tools" / "omni-unity-bridge",
             ASSET_FACTORY]
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


# --------------------------------------------- T-013.1 : scène de bataille

def check_scene_build():
    """Garde-fou scène : chemin UNIQUE partagé, inclusion EXPLICITE de la
    scène dans BuildPlayerOptions.scenes, échec explicite sinon. Interdit
    le retour du chemin faux Assets/Scenes/ (bug T-013.1 corrigé)."""
    guard = OMNI / "Editor" / "BattleSceneGuard.cs"
    if guard.is_file():
        t = guard.read_text(encoding="utf-8")
        if "Assets/OmniWarships/Battle.unity" not in t:
            err("BattleSceneGuard.cs : chemin de scène attendu (Assets/OmniWarships/Battle.unity)")
        if "NewSceneMode.Additive" not in t:
            err("BattleSceneGuard.cs : la création automatique doit être additive (ne pas écraser la scène ouverte)")
    menu = OMNI / "Editor" / "OmniWarshipsMenu.cs"
    if menu.is_file() and "BattleSceneGuard" not in menu.read_text(encoding="utf-8"):
        err("OmniWarshipsMenu.cs : la création de scène doit passer par BattleSceneGuard (chemin partagé avec le build)")
    for name in ("AndroidBuildConfig.cs", "WarshipsBuildScript.cs"):
        p = OMNI / "Editor" / name
        if not p.is_file():
            continue  # déjà signalé par check_required
        t = p.read_text(encoding="utf-8")
        if "BattleSceneGuard.BuildScenesOrAbort()" not in t:
            err(name + " : doit passer par BattleSceneGuard.BuildScenesOrAbort() (scène garantie)")
        if "Assets/Scenes/" in t:
            err(name + " : chemin de scène faux Assets/Scenes/ — la scène vit dans Assets/OmniWarships/")
        if "scenes = scenes" not in t:
            err(name + " : la scène doit être incluse EXPLICITEMENT dans BuildPlayerOptions.scenes")
    build = OMNI / "Editor" / "WarshipsBuildScript.cs"
    if build.is_file():
        t = build.read_text(encoding="utf-8")
        if "EditorApplication.Exit(1)" not in t:
            err("WarshipsBuildScript.cs : tout échec de build doit sortir avec EditorApplication.Exit(1)")


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
            err("README.md : tools/omni-replay-debug n'existe pas dans le dépôt (structure mensongère)")


def main():
    check_required()
    check_json()
    check_copies()
    check_braces()
    check_no_unityengine()
    check_python_syntax()
    check_secrets()
    check_scene_build()
    check_docs()
    if errors:
        print("validate_unity_layer : " + str(len(errors)) + " erreur(s)")
        for e in errors:
            print("  - " + e)
        sys.exit(1)
    total = len(REQUIRED_FILES)
    print("validate_unity_layer : OK — " + str(total) + " fichiers requis, 19 copies noyau"
          + " et 7 specs identiques octet par octet, 7 générateurs Blender"
          + " syntaxiquement valides, garde-fou scène de bataille OK"
          + " (chemin unique + inclusion explicite), aucun secret, docs cohérents.")


if __name__ == "__main__":
    main()

