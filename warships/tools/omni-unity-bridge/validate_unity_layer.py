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
 14. T-013.7 — licence : Unity a SUPPRIMÉ l activation manuelle des
     licences Personal (le portail d activation hors-ligne est
     réservé aux sièges Enterprise/Industry) — le flux .alf/.ulf et
     l outillage npm (67 paquets + navigateur de 2022) sont OBSOLÈTES
     et RETIRÉS ; le workflow de licence devient une GARDE DE
     VÉRIFICATION SANS AUCUNE ACTIVATION (aucun npm, aucun navigateur,
     aucun PAT, aucun fichier de licence, aucune connexion Unity) ;
     l activation réelle = méthode personal PAR IDENTIFIANTS
     (UNITY_EMAIL/UNITY_PASSWORD) dans le conteneur du build
     (warships-gameci.yml) ; 2FA du compte Unity DÉSACTIVÉE requise
     (aucun défi réponse-able en headless, plus de TOTP) ; license-tools
     supprimé du dépôt, AUCUN workflow ne le référence.
  15. T-013.8 — build : la compilation passe par GameCI CLI v0.1.72
     (installateur officiel scripts/install.sh du dépôt game-ci/cli,
     épinglé au tag v0.1.72 — l action composite racine de ce dépôt
     est ÉCARTÉE : son install.sh y est commité sans bit exécutable,
     mode 100644 dans l arbre git du tag, exit 126 constaté par un
     run CI réel) et UNE SEULE commande de build :
     le CLI monte SA PROPRE archive de scripts dans /steps du conteneur
     (src/model/docker.ts) — un seul conteneur fait siège Personal (par
     identifiants) + compilation + restitution (trap EXIT armé par
     runsteps.sh même en cas d échec du build). game-ci/unity-builder@v4
     INTERDIT (il monte SES scripts dans /steps en écrasant ceux de l
     image, et ces scripts ne contiennent PAS le chemin personal — bug
     bloquant T-013.7) ; activation isolée interdite (siège laissé actif,
     restitution entre conteneurs distincts non fiable) ; buildMethod et
     scène explicite conservés ; le mot de passe est transmis au Unity
     Licensing Client PAR ARGUMENT DE PROCESSUS dans le conteneur
     (documenté dans le code du CLI, aucune alternative stdin/fichier,
     jamais affiché, aucun set -x) ; compte Unity CI dédié (jamais le
     compte principal), 2FA de ce compte désactivée.
  16. T-013.9 — sécurisation du CLI GameCI avant toute utilisation des
     identifiants Unity : le CLI officiel v0.1.72 met le mot de passe
     DANS la chaîne de commande docker (getEnvVarString émet
     `--env UNITY_PASSWORD="valeur"` et System.run passe la commande à
     `sh -c` : le secret est visible dans l argv des processus du
     runner ; SecretRedaction protège les LOGS, pas l argv — deux
     problèmes différents). Le CLI corrigé vit dans
     warships/unity/ci/gameci-cli-secure : source officielle ÉPINGLÉE
     par SHA git + overlay MINIMAL committé (dépôt officiel JAMAIS
     modifié, fork bloqué 403), identifiants transmis par l ENVIRONNEMENT
     hérité du processus docker (références `--env` SANS valeur),
     binaire publié en release IMMUABLE avec empreinte ancrée dans git,
     installation STRICTEMENT vérifiée (checksums.txt inaccessible,
     empreinte absente, divergence ou mismatch = FATAL ; binaire
     installé comparé bit à bit à l archive vérifiée ; scripts personal
     et trap EXIT requis dans l artefact). AUCUNE activation dans ce
     workflow de release.

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
    UNITY / "ci" / "gameci-cli-secure" / "README.md",
    UNITY / "ci" / "gameci-cli-secure" / "RELEASE-TRIGGER.md",
    UNITY / "ci" / "gameci-cli-secure" / "verify-gameci-cli.sh",
    UNITY / "ci" / "gameci-cli-secure" / "test-verify-gameci-cli.sh",
    UNITY / "ci" / "gameci-cli-secure" / "patched-src" / "src" / "model" / "image-environment-factory.ts",
    UNITY / "ci" / "gameci-cli-secure" / "patched-src" / "src" / "model" / "secure-env.test.ts",
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


# --------------------------- T-013.4 : securite structurelle + self-tests

LICENSE_WF = ROOT / ".github" / "workflows" / "warships-license.yml"


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
    """T-013.7 : le workflow de licence est une GARDE DE VERIFICATION
    SANS AUCUNE ACTIVATION (Unity a supprime l activation manuelle des
    licences Personal ; l activation reelle = methode personal PAR
    IDENTIFIANTS dans le conteneur du build). Renvoie les violations."""
    errs = []
    steps = parse_steps(text)
    if not steps:
        return ["workflow de licence : aucun step detecte (structure inattendue)"]
    verif = None
    clean = None
    for s in steps:
        if "erification des secrets" in s["name"]:
            verif = s
        if "ettoyage" in s["name"]:
            clean = s
    if verif is None:
        errs.append("step de verification des secrets introuvable (methode personal T-013.7)")
    else:
        envs = [v for _, v in verif["env"]]
        for sec in ("UNITY_EMAIL", "UNITY_PASSWORD"):
            if sec not in envs:
                errs.append("verification : secret " + sec + " absent de l env du step (methode personal)")
        body = step_run_body(verif)
        if "verify_secret UNITY_EMAIL" not in body:
            errs.append("verification : verify_secret UNITY_EMAIL requis (jamais affiche)")
        if "verify_secret UNITY_PASSWORD" not in body:
            errs.append("verification : verify_secret UNITY_PASSWORD requis (jamais affiche)")
        if "UNITY_TOTP_KEY" in body:
            errs.append("verification : UNITY_TOTP_KEY obsolete (T-013.7 : activation headless = 2FA DESACTIVEE, aucun TOTP)")
    if clean is None:
        errs.append("step de nettoyage du runner requis (T-013.7)")
    else:
        if "always()" not in "\n".join(clean["lines"]):
            errs.append("le nettoyage doit etre arme sur if: always()")
        if "/tmp/alfdir" not in step_run_body(clean):
            errs.append("nettoyage : /tmp/alfdir (residu des anciens flux) doit etre supprime")
    noncomment = [ln for ln in text.splitlines() if ln.strip() and not ln.strip().startswith("#")]
    joined = "\n".join(noncomment)
    # T-013.7 : AUCUNE activation, AUCUN npm, AUCUN navigateur, AUCUN
    # fichier de licence, AUCUN PAT dans le workflow de verification.
    motifs = (
        "game-ci activate", "unity-license-activate", "license.unity3d.com",
        "unityci/editor", "docker run", "npm ci", "npm install", "npm run",
        "npx ", "puppeteer", "chromium", "chrome-linux",
        "-createManualActivationFile", "activation.alf", ".ulf",
        "UNITY_SERIAL", "UNITY_TOTP_KEY", "UNITY_LICENSE",
        "ACCESS_TOKEN", "gh secret set", "license-tools",
    )
    for motif in motifs:
        if motif in joined:
            errs.append("workflow de licence T-013.7 SANS activation : motif interdit present : " + motif)
    for ln in noncomment:
        if "set -x" in ln:
            errs.append("workflow de licence : set -x interdit (afficherait les valeurs des secrets)")
        if "upload-artifact" in ln:
            errs.append("workflow de licence : upload-artifact interdit (depot public) : " + ln.strip())
        low = ln.lower()
        if "git add" in low or "git commit" in low or "git push" in low:
            errs.append("workflow de licence : operation git interdite : " + ln.strip())
    return errs


def check_license_workflow():
    """Applique les regles T-013.7 au VRAI workflow du depot."""
    if not LICENSE_WF.is_file():
        err("warships-license.yml introuvable : checks T-013.7 inapplicables")
        return
    for e in check_workflow_security(LICENSE_WF.read_text(encoding="utf-8")):
        err(e)


def check_license_tools():
    """T-013.7 : l outillage npm de licence (dossier license-tools —
    67 paquets, unity-license-activate 0.3.9, puppeteer 13.7.0,
    Chromium 101 d avril 2022) est OBSOLETE et RETIRE : Unity a
    supprime l activation manuelle des licences Personal, l ancien
    outil visait une page qui n existe plus. AUCUN workflow ne doit
    plus referencer ce dossier."""
    errs = []
    wf_dir = ROOT / ".github" / "workflows"
    if not wf_dir.is_dir():
        return ["workflows introuvables : check license-tools inapplicable"]
    for wf in sorted(wf_dir.glob("*.yml")):
        t = wf.read_text(encoding="utf-8")
        noncomment = "\n".join(ln for ln in t.splitlines()
                               if ln.strip() and not ln.strip().startswith("#"))
        if "license-tools" in noncomment:
            errs.append(wf.name + " : reference a license-tools interdite (T-013.7 : outillage npm supprime)")
    return errs


# --------------------------- T-013.9 : CLI corrige (heritage ENV)

CLI_SECURE = UNITY / "ci" / "gameci-cli-secure"
CLI_RELEASE_WF = ROOT / ".github" / "workflows" / "warships-cli-release.yml"


def check_gameci_cli_secure():
    """T-013.9 : structure et integrite du CLI corrige. Le depot officiel
    game-ci/cli n est PAS modifie : la source epinglee + l overlay
    commite ici sont verifies structurellement (correctif de securite
    present, tests factices presents, verificateur strict complet,
    workflow de release sans AUCUNE activation Unity et sans jamais
    toucher au bouton de build)."""
    errs = []
    patched = CLI_SECURE / "patched-src" / "src" / "model" / "image-environment-factory.ts"
    if patched.is_file():
        t = patched.read_text(encoding="utf-8")
        for marker in ("credentialEnvNames", "'UNITY_EMAIL'", "'UNITY_PASSWORD'",
                       "if (ImageEnvironmentFactory.credentialEnvNames.has(p.name))"):
            if marker not in t:
                errs.append("patched image-environment-factory.ts : marqueur T-013.9 absent : " + marker)
    test = CLI_SECURE / "patched-src" / "src" / "model" / "secure-env.test.ts"
    if test.is_file():
        t = test.read_text(encoding="utf-8")
        for marker in ("FAKE_EMAIL", "FAKE_PASSWORD", "getEnvVarString",
                       "getInheritedEnvVars", "--env UNITY_EMAIL",
                       "--env UNITY_PASSWORD", "example.invalid"):
            if marker not in t:
                errs.append("secure-env.test.ts : marqueur T-013.9 absent : " + marker)
    verify = CLI_SECURE / "verify-gameci-cli.sh"
    if verify.is_file():
        t = verify.read_text(encoding="utf-8")
        for marker in ("set -euo pipefail", "checksums.txt", "sha256sum",
                       "--include-personal", "trap return_license_once EXIT",
                       "Returning personal license seat", "/steps/runsteps.sh"):
            if marker not in t:
                errs.append("verify-gameci-cli.sh : garde T-013.9 absente : " + marker)
        if "set -x" in t:
            errs.append("verify-gameci-cli.sh : set -x interdit (affichage de secrets)")
    if CLI_RELEASE_WF.is_file():
        t = CLI_RELEASE_WF.read_text(encoding="utf-8")
        noncomment = "\n".join(ln for ln in t.splitlines()
                               if ln.strip() and not ln.strip().startswith("#"))
        requis = ("game-ci/cli", "7da0cea2f31799a4cbd79c1d452c254023f4f678",
                  "bun-version: 1.3.13", "build:assets", "--compile",
                  "frozen-lockfile", "gh release create", "checksums.txt",
                  "artifact-checksum.txt", "BUILD-INFO.txt", "RELEASE-TRIGGER.md",
                  "verify-gameci-cli.sh", "secure-env.test.ts")
        for marker in requis:
            if marker not in noncomment:
                errs.append("warships-cli-release.yml : requis T-013.9 absent : " + marker)
        interdits = ("secrets.UNITY", "unity-builder", "game-ci build", "BUILD-TRIGGER")
        for marker in interdits:
            if marker in noncomment:
                errs.append("warships-cli-release.yml : interdit T-013.9 present : " + marker)
    else:
        errs.append("warships-cli-release.yml introuvable : checks T-013.9 inapplicables")
    for e in errs:
        err(e)

# --------------------------- T-013.8/T-013.9 : build par CLI corrige (heritage ENV)

GAMECI_WF = ROOT / ".github" / "workflows" / "warships-gameci.yml"


def check_gameci_workflow_content(text):
    """T-013.8/T-013.9 : le workflow de build compile via le CLI GameCI
    CORRIGE T-013.9 (v0.1.72 + heritage ENV des identifiants), installe
    UNIQUEMENT par verify-gameci-cli.sh depuis la release immuable
    gameci-cli-secure-v0.1.72w1 avec empreinte ancree dans git
    (artifact-checksum.txt, divergence FATALE). Un seul conteneur (celui
    du CLI, qui monte SA PROPRE archive dist/ dans /steps) fait : siege
    Personal par identifiants + compilation + restitution du siege
    (trap EXIT, meme en cas d echec). L action de build v4 est INTERDITE
    (bug T-013.7), l installateur officiel du depot game-ci/cli est
    ECARTE (checksum soft-fail + identifiants dans la chaine sh -c,
    audit T-013.9). Renvoie les violations (lignes actives uniquement,
    commentaires exclus)."""
    noncomment = "\n".join(ln for ln in text.splitlines()
                           if ln.strip() and not ln.strip().startswith("#"))
    errs = []
    requis = (
        "verify-gameci-cli.sh",
        "gameci-cli-secure-v0.1.72w1",
        "artifact-checksum.txt",
        "game-ci build",
        "OmniWarships.Unity.EditorTools.WarshipsBuildScript.BuildAndroid",
        "--targetPlatform Android",
        "--androidExportType androidPackage",
        "--versioningStrategy None",
        "verify_secret UNITY_EMAIL",
        "verify_secret UNITY_PASSWORD",
        "always()",
    )
    for req in requis:
        if req not in noncomment:
            errs.append("warships-gameci.yml : requis absent (T-013.9) : " + req)
    interdits = (
        "unity-builder", "unity-activate@", "game-ci activate", "game-ci/cli@",
        "raw.githubusercontent.com/game-ci/cli", "bash -s --",
        "UNITY_LICENSE", "UNITY_SERIAL", "UNITY_TOTP_KEY",
        "license.unity3d.com", "set -x",
    )
    for itd in interdits:
        if itd in noncomment:
            errs.append("warships-gameci.yml : interdit present (T-013.9) : " + itd)
    return errs


def check_gameci_workflow():
    """Applique les regles T-013.8/T-013.9 au VRAI workflow de build du depot."""
    if not GAMECI_WF.is_file():
        err("warships-gameci.yml introuvable : checks T-013.8 inapplicables")
        return
    for e in check_gameci_workflow_content(GAMECI_WF.read_text(encoding="utf-8")):
        err(e)


GOOD_GC_SNIPPET = r"""name: t
on: push
jobs:
  a:
    runs-on: ubuntu-latest
    steps:
      - name: Verification des secrets Unity (jamais affiches)
        env:
          MAIL: ${{ secrets.UNITY_EMAIL }}
          PASS: ${{ secrets.UNITY_PASSWORD }}
        run: |
          verify_secret UNITY_EMAIL "$MAIL"
          verify_secret UNITY_PASSWORD "$PASS"
      - name: Installation du CLI corrige T-013.9 (checksum strict, empreinte ancree dans git)
        run: |
          bash warships/unity/ci/gameci-cli-secure/verify-gameci-cli.sh "https://github.com/$GITHUB_REPOSITORY/releases/download/gameci-cli-secure-v0.1.72w1" gameci-cli-secure-linux-x64.tar.gz "$RUNNER_TEMP/game-ci/bin" warships/unity/ci/gameci-cli-secure/artifact-checksum.txt
      - name: Build (un seul conteneur)
        env:
          UNITY_EMAIL: ${{ secrets.UNITY_EMAIL }}
          UNITY_PASSWORD: ${{ secrets.UNITY_PASSWORD }}
        run: |
          game-ci build warships/unity --targetPlatform Android --buildMethod OmniWarships.Unity.EditorTools.WarshipsBuildScript.BuildAndroid --androidExportType androidPackage --versioningStrategy None
      - name: Nettoyage du runner
        if: always()
        run: |
          rm -rf /tmp/alfdir
"""

BAD_GC_SNIPPETS = [
    ("retour a l action de build v4 (scripts /steps sans chemin personal)",
     GOOD_GC_SNIPPET.replace(
         "bash warships/unity/ci/gameci-cli-secure/verify-gameci-cli.sh",
         "uses: game-ci/unity-builder@v4")),
    ("installation par l action composite racine cassee (install.sh racine commite sans bit executable au tag v0.1.72, exit 126)",
     GOOD_GC_SNIPPET.replace(
         "bash warships/unity/ci/gameci-cli-secure/verify-gameci-cli.sh",
         "uses: game-ci/cli@v0.1.72")),
    ("retour a l installateur officiel (T-013.9 : checksum soft-fail, binaire mettant les secrets dans la chaine sh -c)",
     GOOD_GC_SNIPPET.replace(
         "bash warships/unity/ci/gameci-cli-secure/verify-gameci-cli.sh",
         'curl -fsSL "https://raw.githubusercontent.com/game-ci/cli/v0.1.72/scripts/install.sh" | bash -s -- v0.1.72 "$RUNNER_TEMP/game-ci/bin"')),
    ("installation verifiee SANS empreinte ancree dans git (artifact-checksum.txt requis, T-013.9)",
     GOOD_GC_SNIPPET.replace(
         "warships/unity/ci/gameci-cli-secure/artifact-checksum.txt",
         "$RUNNER_TEMP/empreinte.txt")),
    ("activation isolee (siege laisse actif, restitution inter-conteneurs non fiable)",
     GOOD_GC_SNIPPET.replace(
         "          game-ci build warships/unity",
         "          game-ci activate warships/unity\n"
         "          game-ci build warships/unity")),
    ("build sans buildMethod (compilation par defaut, scene non garantie)",
     GOOD_GC_SNIPPET.replace(
         " --buildMethod OmniWarships.Unity.EditorTools.WarshipsBuildScript.BuildAndroid",
         "")),
]


GOOD_SNIPPET = r"""name: t
on: push
jobs:
  a:
    runs-on: ubuntu-latest
    steps:
      - name: Verification des secrets Unity (jamais affiches)
        env:
          MAIL: ${{ secrets.UNITY_EMAIL }}
          PASS: ${{ secrets.UNITY_PASSWORD }}
        run: |
          verify_secret UNITY_EMAIL "$MAIL"
          verify_secret UNITY_PASSWORD "$PASS"
      - name: Nettoyage du runner (aucun fichier sensible)
        if: always()
        run: |
          rm -rf /tmp/alfdir
"""

BAD_SNIPPETS = [
    ("activation .alf relancee (docker, ancien flux T-013.5)",
     GOOD_SNIPPET.replace(
         "      - name: Nettoyage du runner (aucun fichier sensible)",
         "      - name: Generation du fichier de demande .alf\n"
         "        run: |\n"
         "          docker run --rm -v /tmp/alfdir:/project unityci/editor:2022.3.62f1 \\\n"
         "            unity-editor -batchmode -nographics -createManualActivationFile -quit\n"
         "      - name: Nettoyage du runner (aucun fichier sensible)")),
    ("outil npm unity-license-activate reintroduit (puppeteer)",
     GOOD_SNIPPET.replace(
         "          verify_secret UNITY_PASSWORD \"$PASS\"\n",
         "          verify_secret UNITY_PASSWORD \"$PASS\"\n"
         "          cd warships/unity/ci/license-tools\n"
         "          npm ci --ignore-scripts\n"
         "          node_modules/.bin/unity-license-activate \"$MAIL\" \"$PASS\" a.alf\n")),
    ("stockage d un .ulf via PAT (plus de fichier de licence, T-013.7)",
     GOOD_SNIPPET.replace(
         "      - name: Nettoyage du runner (aucun fichier sensible)",
         "      - name: Stockage du secret\n"
         "        env:\n"
         "          ACCESS_TOKEN: ${{ secrets.ACCESS_TOKEN }}\n"
         "        run: |\n"
         "          ulf_value=$(cat l.ulf)\n"
         "          printf '%s' \"$ulf_value\" | GH_TOKEN=\"$ACCESS_TOKEN\" gh secret set UNITY_LICENSE\n"
         "      - name: Nettoyage du runner (aucun fichier sensible)")),
    ("TOTP exige (obsolete : l activation headless exige une 2FA desactivee)",
     GOOD_SNIPPET.replace(
         "          PASS: ${{ secrets.UNITY_PASSWORD }}\n",
         "          PASS: ${{ secrets.UNITY_PASSWORD }}\n"
         "          TOTP: ${{ secrets.UNITY_TOTP_KEY }}\n").replace(
         "          verify_secret UNITY_PASSWORD \"$PASS\"\n",
         "          verify_secret UNITY_PASSWORD \"$PASS\"\n"
         "          verify_secret UNITY_TOTP_KEY \"$TOTP\"\n")),
    ("secrets affiches (set -x)",
     GOOD_SNIPPET.replace(
         "          verify_secret UNITY_EMAIL \"$MAIL\"\n",
         "          set -x\n"
         "          verify_secret UNITY_EMAIL \"$MAIL\"\n")),
    ("nettoyage arme seulement en cas de succes (if: always() retire)",
     GOOD_SNIPPET.replace("        if: always()\n", "")),
    ("exigence UNITY_LICENSE (fichier .ulf obsolete pour un compte gratuit)",
     GOOD_SNIPPET.replace(
         "          PASS: ${{ secrets.UNITY_PASSWORD }}\n",
         "          PASS: ${{ secrets.UNITY_PASSWORD }}\n"
         "          LIC: ${{ secrets.UNITY_LICENSE }}\n").replace(
         "          verify_secret UNITY_PASSWORD \"$PASS\"\n",
         "          verify_secret UNITY_PASSWORD \"$PASS\"\n"
         "          verify_secret UNITY_LICENSE \"$LIC\"\n")),
    ("activation par navigateur (license.unity3d.com, parcours retire par Unity)",
     GOOD_SNIPPET.replace(
         "          verify_secret UNITY_PASSWORD \"$PASS\"\n",
         "          verify_secret UNITY_PASSWORD \"$PASS\"\n"
         "          curl --fail https://license.unity3d.com/manual -o page.html\n")),
]


def run_security_selftests():
    """SELF-TESTS de non-regression : les snippets SAINS (licence T-013.7
    et build T-013.8/T-013.9) doivent donner 0 erreur, chaque snippet FAUX doit
    etre detecte. Une regression du validateur, du workflow de licence
    ou du workflow de build fait echouer la CI."""
    fails = []
    errs = check_workflow_security(GOOD_SNIPPET)
    if errs:
        fails.append("snippet SAIN (licence) doit donner 0 erreur — trouve : " + " | ".join(errs[:4]))
    for label, snippet in BAD_SNIPPETS:
        if not check_workflow_security(snippet):
            fails.append("regression NON detectee : " + label)
    errs = check_gameci_workflow_content(GOOD_GC_SNIPPET)
    if errs:
        fails.append("snippet SAIN (build) doit donner 0 erreur — trouve : " + " | ".join(errs[:4]))
    for label, snippet in BAD_GC_SNIPPETS:
        if not check_gameci_workflow_content(snippet):
            fails.append("regression NON detectee (build) : " + label)
    total = 2 + len(BAD_SNIPPETS) + len(BAD_GC_SNIPPETS)
    if fails:
        for f in fails:
            err("self-test T-013.7/T-013.9 : " + f)
    else:
        print("self-tests T-013.7/T-013.9 : " + str(total) + "/" + str(total)
              + " OK (2 snippets sains + "
              + str(len(BAD_SNIPPETS) + len(BAD_GC_SNIPPETS))
              + " regressions toutes detectees)")


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
    for e in check_license_tools():
        err(e)
    check_gameci_workflow()
    check_gameci_cli_secure()
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
          + " workflow de licence = VERIFICATION sans activation"
          + " (méthode personal par identifiants, 2FA désactivée requise,"
          + " plus de TOTP ni d outillage npm ni de navigateur,"
          + " license-tools absent des workflows) (T-013.7),"
          + " build = GameCI CLI v0.1.72 en UNE SEULE commande (un seul"
          + " conteneur : siège personal + compilation + restitution par"
          + " trap EXIT, action de build v4 et activation isolée"
          + " INTERDITES) (T-013.8),"
          + " self-tests OK,"
          + " et CLI corrigé T-013.9 (identifiants Unity par ENV hérité,"
          + " hors argv : source officielle épinglée + overlay minimal,"
         + " installation strictement vérifiée, scripts personal intacts).")



if __name__ == "__main__":
    main()


