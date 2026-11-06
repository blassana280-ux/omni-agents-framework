using System;
using System.Collections.Generic;
using OmniWarships.Core.Common;
using OmniWarships.Core.Replay;
using OmniWarships.Core.Spec;
using OmniWarships.Core.Simulation;
using Xunit;

namespace OmniWarships.Core.Tests
{
    /// <summary>OMNI REPLAY & DEBUG : le noyau déterministe rejoue la bataille à l'identique.</summary>
    public class ReplayTests
    {
        [Fact]
        public void ReplayReproducesBattleExactly()
        {
            List<ShipSpec> specs = TestHelpers.Specs();
            var sim = new BattleSim(99, specs, 2, 0.15f, 8f);
            sim.AddShip("ws-frigate-01", "blue", 0f, -3000f, 0f, false);
            sim.AddShip("ws-destroyer-01", "red", 0f, 3000f, 180f, true);

            ReplayData replay = ReplayRecorder.Capture(sim);
            for (int t = 1; t <= 400; t++)
            {
                var cmd = new ShipCommand { Throttle = 0.8f, Rudder = 0.3f };
                cmd.Fires.Add(new FireRequest { WeaponId = "main-gun", TargetShipId = "s2" });
                var cmds = new Dictionary<string, ShipCommand>();
                cmds["s1"] = cmd;
                ReplayRecorder.RecordPlayerCommands(replay, cmds);
                sim.Tick(cmds);
            }

            string text = ReplayRecorder.ToText(replay);
            ReplayData parsed = ReplayRecorder.FromText(text);
            Assert.Equal(99, parsed.Seed);
            Assert.Equal(2, parsed.Ships.Count);
            Assert.Equal(400, parsed.Ticks.Count);

            BattleSim reSim = ReplayRecorder.ReplayToEnd(parsed, specs);

            Assert.Equal(sim.Ships.Count, reSim.Ships.Count);
            Assert.Equal(sim.Events.Count, reSim.Events.Count);
            for (int i = 0; i < sim.Ships.Count; i++)
            {
                ShipState a = sim.Ships[i];
                ShipState b = reSim.Ships[i];
                Assert.True(Vec2.Distance(a.Pos, b.Pos) <= 1e-4f, "position divergente pour " + a.Id);
                Assert.True(Math.Abs(a.HeadingDeg - b.HeadingDeg) <= 1e-4f, "cap divergent pour " + a.Id);
                Assert.Equal(a.Sunk, b.Sunk);
                Assert.Equal(a.Compartments.Count, b.Compartments.Count);
                for (int c = 0; c < a.Compartments.Count; c++)
                    Assert.True(Math.Abs(a.Compartments[c].Hp - b.Compartments[c].Hp) <= 1e-3f,
                        "HP divergent pour " + a.Id + "/" + a.Compartments[c].Id);
            }
        }

        [Fact]
        public void ReplaySurvivesTextRoundTrip()
        {
            List<ShipSpec> specs = TestHelpers.Specs();
            var sim = new BattleSim(5, specs, 3, 0.2f, 12f);
            sim.AddShip("ws-corvette-01", "blue", -500f, 0f, 90f, false);
            sim.AddShip("ws-submarine-01", "red", 500f, 2000f, 180f, true);
            ReplayData replay = ReplayRecorder.Capture(sim);
            var cmds = new Dictionary<string, ShipCommand>();
            var cmd = new ShipCommand { Throttle = 1f, Rudder = -0.2f };
            cmds["s1"] = cmd;
            ReplayRecorder.RecordPlayerCommands(replay, cmds);
            sim.Tick(cmds);
            string text = ReplayRecorder.ToText(replay);
            ReplayData parsed = ReplayRecorder.FromText(text);
            Assert.Equal(5, parsed.Seed);
            Assert.Equal(3, parsed.SeaState);
            Assert.Equal(1, parsed.Ticks.Count);
            Assert.Equal(0.2f, parsed.Fog, 4);
        }
    }
}
