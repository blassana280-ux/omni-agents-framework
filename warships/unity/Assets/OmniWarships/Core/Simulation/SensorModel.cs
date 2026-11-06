using System;
using System.Collections.Generic;
using OmniWarships.Core.Common;
using OmniWarships.Core.Spec;

namespace OmniWarships.Core.Simulation
{
    public sealed class DetectionInfo
    {
        public string Detector;
        public string Target;
        public SensorKind Kind;
        public float RangeM;
    }

    /// <summary>
    /// Detecteurs : portee radar selon RCS (equation du radar, forme
    /// simplifiee), sonar selon signature acoustique.
    /// </summary>
    public static class SensorModel
    {
        public static void Update(BattleSim sim)
        {
            sim.Detections.Clear();
            foreach (var detector in sim.ShipList)
            {
                if (!detector.Alive) continue;
                foreach (var spec in detector.Spec.Sensors)
                {
                    if (spec.Kind == SensorKind.Radar && !detector.HasSystem(ShipSystemKind.Radar)) continue;
                    if (spec.Kind == SensorKind.Sonar && !detector.HasSystem(ShipSystemKind.Sonar)) continue;

                    foreach (var target in sim.ShipList)
                    {
                        if (target.Id == detector.Id || !target.Alive) continue;
                        float dist = Vec2.Distance(detector.Pos, target.Pos);
                        if (dist > RangeFor(spec, target.Spec)) continue;

                        sim.Detections.Add(new DetectionInfo
                        {
                            Detector = detector.Id,
                            Target = target.Id,
                            Kind = spec.Kind,
                            RangeM = dist
                        });
                        sim.Events.Add(new BattleEvent
                        {
                            Kind = BattleEventKind.Detection,
                            Time = sim.Time,
                            Source = detector.Id,
                            Target = target.Id,
                            Detail = dist
                        });
                    }
                }
            }
        }

        /// <summary>Portee de detection effective : varie comme la racine quatrieme de la RCS.</summary>
        public static float RangeFor(SensorSpec sensor, ShipSpec target)
        {
            if (sensor.Kind == SensorKind.Radar)
            {
                float ratio = target.RcsM2 / sensor.Ref;
                return sensor.RangeM * (float)Math.Pow(Math.Max(0.1, ratio), 0.25);
            }
            return sensor.RangeM * (float)Math.Pow(Math.Max(0.1, target.Acoustic / sensor.Ref), 0.5);
        }
    }
}
