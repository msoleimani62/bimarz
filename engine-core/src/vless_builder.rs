// این ماژول یک ServerProfile outbound configuration (که فاز ۲ در پایتون از یک لینک VLESS
// می‌سازد) را به یک OutboundHandlerConfig واقعی و کامل xray-core تبدیل
// می‌کند — دقیقاً همان پیامی که add_outbound در grpc_client.rs نیاز دارد.
//
// This module converts a ServerProfile outbound configuration (built by phase 2's Python
// layer from a VLESS link) into a real, complete xray-core
// OutboundHandlerConfig — exactly the message add_outbound in
// grpc_client.rs needs.

use crate::errors::{EngineError, EngineResult};
use crate::pb::xray;
use prost::Message;

use xray::app::proxyman::SenderConfig;
use xray::common::protocol::{ServerEndpoint, User};
use xray::common::serial::TypedMessage;
use xray::core::OutboundHandlerConfig;
use xray::proxy::vless::outbound::Config as VlessOutboundConfig;
use xray::proxy::vless::Account as VlessAccount;
use xray::transport::internet::reality::Config as RealityConfig;
use xray::transport::internet::StreamConfig;

// نام‌های کاملاً واجد شرایط پیام‌های proto، دقیقاً همان‌طور که در فیلد
// TypedMessage.type استفاده می‌شوند (از proto.MessageName در سمت Go
// می‌آید — همان نام package.Message که در فایل‌های .proto دیده‌ایم).
//
// Fully-qualified proto message names, exactly as used in the
// TypedMessage.type field (comes from proto.MessageName on the Go side —
// the same package.Message name we have seen in the .proto files).
const TYPE_VLESS_OUTBOUND_CONFIG: &str = "xray.proxy.vless.outbound.Config";
const TYPE_VLESS_ACCOUNT: &str = "xray.proxy.vless.Account";
const TYPE_REALITY_CONFIG: &str = "xray.transport.internet.reality.Config";
const TYPE_SENDER_CONFIG: &str = "xray.app.proxyman.SenderConfig";

/// تمام مقادیر خام (رشته‌ای) لازم برای ساختن یک outbound کامل
/// VLESS+Reality+Vision. این ساختار پلی است بین ServerProfile outbound configuration
/// پایتونی (فاز ۲) و پیام‌های تایپ‌شده‌ی protobuf.
///
/// All raw (string-form) values needed to build a complete
/// VLESS+Reality+Vision outbound. This struct is the bridge between
/// Python's ServerProfile outbound configuration (phase 2) and the typed protobuf
/// messages.
pub struct VlessRealityParams {
    pub tag: String,
    pub uuid: String,
    pub flow: String,
    pub address: String,
    pub port: u32,
    pub network: String,
    pub sni: String,
    pub fingerprint: String,
    /// کلید عمومی Reality، به همان فرمت base64url بدون padding که در
    /// پارامتر `pbk` لینک‌های VLESS دیده می‌شود.
    /// Reality public key, in the same unpadded base64url form seen in a
    /// VLESS link's `pbk` parameter.
    pub public_key_b64: String,
    /// شناسه‌ی کوتاه Reality، به‌صورت رشته‌ی hex (پارامتر `sid`).
    /// Reality short id, as a hex string (the `sid` parameter).
    pub short_id_hex: String,
    pub spider_x: String,
}

fn decode_reality_public_key(value: &str) -> EngineResult<Vec<u8>> {
    use base64::engine::general_purpose::URL_SAFE_NO_PAD;
    use base64::Engine;
    URL_SAFE_NO_PAD
        .decode(value)
        .map_err(|e| EngineError::InvalidOutboundConfig {
            reason: format!("invalid Reality public key (expected unpadded base64url): {e}"),
        })
}

fn decode_short_id(value: &str) -> EngineResult<Vec<u8>> {
    if value.is_empty() {
        return Ok(Vec::new());
    }
    hex::decode(value).map_err(|e| EngineError::InvalidOutboundConfig {
        reason: format!("invalid Reality short_id (expected hex string): {e}"),
    })
}

/// یک IpOrDomain واقعی می‌سازد: اگر رشته یک IP معتبر (v4 یا v6) باشد از
/// نوع Ip استفاده می‌کند، در غیر این صورت آن را یک نام دامنه در نظر
/// می‌گیرد. دقیقاً همان دو حالتی که xray.common.net.IpOrDomain پشتیبانی
/// می‌کند.
///
/// Builds a real IpOrDomain: if the string is a valid IP (v4 or v6) it
/// uses the Ip variant, otherwise treats it as a domain name — exactly
/// the two cases xray.common.net.IpOrDomain supports.
fn build_ip_or_domain(address: &str) -> EngineResult<xray::common::net::IpOrDomain> {
    use std::net::IpAddr;
    use xray::common::net::ip_or_domain::Address as IpOrDomainAddress;
    use xray::common::net::IpOrDomain;

    let variant = match address.parse::<IpAddr>() {
        Ok(IpAddr::V4(v4)) => IpOrDomainAddress::Ip(v4.octets().to_vec()),
        Ok(IpAddr::V6(v6)) => IpOrDomainAddress::Ip(v6.octets().to_vec()),
        Err(_) => IpOrDomainAddress::Domain(address.to_string()),
    };

    Ok(IpOrDomain {
        address: Some(variant),
    })
}

// قرارداد API: ورودی‌های نامعتبر قبل از ساختن protobuf رد می‌شوند.
// API contract: invalid inputs are rejected before building protobuf.
fn validate_params(params: &VlessRealityParams) -> EngineResult<()> {
    if params.tag.is_empty() {
        return Err(EngineError::InvalidOutboundConfig {
            reason: "outbound tag must not be empty".to_string(),
        });
    }
    if params.uuid.is_empty() {
        return Err(EngineError::InvalidOutboundConfig {
            reason: "uuid must not be empty".to_string(),
        });
    }
    if params.address.is_empty() {
        return Err(EngineError::InvalidOutboundConfig {
            reason: "address must not be empty".to_string(),
        });
    }
    if params.port == 0 || params.port > 65535 {
        return Err(EngineError::InvalidOutboundConfig {
            reason: format!("port must be between 1 and 65535, got {}", params.port),
        });
    }
    Ok(())
}

/// یک OutboundHandlerConfig کامل و آماده‌ی ارسال به add_outbound می‌سازد.
/// Builds a complete OutboundHandlerConfig, ready to send to add_outbound.
pub fn build_vless_reality_outbound(
    params: VlessRealityParams,
) -> EngineResult<OutboundHandlerConfig> {
    validate_params(&params)?;

    let public_key = decode_reality_public_key(&params.public_key_b64)?;
    let short_id = decode_short_id(&params.short_id_hex)?;

    let reality_config = RealityConfig {
        show: false,
        dest: String::new(),
        r#type: String::new(),
        xver: 0,
        server_names: Vec::new(),
        private_key: Vec::new(),
        min_client_ver: Vec::new(),
        max_client_ver: Vec::new(),
        max_time_diff: 0,
        short_ids: Vec::new(),
        fingerprint: params.fingerprint,
        server_name: params.sni,
        public_key,
        short_id,
        spider_x: params.spider_x,
        spider_y: Vec::new(),
        master_key_log: String::new(),
    };

    #[allow(deprecated)]
    let stream_config = StreamConfig {
        // فیلد deprecated و کد enum قدیمی؛ همیشه از protocol_name (رشته‌ای)
        // استفاده می‌کنیم، پس این را صفر می‌گذاریم.
        // Deprecated enum field; we always use protocol_name (string-based)
        // instead, so this is left at zero.
        protocol: 0,
        protocol_name: params.network,
        transport_settings: Vec::new(),
        security_type: TYPE_REALITY_CONFIG.to_string(),
        security_settings: vec![TypedMessage {
            r#type: TYPE_REALITY_CONFIG.to_string(),
            value: reality_config.encode_to_vec(),
        }],
        socket_settings: None,
    };

    // sender_settings باید یک SenderConfig باشد (که خودش StreamConfig را
    // در فیلد stream_settings نگه می‌دارد) — نه مستقیم یک StreamConfig.
    // این لایه‌ی میانی را از خروجی واقعی xray.app.proxyman.rs تایید کردیم،
    // بعد از اینکه یک بار بدون آن با خطای gRPC واقعی مواجه شدیم
    // ("settings is not SenderConfig").
    //
    // sender_settings must be a SenderConfig (which itself holds the
    // StreamConfig in its stream_settings field) — not a StreamConfig
    // directly. This middle layer was confirmed from the real
    // xray.app.proxyman.rs output, after hitting a real gRPC error
    // without it ("settings is not SenderConfig").
    let sender_config = SenderConfig {
        via: None,
        stream_settings: Some(stream_config),
        proxy_settings: None,
        multiplex_settings: None,
        via_cidr: String::new(),
    };

    let vless_account = VlessAccount {
        id: params.uuid,
        flow: params.flow,
        encryption: "none".to_string(),
    };

    let user = User {
        level: 0,
        email: String::new(),
        account: Some(TypedMessage {
            r#type: TYPE_VLESS_ACCOUNT.to_string(),
            value: vless_account.encode_to_vec(),
        }),
    };

    let server_endpoint = ServerEndpoint {
        address: Some(build_ip_or_domain(&params.address)?),
        port: params.port,
        user: vec![user],
    };

    let vless_outbound_config = VlessOutboundConfig {
        vnext: vec![server_endpoint],
    };

    Ok(OutboundHandlerConfig {
        tag: params.tag,
        sender_settings: Some(TypedMessage {
            r#type: TYPE_SENDER_CONFIG.to_string(),
            value: sender_config.encode_to_vec(),
        }),
        proxy_settings: Some(TypedMessage {
            r#type: TYPE_VLESS_OUTBOUND_CONFIG.to_string(),
            value: vless_outbound_config.encode_to_vec(),
        }),
        expire: 0,
        comment: String::new(),
    })
}

// این تست‌ها هیچ نیازی به xray-core در حال اجرا یا شبکه ندارند — فقط
// خروجی خالص build_vless_reality_outbound را در برابر مقادیر واقعی
// proto (که در گفتگوی توسعه‌ی این پروژه دستی تایید شدند) بررسی می‌کنند.
// اجرا با: cargo test --manifest-path engine-core/Cargo.toml
//
// These tests need no running xray-core and no network — they only check
// build_vless_reality_outbound's pure output against the real proto
// values (manually confirmed during this project's development). Run
// with: cargo test --manifest-path engine-core/Cargo.toml
#[cfg(test)]
mod tests {
    use super::*;

    fn sample_params() -> VlessRealityParams {
        VlessRealityParams {
            tag: "test-tag".to_string(),
            uuid: "8f9a3c2e-1234-4a5b-8c9d-0e1f2a3b4c5d".to_string(),
            flow: "xtls-rprx-vision".to_string(),
            address: "example.com".to_string(),
            port: 443,
            network: "tcp".to_string(),
            sni: "www.microsoft.com".to_string(),
            fingerprint: "chrome".to_string(),
            // base64url (no padding) encoding of 32 zero bytes — a
            // syntactically valid but not cryptographically real key,
            // sufficient for testing the encode/decode path.
            public_key_b64: "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA".to_string(),
            short_id_hex: "a1b2c3".to_string(),
            spider_x: "/".to_string(),
        }
    }

    #[test]
    fn builds_outbound_with_the_given_tag() {
        let outbound = build_vless_reality_outbound(sample_params()).unwrap();
        assert_eq!(outbound.tag, "test-tag");
    }

    #[test]
    fn sender_settings_type_is_the_correct_fully_qualified_name() {
        let outbound = build_vless_reality_outbound(sample_params()).unwrap();
        let sender_settings = outbound.sender_settings.unwrap();
        assert_eq!(sender_settings.r#type, "xray.app.proxyman.SenderConfig");
    }

    #[test]
    fn proxy_settings_type_is_the_correct_fully_qualified_name() {
        let outbound = build_vless_reality_outbound(sample_params()).unwrap();
        let proxy_settings = outbound.proxy_settings.unwrap();
        assert_eq!(proxy_settings.r#type, "xray.proxy.vless.outbound.Config");
    }

    #[test]
    fn sender_settings_decodes_to_a_sender_config_wrapping_a_stream_config() {
        let outbound = build_vless_reality_outbound(sample_params()).unwrap();
        let sender_settings = outbound.sender_settings.unwrap();
        let sender_config = SenderConfig::decode(sender_settings.value.as_slice()).unwrap();

        // این دقیقاً همون لایه‌ی میانی است که فراموش کردنش باعث خطای
        // واقعی gRPC ("settings is not SenderConfig") شد؛ این تست
        // مطمئن می‌شود دیگر هرگز حذف نشود.
        // This is exactly the middle layer whose omission caused the real
        // gRPC error ("settings is not SenderConfig"); this test ensures
        // it is never removed again.
        let stream_config = sender_config.stream_settings.unwrap();
        assert_eq!(stream_config.protocol_name, "tcp");
        assert_eq!(
            stream_config.security_type,
            "xray.transport.internet.reality.Config"
        );
    }

    #[test]
    fn reality_config_carries_the_decoded_public_key_bytes() {
        let outbound = build_vless_reality_outbound(sample_params()).unwrap();
        let sender_settings = outbound.sender_settings.unwrap();
        let sender_config = SenderConfig::decode(sender_settings.value.as_slice()).unwrap();
        let stream_config = sender_config.stream_settings.unwrap();
        let reality_settings = &stream_config.security_settings[0];
        let reality_config = RealityConfig::decode(reality_settings.value.as_slice()).unwrap();

        assert_eq!(reality_config.public_key, vec![0u8; 32]);
        assert_eq!(reality_config.server_name, "www.microsoft.com");
        assert_eq!(reality_config.fingerprint, "chrome");
        assert_eq!(reality_config.spider_x, "/");
        assert_eq!(reality_config.short_id, vec![0xa1, 0xb2, 0xc3]);
    }

    #[test]
    fn proxy_settings_decodes_to_the_vless_account_with_correct_fields() {
        let outbound = build_vless_reality_outbound(sample_params()).unwrap();
        let proxy_settings = outbound.proxy_settings.unwrap();
        let vless_outbound = VlessOutboundConfig::decode(proxy_settings.value.as_slice()).unwrap();

        assert_eq!(vless_outbound.vnext.len(), 1);
        let endpoint = &vless_outbound.vnext[0];
        assert_eq!(endpoint.port, 443);
        assert_eq!(endpoint.user.len(), 1);

        let account_message = endpoint.user[0].account.as_ref().unwrap();
        assert_eq!(account_message.r#type, "xray.proxy.vless.Account");
        let account = VlessAccount::decode(account_message.value.as_slice()).unwrap();
        assert_eq!(account.id, "8f9a3c2e-1234-4a5b-8c9d-0e1f2a3b4c5d");
        assert_eq!(account.flow, "xtls-rprx-vision");
        assert_eq!(account.encryption, "none");
    }

    #[test]
    fn domain_address_produces_the_domain_variant() {
        let mut params = sample_params();
        params.address = "my-server.example.com".to_string();
        let outbound = build_vless_reality_outbound(params).unwrap();
        let proxy_settings = outbound.proxy_settings.unwrap();
        let vless_outbound = VlessOutboundConfig::decode(proxy_settings.value.as_slice()).unwrap();
        let address = vless_outbound.vnext[0]
            .address
            .clone()
            .unwrap()
            .address
            .unwrap();

        match address {
            xray::common::net::ip_or_domain::Address::Domain(domain) => {
                assert_eq!(domain, "my-server.example.com");
            }
            xray::common::net::ip_or_domain::Address::Ip(_) => {
                panic!("expected a Domain variant, got an Ip variant");
            }
        }
    }

    #[test]
    fn ipv4_address_produces_the_ip_variant_with_four_bytes() {
        let mut params = sample_params();
        params.address = "1.2.3.4".to_string();
        let outbound = build_vless_reality_outbound(params).unwrap();
        let proxy_settings = outbound.proxy_settings.unwrap();
        let vless_outbound = VlessOutboundConfig::decode(proxy_settings.value.as_slice()).unwrap();
        let address = vless_outbound.vnext[0]
            .address
            .clone()
            .unwrap()
            .address
            .unwrap();

        match address {
            xray::common::net::ip_or_domain::Address::Ip(bytes) => {
                assert_eq!(bytes, vec![1, 2, 3, 4]);
            }
            xray::common::net::ip_or_domain::Address::Domain(_) => {
                panic!("expected an Ip variant, got a Domain variant");
            }
        }
    }

    #[test]
    fn ipv6_address_produces_the_ip_variant_with_sixteen_bytes() {
        let mut params = sample_params();
        params.address = "::1".to_string();
        let outbound = build_vless_reality_outbound(params).unwrap();
        let proxy_settings = outbound.proxy_settings.unwrap();
        let vless_outbound = VlessOutboundConfig::decode(proxy_settings.value.as_slice()).unwrap();
        let address = vless_outbound.vnext[0]
            .address
            .clone()
            .unwrap()
            .address
            .unwrap();

        match address {
            xray::common::net::ip_or_domain::Address::Ip(bytes) => {
                assert_eq!(bytes.len(), 16);
            }
            xray::common::net::ip_or_domain::Address::Domain(_) => {
                panic!("expected an Ip variant, got a Domain variant");
            }
        }
    }

    #[test]
    fn empty_short_id_produces_empty_bytes_not_an_error() {
        let mut params = sample_params();
        params.short_id_hex = String::new();
        let outbound = build_vless_reality_outbound(params).unwrap();
        let sender_settings = outbound.sender_settings.unwrap();
        let sender_config = SenderConfig::decode(sender_settings.value.as_slice()).unwrap();
        let stream_config = sender_config.stream_settings.unwrap();
        let reality_config =
            RealityConfig::decode(stream_config.security_settings[0].value.as_slice()).unwrap();

        assert_eq!(reality_config.short_id, Vec::<u8>::new());
    }

    #[test]
    fn invalid_public_key_is_rejected_with_a_clear_error() {
        let mut params = sample_params();
        params.public_key_b64 = "not valid base64url!!".to_string();
        let result = build_vless_reality_outbound(params);
        assert!(result.is_err());
        let message = result.unwrap_err().to_string();
        assert!(
            message.contains("Reality public key"),
            "unexpected error message: {message}"
        );
    }

    #[test]
    fn invalid_short_id_hex_is_rejected_with_a_clear_error() {
        let mut params = sample_params();
        params.short_id_hex = "not-hex-zz".to_string();
        let result = build_vless_reality_outbound(params);
        assert!(result.is_err());
        let message = result.unwrap_err().to_string();
        assert!(
            message.contains("short_id"),
            "unexpected error message: {message}"
        );
    }

    // تست‌های قرارداد API: ورودی نامعتبر باید رد شود.
    // API contract tests: invalid inputs must be rejected.
    #[test]
    fn empty_tag_is_rejected() {
        let mut params = sample_params();
        params.tag = String::new();
        let result = build_vless_reality_outbound(params);
        assert!(result.is_err());
        let msg = result.unwrap_err().to_string();
        assert!(msg.contains("tag"), "unexpected error: {msg}");
    }

    #[test]
    fn empty_uuid_is_rejected() {
        let mut params = sample_params();
        params.uuid = String::new();
        let result = build_vless_reality_outbound(params);
        assert!(result.is_err());
        let msg = result.unwrap_err().to_string();
        assert!(msg.contains("uuid"), "unexpected error: {msg}");
    }

    #[test]
    fn empty_address_is_rejected() {
        let mut params = sample_params();
        params.address = String::new();
        let result = build_vless_reality_outbound(params);
        assert!(result.is_err());
        let msg = result.unwrap_err().to_string();
        assert!(msg.contains("address"), "unexpected error: {msg}");
    }

    #[test]
    fn zero_port_is_rejected() {
        let mut params = sample_params();
        params.port = 0;
        let result = build_vless_reality_outbound(params);
        assert!(result.is_err());
        let msg = result.unwrap_err().to_string();
        assert!(msg.contains("port"), "unexpected error: {msg}");
    }

    #[test]
    fn port_too_high_is_rejected() {
        let mut params = sample_params();
        params.port = 65536;
        let result = build_vless_reality_outbound(params);
        assert!(result.is_err());
        let msg = result.unwrap_err().to_string();
        assert!(msg.contains("port"), "unexpected error: {msg}");
    }
}
