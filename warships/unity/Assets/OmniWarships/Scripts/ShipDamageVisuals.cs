using System.Collections.Generic;
using OmniWarships.Core.Simulation;
using UnityEngine;

namespace OmniWarships.Unity
{
    /// <summary>
    /// Dégâts progressifs visuels par navire : chaque compartiment en voix
    /// d'eau (breached) fume en continu, les compartiments détruits fument
    /// épais + escarbilles ; la voie d'eau crée une écume bouillonnante à
    /// la flottaison. Poll du noyau (State.Compartments) — les feux sur
    /// compartiment détruit restent gérés par ShipView.MarkDamage.
    /// </summary>
    public sealed class ShipDamageVisuals : MonoBehaviour
    {
        private sealed class Comp
        {
            public Vector3 Anchor;
            public bool WasBreached;
            public bool WasDestroyed;
            public float NextSmokeS;
            public float NextFoamS;
        }

        private ShipView _view;
        private BattleDirector _director;
        private readonly Dictionary<string, Comp> _comps = new Dictionary<string, Comp>();
        private readonly List<GameObject> _foams = new List<GameObject>();

        public void Bind(ShipView view, BattleDirector director)
        {
            _view = view;
            _director = director;

            // mêmes ancres que ShipView : Center 0 = proue
            float l = view.Spec.LengthM;
            float fb = Mathf.Max(3f, l * 0.028f);
            foreach (CompartmentSpec c in view.Spec.Compartments)
            {
                float lz = l * (0.5f - c.Center);
                _comps[c.Id] = new Comp { Anchor = new Vector3(0f, fb * 0.7f, lz) };
            }
        }

        private void Update()
        {
            if (_view == null || _view.State == null || _view.State.Sunk) return;
            ShipState st = _view.State;

            foreach (KeyValuePair<string, Comp> kv in _comps)
            {
                CompartmentState cs = null;
                foreach (CompartmentState c in st.Compartments)
                {
                    if (c.Id == kv.Key) { cs = c; break; }
                }
                if (cs == null) continue;
                Comp v = kv.Value;

                if (cs.Breached && !v.WasBreached)
                {
                    v.WasBreached = true;
                    _director.Effects.Splash(transform.TransformPoint(v.Anchor + new Vector3(0f, -1.5f, 0f)));
                }
                if (cs.Destroyed && !v.WasDestroyed)
                {
                    v.WasDestroyed = true;
                    _director.Effects.Explosion(transform.TransformPoint(v.Anchor), 9f);
                }

                if (!QualityProfiles.EffectsEnabled) continue;

                if (cs.Breached && Time.time >= v.NextSmokeS)
                {
                    Vector3 world = transform.TransformPoint(v.Anchor);
                    if (cs.Destroyed)
                    {
                        // épaisse fumée noire + escarbilles
                        _director.Effects.Smoke(world + Vector3.up * 4f, 7f);
                        _director.Effects.Smoke(world + Vector3.up * 9f, 5f);
                    }
                    else
                    {
                        _director.Effects.Smoke(world + Vector3.up * 3f, 3.5f);
                    }
                    v.NextSmokeS = Time.time + (cs.Destroyed ? 0.5f : 1.1f);
                }

                if (cs.Flooding > 0.35f && Time.time >= v.NextFoamS)
                {
                    SpawnFoam(transform.TransformPoint(
                        v.Anchor + new Vector3(0f, -v.Anchor.y + 0.25f, 0f)));
                    v.NextFoamS = Time.time + 0.8f;
                }
            }
        }

        /// <summary>Écume bouillonnante à la flottaison (voie d'eau).</summary>
        private void SpawnFoam(Vector3 worldPos)
        {
            if (_foams.Count > 6) return; // budget Android (KN3)
            var go = new GameObject("FloodFoam");
            go.transform.parent = null; // monde : reste à la flottaison
            go.transform.position = worldPos;
            var mf = go.AddComponent<MeshFilter>();
            mf.sharedMesh = EffectsPool.QuadMesh();
            var mr = go.AddComponent<MeshRenderer>();
            Shader s = Shader.Find("OmniWarships/Foam");
            if (s == null) s = Shader.Find("OmniWarships/Flash");
            var m = new Material(s);
            if (m.HasProperty("_TintColor")) m.SetColor("_TintColor", new Color(0.9f, 0.95f, 1f, 0.8f));
            if (m.HasProperty("_Intensity")) m.SetFloat("_Intensity", 1.6f);
            m.SetFloat("_Cull", 0f);
            mr.sharedMaterial = m;
            go.transform.localScale = new Vector3(5f, 1f, 9f);
            _foams.Add(go);
            StartCoroutine(FadeFoam(go, m, 1.6f));
        }

        private System.Collections.IEnumerator FadeFoam(GameObject go, Material m, float dur)
        {
            float t = 0f;
            while (t < dur && go != null)
            {
                t += Time.deltaTime;
                if (m != null && m.HasProperty("_Intensity"))
                {
                    m.SetFloat("_Intensity", 1.6f * (1f - t / dur));
                }
                yield return null;
            }
            _foams.RemoveAll(f => f == go);
            if (go != null) Destroy(go);
        }
    }
}
