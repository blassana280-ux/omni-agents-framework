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
     BuildPlayerOptions.scenes, échec explicite si aucune scène valide ;
 10. T-013.2 — namespaces des API de compilation : BuildReport et
     BuildResult vivent dans UnityEditor.Build.Reporting — using
     UnityEditor; ne suffit PAS (CS0246 à la compilation réelle) ;
 11. T-013.3 — dépôt PUBLIC : aucune publication du .ulf (licence
     Unity nominative) — ni artefact, ni release, ni capture ; le
     workflow de licence n autorise AUCUN artefact et exige ACCESS_TOKEN.
 12. T-013.4 — sécurité structurelle du workflow de licence : PAT isolé
     (stockage uniquement, unset + vérification d absence), TOTP
     obligatoire, parcours email neutralisé, sorties filtrées
     (add-mask + grep -vFf), arbre npm verrouillé (npm ci + package-lock
     67 paquets) — avec SELF-TESTS de non-régression sur snippets.
 13. T-013.5 — installation npm MAITRISEE : npm ci --ignore-scripts
     obligatoire, aucun script d installation tiers exécuté, Chromium
     uniquement depuis l URL épinglée (révision 982053 de puppeteer
     13.7.0), domaines externes explicites limités (whitelist), scripts
     d installation du lock limités aux 3 paquets audités — et
     check_license_lock réellement BRANCHÉ (ses erreurs étaient
     ignorées par main : le comptage remontait un double compteur).

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


# ------------------------------ T-013.2 : namespaces des API de build

def check_build_reporting():
    """BuildReport et BuildResult vivent dans le namespace
    UnityEditor.Build.Reporting : 'using UnityEditor;' ne suffit PAS.
    Empêche le retour de l'erreur CS0246 dans les scripts éditeur qui
    pilotent la compilation Android (audit externe T-013.2)."""
    for name in UNITY_EDITOR_SCRIPTS:
        p = OMNI / "Editor" / name
        if not p.is_file():
            continue  # déjà signalé par check_required
        t = p.read_text(encoding="utf-8")
        uses_api = ("BuildReport" in t) or ("BuildResult" in t)
        has_ns = ("using UnityEditor.Build.Reporting;" in t) \
            or ("UnityEditor.Build.Reporting.BuildReport" in t) \
            or ("UnityEditor.Build.Reporting.BuildResult" in t)
        if uses_api and not has_ns:
            err(name + " : BuildReport/BuildResult exigent "
                + "'using UnityEditor.Build.Reporting;' (ou noms complets "
                + "UnityEditor.Build.Reporting.*) — CS0246 sinon")


# --------------------------- T-013.3 : aucune publication du .ulf

def check_ulf_publication():
    """T-013.3 : le dépôt est PUBLIC. Un .ulf (licence Unity nominative)
    ne doit JAMAIS être publié : les artefacts ne sont PAS privés sur un
    dépôt public. Interdit : artefact .ulf, .ulf en release, capture
    d écran publiée par le workflow de licence. Le .ulf va UNIQUEMENT
    dans le secret UNITY_LICENSE, et ACCESS_TOKEN uniquement dans
    l étape de stockage."""
    wf_dir = ROOT / ".github" / "workflows"
    if not wf_dir.is_dir():
        err(".github/workflows introuvable : garde-fou publication .ulf inapplicable")
        return
    for wf in sorted(wf_dir.glob("*.yml")):
        lines = wf.read_text(encoding="utf-8").splitlines()
        for i, line in enumerate(lines):
            if line.strip().startswith("#"):
                continue
            if "upload-artifact" in line:
                for w in lines[i:i + 10]:
                    s = w.strip()
                    if s.startswith("path:") and ".ulf" in s:
                        err(wf.name + " : publication d un .ulf en ARTEFACT interdite (dépôt public)")
            if ".ulf" in line and "release" in line.lower():
                err(wf.name + " : .ulf associé à une release — publication interdite (dépôt public)")
        if wf.name == "warships-license.yml":
            t = "\n".join(lines)
            if "upload-artifact" in t:
                err("warships-license.yml : AUCUN artefact autorisé dans le workflow de licence (T-013.3)")
            if "ACCESS_TOKEN" not in t:
                err("warships-license.yml : le stockage du secret exige ACCESS_TOKEN (aucun repli)")
            if "npm ci" not in t:
                err("warships-license.yml : npm ci requis — arbre verrouille license-tools (T-013.4)")


# --------------------------- T-013.4 : securite structurelle + self-tests

LICENSE_WF = ROOT / ".github" / "workflows" / "warships-license.yml"
LICENSE_TOOLS = ROOT / "warships" / "unity" / "ci" / "license-tools"


def parse_steps(text):
    """Analyse STRUCTURELLE du workflow de licence : chaque step avec son
    nom, ses secrets d env et le corps de son run (T-013.4). Les
    regressions (PAT deplace, masque retire, filtre supprime, TOTP
    rendu facultatif...) font echouer la CI — pas une recherche de
    chaines isolee."""
    steps = []
    cur = None
    for line in text.splitlines():
        if re.match(r"^\s*- name: ", line):
            cur = {"name": re.sub(r"^\s*- name: ", "", line).strip(),
                   "lines": [], "env": []}
            steps.append(cur)
        elif cur is not None:
            cur["lines"].append(line)
            m = re.match(r"^\s+([A-Z_]+):\s*\$\{\{\s*secrets\.([A-Z_]+)\s*\}\}\s*$", line)
            if m:
                cur["env"].append((m.group(1), m.group(2)))
    return steps


def step_run_body(step):
    body = []
    started = False
    for ln in step["lines"]:
        if not started:
            if re.match(r"^\s*run:\s*\|", ln):
                started = True
            continue
        body.append(ln)
    return "\n".join(body)


def check_workflow_security(text):
    """T-013.4 : regles structurelles du workflow de licence (depot public).
    Renvoie la liste des violations (vide = conforme)."""
    errs = []
    steps = parse_steps(text)
    if not steps:
        return ["workflow de licence : aucun step detecte (structure inattendue)"]
    pat_idx = set()
    for i, s in enumerate(steps):
        if "ACCESS_TOKEN" in "\n".join(s["lines"]) or any(sec == "ACCESS_TOKEN" for _, sec in s["env"]):
            pat_idx.add(i)
    if len(pat_idx) != 1:
        errs.append("ACCESS_TOKEN doit etre reference par EXACTEMENT une etape (le stockage) — etapes trouvees : " + str(len(pat_idx)))
    else:
        s = steps[sorted(pat_idx)[0]]
        if "tockage" not in s["name"]:
            errs.append("ACCESS_TOKEN doit vivre dans l etape de STOCKAGE, pas dans : " + s["name"])
        if ("ACCESS_TOKEN", "ACCESS_TOKEN") not in s["env"]:
            errs.append("l etape de stockage doit recevoir ACCESS_TOKEN: ${{ secrets.ACCESS_TOKEN }}")
        body = step_run_body(s)
        if "unset ulf_value ACCESS_TOKEN" not in body:
            errs.append("l etape de stockage doit effacer ulf_value et ACCESS_TOKEN apres usage (unset)")
        if '-n "${ACCESS_TOKEN:-}"' not in body:
            errs.append("l etape de stockage doit verifier l ABSENCE du PAT apres unset")
        if "gh secret set UNITY_LICENSE" not in body:
            errs.append("l etape de stockage doit ecrire le secret via gh secret set UNITY_LICENSE")
        if "gh secret list" not in body:
            errs.append("l etape de stockage doit verifier la mise a jour via gh secret list (jamais la valeur)")
    for i, s in enumerate(steps):
        if i in pat_idx:
            continue
        if "ACCESS_TOKEN" in "\n".join(s["lines"]):
            errs.append("step « " + s["name"] + " » : ACCESS_TOKEN interdit hors de l etape de stockage")
    act = None
    for s in steps:
        if "ctivation" in s["name"]:
            act = s
    if act is None:
        errs.append("step d activation introuvable")
    else:
        body = step_run_body(act)
        for var in ("UNITY_EMAIL", "UNITY_PASSWORD", "UNITY_TOTP_KEY"):
            if ("::add-mask::$" + var) not in body:
                errs.append("activation : masque GitHub manquant pour " + var + " (::add-mask::)")
        if "--authenticator-key" not in body:
            errs.append("activation : --authenticator-key (TOTP) requis")
        if '-z "${UNITY_TOTP_KEY:-}"' not in body:
            errs.append("activation : le TOTP doit etre OBLIGATOIRE (arret explicite si absent)")
        envs = [v for _, v in act["env"]]
        for sec in ("UNITY_EMAIL", "UNITY_PASSWORD", "UNITY_TOTP_KEY"):
            if sec not in envs:
                errs.append("activation : secret " + sec + " absent de l env du step")
        if "ACCESS_TOKEN" in envs:
            errs.append("activation : le PAT ne doit JAMAIS etre fourni a l etape d activation")
        if "unity-email-guard" not in body:
            errs.append("activation : garde anti-email manquante (shim unity-email-guard)")
        if "BLOCKED" not in body or "2FA (Email)" not in body:
            errs.append("activation : une demande de verification par EMAIL doit ARRETER proprement (marqueur BLOCKED + detection 2FA (Email))")
        if "grep -vFf" not in body:
            errs.append("activation : sortie FILTREE requise (grep -vFf fichier de masques) avant tout affichage")
        if "masks" not in body or "rm -f" not in body:
            errs.append("activation : fichier de masques et fichiers temporaires a supprimer (rm -f)")
    noncomment = [ln for ln in text.splitlines() if ln.strip() and not ln.strip().startswith("#")]
    for ln in noncomment:
        if "unity-verify-code" in ln and "email-guard" not in ln and "ulf_log" not in ln and "$shim_dir" not in ln:
            errs.append("ligne interdite : unity-verify-code appele hors de la garde anti-email : " + ln.strip())
        if "upload-artifact" in ln:
            errs.append("workflow de licence : upload-artifact interdit (depot public) : " + ln.strip())
        low = ln.lower()
        if ".ulf" in ln and "release" in low:
            errs.append("workflow de licence : .ulf associe a une release interdit : " + ln.strip())
        if "git add" in low or "git commit" in low or "git push" in low:
            errs.append("workflow de licence : operation git interdite : " + ln.strip())
        if "set -x" in ln:
            errs.append("workflow de licence : set -x interdit (afficherait les valeurs des secrets)")
    joined = "\n".join(noncomment)
    if "npx" in joined:
        errs.append("workflow de licence : npx interdit — outils installes par npm ci depuis le lock")
    if "@latest" in joined:
        errs.append("workflow de licence : @latest interdit")
    if "npm ci" not in joined:
        errs.append("workflow de licence : npm ci (arbre verrouille) requis")
    # T-013.5 : installation maitrisee
    if "npm ci --ignore-scripts" not in joined:
        errs.append("workflow de licence : npm ci doit bloquer les scripts d installation (--ignore-scripts, T-013.5)")
    if re.search(r"\bnode\s+[^\n]*install\.js", joined):
        errs.append("workflow de licence : execution interdite d un script d installation tiers (node ... install.js, T-013.5)")
    if "chromium-browser-snapshots/Linux_x64/982053/chrome-linux.zip" not in joined:
        errs.append("workflow de licence : Chromium doit venir de l URL epinglee (revision 982053, T-013.5)")
    for m in re.finditer(r"https?://([^/\s\"]+)", joined):
        host = m.group(1)
        if host not in ("storage.googleapis.com", "registry.npmjs.org"):
            errs.append("workflow de licence : domaine externe non autorise : " + host)
    if "node_modules/.bin/unity-license-activate" not in joined:
        errs.append("workflow de licence : le binaire doit venir de l arbre verrouille (node_modules/.bin/unity-license-activate)")
    if re.search(r"unity-license-activate@[0-9]", joined):
        errs.append("workflow de licence : reference npm unity-license-activate@X interdite (epingle via package-lock)")
    return errs


def check_license_workflow():
    """Applique les regles T-013.4 au VRAI workflow du depot."""
    if not LICENSE_WF.is_file():
        err("warships-license.yml introuvable : checks T-013.4 inapplicables")
        return
    for e in check_workflow_security(LICENSE_WF.read_text(encoding="utf-8")):
        err(e)


def check_license_lock():
    """T-013.4 : arbre npm verrouille — package.json epingle, package-lock
    complet (67 paquets, integrite sha512, registry officiel)."""
    errs = []
    pj = LICENSE_TOOLS / "package.json"
    lk = LICENSE_TOOLS / "package-lock.json"
    for p in (pj, lk):
        if not p.is_file():
            errs.append("fichier manquant : " + str(p.relative_to(ROOT)))
    if errs:
        return errs
    pkg = load_json(pj)
    lock = load_json(lk)
    if pkg is not None:
        deps = pkg.get("dependencies", {})
        if deps.get("unity-license-activate") != "0.3.9":
            errs.append("package.json : unity-license-activate doit etre epingle en 0.3.9 EXACT")
        for k, v in deps.items():
            if str(v).startswith("^") or str(v).startswith("~") or str(v) == "latest":
                errs.append("package.json : plage non verrouillee interdite (" + k + " " + str(v) + ")")
    if lock is not None:
        if lock.get("lockfileVersion") not in (2, 3):
            errs.append("package-lock.json : lockfileVersion invalide (2 ou 3 attendu)")
        packs = lock.get("packages", {})
        if packs.get("", {}).get("dependencies", {}).get("unity-license-activate") != "0.3.9":
            errs.append("package-lock.json : la racine doit dependre de unity-license-activate 0.3.9 EXACT")
        n = 0
        for key, entry in packs.items():
            if key == "":
                continue
            n += 1
            if not str(entry.get("version", "")).strip():
                errs.append("package-lock.json : champ version manquant pour " + key + " (npm ci refuserait l entree)")
            if not str(entry.get("integrity", "")).startswith("sha512-"):
                errs.append("package-lock.json : integrite sha512 manquante pour " + key)
            if "registry.npmjs.org" not in str(entry.get("resolved", "")):
                errs.append("package-lock.json : URL registry.npmjs.org absente pour " + key)
        if n != 67:
            errs.append("package-lock.json : 67 paquets verrouilles attendus, trouve " + str(n))
        pp = packs.get("node_modules/puppeteer", {})
        if not pp.get("hasInstallScripts"):
            errs.append("package-lock.json : puppeteer doit declarer hasInstallScripts (telechargement Chromium documente)")
        if "puppeteer-13.7.0.tgz" not in str(pp.get("resolved", "")):
            errs.append("package-lock.json : puppeteer doit etre verrouille en 13.7.0")
        # T-013.5 : scripts d installation declares == les 3 AUDITEES
        # (puppeteer install.js, bufferutil et utf-8-validate
        # node-gyp-build) ; toute autre entree hasInstallScripts est une
        # execution de code inattendue a l installation.
        flagged = sorted(k for k, e in packs.items()
                         if isinstance(e, dict) and e.get("hasInstallScripts"))
        expected_scripts = sorted([
            "node_modules/bufferutil",
            "node_modules/puppeteer",
            "node_modules/utf-8-validate",
        ])
        if flagged != expected_scripts:
            errs.append("package-lock.json : scripts d installation declarees != 3 auditees (puppeteer, bufferutil, utf-8-validate) : " + ", ".join(flagged))
    return errs


GOOD_SNIPPET = r"""name: t
on: push
jobs:
  a:
    runs-on: ubuntu-latest
    steps:
      - name: Verification des secrets Unity (aucun PAT ici)
        env:
          MAIL: ${{ secrets.UNITY_EMAIL }}
        run: |
          echo ok
      - name: Activation (TOTP obligatoire, sorties filtrees)
        env:
          UNITY_EMAIL: ${{ secrets.UNITY_EMAIL }}
          UNITY_PASSWORD: ${{ secrets.UNITY_PASSWORD }}
          UNITY_TOTP_KEY: ${{ secrets.UNITY_TOTP_KEY }}
        run: |
          echo "::add-mask::$UNITY_EMAIL"
          echo "::add-mask::$UNITY_PASSWORD"
          echo "::add-mask::$UNITY_TOTP_KEY"
          if [ -z "${UNITY_TOTP_KEY:-}" ]; then
            echo "::error::TOTP obligatoire"
            exit 1
          fi
          shim_dir="$RUNNER_TEMP/unity-email-guard"
          mkdir -p "$shim_dir"
          cat > "$shim_dir/unity-verify-code" <<'GUARD'
          #!/bin/sh
          exit 86
          GUARD
          chmod +x "$shim_dir/unity-verify-code"
          masks="$RUNNER_TEMP/masks.txt"
          printf '%s\n' "$UNITY_EMAIL" "$UNITY_PASSWORD" "$UNITY_TOTP_KEY" > "$masks"
          npm ci --ignore-scripts
          curl --fail --output "$RUNNER_TEMP/c.zip" "https://storage.googleapis.com/chromium-browser-snapshots/Linux_x64/982053/chrome-linux.zip"
          "$GITHUB_WORKSPACE/tools/node_modules/.bin/unity-license-activate" "$UNITY_EMAIL" "$UNITY_PASSWORD" a.alf --authenticator-key "$UNITY_TOTP_KEY" > "$RUNNER_TEMP/activation.log" 2>&1
          if [ -f "$shim_dir/BLOCKED" ] || grep -q '2FA (Email)' "$RUNNER_TEMP/activation.log"; then
            echo "::error::email 2FA — arret propre"
            rm -f "$masks"
            exit 1
          fi
          grep -vFf "$masks" "$RUNNER_TEMP/activation.log" || true
          rm -f "$masks" "$RUNNER_TEMP/activation.log" error.png error.html
      - name: Stockage du secret
        env:
          ACCESS_TOKEN: ${{ secrets.ACCESS_TOKEN }}
        run: |
          ulf_value=$(cat l.ulf)
          printf '%s' "$ulf_value" | GH_TOKEN="$ACCESS_TOKEN" gh secret set UNITY_LICENSE
          updated=$(GH_TOKEN="$ACCESS_TOKEN" gh secret list --json name,updatedAt)
          unset ulf_value ACCESS_TOKEN
          if [ -n "${ACCESS_TOKEN:-}" ]; then
            echo "::error::PAT encore present"
            exit 1
          fi
"""

BAD_SNIPPETS = [
    ("PAT fourni a l etape de verification",
     GOOD_SNIPPET.replace("          MAIL: ${{ secrets.UNITY_EMAIL }}",
                          "          MAIL: ${{ secrets.UNITY_EMAIL }}\n          PAT: ${{ secrets.ACCESS_TOKEN }}")),
    ("add-mask manquant",
     GOOD_SNIPPET.replace('          echo "::add-mask::$UNITY_PASSWORD"\n', "")),
    ("outil flottant npx --yes @latest",
     GOOD_SNIPPET.replace('          "$GITHUB_WORKSPACE/tools/node_modules/.bin/unity-license-activate" "$UNITY_EMAIL" "$UNITY_PASSWORD" a.alf --authenticator-key "$UNITY_TOTP_KEY" > "$RUNNER_TEMP/activation.log" 2>&1',
                          '          npx --yes unity-license-activate@latest "$UNITY_EMAIL" "$UNITY_PASSWORD" a.alf --authenticator-key "$UNITY_TOTP_KEY" > "$RUNNER_TEMP/activation.log" 2>&1')),
    ("publication artefact",
     GOOD_SNIPPET.replace("      - name: Stockage du secret",
                          "      - uses: actions/upload-artifact@v4\n      - name: Stockage du secret")),
    ("recuperation email autorisee (unity-verify-code direct)",
     GOOD_SNIPPET.replace('          masks="$RUNNER_TEMP/masks.txt"',
                          '          masks="$RUNNER_TEMP/masks.txt"\n          npx unity-verify-code "$UNITY_EMAIL" "$UNITY_PASSWORD" out.txt')),
    ("PAT non efface apres usage",
     GOOD_SNIPPET.replace("          unset ulf_value ACCESS_TOKEN\n", "")),
    ("set -x (affichage des secrets)",
     GOOD_SNIPPET.replace('          echo "::add-mask::$UNITY_EMAIL"',
                          '          set -x\n          echo "::add-mask::$UNITY_EMAIL"')),
    ("TOTP facultatif",
     GOOD_SNIPPET.replace('          if [ -z "${UNITY_TOTP_KEY:-}" ]; then\n            echo "::error::TOTP obligatoire"\n            exit 1\n          fi\n', "")),
    ("npm ci sans --ignore-scripts (scripts tiers executes, T-013.5)",
     GOOD_SNIPPET.replace("npm ci --ignore-scripts", "npm ci")),
    ("script d installation tiers execute (node install.js, T-013.5)",
     GOOD_SNIPPET.replace(
         '          curl --fail --output "$RUNNER_TEMP/c.zip" "https://storage.googleapis.com/chromium-browser-snapshots/Linux_x64/982053/chrome-linux.zip"\n',
         '          curl --fail --output "$RUNNER_TEMP/c.zip" "https://storage.googleapis.com/chromium-browser-snapshots/Linux_x64/982053/chrome-linux.zip"\n'
         '          node node_modules/puppeteer/install.js\n')),
    ("URL Chromium non epinglee (revision non figee, T-013.5)",
     GOOD_SNIPPET.replace("Linux_x64/982053/chrome-linux.zip",
                          "Linux_x64/999999/chrome-linux.zip")),
    ("domaine externe non autorise (miroir inconnu, T-013.5)",
     GOOD_SNIPPET.replace(
         "https://storage.googleapis.com/chromium-browser-snapshots/Linux_x64/982053/chrome-linux.zip",
         "https://chromium.mirror-inconnu.example/Linux_x64/982053/chrome-linux.zip")),
]


def run_security_selftests():
    """SELF-TESTS de non-regression : le snippet SAIN doit donner 0 erreur,
    chaque snippet FAUX doit etre detecte. Une regression du validateur ou
    du workflow de licence fait echouer la CI (T-013.4)."""
    fails = []
    errs = check_workflow_security(GOOD_SNIPPET)
    if errs:
        fails.append("snippet SAIN doit donner 0 erreur — trouve : " + " | ".join(errs[:4]))
    for label, snippet in BAD_SNIPPETS:
        if not check_workflow_security(snippet):
            fails.append("regression NON detectee : " + label)
    total = 1 + len(BAD_SNIPPETS)
    if fails:
        for f in fails:
            err("self-test T-013.4 : " + f)
    else:
        print("self-tests T-013.4 : " + str(total) + "/" + str(total)
              + " OK (snippet sain + " + str(len(BAD_SNIPPETS)) + " regressions toutes detectees)")


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
    check_build_reporting()
    check_ulf_publication()
    check_license_workflow()
    for e in check_license_lock():
        err(e)
    run_security_selftests()
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
          + " (chemin unique + inclusion explicite), namespaces build OK,"
          + " aucune publication .ulf, aucun secret, docs cohérents,"
          + " PAT isolé + TOTP obligatoire + parcours email neutralisé"
          + " + arbre verrouillé 67 paquets + scripts d installation"
          + " maitrisés + domaines épinglés (T-013.4/T-013.5),"
          + " self-tests OK.")


if __name__ == "__main__":
    main()

