using UnityEngine;

namespace OmniWarships.Unity
{
    /// <summary>
    /// Camera militaire dynamique : orbite autour du navire du joueur
    /// (glisser), pince pour le zoom, tremblement d'impact, suivi amorti.
    /// Fonctionne au tactile (Android) et a la souris/clavier (edition).
    /// </summary>
    public sealed class WarshipCamera : MonoBehaviour
    {
        private BattleDirector _director;
        private Camera _cam;
        private Transform _target;

        private float _yaw = 20f;
        private float _pitch = 24f;
        private float _dist = 240f;
        private float _shake;
        private Vector3 _smoothPos;
        private bool _posInit;

        public void Bind(BattleDirector director)
        {
            _director = director;

            _cam = GetComponent<Camera>();
            if (_cam == null)
            {
                _cam = gameObject.AddComponent<Camera>();
                gameObject.tag = "MainCamera";
            }
            _cam.fieldOfView = 55f;
            _cam.nearClipPlane = 0.5f;
            _cam.farClipPlane = 8000f;
            _cam.clearFlags = CameraClearFlags.SolidColor;
            _cam.backgroundColor = new Color(0.55f, 0.65f, 0.75f);
            _cam.allowMSAA = true;

            if (FindObjectOfType(typeof(AudioListener)) == null)
            {
                gameObject.AddComponent<AudioListener>();
            }
        }

        public void Shake(float intensity)
        {
            _shake = Mathf.Max(_shake, intensity);
        }

        private void Update()
        {
            if (_director == null || _director.PlayerShip == null) return;

            ShipView view = _director.ViewOf(_director.PlayerShip.Id);
            if (view != null) _target = view.transform;
            if (_target == null) return;

            TouchInputController input = _director.Input;
            if (input != null)
            {
                Vector2 o = input.ConsumeOrbit();
                _yaw += o.x;
                _pitch += o.y;
                _dist = Mathf.Clamp(_dist * input.ConsumeZoom(), 70f, 900f);
            }
            _pitch = Mathf.Clamp(_pitch, 8f, 78f);

            // victoire/defaite : orbite cinematique lente
            float autoYaw = _director.Outcome != BattleOutcome.InProgress ? 6f * Time.deltaTime : 0f;
            _yaw += autoYaw;

            Vector3 targetPos = _target.position + Vector3.up * 8f;
            Vector3 offset = new Vector3(
                Mathf.Sin(_yaw * Mathf.Deg2Rad) * Mathf.Cos(_pitch * Mathf.Deg2Rad),
                Mathf.Sin(_pitch * Mathf.Deg2Rad),
                Mathf.Cos(_yaw * Mathf.Deg2Rad) * Mathf.Cos(_pitch * Mathf.Deg2Rad)) * _dist;
            Vector3 wanted = targetPos + offset;

            if (!_posInit) { _smoothPos = wanted; _posInit = true; }
            _smoothPos = Vector3.Lerp(_smoothPos, wanted, 1f - Mathf.Exp(-6f * Time.deltaTime));

            Vector3 pos = _smoothPos;
            if (_shake > 0.001f)
            {
                float s = _shake * 1.6f;
                pos += new Vector3(
                    (Mathf.PerlinNoise(Time.time * 25f, 0f) - 0.5f) * s,
                    (Mathf.PerlinNoise(0f, Time.time * 25f) - 0.5f) * s,
                    (Mathf.PerlinNoise(Time.time * 25f, 100f) - 0.5f) * s);
                _shake *= Mathf.Exp(-3.5f * Time.deltaTime);
            }

            transform.position = pos;
            transform.LookAt(targetPos);
        }
    }
}
