package com.blassana.omniroutemobile

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.blassana.omniroutemobile.core.Config
import com.blassana.omniroutemobile.core.Gateway
import com.blassana.omniroutemobile.core.GatewayException
import com.blassana.omniroutemobile.core.GatewayServer
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.net.Inet4Address
import java.net.NetworkInterface

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            MaterialTheme { AppScreen() }
        }
    }
}

private fun localIpAddress(): String? = try {
    val interfaces = NetworkInterface.getNetworkInterfaces()
    var result: String? = null
    while (interfaces.hasMoreElements() && result == null) {
        val nif = interfaces.nextElement()
        if (!nif.isUp || nif.isLoopback) continue
        val addrs = nif.inetAddresses
        while (addrs.hasMoreElements()) {
            val addr = addrs.nextElement()
            if (addr is Inet4Address && !addr.isLoopbackAddress) { result = addr.hostAddress; break }
        }
    }
    result
} catch (e: Exception) { null }

@Composable
fun AppScreen() {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val scroll = rememberScrollState()

    var configText by remember { mutableStateOf("") }
    var serverRunning by remember { mutableStateOf(false) }
    var serverPort by remember { mutableStateOf(8787) }
    var statsText by remember { mutableStateOf("—") }
    var model by remember { mutableStateOf("mock-1") }
    var prompt by remember { mutableStateOf("") }
    var output by remember { mutableStateOf("Prêt. Sans clé API, le provider « mock » répond. Démarrez la passerelle.") }
    var busy by remember { mutableStateOf(false) }
    var serverRef by remember { mutableStateOf<GatewayServer?>(null) }

    LaunchedEffect(Unit) { configText = Config.loadJson(context) }

    LaunchedEffect(serverRunning) {
        while (true) {
            statsText = try { Gateway.stats.snapshot().toString(2) } catch (e: Exception) { "—" }
            delay(1500)
        }
    }

    Column(
        modifier = Modifier.fillMaxSize().verticalScroll(scroll).padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        Text("⚡ OmniRoute Mobile", style = MaterialTheme.typography.headlineSmall)
        Text("Passerelle IA locale — multi-providers · fallback · cache · compression", fontSize = 12.sp)

        // ---- Passerelle ----
        Card(Modifier.fillMaxWidth()) {
            Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                val ip = localIpAddress()
                Text(
                    if (serverRunning) "● ACTIVE — http://${ip ?: "0.0.0.0"}:$serverPort (accessible depuis le réseau local)"
                    else "○ Passerelle arrêtée",
                    fontSize = 14.sp
                )
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Button(onClick = {
                        try {
                            val cfg = Config.parse(JSONObject(configText))
                            Gateway.config = cfg
                            serverPort = cfg.port
                            val s = GatewayServer(cfg.port)
                            s.start()
                            serverRef = s
                            serverRunning = s.isRunning
                            if (!s.isRunning) output = "Impossible d'écouter sur le port ${cfg.port} : ${s.lastError}"
                        } catch (e: Exception) { output = "Config invalide : ${e.message}" }
                    }) { Text("▶ Démarrer") }
                    OutlinedButton(onClick = {
                        serverRef?.stop()
                        serverRef = null
                        serverRunning = false
                    }) { Text("■ Arrêter") }
                }
                Text("Stats live :")
                Text(statsText, fontFamily = FontFamily.Monospace, fontSize = 11.sp)
            }
        }

        // ---- Testeur ----
        Card(Modifier.fillMaxWidth()) {
            Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("Tester la passerelle", style = MaterialTheme.typography.titleMedium)
                OutlinedTextField(
                    value = model, onValueChange = { model = it },
                    label = { Text("Modèle") }, singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )
                OutlinedTextField(
                    value = prompt, onValueChange = { prompt = it },
                    label = { Text("Message") },
                    modifier = Modifier.fillMaxWidth()
                )
                Button(enabled = !busy && prompt.isNotEmpty(), onClick = {
                    busy = true
                    scope.launch {
                        val result = withContext(Dispatchers.IO) {
                            try {
                                val body = JSONObject()
                                    .put("model", model)
                                    .put("messages", JSONArray()
                                        .put(JSONObject().put("role", "user").put("content", prompt)))
                                val r = Gateway.chatCompletions(body)
                                val meta = r.getJSONObject("omniroute")
                                "↪ ${meta.optString("provider")} · cache=${meta.optBoolean("cached")} · économisés=${meta.optInt("tokensSavedByCompression")} tokens\n\n${r.getJSONObject("choices").getJSONObject(0).getJSONObject("message").optString("content")}"
                            } catch (e: GatewayException) { "Erreur ${e.status} : ${e.message}" }
                            catch (e: Exception) { "Erreur : ${e.message}" }
                        }
                        output = result
                        busy = false
                    }
                }) { Text(if (busy) "…" else "Envoyer") }
                Text(output, fontFamily = FontFamily.Monospace, fontSize = 12.sp)
            }
        }

        // ---- Config ----
        Card(Modifier.fillMaxWidth()) {
            Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("Configuration (JSON)", style = MaterialTheme.typography.titleMedium)
                Text("Clés stockées uniquement sur ce téléphone. Types : openai | anthropic | mock.", fontSize = 11.sp)
                OutlinedTextField(
                    value = configText,
                    onValueChange = { configText = it },
                    modifier = Modifier.fillMaxWidth().height(280.dp),
                    textStyle = TextStyle(fontFamily = FontFamily.Monospace, fontSize = 11.sp)
                )
                Button(onClick = {
                    try {
                        val parsed = Config.parse(JSONObject(configText))
                        Config.saveJson(context, configText)
                        Gateway.config = parsed
                        output = "✅ Config sauvegardée et appliquée (${parsed.providers.size} providers, stratégie ${parsed.strategy})"
                    } catch (e: Exception) { output = "❌ Config invalide : ${e.message}" }
                }) { Text("💾 Sauver + appliquer") }
            }
        }
    }
}
