"""Recovery Engine — snapshots et restauration après incident.

La mémoire est un fichier SQLite : un snapshot est une copie horodatée
atomique. La restauration ne remplace JAMAIS le fichier courant sans
copie de sûreté préalable, et toute restauration est scellée dans les
preuves.
"""

from __future__ import annotations

import shutil
import time
from pathlib import Path
from typing import Any, Dict, Optional

from cf100.config import MEMORY_DB, SNAPSHOT_DIR
from cf100.core.evidence import EvidenceEngine


class RecoveryEngine:
    """Sauvegarde et restauration de l'état (mémoire + preuves)."""

    def __init__(self, evidence: Optional[EvidenceEngine] = None,
                 memory_path: Optional[Path] = None,
                 snapshot_dir: Optional[Path] = None):
        self.evidence = evidence
        self.memory_path = Path(memory_path) if memory_path else MEMORY_DB
        self.snapshot_dir = (Path(snapshot_dir) if snapshot_dir
                             else SNAPSHOT_DIR)

    def snapshot(self, label: str = "manual") -> Optional[Path]:
        """Crée un snapshot horodaté de la mémoire."""
        if not self.memory_path.exists():
            return None
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)
        stamp = time.strftime("%Y%m%d-%H%M%S")
        dest = self.snapshot_dir / f"memory-{stamp}-{label}.db"
        shutil.copy2(self.memory_path, dest)
        if self.evidence is not None:
            self.evidence.record("snapshot", label=label, dest=dest.name)
        return dest

    def restore(self, snapshot_path: Path) -> Dict[str, Any]:
        """Restaure un snapshot avec copie de sûreté du fichier courant."""
        snapshot_path = Path(snapshot_path)
        if not snapshot_path.exists():
            return {"ok": False,
                    "error": f"snapshot introuvable : {snapshot_path}"}
        if self.memory_path.exists():
            backup = self.memory_path.with_suffix(
                f".pre-restore-{int(time.time())}.db")
            shutil.copy2(self.memory_path, backup)
        else:
            backup = None
        shutil.copy2(snapshot_path, self.memory_path)
        if self.evidence is not None:
            self.evidence.record("restore", source=snapshot_path.name,
                                backup=str(backup) if backup else None)
        return {"ok": True, "restored_from": snapshot_path.name,
                "safety_backup": str(backup) if backup else None}

    def list_snapshots(self) -> list:
        if not self.snapshot_dir.exists():
            return []
        return sorted(p.name for p in self.snapshot_dir.glob("memory-*.db"))
