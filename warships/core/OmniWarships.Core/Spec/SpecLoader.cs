using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Reflection;

namespace OmniWarships.Core.Spec
{
    /// <summary>
    /// Lecteur du format .ship.txt (meme format que le validateur Python de
    /// la CI). Fichiers embarques dans l'assembly : une seule source de
    /// verite, validee par Python ET par les tests C#.
    /// </summary>
    public static class SpecLoader
    {
        public static ShipSpec Parse(string text)
        {
            var spec = new ShipSpec();
            foreach (string raw in text.Split('\n'))
            {
                string line = raw;
                int hash = line.IndexOf('#');
                if (hash >= 0) line = line.Substring(0, hash);
                line = line.Trim();
                if (line.Length == 0) continue;
                string[] p = line.Split(new char[] { ' ', '\t' }, StringSplitOptions.RemoveEmptyEntries);
                switch (p[0])
                {
                    case "id": spec.Id = p[1]; break;
                    case "name": spec.Name = p[1]; break;
                    case "class": spec.Class = (ShipClass)Enum.Parse(typeof(ShipClass), p[1], false); break;
                    case "length_m": spec.LengthM = PF(p[1]); break;
                    case "beam_m": spec.BeamM = PF(p[1]); break;
                    case "draft_m": spec.DraftM = PF(p[1]); break;
                    case "displacement_t": spec.DisplacementT = PF(p[1]); break;
                    case "max_speed_kn": spec.MaxSpeedKn = PF(p[1]); break;
                    case "accel_m_s2": spec.AccelMs2 = PF(p[1]); break;
                    case "turn_deg_s": spec.TurnDegS = PF(p[1]); break;
                    case "rcs_m2": spec.RcsM2 = PF(p[1]); break;
                    case "acoustic": spec.Acoustic = PF(p[1]); break;
                    case "compartment":
                        {
                            var c = new CompartmentSpec();
                            c.Id = p[1]; c.Center = PF(p[2]); c.Half = PF(p[3]);
                            c.Hp = PF(p[4]); c.Armor = PF(p[5]);
                            string[] sys = p[6].Split(',');
                            c.Systems = new ShipSystemKind[sys.Length];
                            for (int i = 0; i < sys.Length; i++) c.Systems[i] = (ShipSystemKind)Enum.Parse(typeof(ShipSystemKind), sys[i], false);
                            spec.Compartments.Add(c);
                            break;
                        }
                    case "weapon":
                        {
                            var w = new WeaponSpec();
                            w.Id = p[1]; w.Kind = (WeaponKind)Enum.Parse(typeof(WeaponKind), p[2], false);
                            w.Damage = PF(p[3]); w.RangeM = PF(p[4]); w.SpeedMs = PF(p[5]);
                            w.ReloadS = PF(p[6]); w.Salvo = int.Parse(p[7], CultureInfo.InvariantCulture); w.Ammo = int.Parse(p[8], CultureInfo.InvariantCulture);
                            w.Guidance = (GuidanceKind)Enum.Parse(typeof(GuidanceKind), p[9], true);
                            spec.Weapons.Add(w);
                            break;
                        }
                    case "sensor":
                        {
                            var s = new SensorSpec();
                            s.Id = p[1]; s.Kind = (SensorKind)Enum.Parse(typeof(SensorKind), p[2], false);
                            s.RangeM = PF(p[3]); s.Ref = PF(p[4]);
                            spec.Sensors.Add(s);
                            break;
                        }
                }
            }
            return spec;
        }

        /// <summary>Charge tous les .ship.txt embarques dans l'assembly.</summary>
        public static List<ShipSpec> LoadEmbedded()
        {
            var result = new List<ShipSpec>();
            Assembly asm = typeof(SpecLoader).Assembly;
            foreach (string name in asm.GetManifestResourceNames())
            {
                if (!name.EndsWith(".ship.txt")) continue;
                using (var reader = new StreamReader(asm.GetManifestResourceStream(name)))
                {
                    result.Add(Parse(reader.ReadToEnd()));
                }
            }
            result.Sort((a, b) => string.CompareOrdinal(a.Id, b.Id));
            return result;
        }

        private static float PF(string s)
        {
            return float.Parse(s, CultureInfo.InvariantCulture);
        }
    }
}
