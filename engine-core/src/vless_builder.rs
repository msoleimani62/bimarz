// این ماژول یک VlessRealityOutbound (که فاز ۲ در پایتون از یک لینک VLESS
// می‌سازد) را به یک OutboundHandlerConfig واقعی و کامل xray-core تبدیل
// می‌کند — دقیقاً همان پیامی که add_outbound در grpc_client.rs نیاز دارد.
//
// This module converts a VlessRealityOutbound (built by phase 2's Python
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
/// VLESS+Reality+Vision. این ساختار پلی است بین VlessRealityOutbound
/// پایتونی (فاز ۲) و پیام‌های تایپ‌شده‌ی protobuf.
///
/// All raw (string-form) values needed to build a complete
/// VLESS+Reality+Vision outbound. This struct is the bridge between
/// Python's VlessRealityOutbound (phase 2) and the typed protobuf
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

/// یک OutboundHandlerConfig کامل و آماده‌ی ارسال به add_outbound می‌سازد.
/// Builds a complete OutboundHandlerConfig, ready to send to add_outbound.
pub fn build_vless_reality_outbound(params: VlessRealityParams) -> EngineResult<OutboundHandlerConfig> {
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
