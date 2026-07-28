use thiserror::Error;

// خانواده‌ی خطاهای engine-core. هیچ‌کدام از این خطاها به‌تنهایی پروسه را
// نمی‌کشند؛ همیشه به لایه‌ی بالاتر (Python orchestrator) پاس داده می‌شوند
// تا آنجا تصمیم بگیرد چه پیامی به کاربر نشان دهد.
//
// The engine-core error family. None of these errors terminate the process
// on their own; they are always propagated to the caller (the Python
// orchestrator) which decides what to show the user.
#[derive(Debug, Error)]
pub enum EngineError {
    #[error("failed to connect to xray-core gRPC endpoint at {endpoint}: {source}")]
    GrpcConnect {
        endpoint: String,
        #[source]
        source: tonic::transport::Error,
    },

    #[error("xray-core gRPC call '{method}' failed with status {status}")]
    GrpcCall {
        method: &'static str,
        status: tonic::Status,
    },

    #[error("invalid outbound configuration: {reason}")]
    InvalidOutboundConfig { reason: String },

    #[error("outbound with tag '{tag}' was not found")]
    OutboundNotFound { tag: String },

    #[error("xray-core process is not running (expected PID {pid} to be alive)")]
    ProcessNotRunning { pid: u32 },

    #[error("io error: {0}")]
    Io(#[from] std::io::Error),
}

pub type EngineResult<T> = Result<T, EngineError>;
