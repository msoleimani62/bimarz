# Security / امنیت

## Dependency Security Policy

Every dependency security advisory must be in one of these states:
AFFECTED | MITIGATED | UPGRADED | ACCEPTED RISK | FALSE POSITIVE | NOT APPLICABLE

هر advisory امنیتی وابستگی باید در یکی از این وضعیت‌ها باشد.

---

## Known Security Findings / یافته‌های امنیتی شناخته‌شده

### PyO3 0.29.2

The previously affected PyO3 0.22.x dependency has been upgraded to PyO3 0.29.2.

وابستگی آسیب‌پذیر قبلی PyO3 0.22.x به PyO3 0.29.2 ارتقا یافته است.

| Advisory | Title | Disposition | Evidence |
|----------|-------|-------------|----------|
| RUSTSEC-2025-0020 | Risk of buffer overflow in `PyString::from_object` | UPGRADED | PyO3 was upgraded to 0.29.2, which contains the required fix. |
| RUSTSEC-2026-0177 | Missing `Sync` bound on `PyCFunction::new_closure` closures | UPGRADED | PyO3 was upgraded to 0.29.2, which contains the required fix. |

### Verification / راستی‌آزمایی

The migration was validated with:

- `cargo check --manifest-path engine-core/Cargo.toml`
- `cargo build --manifest-path engine-core/Cargo.toml`
- `maturin develop --release`
- Python extension import
- `pytest`
- `cargo test`
- `cargo clippy --all-targets --all-features -- -D warnings`
- `cargo audit`

The migration was verified successfully by the repository verification suite, including build, tests, linting, packaging, extension import, and dependency security auditing.

مهاجرت با موفقیت توسط مجموعه بررسی repository شامل build، تست، lint، بسته‌بندی، import افزونه و audit امنیتی dependencyها تأیید شده است.

## Reporting Security Issues

Please open a private security advisory via GitHub if you discover a new vulnerability.
لطفاً در صورت کشف آسیب‌پذیری جدید، از طریق GitHub Security Advisories به‌صورت خصوصی گزارش دهید.
