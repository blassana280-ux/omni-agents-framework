package com.blassana.omniroutemobile.core

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject

/** Erreur métier avec code HTTP associé. */
class GatewayException(val status: Int, message: String) : Exception(message)

data class Provider(
    val name: String,
    val type: String,          // openai | anthropic | mock
    val baseUrl: String,
    val apiKey: String,
    val models: List<String>,
    val enabled: Boolean = true,
    val timeoutMs: Int = 60_000
) {
    /** Réservé au mode dégradé manuel / futur circuit-breaker. */
    @Volatile var unhealthy: Boolean = false
}

data class AppConfig(
    val port: Int = 8787,
    val gatewayKey: String = "",
    val cacheEnabled: Boolean = true,
    val cacheTtlMs: Long = 3_600_000,
    val compressionEnabled: Boolean = true,
    val strategy: String = "priority",   // priority | round-robin
    val providers: List<Provider> = emptyList()
)

object Config {
    private const val PREFS = "omniroute_mobile"
    private const val KEY = "config_json"

    /** Config par défaut : placeholders + provider mock (aucune clé requise pour tester). */
    val DEFAULT: JSONObject = JSONObject()
        .put("port", 8787)
        .put("gatewayKey", "")
        .put("cache", JSONObject().put("enabled", true).put("ttlMs", 3_600_000L))
        .put("compression", JSONObject().put("enabled", true))
        .put("routing", JSONObject().put("strategy", "priority"))
        .put("providers", JSONArray()
            .put(JSONObject()
                .put("name", "mistral").put("type", "openai")
                .put("baseUrl", "https://api.mistral.ai")
                .put("apiKey", "VOTRE_CLE_MISTRAL")
                .put("models", JSONArray().put("mistral-large-latest").put("mistral-small-latest")))
            .put(JSONObject()
                .put("name", "groq").put("type", "openai")
                .put("baseUrl", "https://api.groq.com/openai")
                .put("apiKey", "VOTRE_CLE_GROQ")
                .put("models", JSONArray().put("llama-3.3-70b-versatile")))
            .put(JSONObject()
                .put("name", "anthropic").put("type", "anthropic")
                .put("baseUrl", "https://api.anthropic.com")
                .put("apiKey", "VOTRE_CLE_ANTHROPIC")
                .put("models", JSONArray().put("claude-sonnet-4-5")))
            .put(JSONObject()
                .put("name", "mock").put("type", "mock")
                .put("models", JSONArray().put("mock-1"))
                .put("enabled", true)))

    /** Les clés restent uniquement sur le téléphone (SharedPreferences privé). */
    fun loadJson(context: Context): String {
        val stored = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getString(KEY, null)
            ?: return DEFAULT.toString(2)
        return runCatching { JSONObject(stored).toString(2) }.getOrElse { DEFAULT.toString(2) }
    }

    fun saveJson(context: Context, json: String) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit().putString(KEY, json).apply()
    }

    fun parse(root: JSONObject): AppConfig {
        val cache = root.optJSONObject("cache")
        val routing = root.optJSONObject("routing")
        val compression = root.optJSONObject("compression")
        val arr = root.optJSONArray("providers") ?: JSONArray()
        val providers = (0 until arr.length()).map { i ->
            val p = arr.getJSONObject(i)
            val models = p.optJSONArray("models")
            Provider(
                name = p.optString("name", "provider-$i"),
                type = p.optString("type", "openai"),
                baseUrl = p.optString("baseUrl"),
                apiKey = p.optString("apiKey"),
                models = if (models == null) emptyList() else (0 until models.length()).map { models.getString(it) },
                enabled = p.optBoolean("enabled", true),
                timeoutMs = p.optInt("timeoutMs", 60_000)
            )
        }
        return AppConfig(
            port = root.optInt("port", 8787),
            gatewayKey = root.optString("gatewayKey", ""),
            cacheEnabled = cache?.optBoolean("enabled", true) ?: true,
            cacheTtlMs = cache?.optLong("ttlMs", 3_600_000L) ?: 3_600_000L,
            compressionEnabled = compression?.optBoolean("enabled", true) ?: true,
            strategy = routing?.optString("strategy", "priority") ?: "priority",
            providers = providers
        )
    }
}
