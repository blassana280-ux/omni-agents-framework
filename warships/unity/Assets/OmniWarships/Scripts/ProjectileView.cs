using System.Collections.Generic;
using OmniWarships.Core.Simulation;
using OmniWarships.Core.Spec;
using UnityEngine;

namespace OmniWarships.Unity
{
    /// <summary>
    /// Vues des projectiles du noyau : obus (trace lumineux), missiles
    /// (corps + flamme), torpilles (sillage de surface). Le noyau reste
    /// la seule source de verite ; les vues interpolent entre deux pas
    /// fixes (30 Hz) pour un rendu fluide, et declenchent les effets
    /// d'impact a la disparition (interception, gerbe, touche).
    /// </summary>
    public sealed class ProjectileView : MonoBehaviour
    {
        private sealed class PView
        {
            public string Id;
            public GameObject Go;
            public Vector3 Prev, Curr;
            public WeaponKind Kind;
        }

        private BattleDirector _director;
        private readonly Dictionary<string, PView> _active = new Dictionary<string, PView>();
        private readonly List<PView> _pool = new List<PView>();

        private Mesh _sphere;
        private Material _shellMat, _missileMat, _flameMat, _wakeMat;

        public void Bind(BattleDirector director)
        {
            _director = director;
            director.OnSimTicked += OnSimTicked;

            var tmp = GameObject.CreatePrimitive(PrimitiveType.Sphere);
            _sphere = tmp.GetComponent<MeshFilter>().sharedMesh;
            Destroy(tmp);

            _shellMat = ShipView.MakeFlashMaterial(new Color(1f, 0.9f, 0.55f, 1f), 3.5f);
            _missileMat = ShipView.MakeLitMaterial(new Color(0.75f, 0.76f, 0.78f));
            _flameMat = ShipView.MakeFlashMaterial(new Color(1f, 0.65f, 0.3f, 1f), 4f);
            _wakeMat = ShipView.MakeFlashMaterial(new Color(0.85f, 0.93f, 1f, 0.9f), 1.4f);
        }

        private void OnSimTicked()
        {
            if (_director == null || _director.Sim == null) return;
            var seen = new HashSet<string>();

            foreach (Projectile p in _director.Sim.Projectiles)
            {
                seen.Add(p.Id);
                if (p.Dead) continue;
                PView v;
                if (!_active.TryGetValue(p.Id, out v))
                {
                    v = Spawn(p);
                    _active[p.Id] = v;
                }
                v.Prev = v.Curr;
                v.Curr = new Vector3(p.Pos.X, p.Altitude, p.Pos.Y);
            }

            // disparitions -> effets
            List<string> gone = null;
            foreach (KeyValuePair<string, PView> kv in _active)
            {
                if (!seen.Contains(kv.Key)) (gone ?? (gone = new List<string>())).Add(kv.Key);
            }
            if (gone != null)
            {
                foreach (string id in gone) Despawn(id);
            }
        }

        private PView Spawn(Projectile p)
        {
            PView v = null;
            for (int i = 0; i < _pool.Count; i++)
            {
                if (_pool[i].Go != null) { v = _pool[i]; _pool.RemoveAt(i); break; }
            }
            if (v == null)
            {
                v = new PView();
                v.Go = new GameObject("Projectile");
                var mf = v.Go.AddComponent<MeshFilter>();
                mf.sharedMesh = _sphere;
                v.Go.AddComponent<MeshRenderer>();
            }
            v.Id = p.Id;
            v.Kind = p.Kind;
            v.Go.SetActive(true);
            v.Prev = v.Curr = new Vector3(p.Pos.X, p.Altitude, p.Pos.Y);

            // habillement selon le type
            foreach (Transform child in v.Go.transform) Destroy(child.gameObject);
            var mr = v.Go.GetComponent<MeshRenderer>();
            Transform body = v.Go.transform;
            switch (p.Kind)
            {
                case WeaponKind.Gun:
                    mr.sharedMaterial = _shellMat;
                    body.localScale = Vector3.one * 0.5f;
                    break;
                case WeaponKind.Ssm:
                case WeaponKind.Sam:
                case WeaponKind.Rocket:
                    mr.sharedMaterial = _missileMat;
                    body.localScale = new Vector3(0.6f, 0.6f, 2.6f);
                    var flame = GameObject.CreatePrimitive(PrimitiveType.Sphere);
                    Destroy(flame.GetComponent<Collider>());
                    flame.transform.parent = body;
                    flame.transform.localPosition = new Vector3(0f, 0f, -1.7f);
                    flame.transform.localScale = new Vector3(0.9f, 0.9f, 1.4f) / 0.6f; // compense l'echelle parent
                    flame.GetComponent<MeshRenderer>().sharedMaterial = _flameMat;
                    break;
                case WeaponKind.Torpedo:
                default:
                    // torpille sous l'eau : corps invisible, sillage en surface
                    mr.enabled = false;
                    var wake = GameObject.CreatePrimitive(PrimitiveType.Sphere);
                    Destroy(wake.GetComponent<Collider>());
                    wake.name = "Wake";
                    wake.transform.parent = body;
                    wake.transform.localPosition = new Vector3(0f, -p.Altitude + 0.25f, 0f);
                    wake.transform.localScale = new Vector3(0.05f, 0.01f, 1.2f);
                    wake.GetComponent<MeshRenderer>().sharedMaterial = _wakeMat;
                    break;
            }
            return v;
        }

        private void Despawn(string id)
        {
            PView v;
            if (!_active.TryGetValue(id, out v)) return;
            _active.Remove(id);

            // effet de fin selon la cause (champs encore presents au dernier pas)
            Projectile p = null;
            foreach (Projectile q in _director.Sim.Projectiles)
            {
                if (q.Id == id) { p = q; break; }
            }
            if (p != null && _director.Effects != null)
            {
                bool nearShip = false;
                foreach (ShipState s in _director.Sim.Ships)
                {
                    if (!s.Sunk && OmniWarships.Core.Common.Vec2.Distance(p.Pos, s.Pos) < 90f) { nearShip = true; break; }
                }
                if (p.Intercepted)
                {
                    _director.Effects.Explosion(v.Curr, 7f);
                }
                else if (!nearShip && p.Altitude <= 1.5f)
                {
                    _director.Effects.Splash(v.Curr);
                }
                // pres d'un navire : l'evenement Hit a deja spawn l'explosion
            }

            if (v.Go != null)
            {
                v.Go.SetActive(false);
                _pool.Add(v);
            }
        }

        private void Update()
        {
            float alpha = Mathf.Clamp01((Time.time - Time.fixedTime) / Time.fixedDeltaTime);
            foreach (KeyValuePair<string, PView> kv in _active)
            {
                PView v = kv.Value;
                if (v.Go == null) continue;
                Vector3 pos = Vector3.Lerp(v.Prev, v.Curr, alpha);
                v.Go.transform.position = pos;
                if (v.Kind == WeaponKind.Ssm || v.Kind == WeaponKind.Sam)
                {
                    Vector3 dir = v.Curr - v.Prev;
                    if (dir.sqrMagnitude > 0.0001f)
                    {
                        v.Go.transform.rotation = Quaternion.LookRotation(dir.normalized);
                    }
                }
            }
        }
    }
}
