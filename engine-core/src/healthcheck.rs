// این ماژول تست سلامت شبکه را مستقیماً روی خودِ سرور (نه از طریق تونل
// xray-core) انجام می‌دهد — یک اتصال TCP خام به آدرس:پورت سرور می‌زند و
// زمان برقراری اتصال را اندازه می‌گیرد. این کار عمداً مستقل از
// EngineClient/gRPC است چون نیازی به xray-core در حال اجرا ندارد؛ فقط
// می‌خواهد بداند خودِ سرور از این شبکه قابل‌دسترسی هست یا نه.
//
// This module performs a network health check directly against the
// server itself (not through the xray-core tunnel) — it opens a raw TCP
// connection to the server's address:port and measures how long that
// takes. It is deliberately independent of EngineClient/gRPC because it
// does not need a running xray-core; it only needs to know whether the
// server itself is reachable from this network.

use std::time::{Duration, Instant};
use tokio::net::TcpStream;
use tokio::time::timeout;

/// نتیجه‌ی یک تست سلامت روی یک سرور.
/// The result of a single health check against one server.
pub struct HealthCheckOutcome {
    pub reachable: bool,
    pub latency_ms: Option<f64>,
    pub error_message: Option<String>,
}

/// یک تلاش برای اتصال TCP خام به address:port انجام می‌دهد و زمان صرف‌شده
/// را اندازه می‌گیرد. هرگز panic نمی‌کند و هرگز پروسه را نمی‌کشد — فقط یک
/// HealthCheckOutcome برمی‌گرداند، طبق قانون همیشگی این پروژه.
///
/// Attempts a raw TCP connection to address:port and measures the time
/// taken. Never panics and never kills the process — always returns a
/// HealthCheckOutcome, per this project's standing rule.
pub async fn check_tcp_reachable(address: &str, port: u16, timeout_ms: u64) -> HealthCheckOutcome {
    let target = format!("{address}:{port}");
    let start = Instant::now();

    match timeout(Duration::from_millis(timeout_ms), TcpStream::connect(&target)).await {
        Ok(Ok(_stream)) => {
            let elapsed_ms = start.elapsed().as_secs_f64() * 1000.0;
            HealthCheckOutcome {
                reachable: true,
                latency_ms: Some(elapsed_ms),
                error_message: None,
            }
        }
        Ok(Err(io_error)) => HealthCheckOutcome {
            reachable: false,
            latency_ms: None,
            error_message: Some(io_error.to_string()),
        },
        Err(_elapsed) => HealthCheckOutcome {
            reachable: false,
            latency_ms: None,
            error_message: Some(format!("connection timed out after {timeout_ms}ms")),
        },
    }
}

/// چند سرور را به‌صورت موازی (نه یکی‌یکی) تست می‌کند — دلیل اصلی اینکه
/// این بخش در Rust نوشته شده، نه پایتون: تست موازی صدها سرور بدون فشار
/// زیاد به CPU/باتری.
///
/// Checks several servers in parallel (not one by one) — the main reason
/// this part is written in Rust rather than Python: parallel-checking
/// many servers without heavy CPU/battery cost.
pub async fn check_many(
    targets: Vec<(String, String, u16)>,
    timeout_ms: u64,
) -> Vec<(String, HealthCheckOutcome)> {
    let mut join_set = tokio::task::JoinSet::new();

    for (profile_id, address, port) in targets {
        join_set.spawn(async move {
            let outcome = check_tcp_reachable(&address, port, timeout_ms).await;
            (profile_id, outcome)
        });
    }

    let mut results = Vec::new();
    while let Some(joined) = join_set.join_next().await {
        // اگر یک task به هر دلیلی panic کند (که نباید، ولی احتیاط)، آن
        // یکی نتیجه را نادیده می‌گیریم نه اینکه کل دسته را خراب کنیم.
        // If a task somehow panics (it shouldn't, but as a precaution),
        // that one result is skipped rather than corrupting the whole
        // batch.
        if let Ok(pair) = joined {
            results.push(pair);
        }
    }
    results
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn unreachable_port_is_reported_as_not_reachable() {
        // پورت 1 روی لوپ‌بک تقریباً همیشه چیزی گوش نمی‌دهد و باید سریع رد شود.
        // Port 1 on loopback almost never has anything listening and
        // should fail fast.
        let outcome = check_tcp_reachable("127.0.0.1", 1, 500).await;
        assert!(!outcome.reachable);
        assert!(outcome.latency_ms.is_none());
        assert!(outcome.error_message.is_some());
    }

    #[tokio::test]
    async fn check_many_returns_one_result_per_target() {
        let targets = vec![
            ("a".to_string(), "127.0.0.1".to_string(), 1u16),
            ("b".to_string(), "127.0.0.1".to_string(), 2u16),
        ];
        let results = check_many(targets, 500).await;
        assert_eq!(results.len(), 2);
    }
}
