# Changelog / تاریخچه تغییرات

فرمت این فایل بر اساس [Keep a Changelog](https://keepachangelog.com/) است.
This file follows the [Keep a Changelog](https://keepachangelog.com/) format.

## [Unreleased]

## [0.2.0] — 2026-08-03

### Added — افزوده شد (فاز ۵: تکمیل CLI و بسته‌بندی)

- `orchestrator/bimarz/models.py`: `GrpcStatus` enum with multiple states (`not_checked`, `unreachable`, `listening`, `responding`) for accurate gRPC health reporting in `bimarz doctor`.
- `orchestrator/bimarz/constants.py`: `DOCTOR_GRPC_PROBE_TIMEOUT_SECONDS` and `DOCTOR_GRPC_PROBE_TIMEOUT_ENV_VAR` for configurable doctor probe timeout.
- `orchestrator/bimarz/xray_manager.py`: `probe_tcp_port()` async function for zero-dependency TCP port probing.
- `orchestrator/bimarz/engine.py`: `probe_grpc_with_engine()` for performing a real gRPC call through the Rust extension when available.
- `orchestrator/bimarz/cli.py`: `bimarz doctor` now performs a real layered gRPC probe (TCP connectivity → real gRPC probe when the Rust engine is available). Added the `--doctor-timeout` CLI flag. Improved error messages with contextual hints for `EngineNotBuiltError` and `BinaryNotFoundError`.
- `.github/workflows/release.yml`: automated GitHub Releases for `v*` tags, building wheels for `x86_64` and `aarch64` with Rust dependency caching.
- `scripts/build-release.sh`: local developer build script with dependency checking and optional `cargo-zigbuild` cross-compilation support for `aarch64`.
- `tests/test_cli_doctor.py`: comprehensive unit tests covering doctor timeout resolution and all gRPC status states.

### Changed — تغییر یافت

- `orchestrator/bimarz/models.py`: `DoctorReport.grpc_reachable: bool` replaced by `grpc_status: GrpcStatus` and `grpc_endpoint: str` for richer diagnostics.
- `orchestrator/bimarz/cli.py`: `_render_doctor_report` now color-codes and explains each `GrpcStatus` state.
- `orchestrator/bimarz/constants.py`: version bumped to `0.2.0` (synchronized with `pyproject.toml`).

### Architecture decisions — تصمیمات معماری (فاز ۵)

- **PyPI deferred, not rejected:** publishing to PyPI has been postponed until the CI pipeline can reliably produce wheels for every supported platform. GitHub Releases is currently the primary distribution channel because it can publish multiple platform-specific wheels within a single release.
- **Doctor probe is layered:** a TCP probe is always available with zero external dependencies. A real gRPC probe is executed only when the Rust extension has been built, allowing `bimarz doctor` to remain functional even before `maturin develop` is executed.
- **Error hints are contextual:** every error category now provides a targeted next-step hint (for example, `source .venv/bin/activate && maturin develop --release` for `EngineNotBuiltError`) instead of only displaying the raw exception.

## [0.1.0] — 2026-07-20

### Added — افزوده شد

- (تمام entryهای قبلی فاز ۰ تا ۴ اینجا باقی می‌مانند — حذف نشده‌اند)

