using UnityEngine;

namespace OmniWarships.Unity
{
    /// <summary>
    /// Bootstrap T-012 : la couche environnement 3D (météo, écume, dégâts
    /// visuels, effets de combat, modèles FBX, pause) est composée par-dessus
    /// la couche Unity existante SANS modifier un seul fichier de la PR #14.
    /// Liaison paresseuse : poll du BattleDirector (créé par
    /// BattleBootstrap), puis attachement par-navire reprise automatiquement
    /// après chaque Restart (les vues sont recréées par le directeur).
    /// </summary>
    public sealed class GameEnvironment : MonoBehaviour
    {
        private BattleDirector _director;
        private WeatherDirector _weather;
        private CombatEffects _combat;
        private ShipModelLibrary _models;
        private PauseMenu _pause;
        private bool _bound;

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        private static void Bootstrap()
        {
            if (FindObjectOfType<GameEnvironment>() == null)
            {
                var go = new GameObject("OMNI Environment");
                go.AddComponent<GameEnvironment>();
            }
        }

        private void Update()
        {
            if (_director == null)
            {
                _director = FindObjectOfType<BattleDirector>();
                if (_director == null) return;
            }
            if (!_bound)
            {
                _weather = GetOrCreate<WeatherDirector>();
                _combat = GetOrCreate<CombatEffects>();
                _models = GetOrCreate<ShipModelLibrary>();
                _pause = GetOrCreate<PauseMenu>();
                _weather.Bind(_director);
                _combat.Bind(_director);
                _models.Bind(_director);
                _pause.Bind(_director);
                _bound = true;
            }

            // (re)attach par navire : couvre aussi les vues neuves du Restart
            var views = _director.Views;
            for (int i = 0; i < views.Count; i++)
            {
                ShipView v = views[i];
                if (v == null || v.State == null) continue;
                if (v.GetComponent<WakeFoamController>() == null)
                {
                    v.gameObject.AddComponent<WakeFoamController>().Bind(v, _director);
                }
                if (v.GetComponent<ShipDamageVisuals>() == null)
                {
                    v.gameObject.AddComponent<ShipDamageVisuals>().Bind(v, _director);
                }
                _models.ApplyTo(v);
            }
        }

        private T GetOrCreate<T>() where T : Component
        {
            T c = GetComponent<T>();
            if (c == null) c = gameObject.AddComponent<T>();
            return c;
        }
    }
}
