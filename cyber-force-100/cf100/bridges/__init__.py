"""Ponts d'intégration : OmniBrain (lecture/export + file de coordination)."""

from cf100.bridges.omni_queue import OmniCoordinator, OmniQueue
from cf100.bridges.omnibrain import OmniBrainBridge

__all__ = ["OmniBrainBridge", "OmniCoordinator", "OmniQueue"]
