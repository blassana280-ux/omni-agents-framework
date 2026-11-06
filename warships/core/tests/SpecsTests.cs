using System;
using System.Collections.Generic;
using OmniWarships.Core.Spec;
using Xunit;

namespace OmniWarships.Core.Tests
{
    /// <summary>Specs embarquées : invariants de la matrice de fidélité.</summary>
    public class SpecsTests
    {
        [Fact]
        public void LoadsSevenEmbeddedSpecsWithUniqueIds()
        {
            List<ShipSpec> specs = TestHelpers.Specs();
            Assert.True(specs.Count >= 7, "7 navires attendus, obtenu " + specs.Count);
            for (int i = 0; i < specs.Count; i++)
            {
                for (int j = i + 1; j < specs.Count; j++)
                    Assert.NotEqual(specs[i].Id, specs[j].Id);
                Assert.True(specs[i].Compartments.Count >= 1, specs[i].Id + ": aucun compartiment");
                Assert.True(specs[i].Weapons.Count >= 1, specs[i].Id + ": aucune arme");
                Assert.True(specs[i].Sensors.Count >= 1, specs[i].Id + ": aucun capteur");
                Assert.True(specs[i].LengthM >= 20f && specs[i].LengthM <= 350f);
            }
        }

        [Fact]
        public void SpeedSpreadAtLeast2_2x()
        {
            List<ShipSpec> specs = TestHelpers.Specs();
            float max = 0f, min = float.MaxValue;
            foreach (ShipSpec s in specs)
            {
                if (s.MaxSpeedKn > max) max = s.MaxSpeedKn;
                if (s.MaxSpeedKn < min) min = s.MaxSpeedKn;
            }
            Assert.True(max / min >= 2.2f, "écart de vitesse " + (max / min) + " < 2.2 (matrice de fidélité)");
        }

        [Fact]
        public void SubmarineIsStealthy()
        {
            ShipSpec sub = TestHelpers.Find(TestHelpers.Specs(), "ws-submarine-01");
            Assert.True(sub.Acoustic <= 0.3f, "sous-marin trop bruyant");
            Assert.True(sub.RcsM2 <= 500f, "sous-marin trop visible");
            float sonar = 0f, radar = 0f;
            foreach (var s in sub.Sensors)
            {
                if (s.Kind == SensorKind.Sonar) sonar = s.RangeM;
                if (s.Kind == SensorKind.Radar) radar = s.RangeM;
            }
            Assert.True(sonar > radar, "un sous-marin écoute plus loin qu'il ne voit");
        }

        [Fact]
        public void BattleshipCarriesThreeCiws()
        {
            ShipSpec b = TestHelpers.Find(TestHelpers.Specs(), "ws-battleship-01");
            int ciws = 0;
            foreach (WeaponSpec w in b.Weapons)
                if (w.Kind == WeaponKind.Ciws) { ciws++; Assert.True(w.Ammo >= 2000, "CIWS sous-munitionné"); }
            Assert.Equal(3, ciws);
        }

        [Fact]
        public void FrigateCarriesTorpedoes()
        {
            ShipSpec f = TestHelpers.Find(TestHelpers.Specs(), "ws-frigate-01");
            WeaponSpec t = TestHelpers.Weapon(f, "torp-x2");
            Assert.NotNull(t);
            Assert.Equal(WeaponKind.Torpedo, t.Kind);
            Assert.True(t.Damage >= 2000f, "torpille trop faible");
        }
    }
}
