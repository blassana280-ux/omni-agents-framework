package com.blassana.omniroutemobile.core

import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

/**
 * Client provider — zéro dépendance : HttpURLConnection (intégré à Android).
 * Deux dialectes : openai-compatible (Mistral, OpenAI, Groq, OpenRouter…)
 * et anthropic (Messages API, avec conversion native).
 */
object ProviderClient {

    fun call(p: Provider, model: String, body: JSONObject): JSONObject {
        val anthropic = p.type == "anthropic"
        val url = if (anthropic) "${p.baseUrl.trimEnd('/')}/v1/messages"
                  else "${p.baseUrl.trimEnd('/')}/v1/chat/completions"

        val conn = (URL(url).openConnection() as HttpURLConnection).apply {
            requestMethod = "POST"
            connectTimeout = 15_000
            readTimeout = p.timeoutMs
            doOutput = true
            setRequestProperty("Content-Type", "application/json; charset=utf-8")
            if (anthropic) {
                setRequestProperty("x-api-key", p.apiKey)
                setRequestProperty("anthropic-version", "2023-06-01")
            } else {
                setRequestProperty("Authorization", "Bearer ${p.apiKey}")
            }
        }

        try {
            val payload = (if (anthropic) OmniCore.toAnthropic(body) else JSONObject()
                .put("model", model)
                .put("messages", body.optJSONArray("messages"))
                .apply {
                    if (body.has("temperature")) put("temperature", body.get("temperature"))
                    if (body.has("max_tokens")) put("max_tokens", body.get("max_tokens"))
                }).toString().toByteArray(Charsets.UTF_8)

            conn.outputStream.use { it.write(payload); it.flush() }

            val code = conn.responseCode
            val text = (if (code in 200..299) conn.inputStream else conn.errorStream)
                ?.bufferedReader()?.use { it.readText() } ?: ""

            if (code !in 200..299) throw Exception("${p.name} HTTP $code : ${text.take(300)}")

            val data = JSONObject(text)
            return if (anthropic) OmniCore.fromAnthropic(model, data) else data
        } finally {
            conn.disconnect()
        }
    }
}
