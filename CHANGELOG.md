# Changelog / تاریخچه تغییرات

فرمت این فایل بر اساس [Keep a Changelog](https://keepachangelog.com/) است.
This file follows the [Keep a Changelog](https://keepachangelog.com/) format.

## [Unreleased]

### Added — افزوده شد

- `docs/INSTALL.md`: step-by-step bilingual installation guide for non-technical users.
- `.github/workflows/security.yml`: scheduled dependency security auditing for Rust and Python dependencies using `cargo-audit`, `pip-audit`, and `bandit`.
- `SECURITY.md`: documented disposition for known PyO3 advisories (RUSTSEC-2025-0020, RUSTSEC-2026-0177) per project Constitution.

### Changed — تغییر یافت

- `README.md`: roadmap synced to reflect phase 6 completion; phase 6 security/CI tasks marked done, phase 7 (Subscription Manager) marked in-progress.
- `scripts/build-release.sh`: added a `cargo clippy` validation step before building and added maturin version validation.

### Security — امنیت

- Added scheduled dependency auditing to the GitHub Actions CI pipeline as part of phase 6.
- Rust dependencies are audited with `cargo-audit`.
- Installed Python dependencies are audited with `pip-audit`.
- Python source is scanned with `bandit` in CI.
- Known PyO3 advisories are dispositioned as **UPGRADED** after migrating from PyO3 0.22.x to PyO3 0.29.2. The affected APIs are not used in this codebase.

### Testing — تست

- Preserved existing integration assertions and active test coverage while removing only obsolete skipped tests.
- No public API was changed as part of the phase 6 test and CI cleanup.
- No runtime dependency was added to the project; `cargo-audit`, `pip-audit`, and `bandit` are CI-only security tooling.

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
- `orchestrator/bimarz/cli.py`: fully modularized — all business logic moved to `commands/` and `services/` modules; cli.py reduced from ~1070 to ~117 lines.

### Fixed — رفع شد

- `orchestrator/bimarz/cli.py`: `_connect_async` now passes the real user UID (`os.getuid()`) to `KillSwitchManager.activate()`, preventing the kill-switch from blocking xray-core's own tunnel traffic.
- `engine-core/src/killswitch.rs`: `build_killswitch_rules` now returns a clear error when `xray_uid` is `None` instead of generating a dangerous blanket-DROP rule that would break the connection.
- `orchestrator/bimarz/gui/connection_worker.py`: fixed signature mismatch in `connect_with_retry` call (was passing only 1 arg instead of 3); defaults added to `bimarz.utils.retry.connect_with_retry`.

### Security — امنیت

- Improved kill-switch rule validation to prevent accidental blanket blocking rules.
- Improved diagnostic handling to make network protection failures visible instead of silently applying unsafe defaults.

### Architecture decisions — تصمیمات معماری (فاز ۵)

- **PyPI deferred, not rejected:** publishing to PyPI has been postponed until the CI pipeline can reliably produce wheels for every supported platform. GitHub Releases is currently the primary distribution channel because it can publish multiple platform-specific wheels within a single release.
- **Doctor probe is layered:** a TCP probe is always available with zero external dependencies. A real gRPC probe is executed only when the Rust extension has been built, allowing `bimarz doctor` to remain functional even before `maturin develop` is executed.
- **Error hints are contextual:** every error category now provides a targeted next-step hint (for example, `source .venv/bin/activate && maturin develop --release` for `EngineNotBuiltError`) instead of only displaying the raw exception.
- **cli.py modularization:** all sub-command logic extracted to `commands/` (CLI-specific) and `services/` (reusable by GUI) to enforce single-responsibility and prevent the monolithic cli.py anti-pattern.

## [0.1.0] — 2026-07-20

### Added — افزوده شد

- Initial project skeleton: Python orchestrator + Rust engine-core via PyO3/maturin.
- gRPC connection skeleton to xray-core with `EngineClient` (Rust) and `PyEngineClient` (Python bridge).
- `bimarz doctor` command with environment detection and xray-core binary discovery.
- Platform detection for Arch Linux, Kali NetHunter/Termux, WSL, and generic Linux.
- CI skeleton with GitHub Actions for Rust tests and Python pytest.

## Version Links

[Unreleased]: https://github.com/msoleimani62/bimarz/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/msoleimani62/bimarz/releases/tag/v0.2.0
[0.1.0]: https://github.com/msoleimani62/bimarz/releases/tag/v0.1.0
