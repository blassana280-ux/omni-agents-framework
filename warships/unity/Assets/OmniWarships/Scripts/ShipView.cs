using System.Collections.Generic;
using OmniWarships.Core.Spec;
using OmniWarships.Core.Simulation;
using UnityEngine;

namespace OmniWarships.Unity
{
    /// <summary>
    /// Vue 3D d'un navire : coque parametrique originale generee depuis la
    /// spec (longueur, largeur, tirant d'eau, tourelles, funnels...),
    /// flottabilite et gite/tangage pilotees par le noyau (OceanModel),
    /// marqueurs de degats par compartiment, voie d'eau -> gite, naufrage
    /// anime. Aucun asset importe : tout est genere par le code.
    /// </summary>
    public sealed class ShipView : MonoBehaviour
    {
        public ShipState State { get; private set; }
        public ShipSpec Spec { get; private set; }

        private Mesh _mesh;
        private Material[] _mats;
        private readonly List<GameObject> _fires = new List<GameObject>();
        private readonly Dictionary<string, Vector3> _compartmentAnchors = new Dictionary<string, Vector3>();
        private float _sinkingT;
        private bool _sinking;
        private float _extraRoll;
        private GameObject _wake;
        private Material _wakeMat;
        private BattleDirector _director;

        // interpolation rendu (30 Hz sim -> rendu fluide)
        private Vector3 _prevPos, _currPos;
        private float _prevYaw, _currYaw, _prevPitch, _currPitch, _prevRoll, _currRoll;
        private bool _firstTick = true;

        private const int MatHull = 0, MatDeck = 1, MatSuper = 2, MatDark = 3, MatAccent = 4;

        public void Bind(ShipState state, BattleDirector director)
        {
            State = state;
            Spec = state.Spec;
            _director = director;
            BuildMesh();
            BuildWake();
            director.OnSimTicked += OnSimTicked;
            OnSimTicked(); // pose initiale
        }

        /// <summary>Position monde de la proue (flash de bouche).</summary>
        public Vector3 BowWorldPos()
        {
            return transform.TransformPoint(new Vector3(0f, 3f, Spec.LengthM * 0.5f));
        }

        private void OnSimTicked()
        {
            if (State == null) return;
            _prevPos = _currPos;
            _prevYaw = _currYaw; _prevPitch = _currPitch; _prevRoll = _currRoll;

            float waveY = 0f;
            if (!State.Sunk && _director != null && _director.Sim != null)
            {
                // MEME noyau, MEME temps : flottabilite = OceanModel.HeightAt (CPU)
                waveY = _director.Sim.Ocean.HeightAt(State.Pos.X, State.Pos.Y, _director.Sim.TimeS);
            }

            _currPos = new Vector3(State.Pos.X, waveY, State.Pos.Y);
            _currYaw = State.HeadingDeg;
            _currPitch = State.PitchDeg;
            float floodRoll = 0f;
            foreach (CompartmentState c in State.Compartments)
            {
                if (c.Breached) floodRoll += c.Flooding;
            }
            _currRoll = State.RollDeg - Mathf.Min(18f, floodRoll * 9f);
            if (_firstTick) { _prevPos = _currPos; _prevYaw = _currYaw; _prevPitch = _currPitch; _prevRoll = _currRoll; _firstTick = false; }
        }

        private void Update()
        {
            if (State == null) return;
            float alpha = Mathf.Clamp01((Time.time - Time.fixedTime) / Time.fixedDeltaTime);

            Vector3 pos = Vector3.Lerp(_prevPos, _currPos, alpha);
            float yaw = Mathf.LerpAngle(_prevYaw, _currYaw, alpha);
            float pitch = Mathf.Lerp(_prevPitch, _currPitch, alpha);
            float roll = Mathf.LerpAngle(_prevRoll, _currRoll, alpha);

            if (_sinking)
            {
                _sinkingT += Time.deltaTime;
                pos.y -= _sinkingT * 0.55f;
                _extraRoll += Time.deltaTime * 1.5f;
                if (_sinkingT > 55f)
                {
                    Destroy(gameObject);
                    return;
                }
            }

            transform.position = pos;
            transform.rotation = Quaternion.Euler(pitch, yaw, roll + _extraRoll);

            UpdateFires();
            UpdateWake();
        }

        private void UpdateFires()
        {
            float t = Time.time;
            for (int i = 0; i < _fires.Count; i++)
            {
                GameObject f = _fires[i];
                if (f == null) continue;
                float flicker = 0.75f + 0.25f * Mathf.Sin(t * 11f + i * 2.1f);
                f.transform.localScale = Vector3.one * (3.2f * flicker);
            }
        }

        private void UpdateWake()
        {
            if (_wake == null) return;
            float sp = Mathf.Abs(State.SpeedMs);
            float wakeLen = Mathf.Clamp(6f + sp * 6f, 6f, 90f);
            _wake.transform.localPosition = new Vector3(0f, 0.25f, -Spec.LengthM * 0.5f - wakeLen * 0.5f);
            _wake.transform.localScale = new Vector3(Mathf.Clamp(Spec.BeamM * 0.9f + sp * 0.3f, 4f, 26f), 1f, wakeLen);
            if (_wakeMat != null)
            {
                float inten = Mathf.Clamp01(sp / 6f) * 0.7f;
                _wakeMat.SetFloat("_Intensity", inten);
            }
        }

        public void MarkDamage(string compartmentId, bool destroyed)
        {
            Vector3 anchor;
            if (!_compartmentAnchors.TryGetValue(compartmentId, out anchor)) return;
            if (!destroyed) return; // v1 : feux visuels sur compartiments detruits
            if (HasFireAt(anchor)) return;
            SpawnFire(anchor);
        }

        private bool HasFireAt(Vector3 anchor)
        {
            foreach (GameObject f in _fires)
            {
                if (f != null && (f.transform.localPosition - anchor).sqrMagnitude < 1f) return true;
            }
            return false;
        }

        private void SpawnFire(Vector3 anchor)
        {
            var go = GameObject.CreatePrimitive(PrimitiveType.Sphere);
            Object.Destroy(go.GetComponent<Collider>());
            go.name = "Fire";
            go.transform.parent = transform;
            go.transform.localPosition = anchor + new Vector3(0f, 4f, 0f);
            go.transform.localScale = Vector3.one * 3.2f;
            go.GetComponent<MeshRenderer>().sharedMaterial = MakeFlashMaterial(new Color(1f, 0.55f, 0.18f, 1f), 2.2f);
            _fires.Add(go);

            var smoke = GameObject.CreatePrimitive(PrimitiveType.Sphere);
            Object.Destroy(smoke.GetComponent<Collider>());
            smoke.name = "Smoke";
            smoke.transform.parent = transform;
            smoke.transform.localPosition = anchor + new Vector3(0f, 9f, 0f);
            smoke.transform.localScale = Vector3.one * 5f;
            smoke.GetComponent<MeshRenderer>().sharedMaterial = MakeSmokeMaterial(new Color(0.25f, 0.25f, 0.27f, 0.5f));
            _fires.Add(smoke);
        }

        public void BeginSink()
        {
            _sinking = true;
            _sinkingT = 0f;
        }

        // ------------------------------------------------------------------
        // Construction parametrique (100% originale, basee sur la spec)
        // ------------------------------------------------------------------

        private void BuildMesh()
        {
            float L = Spec.LengthM;
            float B = Spec.BeamM;
            float draft = Spec.DraftM;
            float fb = Mathf.Max(3f, L * 0.028f); // franc-bord

            bool enemy = State.Team != "blue";
            Color hullCol = enemy ? new Color(0.56f, 0.53f, 0.50f) : new Color(0.62f, 0.65f, 0.68f);
            Color deckCol = new Color(0.30f, 0.31f, 0.33f);
            Color superCol = enemy ? new Color(0.62f, 0.58f, 0.55f) : new Color(0.70f, 0.73f, 0.76f);
            Color darkCol = new Color(0.10f, 0.10f, 0.11f);
            Color accentCol = enemy ? new Color(0.75f, 0.20f, 0.16f) : new Color(0.16f, 0.34f, 0.62f);

            var mb = new MeshBuilder(5);

            // coque : proue effilee surmontee, pouppe droite
            mb.TaperBox(MatHull,
                new Vector2(-B * 0.92f, -L * 0.40f), new Vector2(B * 0.92f, L * 0.55f),
                -draft * 0.55f, fb * 0.6f);
            mb.TaperBox(MatHull,
                new Vector2(-B * 0.55f, L * 0.55f), new Vector2(B * 0.55f, L * 0.66f),
                -draft * 0.55f, fb * 0.75f, bowTaper: true);
            // bande de flottabilite (accent) au niveau de la ligne de flottaison
            mb.TaperBox(MatAccent,
                new Vector2(-B * 0.93f, -L * 0.40f), new Vector2(B * 0.93f, L * 0.55f),
                fb * 0.15f, fb * 0.32f);
            mb.TaperBox(MatAccent,
                new Vector2(-B * 0.56f, L * 0.55f), new Vector2(B * 0.56f, L * 0.66f),
                fb * 0.15f, fb * 0.32f, bowTaper: true);
            // pont
            mb.TaperBox(MatDeck,
                new Vector2(-B * 0.88f, -L * 0.40f), new Vector2(B * 0.88f, L * 0.55f),
                fb * 0.6f, fb * 0.66f);
            mb.TaperBox(MatDeck,
                new Vector2(-B * 0.52f, L * 0.55f), new Vector2(B * 0.52f, L * 0.66f),
                fb * 0.75f, fb * 0.81f, bowTaper: true);
            // helipont
            mb.Box(MatDark, new Vector3(-B * 0.45f, fb * 0.66f, -L * 0.30f),
                new Vector3(B * 0.45f, fb * 0.67f, -L * 0.06f));

            // superstructure : bloc principal + passerelle + mat
            mb.Box(MatSuper, new Vector3(-B * 0.30f, fb * 0.66f, L * 0.02f),
                new Vector3(B * 0.30f, fb * 1.5f, L * 0.22f));
            mb.Box(MatSuper, new Vector3(-B * 0.22f, fb * 1.5f, L * 0.06f),
                new Vector3(B * 0.22f, fb * 1.9f, L * 0.18f));
            mb.Box(MatDark, new Vector3(-B * 0.19f, fb * 1.55f, L * 0.065f),
                new Vector3(B * 0.19f, fb * 1.72f, L * 0.172f)); // vitrees passerelle
            mb.Cylinder(MatDark, new Vector3(0f, fb * 1.9f, L * 0.10f), 0.35f, fb * 1.1f, 8);
            mb.Box(MatDark, new Vector3(-B * 0.16f, fb * 2.75f, L * 0.10f),
                new Vector3(B * 0.16f, fb * 2.85f, L * 0.10f + 1.2f));
            mb.Cylinder(MatSuper, new Vector3(0f, fb * 1.5f, -L * 0.08f), Mathf.Max(0.9f, B * 0.10f), fb * 1.2f, 10);

            // tourelles : canons puis CIWS, positions depuis la spec
            int gunIndex = 0;
            int ciwsIndex = 0;
            foreach (WeaponSpec w in Spec.Weapons)
            {
                if (w.Kind == WeaponKind.Gun)
                {
                    float z = gunIndex == 0 ? L * 0.30f : -L * 0.34f;
                    float dir = gunIndex == 0 ? 1f : -1f;
                    mb.Cylinder(MatSuper, new Vector3(0f, fb * 0.66f, z), Mathf.Max(1.2f, B * 0.16f), fb * 0.5f, 10);
                    mb.Box(MatDark, new Vector3(-0.4f, fb * 0.85f, z),
                        new Vector3(0.4f, fb * 0.95f, z + dir * (Mathf.Max(4f, L * 0.055f))));
                    gunIndex++;
                }
                else if (w.Kind == WeaponKind.Ciws)
                {
                    float z = -L * 0.18f - ciwsIndex * 3f;
                    mb.Cylinder(MatDark, new Vector3(B * 0.34f, fb * 1.5f, z), 0.8f, 1.6f, 8);
                    ciwsIndex++;
                }
                else if (w.Kind == WeaponKind.Ssm || w.Kind == WeaponKind.Sam)
                {
                    mb.Box(MatDark, new Vector3(-B * 0.30f, fb * 0.66f, -L * 0.02f),
                        new Vector3(-B * 0.12f, fb * 0.9f, L * 0.12f));
                }
                else if (w.Kind == WeaponKind.Torpedo)
                {
                    mb.Box(MatDark, new Vector3(B * 0.12f, fb * 0.66f, -L * 0.10f),
                        new Vector3(B * 0.30f, fb * 0.8f, L * 0.02f));
                }
            }

            _mesh = mb.ToMesh();
            _mesh.RecalculateBounds();
            _mats = new Material[5];
            _mats[MatHull] = MakeLitMaterial(hullCol);
            _mats[MatDeck] = MakeLitMaterial(deckCol);
            _mats[MatSuper] = MakeLitMaterial(superCol);
            _mats[MatDark] = MakeLitMaterial(darkCol);
            _mats[MatAccent] = MakeLitMaterial(accentCol);

            var mr = gameObject.AddComponent<MeshRenderer>();
            mr.sharedMaterials = _mats;
            mr.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.On;
            mr.receiveShadows = true;
            var mf = gameObject.AddComponent<MeshFilter>();
            mf.sharedMesh = _mesh;

            // ancres de compartiments (marqueurs de degats) : Center 0 = proue
            foreach (CompartmentSpec c in Spec.Compartments)
            {
                float lz = L * (0.5f - c.Center);
                _compartmentAnchors[c.Id] = new Vector3(0f, fb * 0.7f, lz);
            }
        }

        private void BuildWake()
        {
            _wake = new GameObject("Wake");
            _wake.transform.parent = transform;
            _wake.transform.localPosition = new Vector3(0f, 0.25f, -Spec.LengthM * 0.5f);
            var mf = _wake.AddComponent<MeshFilter>();
            mf.sharedMesh = EffectsPool.QuadMesh();
            _wakeMat = MakeFlashMaterial(new Color(0.75f, 0.85f, 0.92f, 0.8f), 0.5f);
            var mr = _wake.AddComponent<MeshRenderer>();
            mr.sharedMaterial = _wakeMat;
        }

        internal static Material MakeLitMaterial(Color c)
        {
            Shader s = Shader.Find("Universal Render Pipeline/Lit");
            if (s == null) s = Shader.Find("Standard");
            var m = new Material(s);
            m.color = c;
            m.SetFloat("_Smoothness", 0.35f);
            m.SetFloat("_Cull", 0f); // double-face : robuste pour les coques parametriques
            return m;
        }

        internal static Material MakeFlashMaterial(Color c, float intensity)
        {
            Shader s = Shader.Find("OmniWarships/Flash");
            if (s == null) s = Shader.Find("Universal Render Pipeline/Unlit");
            var m = new Material(s);
            if (m.HasProperty("_TintColor")) m.SetColor("_TintColor", c);
            if (m.HasProperty("_Intensity")) m.SetFloat("_Intensity", intensity);
            m.SetFloat("_Cull", 0f);
            return m;
        }

        internal static Material MakeSmokeMaterial(Color c)
        {
            Shader s = Shader.Find("OmniWarships/Smoke");
            if (s == null) s = Shader.Find("Universal Render Pipeline/Unlit");
            var m = new Material(s);
            if (m.HasProperty("_TintColor")) m.SetColor("_TintColor", c);
            m.SetFloat("_Cull", 0f);
            return m;
        }
    }

    /// <summary>
    /// Constructeur de maillage minimal : boites, boites effilees (proue),
    /// cylindres — normales explicites, aucun asset externe.
    /// </summary>
    internal sealed class MeshBuilder
    {
        private readonly List<Vector3> _verts = new List<Vector3>();
        private readonly List<Vector3> _norms = new List<Vector3>();
        private readonly List<List<int>> _tris;

        public MeshBuilder(int materialCount)
        {
            _tris = new List<List<int>>(materialCount);
            for (int i = 0; i < materialCount; i++) _tris.Add(new List<int>());
        }

        public Mesh ToMesh()
        {
            var mesh = new Mesh();
            mesh.SetVertices(_verts);
            mesh.SetNormals(_norms);
            mesh.subMeshCount = _tris.Count;
            for (int i = 0; i < _tris.Count; i++) mesh.SetTriangles(_tris[i], i, false);
            return mesh;
        }

        public void Quad(int mat, Vector3 a, Vector3 b, Vector3 c, Vector3 d, Vector3 n)
        {
            int i = _verts.Count;
            _verts.Add(a); _verts.Add(b); _verts.Add(c); _verts.Add(d);
            _norms.Add(n); _norms.Add(n); _norms.Add(n); _norms.Add(n);
            var t = _tris[mat];
            t.Add(i); t.Add(i + 1); t.Add(i + 2);
            t.Add(i); t.Add(i + 2); t.Add(i + 3);
        }

        public void Box(int mat, Vector3 min, Vector3 max)
        {
            Vector3 n;
            n = Vector3.down;  Quad(mat, new Vector3(min.x, min.y, min.z), new Vector3(max.x, min.y, min.z), new Vector3(max.x, min.y, max.z), new Vector3(min.x, min.y, min.z), n);
            n = Vector3.up;    Quad(mat, new Vector3(min.x, max.y, min.z), new Vector3(min.x, max.y, max.z), new Vector3(max.x, max.y, max.z), new Vector3(max.x, max.y, min.z), n);
            n = Vector3.left;  Quad(mat, new Vector3(min.x, min.y, min.z), new Vector3(min.x, min.y, max.z), new Vector3(min.x, max.y, max.z), new Vector3(min.x, max.y, min.z), n);
            n = Vector3.right; Quad(mat, new Vector3(max.x, min.y, min.z), new Vector3(max.x, max.y, min.z), new Vector3(max.x, max.y, max.z), new Vector3(max.x, min.y, max.z), n);
            n = Vector3.back;  Quad(mat, new Vector3(min.x, min.y, min.z), new Vector3(min.x, max.y, min.z), new Vector3(max.x, max.y, min.z), new Vector3(max.x, min.y, min.z), n);
            n = Vector3.forward; Quad(mat, new Vector3(min.x, min.y, max.z), new Vector3(max.x, min.y, max.z), new Vector3(max.x, max.y, max.z), new Vector3(min.x, max.y, max.z), n);
        }

        /// <summary>Boite dont la face avant (+z) est effilee pour la proue.</summary>
        public void TaperBox(int mat, Vector2 min, Vector2 max, float yMin, float yMax, bool bowTaper = false)
        {
            float x0 = min.x, x1 = max.x, z0 = min.y, z1 = max.y;
            float bowScale = bowTaper ? 0.12f : 1f;
            float bowLift = bowTaper ? (yMax - yMin) * 0.45f : 0f;
            Vector3 a0 = new Vector3(x0, yMin, z0), a1 = new Vector3(x1, yMin, z0);
            Vector3 a2 = new Vector3(x1, yMax, z0), a3 = new Vector3(x0, yMax, z0);
            Vector3 b0 = new Vector3(x0 * bowScale, yMin + bowLift, z1), b1 = new Vector3(x1 * bowScale, yMin + bowLift, z1);
            Vector3 b2 = new Vector3(x1 * bowScale, yMax + bowLift, z1), b3 = new Vector3(x0 * bowScale, yMax + bowLift, z1);

            Quad(mat, a0, a1, a2, a3, Vector3.back);
            Quad(mat, b0, b1, b2, b3, Vector3.forward);
            Quad(mat, a0, a3, b3, b0, Vector3.left);
            Quad(mat, a1, b1, b2, a2, Vector3.right);
            Quad(mat, a3, a2, b2, b3, Vector3.up);
            Quad(mat, a0, b0, b1, a1, Vector3.down);
        }

        public void Cylinder(int mat, Vector3 baseCenter, float radius, float height, int segments)
        {
            for (int i = 0; i < segments; i++)
            {
                float a0 = 2f * Mathf.PI * i / segments;
                float a1 = 2f * Mathf.PI * (i + 1) / segments;
                Vector3 p0 = baseCenter + new Vector3(Mathf.Cos(a0) * radius, 0f, Mathf.Sin(a0) * radius);
                Vector3 p1 = baseCenter + new Vector3(Mathf.Cos(a1) * radius, 0f, Mathf.Sin(a1) * radius);
                Vector3 n = new Vector3(Mathf.Cos((a0 + a1) * 0.5f), 0f, Mathf.Sin((a0 + a1) * 0.5f));
                Quad(mat, p0, p1, p1 + Vector3.up * height, p0 + Vector3.up * height, n);
            }
            Vector3 top = baseCenter + Vector3.up * height;
            int baseIdx = _verts.Count; _verts.Add(baseCenter); _norms.Add(Vector3.down);
            int topIdx = _verts.Count; _verts.Add(top); _norms.Add(Vector3.up);
            var t = _tris[mat];
            for (int i = 0; i < segments; i++)
            {
                float a0 = 2f * Mathf.PI * i / segments;
                float a1 = 2f * Mathf.PI * (i + 1) / segments;
                Vector3 p0 = baseCenter + new Vector3(Mathf.Cos(a0) * radius, 0f, Mathf.Sin(a0) * radius);
                Vector3 p1 = baseCenter + new Vector3(Mathf.Cos(a1) * radius, 0f, Mathf.Sin(a1) * radius);
                int i0 = _verts.Count; _verts.Add(p0); _norms.Add(Vector3.down);
                int i1 = _verts.Count; _verts.Add(p1); _norms.Add(Vector3.down);
                t.Add(baseIdx); t.Add(i0); t.Add(i1);
                int j0 = _verts.Count; _verts.Add(p0 + Vector3.up * height); _norms.Add(Vector3.up);
                int j1 = _verts.Count; _verts.Add(p1 + Vector3.up * height); _norms.Add(Vector3.up);
                t.Add(topIdx); t.Add(j1); t.Add(j0);
            }
        }
    }
}
