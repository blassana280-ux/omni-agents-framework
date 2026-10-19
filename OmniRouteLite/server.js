'use strict';
// OmniRouteLite — zero-dependency AI gateway server (Node >= 18, uses global fetch)
// Config: config.json (see config.example.json). Env overrides: PORT, HOST, OMNILITE_KEY.
const http = require('http');
const fs = require('fs');
const path = require('path');
const core = require('./core.js');

const cfgPath = path.join(__dirname, process.env.OMNILITE_CONFIG || 'config.json');
const cfg = fs.existsSync(cfgPath) ? JSON.parse(fs.readFileSync(cfgPath, 'utf8')) : {};
const PORT = Number(process.env.PORT || cfg.port || 8787);
const HOST = process.env.HOST || cfg.host || '127.0.0.1';
const GATEWAY_KEY = process.env.OMNILITE_KEY || cfg.gatewayKey || ''; // optional bearer key on the API
const CACHE_TTL = cfg.cache?.ttlMs ?? 3600_000;
const CACHE_ENABLED = cfg.cache?.enabled !== false;
const COMPRESSION_ENABLED = cfg.compression?.enabled !== false;

// ---- state ----
const cache = new Map(); // key -> { resp, expires }
let rrCounter = 0;
const stats = { startedAt: new Date().toISOString(), requests: 0, cacheHits: 0, tokensIn: 0, tokensOut: 0, tokensSaved: 0, providers: {} };
const providers = (cfg.providers || []).map(p => {
  stats.providers[p.name] = { calls: 0, failures: 0, healthy: true };
  return { ...p, unhealthy: false };
});

function json(res, code, obj) { res.writeHead(code, { 'Content-Type': 'application/json' }); res.end(JSON.stringify(obj)); }

function readBody(req) {
  return new Promise((resolve, reject) => {
    let data = '';
    req.on('data', c => { data += c; if (data.length > 5_000_000) { reject(new Error('payload too large')); req.destroy(); } });
    req.on('end', () => { try { resolve(data ? JSON.parse(data) : {}); } catch { reject(new Error('invalid JSON')); } });
    req.on('error', reject);
  });
}

function authorized(req) {
  if (!GATEWAY_KEY) return true;
  const h = req.headers['authorization'] || '';
  return h === 'Bearer ' + GATEWAY_KEY;
}

// ---- provider call (OpenAI-compatible or Anthropic) ----
async function callProvider(p, body, timeoutMs) {
  const out = {
    name: p.name,
    url: p.type === 'anthropic' ? `${p.baseUrl}/v1/messages` : `${p.baseUrl}/v1/chat/completions`,
    headers: p.type === 'anthropic'
      ? { 'content-type': 'application/json', 'x-api-key': p.apiKey, 'anthropic-version': '2023-06-01' }
      : { 'content-type': 'application/json', authorization: `Bearer ${p.apiKey}` },
    body: p.type === 'anthropic' ? core.toAnthropic(body) : { model: body.model, messages: body.messages, temperature: body.temperature, max_tokens: body.max_tokens },
  };
  const ctrl = new AbortController();
  const t = setTimeout(() => ctrl.abort(), timeoutMs || 60_000);
  try {
    const r = await fetch(out.url, { method: 'POST', headers: out.headers, body: JSON.stringify(out.body), signal: ctrl.signal });
    const text = await r.text();
    if (!r.ok) throw new Error(`${p.name} HTTP ${r.status}: ${text.slice(0, 300)}`);
    const data = JSON.parse(text);
    return p.type === 'anthropic' ? core.fromAnthropic(body.model, data) : data;
  } finally { clearTimeout(t); }
}

function mockProviderResponse(body) {
  const last = (body.messages || []).slice(-1)[0]?.content || '';
  const content = `[mock:${body.model}] echo(${String(last).slice(0, 120)}) — providers "mock" servent de filet de secours sans clé ; remplacez-les dans config.json.`;
  return { id: 'omnilite-mock', object: 'chat.completion', created: Math.floor(Date.now() / 1000), model: body.model, choices: [{ index: 0, message: { role: 'assistant', content }, finish_reason: 'stop' }], usage: { prompt_tokens: core.estimateTokens(core.messagesToText(body.messages)), completion_tokens: core.estimateTokens(content), total_tokens: 0 } };
}

// ---- OpenAI-compatible chat completions with cache + fallback routing ----
async function chatCompletions(body) {
  if (!Array.isArray(body.messages) || body.messages.length === 0) throw Object.assign(new Error('messages[] requis'), { status: 400 });
  if (!body.model) throw Object.assign(new Error('model requis'), { status: 400 });

  stats.requests++;
  const key = core.cacheKey(body);

  if (CACHE_ENABLED) {
    const hit = cache.get(key);
    if (hit && hit.expires > Date.now()) {
      stats.cacheHits++;
      return { ...hit.resp, omnilite: { cached: true, provider: hit.resp.omnilite?.provider || 'cache' } };
    }
    if (hit) cache.delete(key);
  }

  let comp = { savedTokens: 0 };
  if (COMPRESSION_ENABLED) {
    comp = core.compressMessages(body.messages);
    body = { ...body, messages: comp.messages };
    stats.tokensSaved += comp.savedTokens;
  }

  const chain = core.route(providers, cfg.routing?.strategy, rrCounter++);
  const errors = [];
  for (const p of chain) {
    stats.providers[p.name].calls++;
    try {
      const resp = p.type === 'mock' ? mockProviderResponse(body) : await callProvider(p, body, p.timeoutMs);
      stats.tokensIn += resp.usage?.prompt_tokens || 0;
      stats.tokensOut += resp.usage?.completion_tokens || 0;
      const out = { ...resp, omnilite: { cached: false, provider: p.name, tokensSavedByCompression: comp.savedTokens } };
      if (CACHE_ENABLED) cache.set(key, { resp: out, expires: Date.now() + CACHE_TTL });
      return out;
    } catch (e) {
      stats.providers[p.name].failures++;
      errors.push(e.message);
    }
  }
  if (chain.length === 0 && providers.length) errors.push('aucun provider sain/disponible — vérifiez config.json');
  throw Object.assign(new Error('tous les providers ont échoué: ' + errors.join(' | ')), { status: 502 });
}

// ---- HTTP server ----
const server = http.createServer(async (req, res) => {
  const url = (req.url || '/').split('?')[0];
  try {
    if (req.method === 'GET' && (url === '/' || url === '/index.html')) {
      const html = fs.readFileSync(path.join(__dirname, 'public', 'index.html'));
      res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' }); return res.end(html);
    }
    if (req.method === 'GET' && url === '/health') return json(res, 200, { ok: true, providers: providers.length });
    if (req.method === 'GET' && url === '/stats') return json(res, 200, stats);
    if (req.method === 'GET' && url === '/v1/models') {
      const seen = new Set(); const models = [];
      for (const p of providers) for (const m of p.models || []) if (!seen.has(m)) { seen.add(m); models.push({ id: m, object: 'model', owned_by: p.name }); }
      return json(res, 200, { object: 'list', data: models });
    }
    if (req.method === 'POST' && (url === '/v1/chat/completions' || url === '/api/chat')) {
      if (!authorized(req)) return json(res, 401, { error: { message: 'clé gateway invalide' } });
      const body = await readBody(req);
      if (body.stream === true) return json(res, 400, { error: { message: 'stream non supporté dans ce MVP — utilisez stream:false' } });
      const resp = await chatCompletions(body);
      return json(res, 200, resp);
    }
    return json(res, 404, { error: { message: 'not found' } });
  } catch (e) {
    return json(res, e.status || 500, { error: { message: String(e.message || e) } });
  }
});

if (require.main === module) {
  server.listen(PORT, HOST, () => {
    console.log(`⚡ OmniRouteLite sur http://${HOST}:${PORT} — ${providers.length} provider(s), cache ${CACHE_ENABLED ? 'ON' : 'OFF'}`);
    if (!GATEWAY_KEY && HOST !== '127.0.0.1') console.warn('⚠ Pas de gatewayKey et écoute hors localhost : toute personne sur le réseau peut appeler l\'API.');
  });
}
module.exports = { server, chatCompletions, stats };
