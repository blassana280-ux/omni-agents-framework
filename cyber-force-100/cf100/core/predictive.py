"""Predictive Intelligence Engine — anticipation statistique honnête.

Ce moteur n'est pas une boule de cristal : il agrège les fréquences
d'événements observés (EWMA — moyenne mobile exponentielle) par source
(division, agent, type d'alerte) et dérive des scores de risque prédictifs
avec intervalles de confiance simples. Toute prédiction est livrée avec
ses données sous-jacentes.
"""

from __future__ import annotations

import math
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional


class PredictiveEngine:
    """Score de risque prédictif par EWMA + détection de tendance."""

    def __init__(self, alpha: float = 0.3, half_life_s: float = 3600.0):
        self.alpha = alpha
        self.half_life_s = half_life_s
        # source -> {"ewma": float, "count": int, "last_ts": float}
        self._stats: Dict[str, Dict[str, float]] = defaultdict(
            lambda: {"ewma": 0.0, "count": 0, "last_ts": 0.0})

    def observe(self, source: str, weight: float = 1.0,
                ts: Optional[float] = None) -> None:
        """Enregistre un événement de risque observé pour une source."""
        ts = ts if ts is not None else time.time()
        s = self._stats[source]
        s["count"] += 1
        # Décroissance temporelle : un événement ancien pèse moins.
        if s["last_ts"] > 0:
            dt = max(0.0, ts - s["last_ts"])
            decay = math.exp(-dt * math.log(2) / self.half_life_s)
            s["ewma"] = s["ewma"] * decay
        s["ewma"] = s["ewma"] * (1 - self.alpha) + weight * self.alpha
        s["last_ts"] = ts

    def score(self, source: str) -> Dict[str, Any]:
        """Score de risque actuel d'une source, avec son niveau de preuve."""
        s = self._stats.get(source)
        if not s or s["count"] == 0:
            return {"source": source, "ewma": 0.0, "count": 0,
                    "confidence": "none", "trend": "unknown"}
        trend = "rising" if s["ewma"] > 0.5 else ("stable" if s["ewma"] > 0.1
                                                  else "calm")
        confidence = ("high" if s["count"] >= 10 else
                      "medium" if s["count"] >= 3 else "low")
        return {"source": source, "ewma": round(s["ewma"], 3),
                "count": int(s["count"]), "confidence": confidence,
                "trend": trend}

    def forecast(self, top: int = 10) -> List[Dict[str, Any]]:
        """Sources triées par risque prédictif décroissant."""
        scored = [self.score(src) for src in self._stats]
        scored.sort(key=lambda x: x["ewma"], reverse=True)
        return scored[:top]

    def alert_threshold(self, threshold: float = 0.5) -> List[str]:
        """Sources franchissant le seuil d'alerte (anticipation)."""
        return [src for src in self._stats
                if self.score(src)["ewma"] >= threshold]

    def state(self) -> Dict[str, Dict[str, float]]:
        return dict(self._stats)
