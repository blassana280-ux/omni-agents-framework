using UnityEngine;

namespace OmniWarships.Unity
{
    public enum WeatherState { Clear, Haze, Rain, Storm }

    /// <summary>
    /// Environnement naval : cycle jour/nuit (soleil + ambiance + brouillard
    /// + ciel procédural OmniSky avec étoiles), météo (clair / brume / pluie
    /// / tempête avec pluie particules et éclairs). PUREMENT VISUEL : le
    /// noyau (houle, détection, balistique) reste la seule source de vérité —
    /// la pluie ne change PAS la portée radar du noyau (le Fog de la sim
    /// vient de BattleConfig, pas d'ici).
    /// </summary>
    public sealed class WeatherDirector : MonoBehaviour
    {
        private BattleDirector _director;
        private Light _sun;
        private Material _sky;
        private ParticleSystem _rain;
        private WeatherState _state = WeatherState.Clear;
        private float _nextChangeS;
        private float _dayFraction = 0.38f; // départ en fin de matinée
        private float _flash;

        public const float DayLengthS = 480f; // journée complète en 8 minutes

        public WeatherState State { get { return _state; } }
        /// <summary>0 = minuit, 0.5 = midi.</summary>
        public float DayFraction { get { return _dayFraction; } }
        public bool IsNight { get { return SunElevationDeg < 0f; } }

        public void Bind(BattleDirector director)
        {
            _director = director;
            EnsureSky();
            EnsureRain();
        }

        private void EnsureSky()
        {
            if (_sky != null) return;
            Shader s = Shader.Find("OmniWarships/Sky");
            if (s == null)
            {
                Debug.LogWarning("OMNI WARSHIPS : shader OmniWarships/Sky introuvable — ciel par défaut conservé");
                return;
            }
            _sky = new Material(s);
            RenderSettings.skybox = _sky;
        }

        private void EnsureRain()
        {
            if (_rain != null) return;
            var go = new GameObject("OMNI Rain");
            _rain = go.AddComponent<ParticleSystem>();
            var main = _rain.main;
            main.loop = true;
            main.playOnAwake = true;
            main.startLifetime = 1.2f;
            main.startSpeed = 24f;
            main.startSize = 0.32f;
            main.simulationSpace = ParticleSystemSimulationSpace.World;
            main.gravityModifier = 0.35f;
            main.maxParticles = 700;
            var em = _rain.emission;
            em.rateOverTime = 0f;
            var sh = _rain.shape;
            sh.shapeType = ParticleSystemShapeType.Box;
            sh.scale = new Vector3(90f, 1f, 90f);
            var rend = go.GetComponent<ParticleSystemRenderer>();
            rend.sharedMaterial = ShipView.MakeFlashMaterial(new Color(0.65f, 0.76f, 0.92f, 0.55f), 1.3f);
        }

        private float SunElevationDeg
        {
            get
            {
                float h = _dayFraction * 24f;
                return Mathf.Sin((h - 6f) / 12f * Mathf.PI) * 75f - 12f;
            }
        }

        private void Update()
        {
            if (_director == null || _director.Sim == null) return;
            float dt = Time.deltaTime;
            _dayFraction = (_dayFraction + dt / DayLengthS) % 1f;

            // transitions météo aléatoires (visuel uniquement)
            if (Time.unscaledTime > _nextChangeS)
            {
                _state = PickWeather();
                _nextChangeS = Time.unscaledTime + Random.Range(80f, 190f);
            }

            if (_sun == null || !_sun)
            {
                _sun = RenderSettings.sun;
                if (_sun == null)
                {
                    foreach (Light l in FindObjectsOfType(typeof(Light)))
                    {
                        if (l.type == LightType.Directional) { _sun = l; break; }
                    }
                }
            }

            float elev = SunElevationDeg;
            float dayFactor = Mathf.Clamp01(elev / 25f);
            float h24 = _dayFraction * 24f;
            float azimuth = (h24 * 15f) % 360f;

            if (_sun != null)
            {
                _sun.transform.rotation = Quaternion.Euler(elev, azimuth, 0f);
                _sun.intensity = Mathf.Lerp(0.06f, 1.15f, dayFactor);
                _sun.color = Color.Lerp(new Color(0.55f, 0.62f, 0.85f), new Color(1f, 0.96f, 0.88f), dayFactor);
            }

            // ambiance + brouillard : nuit + météo assombries, la tempête épaissit
            float weatherDark = _state == WeatherState.Storm ? 0.45f :
                _state == WeatherState.Rain ? 0.7f :
                _state == WeatherState.Haze ? 0.88f : 1f;
            Color dayAmbient = new Color(0.38f, 0.42f, 0.48f);
            Color nightAmbient = new Color(0.10f, 0.12f, 0.19f);
            Color ambient = Color.Lerp(nightAmbient, dayAmbient, dayFactor) * weatherDark;

            float flashNow = _flash;
            if (_state == WeatherState.Storm && Random.value < dt * 0.12f) _flash = 1f;
            _flash = Mathf.Max(0f, _flash - dt * 3.5f);
            if (_flash > 0f) ambient += new Color(_flash * 0.5f, _flash * 0.5f, _flash * 0.6f);
            RenderSettings.ambientLight = ambient;

            Color dayFog = _state == WeatherState.Storm ? new Color(0.38f, 0.42f, 0.47f) :
                _state == WeatherState.Rain ? new Color(0.45f, 0.52f, 0.58f) :
                _state == WeatherState.Haze ? new Color(0.62f, 0.68f, 0.74f) : new Color(0.55f, 0.65f, 0.75f);
            Color nightFog = new Color(0.05f, 0.07f, 0.12f);
            RenderSettings.fogColor = Color.Lerp(nightFog, dayFog, dayFactor);
            float simFog = _director.Sim.Fog; // noyau = vérité (détections)
            float weatherFog = _state == WeatherState.Storm ? 0.55f :
                _state == WeatherState.Rain ? 0.3f : _state == WeatherState.Haze ? 0.35f : 0f;
            RenderSettings.fogDensity = 0.000012f + (simFog + weatherFog) * 0.00006f;
            RenderSettings.fog = true;
            RenderSettings.fogMode = FogMode.Exponential;

            if (_sky != null)
            {
                _sky.SetVector("_SunDir", _sun == null ? new Vector4(0.4f, 0.7f, 0.6f, 0f) :
                    new Vector4(-_sun.transform.forward.x, -_sun.transform.forward.y, -_sun.transform.forward.z, 0f));
                _sky.SetFloat("_NightFactor", 1f - dayFactor);
                _sky.SetColor("_ZenithColor", Color.Lerp(new Color(0.02f, 0.03f, 0.08f), new Color(0.30f, 0.50f, 0.78f) * weatherDark, dayFactor));
                _sky.SetColor("_HorizonColor", RenderSettings.fogColor);
                _sky.SetColor("_SunColor", _sun == null ? Color.white : _sun.color);
                _sky.SetFloat("_StarsStrength", Mathf.Clamp01(1f - dayFactor * 2f));
            }

            UpdateRain();
        }

        private static WeatherState PickWeather()
        {
            float r = Random.value;
            if (r < 0.45f) return WeatherState.Clear;
            if (r < 0.70f) return WeatherState.Haze;
            if (r < 0.90f) return WeatherState.Rain;
            return WeatherState.Storm;
        }

        private void UpdateRain()
        {
            if (_rain == null) return;
            var em = _rain.emission;
            float rate = _state == WeatherState.Storm ? 480f :
                _state == WeatherState.Rain ? 220f : 0f;
            em.rateOverTime = QualityProfiles.EffectsEnabled ? rate : rate * 0.5f;
            var main = _rain.main;
            main.startSpeed = _state == WeatherState.Storm ? 32f : 24f;
            Camera cam = Camera.main;
            if (cam != null)
            {
                _rain.transform.position = cam.transform.position + Vector3.up * 22f;
            }
        }
    }
}
