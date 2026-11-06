using System.Collections.Generic;
using UnityEngine;

namespace OmniWarships.Unity
{
    /// <summary>
    /// Pool d'effets de combat : explosions, gerbes d'eau, flashes de bouche,
    /// fumee. Tout est genere (spheres/quads + shaders OmniFlash/OmniSmoke),
    /// aucun asset externe. Budget limite selon le profil de qualite.
    /// </summary>
    public sealed class EffectsPool : MonoBehaviour
    {
        private sealed class Effect
        {
            public GameObject Go;
            public Material Mat;
            public float T, Dur;
            public Vector3 Vel;
            public float StartScale, EndScale;
            public float BaseIntensity;
            public bool Flatten;
            public bool Rise;
            public bool Alive;
        }

        private const int PoolSize = 64;
        private readonly List<Effect> _pool = new List<Effect>();
        private readonly List<Effect> _active = new List<Effect>();
        private Mesh _sphere;
        private Mesh _quad;
        private Material _flashMat, _splashMat, _smokeMat;
        private Light _flashLight;

        private static Mesh _sharedQuad;
        public static Mesh QuadMesh()
        {
            if (_sharedQuad == null)
            {
                var mb = new MeshBuilder(1);
                mb.Quad(0, new Vector3(-0.5f, 0f, -0.5f), new Vector3(0.5f, 0f, -0.5f),
                    new Vector3(0.5f, 0f, 0.5f), new Vector3(-0.5f, 0f, 0.5f), Vector3.up);
                _sharedQuad = mb.ToMesh();
                _sharedQuad.RecalculateBounds();
                _sharedQuad.bounds = new Bounds(Vector3.zero, new Vector3(2000f, 2f, 2000f));
            }
            return _sharedQuad;
        }

        public void Bind(BattleDirector director)
        {
            var tmp = GameObject.CreatePrimitive(PrimitiveType.Sphere);
            _sphere = tmp.GetComponent<MeshFilter>().sharedMesh;
            Destroy(tmp);

            _quad = QuadMesh();
            _flashMat = ShipView.MakeFlashMaterial(new Color(1f, 0.62f, 0.25f, 1f), 3f);
            _splashMat = ShipView.MakeFlashMaterial(new Color(0.85f, 0.93f, 1f, 0.9f), 1.6f);
            _smokeMat = ShipView.MakeSmokeMaterial(new Color(0.22f, 0.22f, 0.25f, 0.55f));

            for (int i = 0; i < PoolSize; i++)
            {
                var go = new GameObject("Effect");
                go.SetActive(false);
                var mf = go.AddComponent<MeshFilter>();
                mf.sharedMesh = _sphere;
                var mr = go.AddComponent<MeshRenderer>();
                mr.sharedMaterial = _flashMat;
                var e = new Effect { Go = go, Mat = new Material(_flashMat) };
                mr.sharedMaterial = e.Mat;
                _pool.Add(e);
            }

            _flashLight = gameObject.AddComponent<Light>();
            _flashLight.type = LightType.Point;
            _flashLight.range = 260f;
            _flashLight.intensity = 0f;
            _flashLight.shadows = LightShadows.None;
        }

        private Effect Acquire()
        {
            foreach (Effect e in _pool)
            {
                if (!e.Alive) return e;
            }
            return null;
        }

        public void Explosion(Vector3 pos, float scale)
        {
            Effect e = Acquire();
            if (e == null) return;
            Setup(e, pos, scale * 0.25f, scale * 1.15f, 0.55f, 4.5f, false, false);
            Effect s = Acquire();
            if (s != null && QualityProfiles.EffectsEnabled)
            {
                Setup(s, pos + Vector3.up * 3f, scale * 0.3f, scale * 0.9f, 1.6f, 0.3f, false, true);
                s.Mat.color = new Color(0.2f, 0.2f, 0.22f, 0.5f);
            }
            if (_flashLight != null)
            {
                _flashLight.transform.position = pos + Vector3.up * 6f;
                _flashLight.intensity = 5f;
                _flashLight.color = new Color(1f, 0.7f, 0.4f);
            }
        }

        public void Splash(Vector3 pos)
        {
            Effect e = Acquire();
            if (e == null) return;
            Setup(e, pos + Vector3.up * 0.5f, 1.5f, 9f, 0.9f, 1.2f, true, false);
            if (QualityProfiles.EffectsEnabled)
            {
                Effect s = Acquire();
                if (s != null)
                {
                    Setup(s, pos + Vector3.up * 3f, 1f, 4f, 1.4f, 0.4f, false, true);
                    s.Mat.color = new Color(0.9f, 0.95f, 1f, 0.4f);
                }
            }
        }

        public void MuzzleFlash(Vector3 pos)
        {
            Effect e = Acquire();
            if (e == null) return;
            Setup(e, pos, 0.5f, 3.5f, 0.16f, 6f, false, false);
        }

        public void Smoke(Vector3 pos, float scale)
        {
            if (!QualityProfiles.EffectsEnabled) return;
            Effect e = Acquire();
            if (e == null) return;
            Setup(e, pos, scale * 0.5f, scale, 2.2f, 0.5f, false, true);
        }

        private void Setup(Effect e, Vector3 pos, float startScale, float endScale,
            float dur, float intensity, bool flatten, bool rise)
        {
            e.Go.transform.position = pos;
            e.Go.transform.rotation = Quaternion.identity;
            e.Go.transform.localScale = Vector3.one * startScale;
            e.Go.SetActive(true);
            e.Mat.color = Color.white;
            if (e.Mat.HasProperty("_Intensity")) e.Mat.SetFloat("_Intensity", intensity);
            if (flatten)
            {
                var mf = e.Go.GetComponent<MeshFilter>();
                mf.sharedMesh = _quad;
                e.Go.transform.localScale = new Vector3(startScale, 1f, startScale);
                e.Go.transform.rotation = Quaternion.identity;
                e.Mat.color = Color.white;
            }
            else
            {
                e.Go.GetComponent<MeshFilter>().sharedMesh = _sphere;
            }
            e.T = 0f; e.Dur = dur;
            e.StartScale = startScale; e.EndScale = endScale;
            e.BaseIntensity = intensity;
            e.Flatten = flatten;
            e.Rise = rise;
            e.Vel = rise ? Vector3.up * 6f : Vector3.zero;
            e.Alive = true;
            if (!_active.Contains(e)) _active.Add(e);
        }

        private void Update()
        {
            for (int i = _active.Count - 1; i >= 0; i--)
            {
                Effect e = _active[i];
                if (!e.Alive) { _active.RemoveAt(i); continue; }
                e.T += Time.deltaTime;
                float k = Mathf.Clamp01(e.T / e.Dur);
                float scale = Mathf.Lerp(e.StartScale, e.EndScale, k);
                if (e.Flatten) e.Go.transform.localScale = new Vector3(scale, 1f, scale);
                else e.Go.transform.localScale = Vector3.one * scale;
                e.Go.transform.position += e.Vel * Time.deltaTime;
                float fade = 1f - k;
                if (e.Mat.HasProperty("_Intensity")) e.Mat.SetFloat("_Intensity", e.BaseIntensity * fade);
                Color c = e.Mat.color;
                c.a = fade;
                e.Mat.color = c;
                if (k >= 1f)
                {
                    e.Alive = false;
                    e.Go.SetActive(false);
                    _active.RemoveAt(i);
                }
            }
            if (_flashLight != null) _flashLight.intensity *= Mathf.Exp(-8f * Time.deltaTime);
        }
    }
}
