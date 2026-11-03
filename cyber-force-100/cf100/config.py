"""Configuration centrale de Cyber Force 100.

Toutes les valeurs sensibles viennent de l'environnement ; aucun secret
n'est jamais codé en dur. Les chemins par défaut sont relatifs à la
racine du projet (le dossier contenant ce package), ce qui fonctionne
aussi bien depuis un checkout git qu'après `pip install -e .`.
"""

from __future__ import annotations

import os
from pathlib import Path

# Racine du dossier cyber-force-100 (parent du package).
ROOT = Path(__file__).resolve().parent.parent

# Emplacements par défaut (surchargeables par variables d'environnement).
REGISTRY_DIR = Path(os.environ.get("CF100_REGISTRY_DIR", ROOT / "registry"))
MEMORY_DB = Path(os.environ.get("CF100_MEMORY_DB", ROOT / "data" / "memory.db"))
EVIDENCE_LOG = Path(os.environ.get("CF100_EVIDENCE_LOG", ROOT / "data" / "evidence.jsonl"))
SNAPSHOT_DIR = Path(os.environ.get("CF100_SNAPSHOT_DIR", ROOT / "data" / "snapshots"))

# Registres OmniBrain (dépôt omni-agents-framework) — intégration Phase 5,
# lecture dès à présent pour l'alignement des formats.
OMNI_REGISTRY_DIR = Path(
    os.environ.get("CF100_OMNI_REGISTRY_DIR", ROOT.parent / "registry")
)

# Chemin vers le dossier registry/ de l'écosystème (cf100 ou omni).
def registry_dir() -> Path:
    """Dossier des registres, créé s'il n'existe pas."""
    REGISTRY_DIR.mkdir(parents=True, exist_ok=True)
    return REGISTRY_DIR


def data_dir() -> Path:
    """Dossier des données locales (mémoire, preuves), jamais versionné."""
    MEMORY_DB.parent.mkdir(parents=True, exist_ok=True)
    return MEMORY_DB.parent
