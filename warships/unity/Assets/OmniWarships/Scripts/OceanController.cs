using System;
using OmniWarships.Core.Common;
using OmniWarships.Core.Simulation;
using UnityEngine;

namespace OmniWarships.Unity
{
    /// <summary>
    /// Ocean 3D anime : maillage plane suivi du joueur, deplacement de houle
    /// calcule DANS LE SHADER avec la meme formule que OceanModel (4
    /// composantes Gerstner, memes parametres derives de la meme graine —
    /// le shader duplique la formule pour le GPU ; la flottabilite des
    /// navires reste au CPU, source unique). Ecume de crete, speculaire
    /// soleil, fondu horizon, brouillard atmospherique.
    /// </summary>
    public sealed class OceanController : MonoBehaviour
    {
        private BattleSim _sim;
        private Mesh _mesh;
        private Material _mat;
        private GameObject _sun;
        private float _size = 4096f;
        private int _segments;

        private void Awake()
        {
            QualityProfiles.OnChanged += OnQualityChanged;
        }

        private void OnDestroy()
        {
            QualityProfiles.OnChanged -= OnQualityChanged;
        }

        private void OnQualityChanged(QualityProfile p)
        {
            BuildMesh();
            ApplyMaterial();
        }

        public void Bind(BattleSim sim)
        {
            _sim = sim;
            BuildMesh();
            ApplyMaterial();
            SetupSky();
        }

        /// <summary>Reproduit le constructeur d'OceanModel : memes parametres, meme graine.</summary>
        private void DeriveWaveParams(out Vector4 amp, out Vector4 waveLen, out Vector4 dirDeg, out Vector4 phase)
        {
            int seaState = _sim.SeaState;
            var rng = new Rng(_sim.Seed);
            amp = Vector4.zero; waveLen = Vector4.zero; dirDeg = Vector4.zero; phase = Vector4.zero;
            float[] a = new float[4], wl = new float[4], d = new float[4], ph = new float[4];
            for (int i = 0; i < 4; i++)
            {
                a[i] = 0.22f * seaState * (1f - 0.18f * i);
                wl[i] = 45f + 30f * i + rng.NextFloat() * 25f;
                d[i] = rng.NextRange(-25f, 25f);
                ph[i] = rng.NextRange(0f, (float)(2.0 * Math.PI));
            }
            amp = new Vector4(a[0], a[1], a[2], a[3]);
            waveLen = new Vector4(wl[0], wl[1], wl[2], wl[3]);
            dirDeg = new Vector4(d[0], d[1], d[2], d[3]);
            phase = new Vector4(ph[0], ph[1], ph[2], ph[3]);
        }

        private void BuildMesh()
        {
            _segments = QualityProfiles.CurrentOceanSegments;
            int n = _segments + 1;
            var verts = new Vector3[n * n];
            var uv = new Vector2[n * n];
            var tris = new int[_segments * _segments * 6];
            float step = _size / _segments;
            int vi = 0;
            for (int z = 0; z < n; z++)
            {
                for (int x = 0; x < n; x++)
                {
                    verts[vi] = new Vector3(-_size * 0.5f + x * step, 0f, -_size * 0.5f + z * step);
                    uv[vi] = new Vector2(x / (float)_segments, z / (float)_segments);
                    vi++;
                }
            }
            int ti = 0;
            for (int z = 0; z < _segments; z++)
            {
                for (int x = 0; x < _segments; x++)
                {
                    int i0 = z * n + x, i1 = i0 + 1, i2 = i0 + n, i3 = i2 + 1;
                    tris[ti++] = i0; tris[ti++] = i2; tris[ti++] = i1;
                    tris[ti++] = i1; tris[ti++] = i2; tris[ti++] = i3;
                }
            }
            if (_mesh == null) _mesh = new Mesh();
            _mesh.Clear();
            _mesh.vertices = verts;
            _mesh.uv = uv;
            _mesh.triangles = tris;
            _mesh.RecalculateNormals();
            _mesh.RecalculateBounds();
            // evite le culling quand les vagues deplacent les sommets
            _mesh.bounds = new Bounds(Vector3.zero, new Vector3(_size, 64f, _size));

            var mf = GetComponent<MeshFilter>();
            if (mf == null) mf = gameObject.AddComponent<MeshFilter>();
            mf.sharedMesh = _mesh;
            var mr = GetComponent<MeshRenderer>();
            if (mr == null) mr = gameObject.AddComponent<MeshRenderer>();
        }

        private void ApplyMaterial()
        {
            Vector4 amp, waveLen, dirDeg, phase;
            DeriveWaveParams(out amp, out waveLen, out dirDeg, out phase);

            Shader s = Shader.Find("OmniWarships/Ocean");
            if (s == null)
            {
                Debug.LogWarning("OMNI WARSHIPS : shader OmniWarships/Ocean introuvable — ocean de secours (URP Lit)");
                s = Shader.Find("Universal Render Pipeline/Lit");
            }
            if (_mat == null || _mat.shader != s)
            {
                _mat = new Material(s);
            }
            if (_mat.HasProperty("_Amp"))
            {
                _mat.SetVector("_Amp", amp);
                _mat.SetVector("_WaveLen", waveLen);
                _mat.SetVector("_DirDeg", dirDeg);
                _mat.SetVector("_Phase", phase);
                _mat.SetVector("_SunDir", new Vector4(0.42f, 0.68f, 0.61f, 0f));
                _mat.SetFloat("_TimeScale", 1f);
                _mat.SetFloat("_FoamThreshold", Mathf.Max(0.35f, amp.x * 0.75f));
                _mat.SetColor("_DeepColor", new Color(0.008f, 0.06f, 0.12f));
                _mat.SetColor("_CrestColor", new Color(0.10f, 0.38f, 0.45f));
                _mat.SetColor("_FoamColor", new Color(0.85f, 0.92f, 0.95f));
                _mat.SetColor("_HorizonColor", new Color(0.55f, 0.65f, 0.75f));
            }
            else
            {
                _mat.color = new Color(0.06f, 0.22f, 0.30f);
            }
            var mr = GetComponent<MeshRenderer>();
            if (mr != null) mr.sharedMaterial = _mat;
        }

        private void SetupSky()
        {
            // brouillard atmospherique pilote par la sim (fog 0..1)
            RenderSettings.fog = true;
            RenderSettings.fogMode = FogMode.Exponential;
            RenderSettings.fogDensity = 0.000012f + _sim.Fog * 0.00006f;
            RenderSettings.fogColor = new Color(0.55f, 0.65f, 0.75f);
            RenderSettings.ambientLight = new Color(0.38f, 0.42f, 0.48f);

            Light sun = null;
            foreach (Light l in FindObjectsOfType(typeof(Light)))
            {
                if (l.type == LightType.Directional) { sun = l; break; }
            }
            if (sun == null)
            {
                _sun = new GameObject("OMNI Sun");
                sun = _sun.AddComponent<Light>();
                sun.type = LightType.Directional;
                sun.shadows = LightShadows.Soft;
                sun.color = new Color(1.0f, 0.96f, 0.88f);
                sun.intensity = 1.15f;
            }
            sun.transform.rotation = Quaternion.Euler(50f, -35f, 0f);
            RenderSettings.sun = sun;
        }

        private void Update()
        {
            if (_sim == null) return;
            // suit le navire du joueur (snap au pas du maillage : vagues en espace monde)
            OmniWarships.Core.Simulation.ShipState player = null;
            foreach (OmniWarships.Core.Simulation.ShipState s in _sim.Ships)
            {
                if (!s.IsAi) { player = s; break; }
            }
            if (player == null) return;
            float step = _size / _segments;
            float sx = Mathf.Floor(player.Pos.X / step) * step;
            float sz = Mathf.Floor(player.Pos.Y / step) * step;
            transform.position = new Vector3(sx, 0f, sz);
        }
    }
}
