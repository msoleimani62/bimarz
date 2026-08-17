#!/usr/bin/env bash
set -euo pipefail

# Build-release script for BiMarz engine-core.
# Checks prerequisites, fetches pinned proto files via
# scripts/fetch-protos.sh, runs the same validation gates as CI
# (fmt + clippy), builds the native wheel, optionally cross-compiles
# aarch64 with maturin's zig integration, and validates every wheel
# it produced.
#
# اسکریپت build-release برای engine-core بی‌مرز.
# پیش‌نیازها را چک می‌کند، proto های پین‌شده را با
# scripts/fetch-protos.sh واکشی می‌کند، همان gateهای اعتبارسنجی CI را
# اجرا می‌کند (fmt + clippy)، wheel نیتیو می‌سازد، اختیاراً aarch64 را
# با یکپارچگی zig در maturin کراس-کامپایل می‌کند و در انتها همه‌ی
# wheelهای ساخته‌شده را اعتبارسنجی می‌کند.

MIN_MATURIN_VERSION="1.8"
MATURIN_CONSTRAINT="maturin>=1.8,<2.0"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENGINE_DIR="${PROJECT_ROOT}/engine-core"
WHEELS_DIR="${ENGINE_DIR}/target/wheels"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $*"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }

die() {
    log_error "$*"
    exit 1
}

check_prerequisites() {
    local missing=()
    command -v python3 &>/dev/null || missing+=("python3")
    command -v cargo &>/dev/null || missing+=("cargo (Rust toolchain)")
    command -v rustup &>/dev/null || missing+=("rustup")
    command -v git &>/dev/null || missing+=("git")
    if [ ${#missing[@]} -ne 0 ]; then
        log_error "Missing prerequisites: ${missing[*]}"
        log_info "Install them first, then re-run this script."
        exit 1
    fi
}

setup_python_env() {
    # Respect an already-active virtual environment; otherwise use (or
    # create) the project-local .venv. The user's global Python is never
    # touched.
    # اگر یک virtual environment از قبل فعال است همان را استفاده می‌کنیم؛
    # در غیر این صورت .venv محلی پروژه ساخته/استفاده می‌شود. به پایتون
    # سراسری کاربر هرگز دست زده نمی‌شود.
    if [ -n "${VIRTUAL_ENV:-}" ]; then
        log_info "Using active virtual environment: ${VIRTUAL_ENV}"
        return
    fi
    local venv_dir="${PROJECT_ROOT}/.venv"
    if [ ! -d "${venv_dir}" ]; then
        log_info "Creating virtual environment at ${venv_dir}..."
        python3 -m venv "${venv_dir}" || die "Failed to create virtual environment."
    fi
    # shellcheck source=/dev/null
    source "${venv_dir}/bin/activate" || die "Failed to activate ${venv_dir}."
}

ensure_maturin() {
    # Install the constrained maturin version only when missing or too old;
    # a release build must never pull "whatever was latest today".
    # maturin فقط وقتی و با همان محدوده‌ی نسخه‌ی پین‌شده نصب/ارتقا می‌یابد
    # که نباشد یا قدیمی باشد؛ build انتشار هرگز نباید «جدیدترین نسخه‌ی امروز»
    # را بکشد.
    local installed=""
    installed="$(python3 -c "import maturin; print(maturin.__version__)" 2>/dev/null || true)"
    if [ -n "${installed}" ]; then
        local cur_major cur_minor
        cur_major="${installed%%.*}"
        cur_minor="$(echo "${installed}" | cut -d. -f2)"
        if [ "${cur_major}" -eq 1 ] && [ "${cur_minor}" -ge "${MIN_MATURIN_VERSION#1.}" ]; then
            log_info "maturin ${installed} OK (${MATURIN_CONSTRAINT})"
            return
        fi
        log_warn "maturin ${installed} is outside ${MATURIN_CONSTRAINT} — installing a compliant version."
    else
        log_info "maturin not found — installing ${MATURIN_CONSTRAINT}."
    fi
    python3 -m pip install "${MATURIN_CONSTRAINT}" || die "Failed to install ${MATURIN_CONSTRAINT}."
}

fetch_protos() {
    # Delegates to the single authoritative fetch mechanism (also used by CI).
    # به مکانیزم معتبر و واحد واکشی proto واگذار می‌کند (همان که CI استفاده می‌کند).
    "${PROJECT_ROOT}/scripts/fetch-protos.sh"
}

run_validation_gates() {
    # Same quality gates as .github/workflows/ci.yml — a release build must
    # not succeed on code that CI would reject.
    # همان gateهای کیفیت گردش‌کار CI — build انتشار نباید روی کدی موفق شود
    # که CI آن را رد می‌کند.
    log_info "Running cargo fmt --check..."
    (cd "${PROJECT_ROOT}" && cargo fmt --all -- --check) ||
        die "cargo fmt check failed — run 'cargo fmt --all' and review the diff."

    log_info "Running cargo clippy..."
    (cd "${ENGINE_DIR}" && cargo clippy --all-targets -- -D warnings) ||
        die "cargo clippy failed — fix warnings before building."
    log_info "Validation gates passed."
}

build_native() {
    log_info "Building native wheel..."
    (cd "${ENGINE_DIR}" && maturin build --release) || die "Native wheel build failed."
    log_info "Native wheel built successfully."
}

build_aarch64() {
    log_info "Building aarch64 wheel (cross-compilation via maturin --zig)..."
    # maturin's --zig integration is the same tool cargo-zigbuild wraps, but
    # driving it through maturin guarantees the produced artifact is a valid
    # Python wheel (correct tags, bundled native module) instead of a bare
    # Rust .so that a later plain 'maturin build' would simply rebuild with
    # the default linker — which is why the old two-step flow could fail at
    # link time.
    # یکپارچگی ‎--zig در maturin همان ابزاری است که cargo-zigbuild دور آن
    # wrapper زده، ولی هدایت از مسیر maturin تضمین می‌کند خروجی یک wheel
    # معتبر پایتون است (تگ‌های درست، ماژول نیتیو همراه) نه یک ‎.so خام —
    # دلیل شکست جریان دومرحله‌ای قبلی در زمان لینک همین بود.
    if ! python3 -c "import ziglang" &>/dev/null && ! command -v zig &>/dev/null; then
        log_info "zig not found — installing the ziglang wheel into the active environment..."
        python3 -m pip install ziglang || die "Failed to install ziglang (needed for --zig cross builds)."
    fi
    if ! rustup target list --installed | grep -q "^aarch64-unknown-linux-gnu$"; then
        log_info "Adding aarch64-unknown-linux-gnu target..."
        rustup target add aarch64-unknown-linux-gnu || die "Failed to add the aarch64 Rust target."
    fi
    (cd "${ENGINE_DIR}" && maturin build --release --zig --target aarch64-unknown-linux-gnu) ||
        die "aarch64 wheel build failed."
    log_info "aarch64 wheel built successfully."
}

expected_package_version() {
    # Reads [project] version from pyproject.toml without any third-party
    # dependency (tomllib needs Python 3.11+, and tomli may be absent).
    # نسخه‌ی [project] را از pyproject.toml بدون هیچ وابستگی third-party
    # می‌خواند (tomllib به پایتون ۳.۱۱+ نیاز دارد و tomli ممکن است نصب نباشد).
    python3 -c '
import re
import sys
match = re.search(r"(?m)^version\s*=\s*\"([^\"]+)\"", open(sys.argv[1], encoding="utf-8").read())
if match is None:
    sys.exit("could not find [project] version in pyproject.toml")
print(match.group(1))
' "${PROJECT_ROOT}/pyproject.toml"
}

validate_wheels() {
    # Post-build gate: a wheel that maturin exited 0 on is NOT automatically
    # a valid release artifact — inspect metadata, native module and version
    # consistency before calling the build done.
    # گیت پس از build: خروج موفق maturin به‌خودی‌خود یعنی artifact معتبر نیست
    # — metadata، ماژول نیتیو و سازگاری نسخه قبل از تمام‌نامیدن build بررسی
    # می‌شوند.
    log_info "Validating built wheels..."
    local expected_version
    expected_version="$(expected_package_version)"

    local wheel_count=0
    local wheel
    for wheel in "${WHEELS_DIR}"/*.whl; do
        [ -e "${wheel}" ] || die "No wheels found in ${WHEELS_DIR} — build produced nothing."
        wheel_count=$((wheel_count + 1))
        log_info "Inspecting $(basename "${wheel}")"
        WHEEL_PATH="${wheel}" EXPECTED_VERSION="${expected_version}" python3 - <<'PY'
import os
import sys
import zipfile

wheel = os.environ["WHEEL_PATH"]
expected = os.environ["EXPECTED_VERSION"]

name = os.path.basename(wheel)
parts = name.split("-")
if len(parts) < 5 or not name.endswith(".whl"):
    sys.exit(f"invalid wheel filename: {name}")

with zipfile.ZipFile(wheel) as zf:
    names = zf.namelist()
    metadata_files = [n for n in names if n.endswith(".dist-info/METADATA")]
    if not metadata_files:
        sys.exit(f"{name}: no .dist-info/METADATA found")
    metadata = zf.read(metadata_files[0]).decode("utf-8", "replace")
    version_line = next(
        (l for l in metadata.splitlines() if l.startswith("Version: ")), None
    )
    if version_line is None:
        sys.exit(f"{name}: METADATA has no Version field")
    wheel_version = version_line.split(":", 1)[1].strip()
    if wheel_version != expected:
        sys.exit(
            f"{name}: wheel version {wheel_version} != pyproject version {expected}"
        )
    if not any(n.endswith(".so") for n in names):
        sys.exit(f"{name}: no native .so module inside the wheel")

print(f"  version={wheel_version} (matches pyproject), native module present")
PY
    done

    log_info "${wheel_count} wheel(s) validated in ${WHEELS_DIR}"
    log_warn "Runtime check on this host: install one matching wheel into a fresh venv and run 'bimarz --version' / 'bimarz doctor'."
}

main() {
    local build_aarch64_flag=false
    local skip_validation=false
    while [[ $# -gt 0 ]]; do
        case $1 in
            --aarch64)
                build_aarch64_flag=true
                shift
                ;;
            --skip-wheel-validation)
                skip_validation=true
                shift
                ;;
            --help|-h)
                echo "Usage: $0 [--aarch64] [--skip-wheel-validation]"
                echo ""
                echo "Options:"
                echo "  --aarch64                 Also build an aarch64-unknown-linux-gnu wheel (maturin --zig)"
                echo "  --skip-wheel-validation   Skip the post-build wheel inspection gate"
                echo "  --help, -h                Show this help message"
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done

    check_prerequisites
    fetch_protos
    setup_python_env
    ensure_maturin
    run_validation_gates
    build_native

    if [ "${build_aarch64_flag}" = true ]; then
        build_aarch64
    fi

    if [ "${skip_validation}" = false ]; then
        validate_wheels
    fi

    log_info "Build complete. Wheels are in ${WHEELS_DIR}/"
}

main "$@"
