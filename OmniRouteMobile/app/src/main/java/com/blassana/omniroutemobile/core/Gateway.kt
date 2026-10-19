package com.blassana.omniroutemobile.core

import org.json.JSONArray
import org.json.JSONObject
import kotlin.math.max

/**
 * Moteur de passerelle — le cœur d'OmniRoute porté sur Android :
 * cache -> compression -> routage fallback -> provider -> stats.
 * Partagé par l'UI et le serveur HTTP local.
 */
object Gateway {
    @Volatile var config: AppConfig = Config.parse(Config.DEFAULT)
    val stats = Stats()

    private class CacheEntry(val expiresAt: Long, val resp: JSONObject)
    private val cache = HashMap<String, CacheEntry>()
    private var rr = 0

    private fun nextRr(): Int = synchronized(this) { rr++ }

    fun chatCompletions(body: JSONObject): JSONObject {
        val messages = body.optJSONArray("messages")
        if (messages == null || messages.length() == 0) throw GatewayException(400, "messages[] requis")
        val model = body.optString("model")
        if (model.isEmpty()) throw GatewayException(400, "model requis")

        stats.incRequests()
        val key = OmniCore.cacheKey(model, messages, body.opt("temperature"))

        // 1. Cache
        if (config.cacheEnabled) {
            val hit = synchronized(this) { cache[key] }
            if (hit != null) {
                if (hit.expiresAt > System.currentTimeMillis()) {
                    stats.incCacheHits()
                    val out = JSONObject(hit.resp.toString())
                    val meta = out.optJSONObject("omniroute") ?: JSONObject()
                    meta.put("cached", true)
                    out.put("omniroute", meta)
                    return out
                }
                synchronized(this) { cache.remove(key) }
            }
        }

        // 2. Compression lossless
        var savedTokens = 0
        var effectiveBody = body
        if (config.compressionEnabled) {
            val (compressed, before, after) = OmniCore.compressMessages(messages)
            effectiveBody = JSONObject(body.toString()).put("messages", compressed)
            savedTokens = max(0, before - after)
            stats.addTokensSaved(savedTokens)
        }

        // 3. Routage fallback : on essaie la chaîne, le premier qui répond gagne
        val chain = OmniCore.route(config.providers, config.strategy, nextRr())
        val errors = ArrayList<String>()
        for (p in chain) {
            stats.providerCall(p.name)
            try {
                val resp = if (p.type == "mock") mockResponse(model, messages)
                           else ProviderClient.call(p, model, effectiveBody)
                val usage = resp.optJSONObject("usage")
                stats.addTokens(usage?.optInt("prompt_tokens", 0) ?: 0,
                                usage?.optInt("completion_tokens", 0) ?: 0)
                val out = JSONObject(resp.toString())
                out.put("omniroute", JSONObject()
                    .put("cached", false)
                    .put("provider", p.name)
                    .put("tokensSavedByCompression", savedTokens))
                if (config.cacheEnabled) {
                    val entry = CacheEntry(System.currentTimeMillis() + config.cacheTtlMs,
                                            JSONObject(out.toString()))
                    synchronized(this) { cache[key] = entry }
                }
                return out
            } catch (e: Exception) {
                stats.providerFail(p.name)
                errors.add(e.message ?: e.toString())
            }
        }

        val msg = if (chain.isEmpty()) "aucun provider activé — vérifiez la configuration"
                  else "tous les providers ont échoué : " + errors.joinToString(" | ")
        throw GatewayException(502, msg)
    }

    /** Provider intégré : tester la passerelle sans aucune clé API. */
    private fun mockResponse(model: String, messages: JSONArray): JSONObject {
        val last = if (messages.length() > 0)
            messages.getJSONObject(messages.length() - 1).optString("content") else ""
        val content = "[mock:$model] echo(${last.take(120)}) — provider « mock » : filet de secours sans clé ; ajoutez vos clés dans la config."
        return JSONObject()
            .put("id", "omniroute-mobile-mock")
            .put("object", "chat.completion")
            .put("created", System.currentTimeMillis() / 1000)
            .put("model", model)
            .put("choices", JSONArray().put(JSONObject()
                .put("index", 0)
                .put("message", JSONObject().put("role", "assistant").put("content", content))
                .put("finish_reason", "stop")))
            .put("usage", JSONObject()
                .put("prompt_tokens", OmniCore.estimateTokens(OmniCore.messagesToText(messages)))
                .put("completion_tokens", OmniCore.estimateTokens(content))
                .put("total_tokens", 0))
    }
}

/** Compteurs thread-safe. */
class Stats {
    val startedAt = System.currentTimeMillis()
    private val lock = Any()
    private var requests = 0
    private var cacheHits = 0
    private var tokensIn = 0
    private var tokensOut = 0
    private var tokensSaved = 0
    private val providers = LinkedHashMap<String, IntArray>() // [calls, failures]

    private fun slot(name: String): IntArray =
        providers.getOrPut(name) { IntArray(2) }

    fun incRequests() { synchronized(lock) { requests++ } }
    fun incCacheHits() { synchronized(lock) { cacheHits++ } }
    fun addTokensSaved(n: Int) { synchronized(lock) { tokensSaved += n } }
    fun addTokens(inTokens: Int, outTokens: Int) {
        synchronized(lock) { tokensIn += inTokens; tokensOut += outTokens }
    }
    fun providerCall(name: String) { synchronized(lock) { slot(name)[0]++ } }
    fun providerFail(name: String) { synchronized(lock) { slot(name)[1]++ } }

    fun snapshot(): JSONObject = synchronized(lock) {
        val p = JSONObject()
        providers.forEach { (name, arr) ->
            p.put(name, JSONObject().put("calls", arr[0]).put("failures", arr[1]))
        }
        JSONObject()
            .put("startedAt", startedAt)
            .put("requests", requests)
            .put("cacheHits", cacheHits)
            .put("tokensIn", tokensIn)
            .put("tokensOut", tokensOut)
            .put("tokensSaved", tokensSaved)
            .put("providers", p)
    }
}
