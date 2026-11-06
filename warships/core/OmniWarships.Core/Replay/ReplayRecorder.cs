using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;
using OmniWarships.Core.Spec;
using OmniWarships.Core.Simulation;

namespace OmniWarships.Core.Replay
{
    public sealed class ShipPlacement
    {
        public string SpecId; public string Team;
        public float X, Z, HeadingDeg; public bool IsAi;
    }

    public sealed class ReplayCommand
    {
        public string ShipId;
        public float Throttle, Rudder;
        public List<FireRequest> Fires = new List<FireRequest>();
    }

    public sealed class ReplayTick
    {
        public List<ReplayCommand> Commands = new List<ReplayCommand>();
    }

    /// <summary>
    /// OMNI REPLAY &amp; DEBUG : capture et rejoue une bataille complete
    /// depuis (graine, environnement, placements, commandes joueur).
    /// Le noyau etant deterministe, le replay reproduit l'etat exact.
    /// </summary>
    public sealed class ReplayData
    {
        public int Seed;
        public int SeaState; public float Fog, WindMs;
        public List<ShipPlacement> Ships = new List<ShipPlacement>();
        public List<ReplayTick> Ticks = new List<ReplayTick>();
    }

    public static class ReplayRecorder
    {
        public static ReplayData Capture(BattleSim sim)
        {
            var d = new ReplayData();
            d.Seed = sim.Seed;
            d.SeaState = sim.SeaState;
            d.Fog = sim.Fog;
            d.WindMs = sim.WindMs;
            foreach (ShipState s in sim.Ships)
            {
                d.Ships.Add(new ShipPlacement { SpecId = s.Spec.Id, Team = s.Team, X = s.Pos.X, Z = s.Pos.Y, HeadingDeg = s.HeadingDeg, IsAi = s.IsAi });
            }
            return d;
        }

        public static void RecordPlayerCommands(ReplayData d, IDictionary<string, ShipCommand> cmds)
        {
            var tick = new ReplayTick();
            if (cmds != null)
            {
                foreach (KeyValuePair<string, ShipCommand> kv in cmds)
                {
                    var rc = new ReplayCommand { ShipId = kv.Key, Throttle = kv.Value.Throttle, Rudder = kv.Value.Rudder };
                    if (kv.Value.Fires != null) rc.Fires.AddRange(kv.Value.Fires);
                    tick.Commands.Add(rc);
                }
            }
            d.Ticks.Add(tick);
        }

        public static string ToText(ReplayData d)
        {
            var sb = new StringBuilder();
            sb.Append("replay v1").Append('\n');
            sb.Append("seed ").Append(d.Seed).Append('\n');
            sb.Append("env ").Append(d.SeaState).Append(' ')
              .Append(F(d.Fog)).Append(' ').Append(F(d.WindMs)).Append('\n');
            foreach (ShipPlacement sp in d.Ships)
            {
                sb.Append("ship ").Append(sp.SpecId).Append(' ').Append(sp.Team).Append(' ')
                  .Append(F(sp.X)).Append(' ').Append(F(sp.Z)).Append(' ').Append(F(sp.HeadingDeg)).Append(' ')
                  .Append(sp.IsAi ? "ai" : "player").Append('\n');
            }
            for (int i = 0; i < d.Ticks.Count; i++)
            {
                sb.Append("tick ").Append(i + 1).Append('\n');
                foreach (ReplayCommand rc in d.Ticks[i].Commands)
                {
                    sb.Append("cmd ").Append(rc.ShipId).Append(' ').Append(F(rc.Throttle)).Append(' ').Append(F(rc.Rudder));
                    foreach (FireRequest fr in rc.Fires)
                    {
                        sb.Append(" fire ").Append(fr.WeaponId).Append(' ').Append(fr.TargetShipId);
                    }
                    sb.Append('\n');
                }
            }
            return sb.ToString();
        }

        public static ReplayData FromText(string text)
        {
            var d = new ReplayData();
            ReplayTick current = null;
            foreach (string raw in text.Split('\n'))
            {
                string line = raw.Trim();
                if (line.Length == 0) continue;
                string[] p = line.Split(new char[] { ' ', '\t' }, StringSplitOptions.RemoveEmptyEntries);
                if (p[0] == "replay") continue;
                if (p[0] == "seed") { d.Seed = int.Parse(p[1], CultureInfo.InvariantCulture); continue; }
                if (p[0] == "env")
                {
                    d.SeaState = int.Parse(p[1], CultureInfo.InvariantCulture);
                    d.Fog = PF(p[2]);
                    d.WindMs = PF(p[3]);
                    continue;
                }
                if (p[0] == "ship")
                {
                    d.Ships.Add(new ShipPlacement
                    {
                        SpecId = p[1], Team = p[2],
                        X = PF(p[3]), Z = PF(p[4]), HeadingDeg = PF(p[5]),
                        IsAi = p[6] == "ai"
                    });
                    continue;
                }
                if (p[0] == "tick")
                {
                    current = new ReplayTick();
                    d.Ticks.Add(current);
                    continue;
                }
                if (p[0] == "cmd" && current != null)
                {
                    var rc = new ReplayCommand { ShipId = p[1], Throttle = PF(p[2]), Rudder = PF(p[3]) };
                    for (int i = 4; i + 1 < p.Length; i += 2)
                    {
                        if (p[i] == "fire") rc.Fires.Add(new FireRequest { WeaponId = p[i + 1], TargetShipId = p[i + 2 <= p.Length - 1 ? p[i + 2] : p[i + 1] });
                    }
                    current.Commands.Add(rc);
                    continue;
                }
            }
            return d;
        }

        public static BattleSim CreateSim(ReplayData d, IList<ShipSpec> specs)
        {
            var sim = new BattleSim(d.Seed, specs, d.SeaState, d.Fog, d.WindMs);
            foreach (ShipPlacement sp in d.Ships)
            {
                sim.AddShip(sp.SpecId, sp.Team, sp.X, sp.Z, sp.HeadingDeg, sp.IsAi);
            }
            return sim;
        }

        /// <summary>Rejoue la bataille enregistree et renvoie la sim finale.</summary>
        public static BattleSim ReplayToEnd(ReplayData d, IList<ShipSpec> specs)
        {
            BattleSim sim = CreateSim(d, specs);
            foreach (ReplayTick t in d.Ticks)
            {
                var cmds = new Dictionary<string, ShipCommand>();
                foreach (ReplayCommand rc in t.Commands)
                {
                    var cmd = new ShipCommand { Throttle = rc.Throttle, Rudder = rc.Rudder };
                    cmd.Fires.AddRange(rc.Fires);
                    cmds[rc.ShipId] = cmd;
                }
                sim.Tick(cmds);
            }
            return sim;
        }

        private static string F(float v)
        {
            return v.ToString("0.####", CultureInfo.InvariantCulture);
        }

        private static float PF(string s)
        {
            return float.Parse(s, CultureInfo.InvariantCulture);
        }
    }
}
