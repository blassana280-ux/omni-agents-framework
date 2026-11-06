using System;
using System.Collections.Generic;
using System.IO;
using System.Reflection;

namespace OmniWarships.Core.Spec
{
    /// <summary>
    /// Lecteur du format .ship.txt (meme format que le validateur Python de la CI).
    /// Les fichiers sont embarques dans l'assembly : une seule source de verite,
    /// validee a la fois par Python et par les tests C#.
    /// </summary>
    public static class SpecLoader
    {
        public static ShipSpec Parse(string text)
        {
            var spec = new ShipSpec();
            foreach (string raw in text.Split('
'))
            {
                string line = raw;
                int hash = line.IndexOf('#');
                if (hash >= 0) line = line.Substring(0, hash);
                line = line.Trim();
                if (line.Length == 0) continue;
                string[] p = line.Split(new char[] { ' ', '	' }, StringSplitOptions.RemoveEmptyEntries);
                switch (p[0])
                {
                    case "id": spec.Id = p[1]; break;
                    case "name": spec.Name = p[1]; break;
                    case "class": spec.Class = (ShipClass)Enum.Parse(typeof(ShipClass), p[1], false); break;
                    case "length_m": spec.LengthM = float.Parse(p[1]); break;
                    case "beam_m": spec.BeamM = float.Parse(p[1]); break;
                    case "draft_m": spec.DraftM = float.Parse(p[1]); break;
                    case "displacement_t": spec.DisplacementT = float.Parse(p[1]); break;
                    case "max_speed_kn": spec.MaxSpeedKn = float.Parse(p[1]); break;
                    case "accel_m_s2": spec.AccelMs2 = float.Parse(p[1]); break;
                    case "turn_deg_s": spec.TurnDegS = float.Parse(p[1]); break;
                    case "rcs_m2": spec.RcsM2 = float.Parse(p[1]); break;
                    case "acoustic": spec.Acoustic = float.Parse(p[1]); break;
                    case "compartment":
                        {
                            var c = new CompartmentSpec();
                            c.Id = p[1]; c.Center = float.Parse(p[2]); c.Half = float.Parse(p[3]);
                            c.Hp = float.Parse(p[4]); c.Armor = float.Parse(p[5]);
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
                            w.Damage = float.Parse(p[3]); w.RangeM = float.Parse(p[4]); w.SpeedMs = float.Parse(p[5]);
                            w.ReloadS = float.Parse(p[6]); w.Salvo = int.Parse(p[7]); w.Ammo = int.Parse(p[8]);
                            w.Guidance = (GuidanceKind)Enum.Parse(typeof(GuidanceKind), p[9], true);
                            spec.Weapons.Add(w);
                            break;
                        }
                    case "sensor":
                        {
                            var s = new SensorSpec();
                            s.Id = p[1]; s.Kind = (SensorKind)Enum.Parse(typeof(SensorKind), p[2], false);
                            s.RangeM = float.Parse(p[3]); s.Ref = float.Parse(p[4]);
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
    }
}
