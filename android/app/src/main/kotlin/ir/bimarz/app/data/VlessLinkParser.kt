package ir.bimarz.app.data

import java.net.URI
import java.net.URLDecoder

/**
 * یک لینک vless:// (فقط طرح VLESS+Reality+Vision، هم‌راستا با چیزی که
 * parsers/vless.py در دسکتاپ می‌پذیرد) را به [ServerProfile] تبدیل
 * می‌کند. فرمت: vless://<uuid>@<host>:<port>?...&security=reality&...#<label>
 *
 * Parses a vless:// link (VLESS+Reality+Vision only, matching what
 * parsers/vless.py accepts on desktop) into a [ServerProfile]. Format:
 * vless://<uuid>@<host>:<port>?...&security=reality&...#<label>
 */
object VlessLinkParser {

    class VlessLinkParseException(message: String) : Exception(message)

    fun parse(rawLink: String): ServerProfile {
        val trimmed = rawLink.trim()
        val uri = try {
            URI(trimmed)
        } catch (e: Exception) {
            throw VlessLinkParseException("Malformed vless:// link: ${e.message}")
        }

        if (uri.scheme?.lowercase() != "vless") {
            throw VlessLinkParseException("Not a vless:// link")
        }

        val uuid = uri.userInfo
            ?: throw VlessLinkParseException("Missing UUID before '@'")
        val address = uri.host
            ?: throw VlessLinkParseException("Missing server address")
        val port = uri.port.takeIf { it > 0 }
            ?: throw VlessLinkParseException("Missing or invalid port")

        val params = parseQuery(uri.rawQuery.orEmpty())

        val security = params["security"]?.lowercase()
        if (security != "reality") {
            throw VlessLinkParseException(
                "Only VLESS+Reality is supported, got security=$security",
            )
        }

        val flow = params["flow"] ?: ""
        val network = params["type"] ?: "tcp"
        val sni = params["sni"] ?: params["peer"] ?: ""
        val fingerprint = params["fp"] ?: "chrome"
        val publicKeyB64 = params["pbk"]
            ?: throw VlessLinkParseException("Missing pbk (Reality public key)")
        val shortIdHex = params["sid"] ?: ""
        val spiderX = params["spx"]?.let { decodeComponent(it) } ?: ""

        val label = uri.rawFragment?.let { decodeComponent(it) } ?: address

        return ServerProfile(
            label = label,
            tag = "bimarz-${System.currentTimeMillis()}",
            uuid = uuid,
            flow = flow,
            address = address,
            port = port,
            network = network,
            sni = sni,
            fingerprint = fingerprint,
            publicKeyB64 = publicKeyB64,
            shortIdHex = shortIdHex,
            spiderX = spiderX,
        )
    }

    private fun parseQuery(rawQuery: String): Map<String, String> {
        if (rawQuery.isEmpty()) return emptyMap()
        return rawQuery.split("&")
            .mapNotNull { pair ->
                val idx = pair.indexOf('=')
                if (idx < 0) return@mapNotNull null
                val key = decodeComponent(pair.substring(0, idx))
                val value = decodeComponent(pair.substring(idx + 1))
                key to value
            }
            .toMap()
    }

    private fun decodeComponent(value: String): String =
        URLDecoder.decode(value, "UTF-8")
}
