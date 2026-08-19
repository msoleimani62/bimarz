#!/usr/bin/env bash
set -euo pipefail

# cross-compile کریت mobile-core برای هر چهار ABI اندروید (با cargo-ndk)،
# .so خروجی هرکدام را در app/src/main/jniLibs/<abi>/ کپی می‌کند، و در
# انتها با اجرای uniffi-bindgen روی یکی از .so های ساخته‌شده، فایل‌های
# bindings کاتلین را در android/app/src/main/kotlin/.../uniffi/ می‌سازد.
# قبل از هر build، اول scripts/fetch-protos.sh را صدا می‌زند تا دقیقاً
# همان درخت proto پین‌شده‌ای که دسکتاپ با آن می‌سازد استفاده شود.
#
# Cross-compiles the mobile-core crate for all four Android ABIs (via
# cargo-ndk), copies each resulting .so into app/src/main/jniLibs/<abi>/,
# and finally runs uniffi-bindgen against one of the built .so files to
# generate the Kotlin binding files under
# android/app/src/main/kotlin/.../uniffi/. Calls scripts/fetch-protos.sh
# first so the build uses the exact same pinned proto tree desktop builds
# against.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
ANDROID_DIR="${PROJECT_ROOT}/android"
JNI_LIBS_DIR="${ANDROID_DIR}/app/src/main/jniLibs"
KOTLIN_OUT_DIR="${ANDROID_DIR}/app/src/main/kotlin/ir/bimarz/app/uniffi"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $*"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }

# نگاشت هدف Rust به ABI اندروید — همان چهار هدفی که cargo-ndk پشتیبانی
# می‌کند و v2rayNG/NekoBox هم دقیقاً همین‌ها را می‌سازند.
# Rust target -> Android ABI mapping — the same four targets cargo-ndk
# supports and the ones v2rayNG/NekoBox build for too.
declare -A TARGET_TO_ABI=(
    ["aarch64-linux-android"]="arm64-v8a"
    ["armv7-linux-androideabi"]="armeabi-v7a"
    ["x86_64-linux-android"]="x86_64"
    ["i686-linux-android"]="x86"
)

if ! command -v cargo-ndk >/dev/null 2>&1; then
    log_error "cargo-ndk not found. Install it with: cargo install cargo-ndk"
    log_error "و rustup target add را برای هر چهار هدف بالا هم اجرا کن."
    exit 1
fi

if [ -z "${ANDROID_NDK_HOME:-}" ]; then
    log_error "ANDROID_NDK_HOME is not set. Point it at your installed NDK, e.g.:"
    log_error '  export ANDROID_NDK_HOME="$HOME/Android/Sdk/ndk/<version>"'
    exit 1
fi

log_info "Fetching the pinned Xray-core proto tree..."
"${SCRIPT_DIR}/fetch-protos.sh"

MIN_SDK="${BIMARZ_ANDROID_MIN_SDK:-24}"
BUILD_PROFILE="${BIMARZ_ANDROID_PROFILE:-release}"

mkdir -p "${JNI_LIBS_DIR}"
for abi_dir in "${TARGET_TO_ABI[@]}"; do
    mkdir -p "${JNI_LIBS_DIR}/${abi_dir}"
done

FIRST_BUILT_SO=""
for target in "${!TARGET_TO_ABI[@]}"; do
    abi="${TARGET_TO_ABI[$target]}"
    log_info "Building mobile-core for ${target} (${abi})..."
    ( cd "${PROJECT_ROOT}" && cargo ndk \
        --target "${target}" \
        --platform "${MIN_SDK}" \
        -o "${JNI_LIBS_DIR}" \
        build -p mobile-core --profile "${BUILD_PROFILE}" )

    built_so="${JNI_LIBS_DIR}/${abi}/libmobile_core.so"
    if [ ! -f "${built_so}" ]; then
        log_error "Expected output not found: ${built_so}"
        log_error "cargo-ndk's -o layout may differ by version; check its actual output path and adjust this script."
        exit 1
    fi
    log_info "Built ${built_so}"
    if [ -z "${FIRST_BUILT_SO}" ]; then
        FIRST_BUILT_SO="${built_so}"
    fi
done

log_info "Generating Kotlin bindings from ${FIRST_BUILT_SO}..."
mkdir -p "${KOTLIN_OUT_DIR}"
( cd "${PROJECT_ROOT}" && cargo run -p mobile-core --bin uniffi-bindgen --features cli -- \
    generate --library "${FIRST_BUILT_SO}" --language kotlin --out-dir "${KOTLIN_OUT_DIR}" )

log_info "Done. jniLibs populated for: ${TARGET_TO_ABI[*]}"
log_info "Kotlin bindings written to: ${KOTLIN_OUT_DIR}"
log_warn "این تنها روی ماشین توسعه اجرا می‌شود؛ خروجی جنی‌لیب‌ها و بایندینگ کاتلین قبل از commit باید review شوند."
log_warn "This only runs on the development machine; review the jniLibs and generated Kotlin bindings before committing."
