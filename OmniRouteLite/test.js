'use strict';
// OmniRouteLite — end-to-end tests. Run: node test.js  (Node >= 18, no deps)
// Boots the real server on an ephemeral port with mock providers, then hits it over HTTP.
const assert = require('assert');
const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

const tmpCfg = path.join(__dirname, 'config.test.json');
fs.writeFileSync(tmpCfg, JSON.stringify({
  port: 0, host: '127.0.0.1', gatewayKey: 'test-key',
  cache: { enabled: true, ttlMs: 60000 },
  routing: { strategy: 'round-robin' },
  providers: [
    { name: 'mock-a', type: 'mock', models: ['mock-1'] },
    { name: 'mock-b', type: 'mock', models: ['mock-2'] },
  ],
}));

const child = spawn(process.execPath, [path.join(__dirname, 'server.js')], {
  env: { ...process.env, OMNILITE_CONFIG: 'config.test.json', PORT: '8917', OMNILITE_KEY: 'test-key' },
  stdio: ['ignore', 'pipe', 'pipe'],
});

const sleep = ms => new Promise(r => setTimeout(r, ms));
async function waitPort() {
  for (let i = 0; i < 50; i++) {
    try { const r = await fetch('http://127.0.0.1:8917/health'); if (r.ok) return; } catch {}
    await sleep(100);
  }
  throw new Error('server did not start');
}

(async () => {
  await waitPort();
  const base = 'http://127.0.0.1:8917';
  const H = { 'content-type': 'application/json', authorization: 'Bearer test-key' };

  // 1. health
  const health = await (await fetch(base + '/health')).json();
  assert.strictEqual(health.ok, true);
  assert.strictEqual(health.providers, 2);

  // 2. auth: bad key rejected
  const unauth = await fetch(base + '/v1/chat/completions', { method: 'POST', headers: { 'content-type': 'application/json', authorization: 'Bearer wrong' }, body: JSON.stringify({ model: 'mock-1', messages: [{ role: 'user', content: 'hi' }] }) });
  assert.strictEqual(unauth.status, 401);

  // 3. validation: missing messages -> 400
  const bad = await fetch(base + '/v1/chat/completions', { method: 'POST', headers: H, body: JSON.stringify({ model: 'mock-1' }) });
  assert.strictEqual(bad.status, 400);

  // 4. first call: miss, provider routed
  const body1 = { model: 'mock-1', messages: [{ role: 'user', content: '  hello   world  \n\n\n\n  testing ' }] };
  const r1 = await (await fetch(base + '/v1/chat/completions', { method: 'POST', headers: H, body: JSON.stringify(body1) })).json();
  assert.strictEqual(r1.omnilite.cached, false);
  assert.ok(r1.choices[0].message.content.length > 0);
  assert.ok(r1.omnilite.tokensSavedByCompression >= 0);

  // 5. identical call: cache HIT (whitespace differences tolerated by cache key normalization)
  const body2 = { model: 'mock-1', messages: [{ role: 'user', content: 'hello world \n\ntesting' }] };
  const r2 = await (await fetch(base + '/v1/chat/completions', { method: 'POST', headers: H, body: JSON.stringify(body2) })).json();
  assert.strictEqual(r2.omnilite.cached, true);

  // 6. round-robin: two distinct prompts hit different providers
  const a = await (await fetch(base + '/v1/chat/completions', { method: 'POST', headers: H, body: JSON.stringify({ model: 'mock-2', messages: [{ role: 'user', content: 'x1' }] }) })).json();
  const b = await (await fetch(base + '/v1/chat/completions', { method: 'POST', headers: H, body: JSON.stringify({ model: 'mock-2', messages: [{ role: 'user', content: 'x2' }] }) })).json();
  assert.ok(a.omnilite.provider !== b.omnilite.provider, 'round-robin should alternate providers');

  // 7. models endpoint
  const models = await (await fetch(base + '/v1/models')).json();
  assert.deepStrictEqual(models.data.map(m => m.id).sort(), ['mock-1', 'mock-2']);

  // 8. stats reflect traffic
  const stats = await (await fetch(base + '/stats')).json();
  assert.ok(stats.requests >= 4);
  assert.ok(stats.cacheHits >= 1);

  console.log('✅ 8/8 tests E2E passés (auth, validation, routage, cache, compression, round-robin, models, stats)');
  child.kill();
  fs.unlinkSync(tmpCfg);
  process.exit(0);
})().catch(e => { console.error('❌ FAIL:', e.message); child.kill(); try { fs.unlinkSync(tmpCfg); } catch {} process.exit(1); });
