using System.Collections.Generic;
using OmniWarships.Core.Spec;
using UnityEngine;

namespace OmniWarships.Unity
{
    /// <summary>
    /// Charge les specs de navires depuis Resources/Ships (*.ship.txt),
    /// copies exactes de warships/data/ships (verifiees par la CI).
    /// Aucun reseau : tout est embarque.
    /// </summary>
    public static class SpecSource
    {
        public const string Folder = "Ships";

        public static List<ShipSpec> LoadAll()
        {
            var specs = new List<ShipSpec>();
            Object[] assets = Resources.LoadAll(Folder, typeof(TextAsset));
            foreach (Object o in assets)
            {
                var ta = o as TextAsset;
                if (ta == null) continue;
                ShipSpec s = SpecLoader.Parse(ta.text);
                specs.Add(s);
            }
            specs.Sort((a, b) => string.CompareOrdinal(a.Id, b.Id));
            if (specs.Count == 0)
            {
                Debug.LogError("OMNI WARSHIPS : aucune spec dans Resources/" + Folder + " — copier warships/data/ships/*.ship.txt");
            }
            return specs;
        }
    }
}
