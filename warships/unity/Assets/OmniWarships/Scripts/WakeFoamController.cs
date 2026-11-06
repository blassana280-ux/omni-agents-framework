using UnityEngine;

namespace OmniWarships.Unity
{
    /// <summary>
    /// Écume de sillage renforcée par navire : moustaches d'écume de proue
    /// (2 nappes en V), turbulence de poupe, suivies par navire et
    /// modulées par la vitesse réelle du noyau. Hauteur = océan du noyau
    /// (le navire flotte déjà dessus ; les nappes restent au voisinage de
    /// la flottaison). Aucun asset : quads + shader OmniWarships/Foam.
    /// </summary>
    public sealed class WakeFoamController : MonoBehaviour
    {
        private ShipView _view;
        private BattleDirector _director;
        private readonly System.Collections.Generic.List<GameObject> _quads =
            new System.Collections.Generic.List<GameObject>();

        public void Bind(ShipView view, BattleDirector director)
        {
            _view = view;
            _director = director;
            Build();
        }

        private void Build()
        {
            float l = _view.Spec.LengthM;
            float b = _view.Spec.BeamM;

            // moustaches de proue : 2 nappes en V depuis l'étrave
            MakeQuad("FoamBowP", new Vector3(-b * 0.34f, 0.32f, l * 0.40f),
                Quaternion.Euler(0f, 35f, 0f), 1.9f);
            MakeQuad("FoamBowS", new Vector3(b * 0.34f, 0.32f, l * 0.40f),
                Quaternion.Euler(0f, -35f, 0f), 1.9f);

            // turbulence de poupe + tourbillon médian
            MakeQuad("FoamStern", new Vector3(0f, 0.3f, -l * 0.52f),
                Quaternion.identity, 2.6f);

            // nappe latérale (remous le long de la coque)
            MakeQuad("FoamSideP", new Vector3(-b * 0.48f, 0.26f, -l * 0.05f),
                Quaternion.identity, 2.2f);
            MakeQuad("FoamSideS", new Vector3(b * 0.48f, 0.26f, -l * 0.05f),
                Quaternion.identity, 2.2f);
        }

        private void MakeQuad(string name, Vector3 localPos, Quaternion localRot, float size)
        {
            var go = new GameObject(name);
            go.transform.parent = _view.transform;
            go.transform.localPosition = localPos;
            go.transform.localRotation = localRot;
            var mf = go.AddComponent<MeshFilter>();
            mf.sharedMesh = EffectsPool.QuadMesh();
            var mr = go.AddComponent<MeshRenderer>();
            Shader s = Shader.Find("OmniWarships/Foam");
            if (s == null) s = Shader.Find("OmniWarships/Flash");
            if (s == null) s = Shader.Find("Universal Render Pipeline/Unlit");
            var m = new Material(s);
            if (m.HasProperty("_TintColor")) m.SetColor("_TintColor", new Color(0.92f, 0.96f, 1f, 0.85f));
            if (m.HasProperty("_Intensity")) m.SetFloat("_Intensity", 0f);
            m.SetFloat("_Cull", 0f);
            mr.sharedMaterial = m;
            go.transform.localScale = new Vector3(size, 1f, size * 2.2f);
            _quads.Add(go);
        }

        private void Update()
        {
            if (_view == null || _view.State == null) return;
            float sp = Mathf.Abs(_view.State.SpeedMs);
            float intensity = Mathf.Clamp01(sp / 5.5f);
            bool visible = !_view.State.Sunk && intensity > 0.02f;

            for (int i = 0; i < _quads.Count; i++)
            {
                GameObject q = _quads[i];
                if (q == null) continue;
                var mr = q.GetComponent<MeshRenderer>();
                if (mr != null) mr.enabled = visible;
                if (!visible) continue;
                Material m = mr.sharedMaterial;
                if (m != null && m.HasProperty("_Intensity"))
                {
                    // pulsation douce (remous) — visuel uniquement
                    float puls = 0.85f + 0.15f * Mathf.Sin(Time.time * 3f + i * 1.7f);
                    m.SetFloat("_Intensity", intensity * puls);
                }
            }
        }
    }
}
