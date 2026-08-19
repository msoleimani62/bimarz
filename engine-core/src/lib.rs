//! engine-core: لایه‌ی Rust که مستقیماً با gRPC API باینری xray-core صحبت
//! می‌کند و به‌صورت یک ماژول پایتونی (`engine_core`) قابل import است.
//!
//! engine-core: the Rust layer that talks directly to xray-core's gRPC API,
//! exposed as an importable Python module (`engine_core`).

#![allow(clippy::useless_conversion)]

// این چهار ماژول از نسخه‌ی ۰.۲.۳ به بعد pub شده‌اند تا کریت جدید
// `mobile-core` (بایندینگ uniffi برای اندروید/کاتلین) بتواند دقیقاً همین
// منطق تست‌شده را دوباره استفاده کند، بدون کپی یا بازنویسی. `killswitch`
// عمداً private می‌ماند چون فقط روی iptables (لینوکس) معنا دارد — روی
// اندروید VPN kill-switch از طریق خودِ VpnService (تنظیم
// "block connections without VPN") انجام می‌شود.
//
// As of 0.2.3, these four modules are pub so the new `mobile-core` crate
// (the uniffi binding layer for Android/Kotlin) can reuse this exact,
// already-tested logic instead of copying or reimplementing it.
// `killswitch` stays private on purpose — it is meaningful only on
// iptables (Linux); on Android the VPN kill switch is handled by
// VpnService itself ("block connections without VPN").
pub mod dns_guard;
pub mod errors;
pub mod grpc_client;
pub mod healthcheck;
mod killswitch;
pub mod vless_builder;

mod pb {
    #![allow(dead_code)]
    #![allow(clippy::module_inception)]
    #![allow(clippy::doc_lazy_continuation)]
    include!(concat!(env!("OUT_DIR"), "/pb_tree.rs"));
}

// از این‌جا تا انتهای فایل، همه‌چیز مخصوص بایندینگ پایتون (pyo3) است و
// پشت feature اختیاری «python» قرار گرفته (پیش‌فرض روشن، پس رفتار
// `maturin develop`/دسکتاپ بدون هیچ تغییری دقیقاً مثل قبل کار می‌کند).
// دلیل: کریت جدید `mobile-core` (اندروید) به همین کریت engine-core به‌عنوان
// یک کتابخانه‌ی معمولی Rust وابسته است، بدون هیچ پایتونی؛ اگر pyo3
// همیشه اجباری می‌بود، cross-compile کردن برای اندروید تلاش می‌کرد یک
// مفسر پایتون برای هدف NDK پیدا کند که اصلاً وجود ندارد.
//
// From here to the end of the file, everything is specific to the Python
// binding (pyo3) and sits behind an optional "python" feature (on by
// default, so desktop `maturin develop` behaves exactly as before with no
// change at all). Reason: the new `mobile-core` crate (Android) depends on
// this same engine-core crate as a plain Rust library, with no Python
// involved at all; if pyo3 were always mandatory, cross-compiling for
// Android would try to locate a Python interpreter for the NDK target
// that simply does not exist.
#[cfg(feature = "python")]
use errors::EngineError;
#[cfg(feature = "python")]
use grpc_client::EngineClient;
#[cfg(feature = "python")]
use pyo3::exceptions::{PyConnectionError, PyRuntimeError};
#[cfg(feature = "python")]
use pyo3::prelude::*;
#[cfg(feature = "python")]
use pyo3::wrap_pyfunction;

#[cfg(feature = "python")]
impl From<EngineError> for PyErr {
    fn from(err: EngineError) -> PyErr {
        match err {
            EngineError::GrpcConnect { .. } => PyConnectionError::new_err(err.to_string()),
            err => PyRuntimeError::new_err(err.to_string()),
        }
    }
}

#[cfg(feature = "python")]
#[pyclass]
struct PyEngineClient {
    inner: EngineClient,
}

#[cfg(feature = "python")]
#[pymethods]
impl PyEngineClient {
    #[staticmethod]
    fn connect(py: Python<'_>, endpoint: String) -> PyResult<Bound<'_, PyAny>> {
        pyo3_async_runtimes::tokio::future_into_py(py, async move {
            let inner = EngineClient::connect(endpoint).await?;
            Ok(PyEngineClient { inner })
        })
    }

    #[allow(clippy::too_many_arguments)]
    fn add_vless_reality_outbound<'py>(
        &self,
        py: Python<'py>,
        tag: String,
        uuid: String,
        flow: String,
        address: String,
        port: u32,
        network: String,
        sni: String,
        fingerprint: String,
        public_key_b64: String,
        short_id_hex: String,
        spider_x: String,
    ) -> PyResult<Bound<'py, PyAny>> {
        let mut client = self.inner.clone();
        pyo3_async_runtimes::tokio::future_into_py(py, async move {
            let params = vless_builder::VlessRealityParams {
                tag,
                uuid,
                flow,
                address,
                port,
                network,
                sni,
                fingerprint,
                public_key_b64,
                short_id_hex,
                spider_x,
            };
            let outbound = vless_builder::build_vless_reality_outbound(params)?;
            client.add_outbound(outbound).await?;
            Ok(())
        })
    }

    fn remove_outbound<'py>(&self, py: Python<'py>, tag: String) -> PyResult<Bound<'py, PyAny>> {
        let mut client = self.inner.clone();
        pyo3_async_runtimes::tokio::future_into_py(py, async move {
            client.remove_outbound(&tag).await?;
            Ok(())
        })
    }

    fn get_outbound_stats<'py>(&self, py: Python<'py>, tag: String) -> PyResult<Bound<'py, PyAny>> {
        let mut client = self.inner.clone();
        pyo3_async_runtimes::tokio::future_into_py(py, async move {
            let stats = client.get_outbound_stats(&tag).await?;
            Ok((stats.tag, stats.uplink_bytes, stats.downlink_bytes))
        })
    }
}

#[cfg(feature = "python")]
#[pyfunction]
fn check_server_health(
    py: Python<'_>,
    address: String,
    port: u16,
    timeout_ms: u64,
) -> PyResult<Bound<'_, PyAny>> {
    pyo3_async_runtimes::tokio::future_into_py(py, async move {
        let outcome = healthcheck::check_tcp_reachable(&address, port, timeout_ms).await;
        Ok((outcome.reachable, outcome.latency_ms, outcome.error_message))
    })
}

#[cfg(feature = "python")]
#[pyfunction]
fn check_servers_health(
    py: Python<'_>,
    targets: Vec<(String, String, u16)>,
    timeout_ms: u64,
) -> PyResult<Bound<'_, PyAny>> {
    pyo3_async_runtimes::tokio::future_into_py(py, async move {
        let results = healthcheck::check_many(targets, timeout_ms).await;
        let py_results: Vec<(String, bool, Option<f64>, Option<String>)> = results
            .into_iter()
            .map(|(profile_id, outcome)| {
                (
                    profile_id,
                    outcome.reachable,
                    outcome.latency_ms,
                    outcome.error_message,
                )
            })
            .collect();
        Ok(py_results)
    })
}

#[cfg(feature = "python")]
#[pyfunction]
fn probe_kernel_killswitch_capability() -> bool {
    killswitch::probe_kernel_capability()
}

#[cfg(feature = "python")]
#[pyfunction]
#[pyo3(signature = (interface, xray_uid=None))]
fn apply_killswitch_rules(interface: String, xray_uid: Option<u32>) -> PyResult<()> {
    let ruleset = killswitch::build_killswitch_rules(&interface, xray_uid)
        .map_err(PyRuntimeError::new_err)?;
    let executor = killswitch::IptablesExecutor;
    killswitch::apply_ruleset(&ruleset, &executor).map_err(PyRuntimeError::new_err)
}

#[cfg(feature = "python")]
#[pyfunction]
#[pyo3(signature = (interface, xray_uid=None))]
fn remove_killswitch_rules(interface: String, xray_uid: Option<u32>) -> PyResult<()> {
    let ruleset = killswitch::build_killswitch_rules(&interface, xray_uid)
        .map_err(PyRuntimeError::new_err)?;
    let executor = killswitch::IptablesExecutor;
    killswitch::remove_ruleset(&ruleset, &executor).map_err(PyRuntimeError::new_err)
}

// نسخه‌ی پین‌شده‌ی proto مربوط به Xray-core که این اکستنشن با آن ساخته شده
// (توسط build.rs از xray-proto-pin.env تزریق می‌شود). doctor از آن برای
// هشدار ناهماهنگی proto/باینری استفاده می‌کند.
//
// تابع خالص pub جدا شده تا کریت `mobile-core` (بایندینگ uniffi برای
// اندروید) هم بدون تکرار همین `env!` بتواند از همان مقدار استفاده کند —
// چون `env!` در محل تعریف‌شدنش (همین کریت) resolve می‌شود، نه در کریتی
// که آن را صدا می‌زند.
//
// The pinned Xray-core proto version this extension was built against
// (injected by build.rs from xray-proto-pin.env). doctor uses it to warn
// about proto/binary mismatches.
//
// Split out as a plain pub function so the `mobile-core` crate (the
// Android uniffi binding layer) can reuse the same value without
// duplicating the `env!` call — `env!` resolves where it is written (this
// crate), not in whichever crate calls the function.
pub fn xray_proto_version_str() -> &'static str {
    env!("BIMARZ_XRAY_PROTO_TAG")
}

#[cfg(feature = "python")]
#[pyfunction]
fn xray_proto_version() -> String {
    xray_proto_version_str().to_string()
}

#[cfg(feature = "python")]
#[pyfunction]
fn build_dns_guard_config_json() -> String {
    let config = dns_guard::DnsGuardConfig::default();
    dns_guard::build_dns_config_json(&config)
}

#[cfg(feature = "python")]
#[pyfunction]
fn build_dns_routing_rule_json() -> String {
    dns_guard::build_dns_routing_rule_json("dns-out")
}

#[cfg(feature = "python")]
#[pymodule]
fn _engine_core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyEngineClient>()?;
    m.add_function(wrap_pyfunction!(check_server_health, m)?)?;
    m.add_function(wrap_pyfunction!(check_servers_health, m)?)?;
    m.add_function(wrap_pyfunction!(probe_kernel_killswitch_capability, m)?)?;
    m.add_function(wrap_pyfunction!(apply_killswitch_rules, m)?)?;
    m.add_function(wrap_pyfunction!(remove_killswitch_rules, m)?)?;
    m.add_function(wrap_pyfunction!(xray_proto_version, m)?)?;
    m.add_function(wrap_pyfunction!(build_dns_guard_config_json, m)?)?;
    m.add_function(wrap_pyfunction!(build_dns_routing_rule_json, m)?)?;
    Ok(())
}
