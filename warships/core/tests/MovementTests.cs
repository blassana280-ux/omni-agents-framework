using System;
using OmniWarships.Core.Common;
using OmniWarships.Core.Spec;
using OmniWarships.Core.Simulation;
using Xunit;

namespace OmniWarships.Core.Tests
{
    /// <summary>Physique de navigation (matrice : inertie, crash-stop, virage).</summary>
    public class MovementTests
    {
        private const float Dt = 1f / 30f;

        [Fact]
        public void FrigateReaches95PctOfMaxSpeedIn60s()
        {
            ShipSpec spec = TestHelpers.Find(TestHelpers.Specs(), "ws-frigate-01");
            ShipState s = TestHelpers.MakeShip(spec);
            var ocean = new OceanModel(0, 0f, 1);
            var cmd = new ShipCommand { Throttle = 1f };
            float t = 0f;
            for (int i = 0; i < 1800; i++) { NavalMovementModel.Step(s, cmd, ocean, Dt, t); t += Dt; }
            Assert.True(s.SpeedMs >= 0.95f * spec.MaxSpeedMs,
                "vitesse " + s.SpeedMs + " < 95% de " + spec.MaxSpeedMs);
        }

        [Fact]
        public void NoTurnInPlaceWhenStopped()
        {
            ShipSpec spec = TestHelpers.Find(TestHelpers.Specs(), "ws-frigate-01");
            ShipState s = TestHelpers.MakeShip(spec);
            var ocean = new OceanModel(0, 0f, 1);
            var cmd = new ShipCommand { Throttle = 0f, Rudder = 1f };
            float t = 0f;
            for (int i = 0; i < 300; i++) { NavalMovementModel.Step(s, cmd, ocean, Dt, t); t += Dt; }
            Assert.Equal(0f, s.HeadingDeg);
            Assert.Equal(0f, s.SpeedMs);
        }

        [Fact]
        public void CrashStopDistanceAtLeast8ShipLengths()
        {
            ShipSpec spec = TestHelpers.Find(TestHelpers.Specs(), "ws-frigate-01");
            ShipState s = TestHelpers.MakeShip(spec);
            var ocean = new OceanModel(0, 0f, 1);
            var full = new ShipCommand { Throttle = 1f };
            var back = new ShipCommand { Throttle = -1f };
            float t = 0f;
            for (int i = 0; i < 1450; i++) { NavalMovementModel.Step(s, full, ocean, Dt, t); t += Dt; }
            Assert.True(s.SpeedMs >= 0.99f * spec.MaxSpeedMs, "le navire n'a pas atteint sa vitesse max");
            Vec2 stopStart = s.Pos;
            int steps = 0;
            while (s.SpeedMs > 0f && steps < 9000)
            {
                NavalMovementModel.Step(s, back, ocean, Dt, t); t += Dt; steps++;
            }
            float dist = Vec2.Distance(stopStart, s.Pos);
            Assert.True(dist >= 8f * spec.LengthM,
                "distance d'arrêt " + dist + " m < 8 x " + spec.LengthM + " m");
        }

        [Fact]
        public void TurnRateRealisticAtSpeed()
        {
            ShipSpec spec = TestHelpers.Find(TestHelpers.Specs(), "ws-frigate-01");
            ShipState s = TestHelpers.MakeShip(spec);
            var ocean = new OceanModel(0, 0f, 1);
            var cmd = new ShipCommand { Throttle = 1f, Rudder = 1f };
            float t = 0f;
            for (int i = 0; i < 1800; i++) { NavalMovementModel.Step(s, cmd, ocean, Dt, t); t += Dt; }
            float delta = OmniWarships.Core.AI.TacticalAI.HeadingDelta(0f, s.HeadingDeg);
            Assert.True(delta >= 100f && delta <= 150f,
                "virage en 60 s : " + delta + " degrés (attendu ~130)");
        }
    }
}
