import { describe, it, expect } from 'bun:test';
import { ImageEnvironmentFactory } from './image-environment-factory.ts';
import { UnityEnvironment } from '../logic/unity/environment.ts';
import { System } from './system/system.ts';

// T-013.9 (omni-warships) — VALEURS 100% FACTICES : aucun identifiant reel
// n apparait dans ce fichier, aucune valeur n est jamais affichee. Ces
// tests prouvent le correctif de securite de image-environment-factory.ts :
// UNITY_EMAIL et UNITY_PASSWORD atteignent le conteneur par l ENVIRONNEMENT
// herite du processus docker (references `--env NAME` SANS valeur), jamais
// par la chaine de commande — System.run passe cette chaine a `sh -c`, ce
// qui la mettrait dans l argv des processus du runner.

const FAKE_EMAIL = 'fake-ci-account@example.invalid';
const FAKE_PASSWORD = 'fake-ci-password-never-real-42';

const buildOptions = () =>
  ({
    engine: 'unity',
    hostOS: 'linux',
    projectPath: 'test-project',
    targetPlatform: 'Android',
    engineVersion: '2022.3.62f1',
    unityEmail: FAKE_EMAIL,
    unityPassword: FAKE_PASSWORD,
  }) as any;

describe('T-013.9 : identifiants JAMAIS dans la chaine de commande docker (argv)', () => {
  it('emet des references SANS valeur : --env UNITY_EMAIL et --env UNITY_PASSWORD', () => {
    const options = buildOptions();
    const extra = UnityEnvironment.getVariables(options);
    const envString = ImageEnvironmentFactory.getEnvVarString(options, extra);

    expect(envString).toContain('--env UNITY_EMAIL');
    expect(envString).toContain('--env UNITY_PASSWORD');
    expect(envString).not.toContain('--env UNITY_EMAIL="');
    expect(envString).not.toContain('--env UNITY_PASSWORD="');
  });

  it('la chaine de commande ne contient NI l email NI le mot de passe', () => {
    const options = buildOptions();
    const extra = UnityEnvironment.getVariables(options);
    const envString = ImageEnvironmentFactory.getEnvVarString(options, extra);

    expect(envString).not.toContain(FAKE_EMAIL);
    expect(envString).not.toContain(FAKE_PASSWORD);
  });

  it('les valeurs arrivent au processus docker PAR SON ENVIRONNEMENT (heritage)', () => {
    const options = buildOptions();
    const extra = UnityEnvironment.getVariables(options);
    const inherited = ImageEnvironmentFactory.getInheritedEnvVars(options, extra);

    expect(inherited.UNITY_EMAIL).toBe(FAKE_EMAIL);
    expect(inherited.UNITY_PASSWORD).toBe(FAKE_PASSWORD);
  });

  it('le conteneur recoit les identifiants : reference --env + valeur dans l env herite', () => {
    const options = buildOptions();
    const extra = UnityEnvironment.getVariables(options);
    const envString = ImageEnvironmentFactory.getEnvVarString(options, extra);
    const inherited = ImageEnvironmentFactory.getInheritedEnvVars(options, extra);

    expect(envString).toContain('--env UNITY_EMAIL');
    expect(envString).toContain('--env UNITY_PASSWORD');
    expect(inherited.UNITY_EMAIL).toBe(FAKE_EMAIL);
    expect(inherited.UNITY_PASSWORD).toBe(FAKE_PASSWORD);
  });

  it('System.run (sh -c) porte les valeurs dans l ENVIRONNEMENT enfant, pas dans argv', async () => {
    // Le flux reel : Docker.run passe a System.run la commande (qui ne
    // contient plus que des references) ET l env herite — le spawn sh -c
    // docker ... recoit les valeurs par son environnement. La commande
    // reste la MEME pour sh : les valeurs ne sont pas dedans.
    const cmd =
      'node -e "process.stdout.write(process.env.UNITY_EMAIL + \'/\' + process.env.UNITY_PASSWORD)"';

    const result = await System.run(cmd, undefined, {
      silent: true,
      env: { UNITY_EMAIL: FAKE_EMAIL, UNITY_PASSWORD: FAKE_PASSWORD },
    });

    expect(result.output.trim()).toBe(FAKE_EMAIL + '/' + FAKE_PASSWORD);
    expect(cmd).not.toContain(FAKE_EMAIL);
    expect(cmd).not.toContain(FAKE_PASSWORD);
  });
});
