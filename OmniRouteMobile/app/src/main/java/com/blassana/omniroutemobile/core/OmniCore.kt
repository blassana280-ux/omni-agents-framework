package com.blassana.omniroutemobile.core

import org.json.JSONArray
import org.json.JSONObject
import kotlin.math.max
import kotlin.math.roundToInt

/**
 * OmniRoute Mobile — cœur logique.
 * Portage natif Kotlin des algorithmes clés d'OmniRoute (v3.8.50, diegosouzapw) :
 * - routage multi-providers avec fallback auto (priority / round-robin)
 * - compression de prompt lossless (normalisation des blancs, économie comptée)
 * - cache de réponses par clé normalisée (insensible aux différences d'espacement)
 * - adaptateurs Anthropic Messages API <-> OpenAI Chat Completions
 * Logique pure : aucune dépendance externe (org.json est intégré à Android).
 */
object OmniCore {

    /** Hash déterministe (djb2, 32 bits, base 36) — stable entre exécutions. */
    fun stableHash(s: String): String {
        var h = 5381L
        for (c in s) h = ((h shl 5) + h + c.code) and 0xFFFFFFFFL
        return h.toString(36)
    }

    /** Estimation grossière ~4 caractères/token. */
    fun estimateTokens(text: String): Int = max(1, (text.length / 4.0).roundToInt())

    /** Normalisation lossless : jamais un mot modifié, uniquement des blancs. */
    fun cleanText(text: String): String = text
        .replace("\r\n", "\n")
        .replace(Regex("[ \\t]+"), " ")
        .replace(Regex(" *\\n *"), "\n")
        .replace(Regex("\\n{3,}"), "\n\n")
        .trim()

    fun messagesToText(messages: JSONArray): String =
        (0 until messages.length()).joinToString("\u0001") { i ->
            val m = messages.getJSONObject(i)
            "${m.optString("role")}\u0000${m.optString("content")}"
        }

    /** Compression lossless : (messages compressés, tokens avant, tokens après). */
    fun compressMessages(messages: JSONArray): Triple<JSONArray, Int, Int> {
        val before = estimateTokens(messagesToText(messages))
        val out = JSONArray()
        for (i in 0 until messages.length()) {
            val m = messages.getJSONObject(i)
            out.put(JSONObject()
                .put("role", m.optString("role"))
                .put("content", cleanText(m.optString("content"))))
        }
        val after = estimateTokens(messagesToText(out))
        return Triple(out, before, after)
    }

    /** Clé de cache : modèle + messages normalisés + température. */
    fun cacheKey(model: String, messages: JSONArray, temperature: Any?): String {
        val parts = (0 until messages.length()).joinToString("|") { i ->
            val m = messages.getJSONObject(i)
            m.optString("role") + ":" + cleanText(m.optString("content"))
        }
        return stableHash("$model|$parts|t:$temperature")
    }

    /** Chaîne de fallback : providers activés et sains, priority ou round-robin. */
    fun route(providers: List<Provider>, strategy: String, rrCounter: Int): List<Provider> {
        val usable = providers.filter { it.enabled && !it.unhealthy }
        if (usable.isEmpty()) return emptyList()
        return if (strategy == "round-robin") {
            val start = rrCounter % usable.size
            List(usable.size) { i -> usable[(start + i) % usable.size] }
        } else usable
    }

    /** Corps OpenAI -> corps Anthropic Messages API. */
    fun toAnthropic(body: JSONObject): JSONObject {
        val messages = body.optJSONArray("messages") ?: JSONArray()
        val system = StringBuilder()
        val rest = JSONArray()
        for (i in 0 until messages.length()) {
            val m = messages.getJSONObject(i)
            if (m.optString("role") == "system") {
                if (system.isNotEmpty()) system.append("\n\n")
                system.append(m.optString("content"))
            } else {
                rest.put(JSONObject()
                    .put("role", if (m.optString("role") == "assistant") "assistant" else "user")
                    .put("content", m.optString("content")))
            }
        }
        val out = JSONObject()
        if (system.isNotEmpty()) out.put("system", system.toString())
        out.put("max_tokens", body.optInt("max_tokens", 1024))
        out.put("messages", rest)
        return out
    }

    /** Réponse Anthropic -> réponse au format OpenAI. */
    fun fromAnthropic(model: String, resp: JSONObject): JSONObject {
        val text = StringBuilder()
        val content = resp.optJSONArray("content")
        if (content != null) for (i in 0 until content.length()) text.append(content.getJSONObject(i).optString("text"))
        val usage = resp.optJSONObject("usage")
        val pt = usage?.optInt("input_tokens", 0) ?: 0
        val ct = usage?.optInt("output_tokens", 0) ?: 0
        return JSONObject()
            .put("id", "omniroute-mobile-" + stableHash(model + text))
            .put("object", "chat.completion")
            .put("created", System.currentTimeMillis() / 1000)
            .put("model", model)
            .put("choices", JSONArray().put(JSONObject()
                .put("index", 0)
                .put("message", JSONObject().put("role", "assistant").put("content", text.toString()))
                .put("finish_reason", resp.optString("stop_reason", "stop"))))
            .put("usage", JSONObject()
                .put("prompt_tokens", pt)
                .put("completion_tokens", ct)
                .put("total_tokens", pt + ct))
    }
}
