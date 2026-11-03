"""Evidence Engine — journal de preuves append-only à chaîne de hachage.

Chaque entrée embarque le hash de la précédente : toute altération
a posteriori casse la chaîne et est détectée par verify().
"Non altérable autant que possible" = chaîne de hachage vérifiable,
aucune API de suppression ou réécriture exposée aux agents.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from cf100.config import EVIDENCE_LOG

GENESIS = "0" * 64


class EvidenceTampered(Exception):
    """La chaîne de preuves est cassée — incident de sécurité."""


class EvidenceEngine:
    """Journal JSONL append-only avec chaînage cryptographique."""

    def __init__(self, path: Optional[Path] = None):
        self.path = Path(path) if path is not None else Path(EVIDENCE_LOG)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._prev_hash = GENESIS
        if self.path.exists():
            self._prev_hash = self._last_hash()

    # -- écriture -----------------------------------------------------
    def record(self, kind: str, **fields: Any) -> Dict[str, Any]:
        """Ajoute une entrée de preuve ; retourne l'entrée scellée."""
        entry = {
            "ts": round(time.time(), 3),
            "kind": kind,
        }
        entry.update(fields)
        entry["prev_hash"] = self._prev_hash
        canonical = json.dumps(entry, sort_keys=True, ensure_ascii=False)
        entry_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        entry["hash"] = entry_hash
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
        self._prev_hash = entry_hash
        return entry

    # -- lecture / vérification -----------------------------------------
    def entries(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        if not self.path.exists():
            return out
        with self.path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    out.append(json.loads(line))
        return out[-limit:] if limit else out

    def _last_hash(self) -> str:
        entries = self.entries()
        return entries[-1]["hash"] if entries else GENESIS

    def verify(self) -> Dict[str, Any]:
        """Vérifie l'intégrité de toute la chaîne de preuves."""
        prev = GENESIS
        for i, entry in enumerate(self.entries()):
            expected_prev = entry.get("prev_hash")
            stored_hash = entry.get("hash")
            payload = {k: v for k, v in entry.items() if k != "hash"}
            canonical = json.dumps(payload, sort_keys=True,
                                   ensure_ascii=False)
            recomputed = hashlib.sha256(
                canonical.encode("utf-8")).hexdigest()
            if expected_prev != prev or recomputed != stored_hash:
                return {"ok": False, "broken_at": i,
                        "detail": "chaîne de preuves altérée ou entrée "
                                  "réécrite"}
            prev = stored_hash
        return {"ok": True, "entries": len(self.entries()),
                "last_hash": prev}
