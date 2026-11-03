"""Mémoire persistante Cyber Force 100 — stockage SQLite (stdlib).

Quatre niveaux :
- individuelle  : par agent (clé/valeur) ;
- collective     : savoir partagé, écriture réservée ;
- technique      : configurations, scripts, procédures validées ;
- décisions      : historique immuable des décisions (append-only).

Le stockage par défaut est un fichier SQLite local : aucun service
externe indispensable (PostgreSQL/Qdrant restent des adaptateurs
futurs, cf. docs/ARCHITECTURE.md).
"""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from cf100.config import MEMORY_DB

SCHEMA = """
CREATE TABLE IF NOT EXISTS memory_kv (
    tier        TEXT NOT NULL,
    owner       TEXT NOT NULL,
    key         TEXT NOT NULL,
    value       TEXT NOT NULL,
    created_at  REAL NOT NULL,
    updated_at  REAL NOT NULL,
    PRIMARY KEY (tier, owner, key)
);
CREATE TABLE IF NOT EXISTS decision_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ts          REAL NOT NULL,
    actor       TEXT NOT NULL,
    kind        TEXT NOT NULL,
    action      TEXT NOT NULL,
    risk        TEXT NOT NULL,
    approved_by TEXT,
    payload     TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS knowledge (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ts          REAL NOT NULL,
    agent       TEXT NOT NULL,
    claim       TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'proposed',
    evidence    TEXT NOT NULL DEFAULT '[]'
);
"""

TIERS = ("individual", "collective", "technical")


class MemoryStore:
    """Stockage clé/valeur et historique de décisions, persistant."""

    def __init__(self, path: Optional[Path] = None):
        self.path = Path(path) if path is not None else Path(MEMORY_DB)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.path)
        self._conn.executescript(SCHEMA)
        self._conn.commit()

    # -- clé/valeur --------------------------------------------------
    def set(self, tier: str, owner: str, key: str, value: Any) -> None:
        now = time.time()
        self._conn.execute(
            """INSERT INTO memory_kv (tier, owner, key, value, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(tier, owner, key)
               DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at""",
            (tier, owner, key, json.dumps(value, ensure_ascii=False), now, now))
        self._conn.commit()

    def get(self, tier: str, owner: str, key: str) -> Optional[Any]:
        row = self._conn.execute(
            "SELECT value FROM memory_kv WHERE tier=? AND owner=? AND key=?",
            (tier, owner, key)).fetchone()
        return json.loads(row[0]) if row else None

    def delete(self, tier: str, owner: str, key: str) -> bool:
        cur = self._conn.execute(
            "DELETE FROM memory_kv WHERE tier=? AND owner=? AND key=?",
            (tier, owner, key))
        self._conn.commit()
        return cur.rowcount > 0

    def keys(self, tier: str, owner: str) -> List[str]:
        rows = self._conn.execute(
            "SELECT key FROM memory_kv WHERE tier=? AND owner=? ORDER BY key",
            (tier, owner)).fetchall()
        return [r[0] for r in rows]

    def owners(self, tier: str) -> List[str]:
        rows = self._conn.execute(
            "SELECT DISTINCT owner FROM memory_kv WHERE tier=? ORDER BY owner",
            (tier,)).fetchall()
        return [r[0] for r in rows]

    # -- historique des décisions (append-only) -----------------------
    def log_decision(self, actor: str, kind: str, action: str, risk: str,
                     payload: Dict[str, Any],
                     approved_by: Optional[str] = None) -> int:
        cur = self._conn.execute(
            """INSERT INTO decision_log (ts, actor, kind, action, risk,
               approved_by, payload) VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (time.time(), actor, kind, action, risk, approved_by,
             json.dumps(payload, ensure_ascii=False)))
        self._conn.commit()
        return cur.lastrowid

    def decisions(self, actor: Optional[str] = None,
                  limit: int = 50) -> List[Dict[str, Any]]:
        if actor:
            rows = self._conn.execute(
                """SELECT id, ts, actor, kind, action, risk, approved_by, payload
                   FROM decision_log WHERE actor=? ORDER BY id DESC LIMIT ?""",
                (actor, limit)).fetchall()
        else:
            rows = self._conn.execute(
                """SELECT id, ts, actor, kind, action, risk, approved_by, payload
                   FROM decision_log ORDER BY id DESC LIMIT ?""",
                (limit,)).fetchall()
        return [{
            "id": r[0], "ts": r[1], "actor": r[2], "kind": r[3],
            "action": r[4], "risk": r[5], "approved_by": r[6],
            "payload": json.loads(r[7]),
        } for r in rows]

    # -- apprentissage contrôlé : propositions de connaissances -------
    def propose_knowledge(self, agent: str, claim: str,
                          evidence: Optional[List[str]] = None) -> int:
        cur = self._conn.execute(
            """INSERT INTO knowledge (ts, agent, claim, status, evidence)
               VALUES (?, ?, ?, 'proposed', ?)""",
            (time.time(), agent, claim,
             json.dumps(evidence or [], ensure_ascii=False)))
        self._conn.commit()
        return cur.lastrowid

    def knowledge_status(self, kid: int) -> str:
        row = self._conn.execute(
            "SELECT status FROM knowledge WHERE id=?", (kid,)).fetchone()
        return row[0] if row else ""

    def set_knowledge_status(self, kid: int, status: str) -> None:
        if status not in ("proposed", "tested", "validated", "rejected"):
            raise ValueError(f"statut de connaissance invalide : {status}")
        self._conn.execute("UPDATE knowledge SET status=? WHERE id=?",
                           (status, kid))
        self._conn.commit()

    def validated_knowledge(self) -> List[Dict[str, Any]]:
        rows = self._conn.execute(
            """SELECT id, ts, agent, claim, evidence FROM knowledge
               WHERE status='validated' ORDER BY id""").fetchall()
        return [{"id": r[0], "ts": r[1], "agent": r[2], "claim": r[3],
                 "evidence": json.loads(r[4])} for r in rows]

    def close(self) -> None:
        self._conn.close()
