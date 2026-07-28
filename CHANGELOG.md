# Changelog / تاریخچه تغییرات

فرمت این فایل بر اساس [Keep a Changelog](https://keepachangelog.com/) است.
هر تغییر نسخه، تغییر معماری، یا نکته‌ی خاصی که ممکن است در آینده دوباره
اشتباه تکرار شود، اینجا ثبت می‌شود — دقیقاً طبق درخواست صریح برای مدیریت
تغییرات نسخه‌ها در طول کل پروژه.

This file follows [Keep a Changelog](https://keepachangelog.com/) format.
Every version bump, architecture change, or gotcha that could otherwise be
re-made as a mistake later is recorded here.

## [Unreleased]

### Renamed — تغییر نام
- Project renamed from `xray-orchestrator` / `xo` to **BiMarz** (`bimarz` — بی‌مرز, "borderless") across everything: PyPI/package name in `pyproject.toml`, the Python package directory (`orchestrator/xo/` → `orchestrator/bimarz/`), the CLI command (`xo` → `bimarz`), the PyO3 module path (`xo._engine_core` → `bimarz._engine_core`), the config directory (`~/.config/xo/` → `~/.config/bimarz/`), the `XO_VERSION` constant (→ `BIMARZ_VERSION`), and the GitHub repository (`msoleimani62/xray-orchestrator` → `msoleimani62/bimarz`, renamed after the phase-1 push). The underlying Rust crate name (`engine-core`) was intentionally left unchanged — it is an internal implementation detail, not user-facing.

### Verified — تایید شد
- `maturin develop --release` compiles cleanly end-to-end on the Redmi Note 8 Pro (Kali NetHunter chroot, aarch64): proto fetch → Rust compilation (all 69 xray-core proto files, auto-generated module tree) → PyO3 wheel build → install. `xo doctor` runs and correctly detects `kali_nethunter` as the environment. Only cosmetic dead-code warnings remain (unused generated proto structs — expected at this phase since only a handful of message types are wired up yet).

### Added — افزوده شد
- Project skeleton: Rust workspace (`engine-core`) + Python package (`orchestrator/xo`) wired together via maturin.
- `xo doctor` command: environment detection, xray-core binary discovery, xray-core version read. gRPC probing is honestly reported as "not checked yet" — not implemented at this phase.
- `platform_detect.py`: environment detection (Termux/Kali NetHunter/Desktop Linux/WSL), reusing the kernel-mount-signal strategy already validated in `open-downloader-cli`.
- `xray_manager.py`: subprocess lifecycle wrapper for the xray-core binary (find, get version, start, stop) — zero `sys.exit()` calls, exceptions only.
- `engine-core` Rust crate: gRPC client skeleton (`grpc_client.rs`) targeting xray-core's `HandlerService`/`StatsService`. The actual message-field wiring for `add_outbound`/`remove_outbound`/`list_outbounds`/`get_outbound_stats` is `unimplemented!()` pending the real `.proto` fetch (see `engine-core/proto/README.md`) — tracked as the first task of the next work session.
- PyO3 bridge (`lib.rs`) exposing `PyEngineClient` as an async-friendly Python class.
- pytest suite for `platform_detect.py` and `xray_manager.py` (offline, stub/fake-binary based — no real xray-core or network dependency).

### Known gaps at this stage — کمبودهای شناخته‌شده در این مرحله
- `engine-core`'s gRPC calls are not yet wired to real proto messages (blocked on fetching the actual `.proto` files, which requires network access not available in the dev sandbox — must be done by the user on the Arch laptop).
- No profile/subscription manager yet (phase 2).
- No health-check, failover, kill-switch, or DNS-leak-guard yet (phases 3–4).
- CI workflow not yet added to this changelog entry's diff (queued for the next session, once `cargo test` can actually run somewhere).

### Architecture decisions — تصمیمات معماری
- Switched from requiring a system-installed `protoc` binary to the `protobuf-src` crate, which compiles `protoc` from source at build time via `build.rs` (`std::env::set_var("PROTOC", protobuf_src::protoc())`). This removes a fragile per-platform dependency (`protobuf-compiler` is not reliably packaged in a Kali NetHunter chroot) — a C/C++ toolchain (e.g. `build-essential`/`clang`) is the only remaining requirement, and that is needed anyway to compile Rust's own native dependencies.

### Fixed — رفع اشکال
- `engine-core/proto/README.md` and CI now copy the **entire** `app/` and `common/` proto trees from xray-core instead of four hand-picked files. Copying only `command.proto` + `user.proto` + `typed_message.proto` compiled successfully with `protoc` but made `prost-build` miscalculate the depth of generated `super::` module paths (Rust error `E0433: too many leading super keywords`), because `app/proxyman/command/command.proto` also depends on `app/proxyman/config.proto` (for `InboundHandlerConfig`/`OutboundHandlerConfig`) which was missing from the explicit file list. Lesson: with `tonic-build`/`prost-build`, always pass **every** transitively-imported `.proto` file explicitly — do not rely on `protoc`'s own import resolution alone. `build.rs` now auto-discovers every `.proto` file under `proto/` recursively instead of hardcoding a file list, so this class of bug cannot recur even if the proto tree changes shape in a future xray-core version.
- The `xray.app.proxyman.command` / `xray.app.stats.command` module paths guessed in `grpc_client.rs`'s `include_proto!()` calls were confirmed correct by this real build (the generated `.rs` files landed at exactly those paths) — no change needed there.

### Reverted — بازگردانده شد
- Reverted the `protobuf-src` decision above: compiling the full Protobuf/abseil/upb C++ source tree from scratch on the phone's ARM CPU (inside the Kali NetHunter chroot) took over 57 minutes without finishing — impractical on mobile hardware. Switched back to the system `protoc` binary (`apt install protobuf-compiler`, tested working at `libprotoc 3.21.12` on Kali). `protobuf-src` build-dependency removed from `engine-core/Cargo.toml`; the `PROTOC` env var override removed from `build.rs`. Lesson: `protobuf-src` is fine for desktop/CI but not for building on a phone — always check target hardware before choosing "build from source" over "require a system package" for heavy C/C++ dependencies.

### Fixed (root cause, second attempt) — رفع اشکال (علت واقعی، تلاش دوم)
- The "too many leading super keywords" error persisted identically even after fetching the *entire* xray-core proto tree (69 files) — proving the earlier "missing proto files" diagnosis was incomplete. The real root cause: `prost-build` emits one flat `.rs` file per unique proto package and expects the *consuming* Rust crate to nest its own modules to exactly match the dotted package path; our code declared flat, arbitrarily-named wrapper modules (`pub mod proxyman_command`) instead. Fixed properly and permanently: `build.rs` now scans `OUT_DIR` after compilation and auto-generates a nested `pub mod` tree (`pb_tree.rs`) that exactly mirrors every package's dotted path, so it self-adjusts if a future xray-core version reshuffles its proto structure. `grpc_client.rs` and `lib.rs` updated to consume types via `crate::pb::xray::app::proxyman::command::...` instead of the old flat modules.

### Pinned versions to track — نسخه‌های قفل‌شده برای رهگیری
- xray-core proto source: not yet pinned (`XRAY_TAG` placeholder in `engine-core/proto/README.md` — set this the first time you actually fetch the proto files and update this line).
