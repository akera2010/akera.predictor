package com.akeraten.valuebetmonitor.data.remote

import android.content.Context
import android.net.wifi.WifiManager
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.sync.Semaphore
import kotlinx.coroutines.sync.withPermit
import kotlinx.coroutines.withContext
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import okhttp3.Request
import java.net.DatagramPacket
import java.net.DatagramSocket
import java.net.Inet4Address
import java.net.InetSocketAddress
import java.net.NetworkInterface
import java.net.SocketTimeoutException
import java.util.concurrent.TimeUnit

/**
 * Finds the AKERATEN backend running on the user's PC.
 *
 * 1. Listens for the UDP beacon the backend broadcasts on port 47800 (see backend/akeraten/discovery.py).
 * 2. If no beacon arrives (some routers/firewalls drop broadcasts), scans the phone's /24 subnet
 *    for a host answering `GET :8000/api/health` with app "AKERATEN".
 */
class LanDiscovery(context: Context) {

    private val wifi = context.applicationContext.getSystemService(Context.WIFI_SERVICE) as WifiManager?

    private val probeClient by lazy {
        Network.okHttp.newBuilder()
            .connectTimeout(450, TimeUnit.MILLISECONDS)
            .readTimeout(1500, TimeUnit.MILLISECONDS)
            .retryOnConnectionFailure(false)
            .build()
    }

    /** Beacon first, then (optionally) subnet scan. Returns a verified base URL or null. */
    suspend fun find(listenMillis: Int = 3_000, scanSubnet: Boolean = true, port: Int = 8000): String? {
        listenForBeacon(listenMillis)?.let { return it }
        return if (scanSubnet) scanSubnet(port) else null
    }

    suspend fun listenForBeacon(timeoutMillis: Int): String? = withContext(Dispatchers.IO) {
        val lock = wifi?.createMulticastLock("akeraten-discovery")?.apply {
            setReferenceCounted(false)
            runCatching { acquire() }
        }
        try {
            DatagramSocket(null).use { socket ->
                socket.reuseAddress = true
                socket.broadcast = true
                socket.bind(InetSocketAddress(DISCOVERY_PORT))
                receiveUntil(socket, System.currentTimeMillis() + timeoutMillis)
            }
        } catch (e: Exception) {
            null
        } finally {
            runCatching { lock?.release() }
        }
    }

    private suspend fun receiveUntil(socket: DatagramSocket, deadline: Long): String? {
        val buf = ByteArray(2048)
        var left = deadline - System.currentTimeMillis()
        while (left > 0) {
            socket.soTimeout = left.toInt()
            val packet = DatagramPacket(buf, buf.size)
            try {
                socket.receive(packet)
            } catch (e: SocketTimeoutException) {
                return null
            }
            val text = String(packet.data, 0, packet.length, Charsets.UTF_8)
            for (url in beaconUrls(text, packet.address?.hostAddress)) {
                if (verify(url)) return url
            }
            left = deadline - System.currentTimeMillis()
        }
        return null
    }

    /** Candidate URLs from a beacon; the sender's own address goes first (it is always reachable). */
    private fun beaconUrls(text: String, senderIp: String?): List<String> {
        val obj = runCatching { Network.json.parseToJsonElement(text).jsonObject }.getOrNull() ?: return emptyList()
        if (obj["app"]?.jsonPrimitive?.content != "AKERATEN") return emptyList()
        val port = obj["port"]?.jsonPrimitive?.content?.toIntOrNull() ?: 8000
        val urls = mutableListOf<String>()
        if (senderIp != null) urls += "http://$senderIp:$port/"
        obj["urls"]?.jsonArray?.forEach { el -> runCatching { urls += el.jsonPrimitive.content } }
        return urls.map(Network::normalizeBaseUrl).distinct()
    }

    suspend fun scanSubnet(port: Int = 8000): String? = coroutineScope {
        val prefixes = localIpv4().map { it.substringBeforeLast('.') }.distinct()
        val gate = Semaphore(48)
        for (prefix in prefixes) {
            val hits = (1..254).map { host ->
                async(Dispatchers.IO) {
                    gate.withPermit {
                        val url = "http://$prefix.$host:$port/"
                        if (verify(url)) url else null
                    }
                }
            }.awaitAll().filterNotNull()
            if (hits.isNotEmpty()) return@coroutineScope hits.first()
        }
        null
    }

    /** True when [baseUrl] answers /api/health as an AKERATEN backend. */
    suspend fun verify(baseUrl: String): Boolean = withContext(Dispatchers.IO) {
        val url = Network.normalizeBaseUrl(baseUrl) + "api/health"
        runCatching {
            probeClient.newCall(Request.Builder().url(url).build()).execute().use { r ->
                r.isSuccessful && (r.body?.string()?.contains("AKERATEN") == true)
            }
        }.getOrDefault(false)
    }

    private fun localIpv4(): List<String> = runCatching {
        NetworkInterface.getNetworkInterfaces().toList()
            .filter { it.isUp && !it.isLoopback }
            .flatMap { it.inetAddresses.toList() }
            .filterIsInstance<Inet4Address>()
            .filter { it.isSiteLocalAddress }
            .mapNotNull { it.hostAddress }
    }.getOrDefault(emptyList())

    companion object {
        const val DISCOVERY_PORT = 47800
    }
}
