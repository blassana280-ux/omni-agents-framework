"""Evidence Engine — journal de preuves append-only à chaîne de hachage.

Chaque entrée embarque le hash de la précédente : toute altération
a posteriori casse la chaîne et est détectée par verify(). La
troncature de la fin du journal (suppression de la dernière entrée)
est indétectable par la seule chaîne : un sidecar `<journal>.head`
compte les entrées et retient le dernier hash — verify() compare
les deux et détecte le journal raccourci.
"Non altérable autant que possible" = chaîne vérifiable + sidecar,
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
        self._count = 0
        head = self._head_path()
        if self.path.exists():
            if head.is_file():
                try:
                    data = json.loads(head.read_text(encoding="utf-8"))
                    self._count = int(data.get("count", 0))
                    self._prev_hash = data.get("last_hash", GENESIS)
                except (json.JSONDecodeError, OSError):
                    self._rebuild_from_journal()
            else:
                self._rebuild_from_journal()

    # -- chemins -------------------------------------------------------
    def _head_path(self) -> Path:
        return self.path.with_name(self.path.name + ".head")

    def _rebuild_from_journal(self) -> None:
        """Fichier sans sidecar : l'état est reconstruit depuis le journal."""
        entries = self.entries()
        self._count = len(entries)
        self._prev_hash = entries[-1]["hash"] if entries else GENESIS

    def _write_head(self) -> None:
        self._head_path().write_text(
            json.dumps({"count": self._count, "last_hash": self._prev_hash}),
            encoding="utf-8")

    # -- écriture -----------------------------------------------------
    def record(self, kind: str, **fields: Any) -> Dict[str, Any]:
        """Ajoute une entrée de preuve ; retourne l'entrée scellée."""
        entry: Dict[str, Any] = {
            "ts": round(time.time(), 3),
            "kind": kind,
            "seq": self._count,
        }
        entry.update(fields)
        entry["prev_hash"] = self._prev_hash
        canonical = json.dumps(entry, sort_keys=True, ensure_ascii=False)
        entry_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        entry["hash"] = entry_hash
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
        self._count += 1
        self._prev_hash = entry_hash
        self._write_head()
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

    def verify(self) -> Dict[str, Any]:
        """Vérifie l'intégrité de la chaîne ET l'absence de troncature."""
        prev = GENESIS
        seq_expected = 0
        last_hash = GENESIS
        for i, entry in enumerate(self.entries()):
            if entry.get("seq") != seq_expected:
                return {"ok": False, "broken_at": i,
                        "detail": "séquence discontinue — entrée insérée "
                                  "ou supprimée"}
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
            last_hash = stored_hash
            seq_expected += 1
        # sidecar : le journal a-t-il été raccourci depuis la fin ?
        head = self._head_path()
        if head.is_file():
            try:
                data = json.loads(head.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                return {"ok": False, "broken_at": seq_expected,
                        "detail": "sidecar de preuves illisible"}
            if int(data.get("count", -1)) != seq_expected:
                return {"ok": False, "broken_at": seq_expected,
                        "detail": "journal tronqué : "
                                  f"{data.get('count')} entrées attendues, "
                                  f"{seq_expected} présentes"}
            if data.get("last_hash") not in (None, last_hash):
                return {"ok": False, "broken_at": seq_expected,
                        "detail": "dernier hash divergent du sidecar"}
        return {"ok": True, "entries": seq_expected, "last_hash": prev}
