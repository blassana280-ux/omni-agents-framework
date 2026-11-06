using System.Collections.Generic;
using OmniWarships.Core.Simulation;
using UnityEngine;

namespace OmniWarships.Unity
{
    /// <summary>
    /// Chargement des modèles 3D FBX générés par omni-asset-factory (Blender)
    /// et exportés dans Resources/Models/{specId}.fbx. Tant que le FBX
    /// n'existe pas dans le projet, la coque procédurale ShipView est
    /// conservée (fallback honnête : aucun modèle n'est prétendu chargé).
    /// </summary>
    public sealed class ShipModelLibrary : MonoBehaviour
    {
        private BattleDirector _director;
        private static readonly HashSet<string> _missing = new HashSet<string>();

        public void Bind(BattleDirector director)
        {
            _director = director;
        }

        public void ApplyTo(ShipView view)
        {
            if (_director == null || view == null || view.State == null) return;
            if (view.GetComponent<ShipModelInstance>() != null) return;

            string id = view.Spec.Id;
            if (_missing.Contains(id)) return;

            GameObject prefab = Resources.Load<GameObject>("Models/" + id);
            if (prefab == null)
            {
                _missing.Add(id); // une seule tentative par spec et par session
                Debug.Log("OMNI WARSHIPS : pas de modele 3D pour " + id +
                    " — coque procedurale conservee (generer le FBX via omni-asset-factory)");
                return;
            }
            ShipModelInstance inst = view.gameObject.AddComponent<ShipModelInstance>();
            inst.Configure(view, _director, prefab);
        }
    }

    /// <summary>
    /// Instance d'un modèle FBX : pivots animés (radars/CIWS en balayage,
    /// tourelles visant la cible du noyau, rotors/hélices) et bascule
    /// LOD0/LOD1/LOD2 selon la distance caméra.
    /// </summary>
    public sealed class ShipModelInstance : MonoBehaviour
    {
        private ShipView _view;
        private BattleDirector _director;
        private readonly List<Transform> _radars = new List<Transform>();
        private readonly List<Transform> _turrets = new List<Transform>();
        private readonly List<Transform> _rotors = new List<Transform>();
        private readonly List<Renderer> _lod0 = new List<Renderer>();
        private readonly List<Renderer> _lod1 = new List<Renderer>();
        private readonly List<Renderer> _lod2 = new List<Renderer>();

        public void Configure(ShipView view, BattleDirector director, GameObject prefab)
        {
            _view = view;
            _director = director;

            Transform model = Instantiate(prefab.transform, view.transform);
            model.localPosition = Vector3.zero;
            // NOTE calibrage : les generateurs Blender exportent la proue vers
            // +Y ; selon l'axe Forward de l'exporteur FBX, ce cap peut demander
            // un ajustement 180 au premier import reel (a verifier).
            model.localRotation = Quaternion.identity;
            model.localScale = Vector3.one;
            model.name = "Model3D";

            Renderer proc = view.GetComponent<MeshRenderer>();
            if (proc != null) proc.enabled = false; // le FBX remplace la coque procedurale

            Collect(model);
        }

        private void Collect(Transform t)
        {
            Renderer rend = t.GetComponent<Renderer>();
            string n = t.name.ToLowerInvariant();

            if (n.Contains("radar") || n.Contains("ciws")) _radars.Add(t);
            else if (n.Contains("turret")) _turrets.Add(t);
            else if (n.Contains("rotor") || n.Contains("propeller")) _rotors.Add(t);

            if (rend != null)
            {
                if (n.EndsWith("_lod1")) { _lod1.Add(rend); rend.enabled = false; }
                else if (n.EndsWith("_lod2")) { _lod2.Add(rend); rend.enabled = false; }
                else _lod0.Add(rend);
            }

            foreach (Transform c in t) Collect(c);
        }

        private void Update()
        {
            if (_view == null || _view.State == null || _view.State.Sunk) return;
            float dt = Time.deltaTime;

            for (int i = 0; i < _radars.Count; i++)
            {
                _radars[i].Rotate(0f, 110f * dt, 0f, Space.Self);
            }
            for (int i = 0; i < _rotors.Count; i++)
            {
                _rotors[i].Rotate(0f, 850f * dt, 0f, Space.Self);
            }

            ShipState target = FindTarget();
            for (int i = 0; i < _turrets.Count; i++)
            {
                Transform turret = _turrets[i];
                float localYaw = 0f;
                if (target != null)
                {
                    Vector3 world = new Vector3(target.Pos.X - _view.State.Pos.X, 0f,
                        target.Pos.Y - _view.State.Pos.Y);
                    Transform parent = turret.parent;
                    Vector3 local = parent == null ? world : parent.InverseTransformDirection(world);
                    localYaw = Mathf.Atan2(local.x, local.z) * Mathf.Rad2Deg;
                }
                Quaternion goal = Quaternion.Euler(0f, localYaw, 0f);
                turret.localRotation = Quaternion.Slerp(turret.localRotation, goal, dt * 3f);
            }

            UpdateLods();
        }

        private ShipState FindTarget()
        {
            if (_director == null || _director.Sim == null) return null;
            ShipState me = _view.State;
            string targetId = null;
            if (_director.PlayerShip == me && _director.Input != null)
            {
                targetId = _director.Input.CurrentTargetId;
            }
            if (string.IsNullOrEmpty(targetId))
            {
                foreach (KeyValuePair<string, Contact> kv in me.Contacts)
                {
                    targetId = kv.Key;
                    break;
                }
            }
            if (string.IsNullOrEmpty(targetId)) return null;
            ShipState t = _director.Sim.Ship(targetId);
            if (t == null || t.Sunk) return null;
            return t;
        }

        private void UpdateLods()
        {
            if (_lod1.Count == 0 && _lod2.Count == 0) return;
            Camera cam = Camera.main;
            if (cam == null) return;
            float d = Vector3.Distance(cam.transform.position, transform.position);
            int level = d < 260f ? 0 : (d < 850f ? 1 : 2);
            SetLod(_lod0, level == 0);
            SetLod(_lod1, level == 1);
            SetLod(_lod2, level == 2);
        }

        private static void SetLod(List<Renderer> list, bool on)
        {
            for (int i = 0; i < list.Count; i++)
            {
                if (list[i] != null) list[i].enabled = on;
            }
        }
    }
}
