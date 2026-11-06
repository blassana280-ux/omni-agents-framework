using System;
using OmniWarships.Core.Simulation;
using Xunit;

namespace OmniWarships.Core.Tests
{
    /// <summary>Voie d'eau et naufrage (matrice : 20-120 s, cloisonnement).</summary>
    public class FloodingTests
    {
        private const float Dt = 1f / 30f;

        private ShipState NewFrigate()
        {
            ShipState s = TestHelpers.MakeShip(TestHelpers.Find(TestHelpers.Specs(), "ws-frigate-01"));
            return s;
        }

        [Fact]
        public void TwoDestroyedCompartmentsSinkIn20to120Seconds()
        {
            ShipState s = NewFrigate();
            TestHelpers.Compartment(s, "bow").Breached = true;
            TestHelpers.Compartment(s, "bow").Destroyed = true;
            TestHelpers.Compartment(s, "engine").Breached = true;
            TestHelpers.Compartment(s, "engine").Destroyed = true;
            float t = 0f;
            while (!s.Sunk && t < 300f) { FloodingModel.Step(s, Dt, t); t += Dt; }
            Assert.True(s.Sunk, "le navire doit couler");
            Assert.True(t >= 20f && t <= 120f,
                "naufrage à " + t + " s (matrice : 20 à 120 s selon gravité)");
        }

        [Fact]
        public void SingleBreachNeverSinksCompartmentalizedShip()
        {
            ShipState s = NewFrigate();
            TestHelpers.Compartment(s, "engine").Breached = true;
            TestHelpers.Compartment(s, "engine").Destroyed = true;
            float t = 0f;
            while (t < 300f) { FloodingModel.Step(s, Dt, t); t += Dt; }
            Assert.False(s.Sunk, "un navire cloisonné survit à une seule brèche");
        }

        [Fact]
        public void LostBuoyancyGrowsWithFlooding()
        {
            ShipState s = NewFrigate();
            TestHelpers.Compartment(s, "engine").Breached = true;
            float prev = FloodingModel.LostBuoyancy(s);
            float t = 0f;
            for (int i = 0; i < 500; i++) { FloodingModel.Step(s, Dt, t); t += Dt; }
            Assert.True(FloodingModel.LostBuoyancy(s) > prev, "la voie d'eau doit s'aggraver");
            Assert.True(FloodingModel.LostBuoyancy(s) <= 1f);
        }
    }
}
