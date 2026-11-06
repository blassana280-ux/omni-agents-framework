using System;
using System.Collections.Generic;
using OmniWarships.Core.Spec;
using OmniWarships.Core.Simulation;
using Xunit;

namespace OmniWarships.Core.Tests
{
    /// <summary>CIWS (matrice : 55-85% d'interception de missiles subsoniques, graine fixe).</summary>
    public class CiwsTests
    {
        [Fact]
        public void CiwsInterceptsSubsonicSsmSalvo()
        {
            List<ShipSpec> specs = TestHelpers.Specs();
            var sim = new BattleSim(42, specs, 2, 0f, 8f);
            sim.AddShip("ws-cruiser-01", "blue", 0f, 0f, 0f, false);
            sim.AddShip("ws-destroyer-01", "red", 0f, 8000f, 180f, false);

            int launches = 0;
            for (int t = 1; t <= 1600; t++)
            {
                var cmds = new Dictionary<string, ShipCommand>();
                if (launches < 12 && t <= 700)
                {
                    var cmd = new ShipCommand();
                    cmd.Fires.Add(new FireRequest { WeaponId = "ssm-x16", TargetShipId = "s2" });
                    cmds["s1"] = cmd;
                }
                sim.Tick(cmds);
                launches = Count(sim, BattleEventKind.Launch, "s1", null);
            }
            int intercepts = Count(sim, BattleEventKind.Intercept, "s2", null);
            int hits = Count(sim, BattleEventKind.Hit, null, "s2");

            Assert.Equal(12, launches);
            Assert.True(intercepts >= 7 && intercepts <= 10,
                "interceptions " + intercepts + "/12 = " + (100 * intercepts / 12) + "% (matrice : 55-85%)");
            Assert.Equal(12, intercepts + hits); // chaque missile est résolu
        }

        private static int Count(BattleSim sim, BattleEventKind kind, string shipId, string targetId)
        {
            int n = 0;
            foreach (BattleEvent e in sim.Events)
            {
                if (e.Kind != kind) continue;
                if (shipId != null && e.ShipId != shipId) continue;
                if (targetId != null && e.TargetId != targetId) continue;
                n++;
            }
            return n;
        }
    }
}
