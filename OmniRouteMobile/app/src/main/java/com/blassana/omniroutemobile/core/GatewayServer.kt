package com.blassana.omniroutemobile.core

import org.json.JSONArray
import org.json.JSONObject
import java.io.BufferedInputStream
import java.io.ByteArrayOutputStream
import java.net.ServerSocket
import java.net.Socket

/**
 * Serveur HTTP local compatible OpenAI — zéro dépendance (ServerSocket brut).
 * Fait du téléphone une passerelle : les autres apps/outils du réseau
 * (Termux, PC, autre téléphone) peuvent pointer sur http://<ip-du-tel>:8787.
 *
 * Endpoints :
 *   POST /v1/chat/completions   (auth Bearer si gatewayKey définie)
 *   GET  /v1/models
 *   GET  /stats
 *   GET  /health
 */
class GatewayServer(private val port: Int) {

    @Volatile private var running = false
    private var serverSocket: ServerSocket? = null
    var lastError: String? = null
        private set
    val isRunning: Boolean get() = running

    fun start() {
        if (running) return
        running = true
        Thread {
            try {
                val ss = ServerSocket(port)
                serverSocket = ss
                while (running) {
                    val client = try { ss.accept() } catch (_: Exception) { break }
                    Thread { handle(client) }.start()
                }
            } catch (e: Exception) {
                lastError = e.message
                running = false
            }
        }.start()
    }

    fun stop() {
        running = false
        try { serverSocket?.close() } catch (_: Exception) {}
        serverSocket = null
    }

    private fun handle(socket: Socket) {
        try {
            socket.soTimeout = 30_000
            val input = BufferedInputStream(socket.getInputStream())

            // Lecture des en-têtes jusqu'à \r\n\r\n (parsing octet par octet, fiable)
            val headerBytes = ByteArrayOutputStream()
            var b3 = -10; var b2 = -10; var b1 = -10
            while (true) {
                val b = input.read()
                if (b < 0) return
                headerBytes.write(b)
                if (b3 == 13 && b2 == 10 && b1 == 13 && b == 10) break
                b3 = b2; b2 = b1; b1 = b
            }

            val headerText = headerBytes.toString("UTF-8").trim('\r', '\n')
            val lines = headerText.split("\r\n")
            if (lines.isEmpty()) return
            val reqParts = lines[0].split(" ")
            if (reqParts.size < 2) return
            val method = reqParts[0]
            val path = reqParts[1].substringBefore('?')

            var contentLength = 0
            var auth: String? = null
            for (i in 1 until lines.size) {
                val sep = lines[i].indexOf(':')
                if (sep <= 0) continue
                val name = lines[i].substring(0, sep).trim().lowercase()
                val value = lines[i].substring(sep + 1).trim()
                if (name == "content-length") contentLength = value.toIntOrNull() ?: 0
                if (name == "authorization") auth = value
            }

            val body = if (contentLength > 0) {
                val buf = ByteArray(contentLength)
                var off = 0
                while (off < contentLength) {
                    val n = input.read(buf, off, contentLength - off)
                    if (n < 0) break
                    off += n
                }
                String(buf, 0, off, Charsets.UTF_8)
            } else ""

            val (status, payload) = route(method, path, body, auth)
            writeResponse(socket, status, payload)
        } catch (_: Exception) {
            // connexion interrompue : on ignore
        } finally {
            try { socket.close() } catch (_: Exception) {}
        }
    }

    private fun route(method: String, path: String, body: String, auth: String?): Pair<Int, JSONObject> {
        val cfg = Gateway.config
        return try {
            when {
                method == "GET" && path == "/health" ->
                    200 to JSONObject().put("ok", true).put("providers", cfg.providers.size)

                method == "GET" && path == "/stats" ->
                    200 to Gateway.stats.snapshot()

                method == "GET" && path == "/v1/models" -> {
                    val seen = HashSet<String>()
                    val data = JSONArray()
                    for (p in cfg.providers) for (m in p.models) {
                        if (seen.add(m)) data.put(JSONObject()
                            .put("id", m).put("object", "model").put("owned_by", p.name))
                    }
                    200 to JSONObject().put("object", "list").put("data", data)
                }

                method == "POST" && (path == "/v1/chat/completions" || path == "/api/chat") -> {
                    if (cfg.gatewayKey.isNotEmpty() && auth != "Bearer ${cfg.gatewayKey}") {
                        401 to error("clé gateway invalide")
                    } else {
                        200 to Gateway.chatCompletions(JSONObject(body))
                    }
                }

                else -> 404 to error("not found")
            }
        } catch (e: GatewayException) {
            e.status to error(e.message ?: "erreur")
        } catch (e: Exception) {
            500 to error(e.message ?: e.toString())
        }
    }

    private fun error(msg: String) = JSONObject().put("error", JSONObject().put("message", msg))

    private fun writeResponse(socket: Socket, status: Int, payload: JSONObject) {
        val bytes = payload.toString().toByteArray(Charsets.UTF_8)
        val statusText = when (status) {
            200 -> "OK"; 400 -> "Bad Request"; 401 -> "Unauthorized"; 404 -> "Not Found"
            500 -> "Internal Server Error"; 502 -> "Bad Gateway"; else -> "Status"
        }
        val head = "HTTP/1.1 $status $statusText\r\n" +
            "Content-Type: application/json; charset=utf-8\r\n" +
            "Content-Length: ${bytes.size}\r\n" +
            "Access-Control-Allow-Origin: *\r\n" +
            "Connection: close\r\n\r\n"
        socket.getOutputStream().apply {
            write(head.toByteArray(Charsets.ISO_8859_1))
            write(bytes)
            flush()
        }
    }
}
