//! mobile-core: همان منطق تست‌شده‌ی engine-core (اتصال gRPC به xray-core،
//! ساخت outbound از روی VLESS+Reality، بررسی سلامت سرور، کانفیگ DNS-guard)
//! را — بدون هیچ پایتونی — از طریق uniffi برای کاتلین/اندروید صادر می‌کند.
//! هیچ منطقی اینجا تکرار یا بازنویسی نشده؛ این کریت فقط یک لایه‌ی نازک
//! تبدیل نوع (Rust ⇄ uniffi) روی توابع عمومی engine-core است.
//!
//! mobile-core: exports the exact same tested engine-core logic
//! (gRPC connection to xray-core, building a VLESS+Reality outbound,
//! server health checks, DNS-guard config) — with no Python involved —
//! to Kotlin/Android via uniffi. Nothing is duplicated or reimplemented
//! here; this crate is only a thin type-conversion (Rust ⇄ uniffi) layer
//! over engine-core's public functions.

// نکته: نام کریت engine-core در اینجا `_engine_core` است، نه
// `engine_core` — چون خودِ engine-core/Cargo.toml یک [lib] name صریح
// دارد (`_engine_core`, همان چیزی که پایتون هم به‌عنوان
// `bimarz._engine_core` ایمپورت می‌کند)، و کارگو همیشه از همان [lib]
// name به‌جای نام پکیج برای extern crate استفاده می‌کند.
//
// Note: the engine-core crate's name here is `_engine_core`, not
// `engine_core` — because engine-core/Cargo.toml has an explicit [lib]
// name (`_engine_core`, the same name Python imports as
// `bimarz._engine_core`), and Cargo always uses that [lib] name, not the
// package name, for the extern crate identifier.
use _engine_core::dns_guard;
use _engine_core::errors::EngineError;
use _engine_core::grpc_client::EngineClient;
use _engine_core::healthcheck;
use _engine_core::vless_builder::{self, VlessRealityParams};

uniffi::setup_scaffolding!();

/// خانواده‌ی خطاهای قابل‌عبور به کاتلین. هر یک از EngineError واقعی
/// engine-core نگاشت می‌شود؛ متن پیام همان‌جا حفظ می‌شود، فقط انواع
/// غیر-uniffi-friendly (مثل tonic::Status) به رشته تبدیل می‌شوند.
///
/// The error family exposed to Kotlin. Each variant maps from a real
/// engine-core EngineError; the message text is preserved, only the
/// non-uniffi-friendly inner types (like tonic::Status) are turned into
/// strings.
#[derive(Debug, thiserror::Error, uniffi::Error)]
pub enum MobileError {
    #[error("failed to connect to xray-core gRPC endpoint at {endpoint}: {detail}")]
    GrpcConnect { endpoint: String, detail: String },

    #[error("xray-core gRPC call '{method}' failed: {detail}")]
    GrpcCall { method: String, detail: String },

    #[error("invalid outbound configuration: {reason}")]
    InvalidOutboundConfig { reason: String },

    #[error("outbound with tag '{tag}' was not found")]
    OutboundNotFound { tag: String },

    #[error("xray-core process is not running (expected pid {pid} to be alive)")]
    ProcessNotRunning { pid: u32 },

    #[error("io error: {detail}")]
    Io { detail: String },
}

impl From<EngineError> for MobileError {
    fn from(err: EngineError) -> Self {
        match err {
            EngineError::GrpcConnect { endpoint, source } => MobileError::GrpcConnect {
                endpoint,
                detail: source.to_string(),
            },
            EngineError::GrpcCall { method, status } => MobileError::GrpcCall {
                method: method.to_string(),
                detail: status.to_string(),
            },
            EngineError::InvalidOutboundConfig { reason } => {
                MobileError::InvalidOutboundConfig { reason }
            }
            EngineError::OutboundNotFound { tag } => MobileError::OutboundNotFound { tag },
            EngineError::ProcessNotRunning { pid } => MobileError::ProcessNotRunning { pid },
            EngineError::Io(source) => MobileError::Io {
                detail: source.to_string(),
            },
        }
    }
}

/// معادل uniffi-friendly همان VlessRealityParams خودِ engine-core —
/// عمداً یک struct جدا، تا امضای داخلی engine-core آزاد باشد تغییر کند
/// بدون اینکه مستقیماً روی ABI کاتلین اثر بگذارد.
///
/// A uniffi-friendly mirror of engine-core's own VlessRealityParams —
/// deliberately a separate struct, so engine-core's internal signature
/// stays free to change without directly touching the Kotlin ABI.
#[derive(Debug, Clone, uniffi::Record)]
pub struct VlessRealityProfile {
    pub tag: String,
    pub uuid: String,
    pub flow: String,
    pub address: String,
    pub port: u32,
    pub network: String,
    pub sni: String,
    pub fingerprint: String,
    pub public_key_b64: String,
    pub short_id_hex: String,
    pub spider_x: String,
}

impl From<VlessRealityProfile> for VlessRealityParams {
    fn from(p: VlessRealityProfile) -> Self {
        VlessRealityParams {
            tag: p.tag,
            uuid: p.uuid,
            flow: p.flow,
            address: p.address,
            port: p.port,
            network: p.network,
            sni: p.sni,
            fingerprint: p.fingerprint,
            public_key_b64: p.public_key_b64,
            short_id_hex: p.short_id_hex,
            spider_x: p.spider_x,
        }
    }
}

/// آمار ترافیک یک outbound، معادل uniffi-friendly همان OutboundStats.
/// Traffic stats for one outbound, a uniffi-friendly mirror of OutboundStats.
#[derive(Debug, Clone, uniffi::Record)]
pub struct MobileOutboundStats {
    pub tag: String,
    pub uplink_bytes: i64,
    pub downlink_bytes: i64,
}

/// نتیجه‌ی یک تست سلامت TCP خام، معادل uniffi-friendly HealthCheckOutcome.
/// The outcome of a raw TCP health check, a uniffi-friendly mirror of
/// HealthCheckOutcome.
#[derive(Debug, Clone, uniffi::Record)]
pub struct MobileHealthOutcome {
    pub reachable: bool,
    pub latency_ms: Option<f64>,
    pub error_message: Option<String>,
}

/// کلاینت اصلی که کاتلین با آن کار می‌کند. یک handle سبک به همان
/// EngineClient واقعی engine-core نگه می‌دارد — Clone آن ارزان است
/// (فقط یک هندل کانال HTTP/2 مشترک کپی می‌شود)، دقیقاً همان الگویی که
/// لایه‌ی pyo3 (`PyEngineClient` در engine-core/src/lib.rs) هم استفاده
/// می‌کند.
///
/// The main client Kotlin works with. Holds a lightweight handle to the
/// same real engine-core EngineClient — cloning it is cheap (it just
/// copies a shared HTTP/2 channel handle), the exact same pattern the
/// pyo3 layer (`PyEngineClient` in engine-core/src/lib.rs) already uses.
#[derive(uniffi::Object)]
pub struct MobileEngineClient {
    inner: EngineClient,
}

#[uniffi::export(async_runtime = "tokio")]
impl MobileEngineClient {
    /// یک اتصال جدید به آدرس gRPC محلی xray-core برقرار می‌کند، مثلاً
    /// "http://127.0.0.1:10085".
    ///
    /// Establishes a new connection to xray-core's local gRPC address,
    /// e.g. "http://127.0.0.1:10085".
    #[uniffi::constructor]
    pub async fn connect(endpoint: String) -> Result<std::sync::Arc<Self>, MobileError> {
        let inner = EngineClient::connect(endpoint).await?;
        Ok(std::sync::Arc::new(Self { inner }))
    }

    /// یک outbound جدید VLESS+Reality+Vision اضافه می‌کند.
    /// Adds a new VLESS+Reality+Vision outbound.
    pub async fn add_vless_reality_outbound(
        &self,
        profile: VlessRealityProfile,
    ) -> Result<(), MobileError> {
        let mut client = self.inner.clone();
        let outbound = vless_builder::build_vless_reality_outbound(profile.into())?;
        client.add_outbound(outbound).await?;
        Ok(())
    }

    /// یک outbound موجود را با تگش حذف می‌کند.
    /// Removes an existing outbound by its tag.
    pub async fn remove_outbound(&self, tag: String) -> Result<(), MobileError> {
        let mut client = self.inner.clone();
        client.remove_outbound(&tag).await?;
        Ok(())
    }

    /// آمار ترافیک آپلود/دانلود یک outbound را می‌خواند.
    /// Reads uplink/downlink traffic stats for an outbound.
    pub async fn get_outbound_stats(
        &self,
        tag: String,
    ) -> Result<MobileOutboundStats, MobileError> {
        let mut client = self.inner.clone();
        let stats = client.get_outbound_stats(&tag).await?;
        Ok(MobileOutboundStats {
            tag: stats.tag,
            uplink_bytes: stats.uplink_bytes,
            downlink_bytes: stats.downlink_bytes,
        })
    }
}

/// یک سرور را با اتصال TCP خام (نه از طریق تونل) تست می‌کند — هرگز panic
/// نمی‌کند، همیشه یک نتیجه برمی‌گرداند.
///
/// Checks a server with a raw TCP connection (not through the tunnel) —
/// never panics, always returns an outcome.
#[uniffi::export(async_runtime = "tokio")]
pub async fn check_server_health(
    address: String,
    port: u16,
    timeout_ms: u64,
) -> MobileHealthOutcome {
    let outcome = healthcheck::check_tcp_reachable(&address, port, timeout_ms).await;
    MobileHealthOutcome {
        reachable: outcome.reachable,
        latency_ms: outcome.latency_ms,
        error_message: outcome.error_message,
    }
}

/// چند سرور را موازی تست می‌کند. ورودی: لیستی از (profile_id, address, port).
/// خروجی: لیستی هم‌طول از (profile_id, نتیجه).
///
/// Checks several servers in parallel. Input: a list of
/// (profile_id, address, port). Output: an equal-length list of
/// (profile_id, outcome).
#[derive(Debug, Clone, uniffi::Record)]
pub struct HealthCheckTarget {
    pub profile_id: String,
    pub address: String,
    pub port: u16,
}

#[derive(Debug, Clone, uniffi::Record)]
pub struct HealthCheckResult {
    pub profile_id: String,
    pub outcome: MobileHealthOutcome,
}

#[uniffi::export(async_runtime = "tokio")]
pub async fn check_servers_health(
    targets: Vec<HealthCheckTarget>,
    timeout_ms: u64,
) -> Vec<HealthCheckResult> {
    let raw_targets = targets
        .into_iter()
        .map(|t| (t.profile_id, t.address, t.port))
        .collect();
    healthcheck::check_many(raw_targets, timeout_ms)
        .await
        .into_iter()
        .map(|(profile_id, outcome)| HealthCheckResult {
            profile_id,
            outcome: MobileHealthOutcome {
                reachable: outcome.reachable,
                latency_ms: outcome.latency_ms,
                error_message: outcome.error_message,
            },
        })
        .collect()
}

/// بخش dns کانفیگ xray-core را به‌صورت JSON برمی‌گرداند (DNS-over-HTTPS،
/// برای جلوگیری از نشت DNS) — همان منطقی که دسکتاپ هم استفاده می‌کند.
///
/// Returns the dns section of xray-core config as JSON (DNS-over-HTTPS,
/// to prevent DNS leaks) — the exact same logic desktop uses.
#[uniffi::export]
pub fn build_dns_guard_config_json() -> String {
    let config = dns_guard::DnsGuardConfig::default();
    dns_guard::build_dns_config_json(&config)
}

/// یک RoutingRule JSON برای هدایت ترافیک DNS به outbound dns برمی‌گرداند.
/// Returns a RoutingRule JSON that routes DNS traffic to the dns outbound.
#[uniffi::export]
pub fn build_dns_routing_rule_json() -> String {
    dns_guard::build_dns_routing_rule_json("dns-out")
}

/// نسخه‌ی پین‌شده‌ی proto مربوط به Xray-core که این اکستنشن با آن ساخته
/// شده — همان مقداری که در دسکتاپ هم `doctor` گزارش می‌دهد.
///
/// The pinned Xray-core proto version this extension was built against —
/// the same value desktop's `doctor` reports too.
#[uniffi::export]
pub fn xray_proto_version() -> String {
    _engine_core::xray_proto_version_str().to_string()
}
