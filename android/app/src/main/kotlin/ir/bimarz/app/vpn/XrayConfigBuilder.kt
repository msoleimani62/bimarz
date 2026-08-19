package ir.bimarz.app.vpn

import ir.bimarz.app.uniffi.buildDnsGuardConfigJson
import ir.bimarz.app.uniffi.buildDnsRoutingRuleJson
import org.json.JSONArray
import org.json.JSONObject

/**
 * کانفیگ اجرای xray-core را می‌سازد: یک inbound SOCKS5 محلی (که
 * hev-socks5-tunnel به آن وصل می‌شود)، یک inbound gRPC API محلی (که
 * mobile-core از طریق آن outbound واقعی VLESS+Reality را بعد از بالا
 * آمدن xray اضافه می‌کند — دقیقاً همان الگوی ACTIVE_OUTBOUND_TAG که
 * دسکتاپ استفاده می‌کند)، و بخش dns/routing که مستقیماً از همان منطق
 * تست‌شده‌ی engine-core (از طریق mobile-core) گرفته شده، نه بازنویسی.
 *
 * Builds the xray-core runtime config: a local SOCKS5 inbound (which
 * hev-socks5-tunnel connects to), a local gRPC API inbound (through which
 * mobile-core adds the real VLESS+Reality outbound after xray comes up —
 * the exact same ACTIVE_OUTBOUND_TAG pattern desktop uses), and a
 * dns/routing section pulled straight from engine-core's own tested logic
 * (via mobile-core), not reimplemented.
 *
 * ⚠️ نام و امضای واقعی buildDnsGuardConfigJson/buildDnsRoutingRuleJson
 * بعد از تولید bindings با uniffi-bindgen (اسکریپت build-android.sh)
 * باید تأیید شود؛ اینجا طبق قاعده‌ی تبدیل نام‌گذاری استاندارد uniffi
 * (snake_case -> camelCase) نوشته شده.
 *
 * ⚠️ The real name/signature of buildDnsGuardConfigJson/
 * buildDnsRoutingRuleJson must be confirmed once bindings are generated
 * by uniffi-bindgen (build-android.sh); written here per uniffi's
 * standard naming convention (snake_case -> camelCase).
 */
object XrayConfigBuilder {

    const val ACTIVE_OUTBOUND_TAG = "bimarz-active"
    private const val SOCKS_INBOUND_TAG = "socks-in"
    private const val API_INBOUND_TAG = "api-in"

    data class Ports(val socksPort: Int, val apiPort: Int)

    fun build(ports: Ports): String {
        val dnsSection = JSONObject(buildDnsGuardConfigJson())
        val dnsRoutingRule = JSONObject(buildDnsRoutingRuleJson())

        val root = JSONObject()
        root.put("log", JSONObject().put("loglevel", "warning"))
        root.put("dns", dnsSection)
        root.put("stats", JSONObject())
        root.put(
            "api",
            JSONObject()
                .put("tag", "api")
                .put("services", JSONArray(listOf("HandlerService", "StatsService"))),
        )
        root.put(
            "policy",
            JSONObject().put(
                "system",
                JSONObject()
                    .put("statsOutboundUplink", true)
                    .put("statsOutboundDownlink", true),
            ),
        )

        root.put(
            "inbounds",
            JSONArray()
                .put(
                    JSONObject()
                        .put("tag", SOCKS_INBOUND_TAG)
                        .put("listen", "127.0.0.1")
                        .put("port", ports.socksPort)
                        .put("protocol", "socks")
                        .put("settings", JSONObject().put("udp", true)),
                )
                .put(
                    JSONObject()
                        .put("tag", API_INBOUND_TAG)
                        .put("listen", "127.0.0.1")
                        .put("port", ports.apiPort)
                        .put("protocol", "dokodemo-door")
                        .put("settings", JSONObject().put("address", "127.0.0.1")),
                ),
        )

        root.put(
            "outbounds",
            JSONArray()
                // placeholder اولیه — بلافاصله بعد از بالا آمدن xray از
                // طریق gRPC با outbound واقعی VLESS+Reality جایگزین
                // می‌شود (دقیقاً مثل desktop).
                // Initial placeholder — replaced with the real
                // VLESS+Reality outbound via gRPC right after xray comes
                // up (exactly like desktop).
                .put(
                    JSONObject()
                        .put("tag", ACTIVE_OUTBOUND_TAG)
                        .put("protocol", "freedom")
                        .put("settings", JSONObject()),
                )
                .put(JSONObject().put("tag", "dns-out").put("protocol", "dns"))
                .put(JSONObject().put("tag", "direct").put("protocol", "freedom"))
                .put(JSONObject().put("tag", "block").put("protocol", "blackhole")),
        )

        root.put(
            "routing",
            JSONObject().put(
                "rules",
                JSONArray()
                    .put(dnsRoutingRule)
                    .put(
                        JSONObject()
                            .put("type", "field")
                            .put("inboundTag", JSONArray(listOf(API_INBOUND_TAG)))
                            .put("outboundTag", "api"),
                    )
                    .put(
                        JSONObject()
                            .put("type", "field")
                            .put("inboundTag", JSONArray(listOf(SOCKS_INBOUND_TAG)))
                            .put("outboundTag", ACTIVE_OUTBOUND_TAG),
                    ),
            ),
        )

        return root.toString()
    }
}
