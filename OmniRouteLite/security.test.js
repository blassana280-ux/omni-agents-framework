'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const {
  storeProviderKey,
  readProviderKey,
  resolveProviderKey,
  isSafeProviderEndpoint,
} = require('./provider-keys');

function temporaryRoot(t) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'omniroute-security-'));
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  return root;
}

test('stores provider keys only beneath a private 0700 directory and 0600 file', t => {
  const root = temporaryRoot(t);
  const file = storeProviderKey(root, 'mistral', 'safe-test-key');
  assert.equal(path.dirname(file), path.join(root, 'secrets'));
  assert.equal(readProviderKey(root, 'mistral'), 'safe-test-key');
  if (process.platform !== 'win32') {
    assert.equal(fs.statSync(path.dirname(file)).mode & 0o777, 0o700);
    assert.equal(fs.statSync(file).mode & 0o777, 0o600);
  }
});

test('rejects provider names that could escape the secrets directory', t => {
  const root = temporaryRoot(t);
  for (const name of ('../outside', 'nested/provider', '..', 'mistral/../../outside', '')) {
    assert.throws(() => storeProviderKey(root, name, 'secret'));
    assert.throws(() => readProviderKey(root, name));
  }
  assert.equal(fs.existsSync(path.join(root, 'outside.key')), false);
});

test('refuses to overwrite a pre-existing secret symlink', t => {
  const root = temporaryRoot(t);
  const dir = path.join(root, 'secrets');
  fs.mkdirSync(dir, { mode: 0o700 });
  const victim = path.join(root, 'victim.txt');
  fs.writeFileSync(victim, 'do-not-overwrite');
  fs.symlinkSync(victim, path.join(dir, 'mistral.key'));
  assert.throws(() => storeProviderKey(root, 'mistral', 'attacker-secret'));
  assert.equal(fs.readFileSync(victim, 'utf8'), 'do-not-overwrite');
});

test('refuses to read a symlink or group/world-readable key file', t => {
  const root = temporaryRoot(t);
  const dir = path.join(root, 'secrets');
  fs.mkdirSync(dir, { mode: 0o700 });
  const victim = path.join(root, 'victim.txt');
  fs.writeFileSync(victim, 'secret');
  fs.symlinkSync(victim, path.join(dir, 'mistral.key'));
  assert.throws(() => readProviderKey(root, 'mistral'));

  fs.unlinkSync(path.join(dir, 'mistral.key'));
  const keyPath = path.join(dir, 'mistral.key');
  fs.writeFileSync(keyPath, 'secret', { mode: 0o644 });
  if (process.platform !== 'win32') fs.chmodSync(keyPath, 0o644);
  assert.throws(() => readProviderKey(root, 'mistral'));
});

test('provider endpoints require HTTPS and reject embedded credentials or URL modifiers', () => {
  assert.equal(isSafeProviderEndpoint('https://api.mistral.ai'), true);
  assert.equal(isSafeProviderEndpoint('https://api.mistral.ai/v1'), true);
  for (const endpoint of [
    'http://api.mistral.ai',
    'https://user:password@api.mistral.ai',
    'https://api.mistral.ai?redirect=http://attacker.invalid',
    'https://api.mistral.ai#fragment',
    'not a url',
    '',
  ]) {
    assert.equal(isSafeProviderEndpoint(endpoint), false, endpoint);
  }
});

test('environment key takes precedence and invalid file paths never fall back to inline secrets', () => {
  const envProvider = { name: 'mistral', apiKeyEnv: 'MISTRAL_TEST_KEY', apiKey: 'inline-secret' };
  assert.equal(resolveProviderKey(envProvider, '/unused', { MISTRAL_TEST_KEY: 'environment-secret' }), 'environment-secret');

  const invalidFileProvider = {
    name: 'mistral',
    apiKeyFile: 'secrets/../../outside.key',
    apiKey: 'inline-secret',
  };
  assert.equal(resolveProviderKey(invalidFileProvider, '/unused', {}), '');
});
