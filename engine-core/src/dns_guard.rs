use serde_json::json;

// کانفیگ DNS-over-HTTPS برای جلوگیری از نشت DNS.
// DNS-over-HTTPS configuration to prevent DNS leaks.

pub struct DnsGuardConfig {
    pub doh_server: String,
    pub query_strategy: String,
    pub tag: String,
}

impl Default for DnsGuardConfig {
    fn default() -> Self {
        Self {
            doh_server: "https+local://1.1.1.1/dns-query".to_string(),
            query_strategy: "UseIP".to_string(),
            tag: "dns-out".to_string(),
        }
    }
}

// بخش dns کانفیگ xray-core را به‌صورت JSON می‌سازد.
// Builds the dns section of xray-core config as JSON.
pub fn build_dns_config_json(config: &DnsGuardConfig) -> String {
    let value = json!({
        "servers": [config.doh_server],
        "queryStrategy": config.query_strategy,
        "tag": config.tag,
    });
    value.to_string()
}

// یک RoutingRule JSON برای هدایت ترافیک DNS (پورت ۵۳) به outbound dns.
// A JSON RoutingRule to route DNS traffic (port 53) to the dns outbound.
pub fn build_dns_routing_rule_json(dns_tag: &str) -> String {
    let value = json!({
        "type": "field",
        "port": "53",
        "network": "udp,tcp",
        "outboundTag": dns_tag,
    });
    value.to_string()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn default_dns_config_contains_doh_server() {
        let config = DnsGuardConfig::default();
        let json_str = build_dns_config_json(&config);
        assert!(json_str.contains("1.1.1.1"));
        assert!(json_str.contains("UseIP"));
    }

    #[test]
    fn dns_routing_rule_targets_dns_tag() {
        let json_str = build_dns_routing_rule_json("dns-out");
        assert!(json_str.contains("dns-out"));
        assert!(json_str.contains("53"));
    }
}
