//! engine-core: لایه‌ی Rust که مستقیماً با gRPC API باینری xray-core صحبت
//! می‌کند و به‌صورت یک ماژول پایتونی (`engine_core`) قابل import است.
//!
//! engine-core: the Rust layer that talks directly to xray-core's gRPC API,
//! exposed as an importable Python module (`engine_core`).

mod errors;
mod grpc_client;
mod healthcheck;
mod vless_builder;
mod killswitch;
mod dns_guard;

mod pb {
    include!(concat!(env!("OUT_DIR"), "/pb_tree.rs"));
}

use errors::EngineError;
use grpc_client::EngineClient;
use pyo3::exceptions::PyRuntimeError;
use pyo3::prelude::*;
use pyo3::wrap_pyfunction;

impl From<EngineError> for PyErr {
    fn from(err: EngineError) -> PyErr {
        PyRuntimeError::new_err(err.to_string())
    }
}

#[pyclass]
struct PyEngineClient {
    inner: EngineClient,
}

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

    fn get_outbound_stats<'py>(
        &self,
        py: Python<'py>,
        tag: String,
    ) -> PyResult<Bound<'py, PyAny>> {
        let mut client = self.inner.clone();
        pyo3_async_runtimes::tokio::future_into_py(py, async move {
            let stats = client.get_outbound_stats(&tag).await?;
            Ok((stats.tag, stats.uplink_bytes, stats.downlink_bytes))
        })
    }
}

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
                (profile_id, outcome.reachable, outcome.latency_ms, outcome.error_message)
            })
            .collect();
        Ok(py_results)
    })
}

#[pyfunction]
fn probe_kernel_killswitch_capability() -> bool {
    killswitch::probe_kernel_capability()
}

#[pyfunction]
#[pyo3(signature = (interface, xray_uid=None))]
fn apply_killswitch_rules(interface: String, xray_uid: Option<u32>) -> PyResult<()> {
    let ruleset = killswitch::build_killswitch_rules(&interface, xray_uid)
        .map_err(PyRuntimeError::new_err)?;
    let executor = killswitch::IptablesExecutor;
    killswitch::apply_ruleset(&ruleset, &executor)
        .map_err(PyRuntimeError::new_err)
}

#[pyfunction]
#[pyo3(signature = (interface, xray_uid=None))]
fn remove_killswitch_rules(interface: String, xray_uid: Option<u32>) -> PyResult<()> {
    let ruleset = killswitch::build_killswitch_rules(&interface, xray_uid)
        .map_err(PyRuntimeError::new_err)?;
    let executor = killswitch::IptablesExecutor;
    killswitch::remove_ruleset(&ruleset, &executor)
        .map_err(PyRuntimeError::new_err)
}

#[pyfunction]
fn build_dns_guard_config_json() -> String {
    let config = dns_guard::DnsGuardConfig::default();
    dns_guard::build_dns_config_json(&config)
}

#[pyfunction]
fn build_dns_routing_rule_json() -> String {
    dns_guard::build_dns_routing_rule_json("dns-out")
}

#[pymodule]
fn _engine_core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyEngineClient>()?;
    m.add_function(wrap_pyfunction!(check_server_health, m)?)?;
    m.add_function(wrap_pyfunction!(check_servers_health, m)?)?;
    m.add_function(wrap_pyfunction!(probe_kernel_killswitch_capability, m)?)?;
    m.add_function(wrap_pyfunction!(apply_killswitch_rules, m)?)?;
    m.add_function(wrap_pyfunction!(remove_killswitch_rules, m)?)?;
    m.add_function(wrap_pyfunction!(build_dns_guard_config_json, m)?)?;
    m.add_function(wrap_pyfunction!(build_dns_routing_rule_json, m)?)?;
    Ok(())
}
