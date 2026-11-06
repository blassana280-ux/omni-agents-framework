using System;
using OmniWarships.Core.Simulation;
using Xunit;

namespace OmniWarships.Core.Tests
{
    /// <summary>Capteurs (matrice : qualité 0.9 à mi-portée, brouillard -30%, brouillage -40%, sonar/profondeur).</summary>
    public class SensorTests
    {
        private ShipState Frigate() { return TestHelpers.MakeShip(TestHelpers.Find(TestHelpers.Specs(), "ws-frigate-01")); }
        private ShipState Destroyer() { return TestHelpers.MakeShip(TestHelpers.Find(TestHelpers.Specs(), "ws-destroyer-01")); }
        private ShipState Submarine() { return TestHelpers.MakeShip(TestHelpers.Find(TestHelpers.Specs(), "ws-submarine-01")); }

        private SensorSpec Radar(ShipState owner)
        {
            foreach (SensorSpec s in owner.Spec.Sensors) if (s.Kind == SensorKind.Radar) return s;
            return null;
        }
        private SensorSpec Sonar(ShipState owner)
        {
            foreach (SensorSpec s in owner.Spec.Sensors) if (s.Kind == SensorKind.Sonar) return s;
            return null;
        }

        [Fact]
        public void RadarQualityAtHalfEffectiveRange()
        {
            SensorSpec radar = Radar(Frigate());
            ShipState target = Destroyer();
            float rangeEff = radar.RangeM * (float)Math.Sqrt(target.Spec.RcsM2 / radar.Ref);
            float q;
            Assert.True(SensorModel.DetectRadar(radar, target, rangeEff * 0.5f, 0f, 0f, out q));
            Assert.True(q >= 0.89f && q <= 0.91f, "qualité à mi-portée : " + q + " (matrice : 0.9)");
        }

        [Fact]
        public void NoDetectionBeyondEffectiveRange()
        {
            SensorSpec radar = Radar(Frigate());
            ShipState target = Destroyer();
            float rangeEff = radar.RangeM * (float)Math.Sqrt(target.Spec.RcsM2 / radar.Ref);
            float q;
            Assert.False(SensorModel.DetectRadar(radar, target, rangeEff * 1.05f, 0f, 0f, out q));
        }

        [Fact]
        public void DenseFogCutsRadarRangeBy30Pct()
        {
            SensorSpec radar = Radar(Frigate());
            ShipState target = Destroyer();
            float rangeEff = radar.RangeM * (float)Math.Sqrt(target.Spec.RcsM2 / radar.Ref);
            float q;
            Assert.False(SensorModel.DetectRadar(radar, target, rangeEff * 0.75f, 1f, 0f, out q),
                "à 75% de portée sous brouillard dense : non détecté");
            Assert.True(SensorModel.DetectRadar(radar, target, rangeEff * 0.65f, 1f, 0f, out q),
                "à 65% de portée : encore détecté");
        }

        [Fact]
        public void JammingCutsRadarRangeBy40Pct()
        {
            SensorSpec radar = Radar(Frigate());
            ShipState target = Destroyer();
            float rangeEff = radar.RangeM * (float)Math.Sqrt(target.Spec.RcsM2 / radar.Ref);
            float q;
            Assert.False(SensorModel.DetectRadar(radar, target, rangeEff * 0.65f, 0f, 1f, out q),
                "sous brouillage actif, 65% de portée : non détecté");
            Assert.True(SensorModel.DetectRadar(radar, target, rangeEff * 0.5f, 0f, 1f, out q));
        }

        [Fact]
        public void DeepSubmarineSonarRangeIs40PctOfSurfaced()
        {
            SensorSpec sonar = Sonar(Frigate());
            ShipState sub = Submarine();
            float q;
            sub.DepthM = 0f;
            Assert.True(SensorModel.DetectSonar(sonar, sub, 2700f, out q), "en surface : détecté à 2700 m");
            sub.DepthM = 150f;
            Assert.False(SensorModel.DetectSonar(sonar, sub, 1200f, out q),
                "en plongée profonde : non détecté à 1200 m (> 40% de la portée surface)");
            Assert.True(SensorModel.DetectSonar(sonar, sub, 1000f, out q), "en plongée : détecté à 1000 m");
        }

        [Fact]
        public void RadarBlindToDivedSubmarine()
        {
            SensorSpec radar = Radar(Frigate());
            ShipState sub = Submarine();
            float q;
            sub.DepthM = 150f;
            Assert.False(SensorModel.DetectRadar(radar, sub, 500f, 0f, 0f, out q));
            sub.DepthM = 0f;
            Assert.True(SensorModel.DetectRadar(radar, sub, 500f, 0f, 0f, out q));
        }
    }
}
