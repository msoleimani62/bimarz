#!/usr/bin/env bash
set -euo pipefail

# Build-release script for BiMarz engine-core.
# Checks prerequisites, fetches pinned proto files, runs clippy,
# builds native wheel, and optionally cross-compiles aarch64 with cargo-zigbuild.
#
# اسکریپت build-release برای engine-core بی‌مرز.
# پیش‌نیازها را چک می‌کند، proto های پین‌شده را واکشی می‌کند،
# clippy اجرا می‌کند، wheel نیتیو می‌سازد و اختیاراً aarch64 را
# با cargo-zigbuild کراس-کامپایل می‌کند.

XRAY_TAG="v1.8.24"
MIN_MATURIN_VERSION="1.7"
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENGINE_DIR="${PROJECT_ROOT}/engine-core"
VENV_DIR="${PROJECT_ROOT}/.venv"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $*"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }

check_prerequisites() {
    local missing=()
    if ! command -v python3 &> /dev/null; then
        missing+=("python3")
    fi
    if ! command -v cargo &> /dev/null; then
        missing+=("cargo (Rust toolchain)")
    fi
    if ! command -v git &> /dev/null; then
        missing+=("git")
    fi
    if [ ${#missing[@]} -ne 0 ]; then
        log_error "Missing prerequisites: ${missing[*]}"
        log_info "Install them first, then re-run this script."
        exit 1
    fi
}

check_maturin_version() {
    local maturin_version
    maturin_version=$(python3 -c "import maturin; print(maturin.__version__)" 2>/dev/null || echo "0.0.0")
    if [ "${maturin_version}" = "0.0.0" ]; then
        log_warn "maturin not found in Python environment — will install"
        return 1
    fi
    # Simple semver comparison: extract major.minor
    local current_major current_minor
    current_major=$(echo "$maturin_version" | cut -d. -f1)
    current_minor=$(echo "$maturin_version" | cut -d. -f2)
    local min_major min_minor
    min_major=$(echo "$MIN_MATURIN_VERSION" | cut -d. -f1)
    min_minor=$(echo "$MIN_MATURIN_VERSION" | cut -d. -f2)

    if [ "$current_major" -lt "$min_major" ] ||        ([ "$current_major" -eq "$min_major" ] && [ "$current_minor" -lt "$min_minor" ]); then
        log_warn "maturin ${maturin_version} found, but >= ${MIN_MATURIN_VERSION} required — will upgrade"
        return 1
    fi
    log_info "maturin ${maturin_version} OK (>= ${MIN_MATURIN_VERSION})"
    return 0
}

fetch_protos() {
    log_info "Fetching xray-core proto files (tag: ${XRAY_TAG})..."
    if [ -d "/tmp/xray-core-src" ]; then
        rm -rf /tmp/xray-core-src
    fi
    git clone --depth 1 --branch "${XRAY_TAG}"         https://github.com/XTLS/xray-core.git /tmp/xray-core-src
    mkdir -p "${ENGINE_DIR}/proto"
    cp -r /tmp/xray-core-src/app "${ENGINE_DIR}/proto/"
    cp -r /tmp/xray-core-src/common "${ENGINE_DIR}/proto/"
    rm -rf /tmp/xray-core-src
    log_info "Proto files fetched successfully."
}

setup_venv() {
    if [ ! -d "${VENV_DIR}" ]; then
        log_info "Creating virtual environment..."
        python3 -m venv "${VENV_DIR}"
    fi
    source "${VENV_DIR}/bin/activate"
    log_info "Installing/Upgrading build dependencies..."
    pip install --upgrade pip maturin
}

run_clippy() {
    log_info "Running cargo clippy..."
    cd "${ENGINE_DIR}"
    if ! cargo clippy --all-targets -- -D warnings; then
        log_error "cargo clippy failed — fix warnings before building."
        exit 1
    fi
    log_info "cargo clippy passed."
}

build_native() {
    log_info "Building native wheel..."
    cd "${ENGINE_DIR}"
    maturin build --release
    log_info "Native wheel built successfully."
}

build_aarch64() {
    log_info "Building aarch64 wheel (cross-compilation)..."
    if ! command -v cargo-zigbuild &> /dev/null; then
        log_warn "cargo-zigbuild not found. Installing..."
        cargo install cargo-zigbuild
    fi
    if ! rustup target list --installed | grep -q "aarch64-unknown-linux-gnu"; then
        log_info "Adding aarch64 target..."
        rustup target add aarch64-unknown-linux-gnu
    fi
    cd "${ENGINE_DIR}"
    cargo zigbuild --target aarch64-unknown-linux-gnu --release
    maturin build --release --target aarch64-unknown-linux-gnu
    log_info "aarch64 wheel built successfully."
}

main() {
    local build_aarch64_flag=false
    while [[ $# -gt 0 ]]; do
        case $1 in
            --aarch64)
                build_aarch64_flag=true
                shift
                ;;
            --help|-h)
                echo "Usage: $0 [--aarch64]"
                echo ""
                echo "Options:"
                echo "  --aarch64    Also build aarch64 wheel using cargo-zigbuild"
                echo "  --help, -h   Show this help message"
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
    setup_venv
    check_maturin_version || pip install --upgrade "maturin>=${MIN_MATURIN_VERSION}"
    run_clippy
    build_native

    if [ "${build_aarch64_flag}" = true ]; then
        build_aarch64
    fi

    log_info "Build complete. Wheels are in ${ENGINE_DIR}/target/wheels/"
}

main "$@"
