"""CLI Cyber Force 100.

Commandes :
  validate        — valide le registre (10 divisions, 100 agents) ;
  audit           — auto-audit complet (registre, preuves, secrets) ;
  list [division] — liste les agents (par division) ;
  export-omni     — exporte les agents au format OmniBrain ;
  serve           — démarre l'API (extra api requis) ;
  selftest        — mini-vérification interne (registre + politiques).
"""

from __future__ import annotations

import json
import sys

from cf100.agents.registry import Registry, RegistryError, load_registry
from cf100.core.selfaudit import SelfAuditEngine


def _cmd_validate(_args) -> int:
    reg = load_registry()
    problems = reg.check_tools_against_policy()
    if problems:
        print("ERREURS :", *problems, sep="\n- ")
        return 1
    print(f"OK : {len(reg.divisions)} divisions, {len(reg)} agents, "
          f"outils conformes à la liste blanche.")
    return 0


def _cmd_audit(_args) -> int:
    report = SelfAuditEngine().audit()
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["ok"] else 1


def _cmd_list(args) -> int:
    reg = load_registry()
    if args and args[0] in ("CI", "TH", "VR", "DP", "IR", "MA", "NS",
                            "AS", "AI", "AC"):
        agents = reg.by_division(args[0])
        for a in agents:
            print(f"{a.id:8} {a.name:32} [{a.autonomy.value}/"
                  f"{a.risk_class.value}] {a.mission[:70]}…")
        return 0
    for d in reg.divisions:
        print(f"\n== {d.code} — {d.name} ({len(d.agents)} agents) ==")
        for a in d.agents:
            print(f"  {a.id:8} {a.name}")
    return 0


def _cmd_export_omni(_args) -> int:
    from cf100.bridges.omnibrain import OmniBrainBridge
    reg = load_registry()
    out = OmniBrainBridge(cf100_registry=reg).export_cf100_for_omni()
    print(f"export OmniBrain : {out} ({len(reg)} agents)")
    return 0


def _cmd_serve(_args) -> int:
    try:
        import uvicorn
        from cf100.api.app import create_app
    except ImportError:
        print("extra manquant : pip install '.[api]'")
        return 2
    uvicorn.run(create_app(), host="127.0.0.1", port=8100)


def _cmd_selftest(_args) -> int:
    reg = load_registry()
    bridge_problems = reg.check_tools_against_policy()
    print(f"registre : {len(reg)} agents sur "
          f"{len(reg.divisions)} divisions — "
          f"{'OK' if not bridge_problems else 'PROBLÈMES'}")
    if bridge_problems:
        print(*bridge_problems, sep="\n- ")
        return 1
    return 0


COMMANDS = {
    "validate": _cmd_validate,
    "audit": _cmd_audit,
    "list": _cmd_list,
    "export-omni": _cmd_export_omni,
    "serve": _cmd_serve,
    "selftest": _cmd_selftest,
}


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(__doc__)
        return 0
    cmd, *rest = argv
    handler = COMMANDS.get(cmd)
    if handler is None:
        print(f"commande inconnue : {cmd}\n{__doc__}")
        return 2
    try:
        return handler(rest)
    except RegistryError as exc:
        print(f"registre invalide : {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
