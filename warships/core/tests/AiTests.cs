using System;
using System.Collections.Generic;
using OmniWarships.Core.Spec;
using OmniWarships.Core.Simulation;
using Xunit;

namespace OmniWarships.Core.Tests
{
    /// <summary>IA tactique (matrice : réaction <= 2 s en difficulté normale).</summary>
    public class AiTests
    {
        [Fact]
        public void AiEngagesWithinTwoSecondsOfDetection()
        {
            List<ShipSpec> specs = TestHelpers.Specs();
            var sim = new BattleSim(7, specs, 2, 0f, 8f);
            sim.AddShip("ws-destroyer-01", "red", 0f, 0f, 0f, true);   // IA
            sim.AddShip("ws-frigate-01", "blue", 0f, 9000f, 180f, false); // joueur immobile

            int detectionTick = -1;
            int launchTick = -1;
            for (int t = 1; t <= 300; t++)
            {
                sim.Tick(null);
                foreach (BattleEvent e in sim.Events)
                {
                    if (e.Tick != sim.TickIndex) continue;
                    if (e.Kind == BattleEventKind.Detection && e.ShipId == "s1" && detectionTick < 0) detectionTick = e.Tick;
                    if (e.Kind == BattleEventKind.Launch && e.ShipId == "s1" && launchTick < 0) launchTick = e.Tick;
                }
            }
            Assert.True(detectionTick > 0, "le destroyer IA doit détecter la frégate");
            Assert.True(launchTick > 0, "le destroyer IA doit ouvrir le feu");
            Assert.True(launchTick - detectionTick <= 60,
                "réaction en " + (launchTick - detectionTick) / 30f + " s (matrice : <= 2 s)");
            Assert.True(sim.Ship("s1").SpeedMs > 0.1f, "l'IA doit manœurer (approche)");
        }

        [Fact]
        public void ThreatBoardRanksBattleshipAboveCorvette()
        {
            ShipState self = TestHelpers.MakeShip(TestHelpers.Find(TestHelpers.Specs(), "ws-frigate-01"));
            ShipState corvette = TestHelpers.MakeShip(TestHelpers.Find(TestHelpers.Specs(), "ws-corvette-01"));
            ShipState battleship = TestHelpers.MakeShip(TestHelpers.Find(TestHelpers.Specs(), "ws-battleship-01"));
            corvette.Pos = new OmniWarships.Core.Common.Vec2(0f, 5000f);
            battleship.Pos = new OmniWarships.Core.Common.Vec2(0f, 5000f);
            var ctC = new Contact { ShipId = corvette.Id, Quality = 0.9f, EstimatedPos = corvette.Pos };
            var ctB = new Contact { ShipId = battleship.Id, Quality = 0.9f, EstimatedPos = battleship.Pos };
            float scoreC = OmniWarships.Core.AI.ThreatBoard.Score(self, ctC, corvette);
            float scoreB = OmniWarships.Core.AI.ThreatBoard.Score(self, ctB, battleship);
            Assert.True(scoreB > scoreC * 2.5f, "un cuirassé est bien plus menaçant qu'une corvette");
        }
    }
}
