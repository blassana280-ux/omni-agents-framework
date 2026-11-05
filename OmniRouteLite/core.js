'use strict';
// OmniRouteLite — core logic (pure functions, zero dependencies, Node >= 16)
// Tested by test.js. Server logic (server.js) builds on these primitives.

/** Deterministic 53-bit hash (djb2-ish) — used for cache keys, stable across runs. */
function stableHash(str) {
  let h = 5381;
  for (let i = 0; i < str.length; i++) {
    h = ((h << 5) + h + str.charCodeAt(i)) >>> 0;
  }
  return h.toString(36);
}

/** Rough token estimate (~4 chars/token heuristic). */
function estimateTokens(text) {
  return Math.max(1, Math.round(String(text).length / 4));
}

function messagesToText(messages) {
  return (messages || []).map(m => `${m.role}\u0000${String(m.content || '')}`).join('\u0001');
}

/** Collapse whitespace-only redundancy in a single message content. Never alters words. */
function cleanText(text) {
  return String(text || '')
    .replace(/\r\n/g, '\n')
    .replace(/[ \t]+/g, ' ')
    .replace(/ *\n */g, '\n')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

/**
 * Lossless compression: whitespace normalization of all messages.
 * Returns { messages, beforeTokens, afterTokens, savedTokens }.
 */
function compressMessages(messages) {
  const before = messagesToText(messages);
  const out = (messages || []).map(m => ({ ...m, content: cleanText(m.content) }));
  const after = messagesToText(out);
  return {
    messages: out,
    beforeTokens: estimateTokens(before),
    afterTokens: estimateTokens(after),
    savedTokens: Math.max(0, estimateTokens(before) - estimateTokens(after)),
  };
}

/** Cache key from model + normalized messages + temperature. */
function cacheKey(body) {
  const msgs = (body.messages || []).map(m => ({ role: m.role, content: cleanText(m.content) }));
  return stableHash(`${body.model || ''}|${msgs.map(m => m.role + ':' + m.content).join('|')}|t:${body.temperature ?? ''}`);
}

/** Fallback routing: ordered providers, skipping ones marked unhealthy. */
function route(providers, strategy, rrCounter) {
  const usable = providers.filter(p => p.enabled !== false && !p.unhealthy);
  if (usable.length === 0) return [];
  if (strategy === 'round-robin') {
    const start = rrCounter % usable.length;
    return usable.map((_, i) => usable[(start + i) % usable.length]);
  }
  return usable; // default: priority fallback order as declared
}

/** Map OpenAI-format body to Anthropic Messages API format. Returns null if provider is OpenAI-like. */
function toAnthropic(body) {
  const system = (body.messages || []).filter(m => m.role === 'system').map(m => m.content).join('\n\n');
  const rest = (body.messages || []).filter(m => m.role !== 'system');
  return {
    system: system || undefined,
    max_tokens: body.max_tokens || 1024,
    messages: rest.map(m => ({ role: m.role === 'assistant' ? 'assistant' : 'user', content: m.content })),
  };
}

/** Anthropic response -> OpenAI-format response object. */
function fromAnthropic(model, resp) {
  const text = (resp.content || []).map(c => c.text || '').join('');
  return {
    id: 'omnilite-' + stableHash(model + text),
    object: 'chat.completion',
    created: Math.floor(Date.now() / 1000),
    model,
    choices: [{ index: 0, message: { role: 'assistant', content: text }, finish_reason: resp.stop_reason || 'stop' }],
    usage: { prompt_tokens: resp.usage?.input_tokens || 0, completion_tokens: resp.usage?.output_tokens || 0, total_tokens: (resp.usage?.input_tokens || 0) + (resp.usage?.output_tokens || 0) },
  };
}

module.exports = { stableHash, estimateTokens, messagesToText, cleanText, compressMessages, cacheKey, route, toAnthropic, fromAnthropic };
