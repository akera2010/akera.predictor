package com.akeraten.valuebetmonitor.data.remote

import com.akeraten.valuebetmonitor.data.model.WsMessage
import kotlinx.coroutines.channels.awaitClose
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.callbackFlow
import okhttp3.Request
import okhttp3.Response
import okhttp3.WebSocket
import okhttp3.WebSocketListener

sealed interface SocketEvent {
    data object Open : SocketEvent
    data class Message(val message: WsMessage) : SocketEvent
}

/** Thin OkHttp WebSocket wrapper for `WS /ws/live`. The flow completes / fails when the socket closes. */
object LiveSocket {

    fun events(baseUrl: String): Flow<SocketEvent> = callbackFlow {
        val request = Request.Builder().url(Network.webSocketUrl(baseUrl)).build()
        val listener = object : WebSocketListener() {
            override fun onOpen(webSocket: WebSocket, response: Response) {
                trySend(SocketEvent.Open)
            }

            override fun onMessage(webSocket: WebSocket, text: String) {
                val parsed = runCatching {
                    Network.json.decodeFromString(WsMessage.serializer(), text)
                }.getOrNull()
                if (parsed != null) trySend(SocketEvent.Message(parsed))
            }

            override fun onClosing(webSocket: WebSocket, code: Int, reason: String) {
                webSocket.close(1000, null)
            }

            override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
                channel.close()
            }

            override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
                channel.close(t)
            }
        }
        val socket = Network.okHttp.newWebSocket(request, listener)
        awaitClose { socket.cancel() }
    }
}
