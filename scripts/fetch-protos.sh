#!/usr/bin/env bash
set -euo pipefail

# Authoritative mechanism for fetching the official Xray-core proto files.
# Used by scripts/build-release.sh, the CI workflow and the release
# workflow so all of them always build against the exact same proto tree.
#
# مکانیزم معتبر و واحد برای واکشی فایل‌های رسمی proto مربوط به Xray-core.
# هم scripts/build-release.sh و هم گردش‌کارهای CI و release از همین اسکریپت
# استفاده می‌کنند تا همیشه دقیقاً روی یک درخت proto یکسان ساخته شوند.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
ENGINE_DIR="${PROJECT_ROOT}/engine-core"
PIN_FILE="${ENGINE_DIR}/xray-proto-pin.env"
PROTO_DIR="${ENGINE_DIR}/proto"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $*"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }

if [ ! -f "${PIN_FILE}" ]; then
    log_error "Pin file not found: ${PIN_FILE}"
    log_error "The Xray proto version pin is mandatory; restore the file and retry."
    exit 1
fi

# shellcheck source=/dev/null
source "${PIN_FILE}"

# Optional escape hatch: XRAY_TAG in the environment overrides the pin for
# experimental builds, with a loud warning so it never happens silently.
# دریچه‌ی فرار اختیاری: متغیر محیطی XRAY_TAG برای buildهای آزمایشی پین را
# نادیده می‌گیرد، البته با هشدار پرصدایی که هرگز بی‌صدا اتفاق نمی‌افتد.
if [ -n "${XRAY_TAG:-}" ]; then
    log_warn "XRAY_TAG=${XRAY_TAG} overrides pinned ${XRAY_PROTO_TAG} — experimental build, proto/binary compatibility is on you."
    XRAY_PROTO_TAG="${XRAY_TAG}"
    XRAY_PROTO_COMMIT=""
fi

if [ -z "${XRAY_PROTO_TAG:-}" ]; then
    log_error "XRAY_PROTO_TAG is empty in ${PIN_FILE}"
    exit 1
fi

TMP_DIR="$(mktemp -d /tmp/bimarz-xray-proto.XXXXXX)"
cleanup() {
    rm -rf "${TMP_DIR}"
}
trap cleanup EXIT

log_info "Fetching xray-core proto files (tag: ${XRAY_PROTO_TAG})..."

if ! git clone --depth 1 --branch "${XRAY_PROTO_TAG}" \
    https://github.com/XTLS/xray-core.git "${TMP_DIR}/xray-core-src"; then
    log_error "git clone failed for tag ${XRAY_PROTO_TAG}."
    log_error "Check network access and that the tag still exists upstream."
    exit 1
fi

# Verify the cloned tag still points at the pinned immutable commit, so a
# moved/re-targeted upstream tag can never silently change the proto tree.
# بررسی می‌کند تگ clone‌شده هنوز به همان کامیت پین‌شده‌ی غیرقابل‌تغییر اشاره
# کند تا جابه‌جاشدن تگ upstream هرگز بی‌صدا درخت proto را عوض نکند.
if [ -n "${XRAY_PROTO_COMMIT:-}" ]; then
    actual_commit="$(git -C "${TMP_DIR}/xray-core-src" rev-parse HEAD)"
    if [ "${actual_commit}" != "${XRAY_PROTO_COMMIT}" ]; then
        log_error "Tag ${XRAY_PROTO_TAG} now points at ${actual_commit}, expected ${XRAY_PROTO_COMMIT}."
        log_error "The upstream tag moved. Review the change, then update ${PIN_FILE} deliberately."
        exit 1
    fi
fi

# Verify the expected directories exist before touching the destination.
# قبل از دست‌زدن به مقصد، وجود دایرکتوری‌های مورد انتظار بررسی می‌شود.
for required in app common; do
    if [ ! -d "${TMP_DIR}/xray-core-src/${required}" ]; then
        log_error "Upstream tree is missing '${required}/' — refusing to install an incomplete proto tree."
        exit 1
    fi
done

app_count="$(find "${TMP_DIR}/xray-core-src/app" -name '*.proto' | wc -l)"
common_count="$(find "${TMP_DIR}/xray-core-src/common" -name '*.proto' | wc -l)"
if [ "${app_count}" -eq 0 ] || [ "${common_count}" -eq 0 ]; then
    log_error "No .proto files found under app/ (${app_count}) or common/ (${common_count}) — incomplete tree, aborting."
    exit 1
fi

# Clean the destination before copying so stale files from a previous
# fetch can never contaminate the build.
# مقصد قبل از کپی پاک می‌شود تا فایل‌های کهنه‌ی واکشی قبلی هرگز build را
# آلوده نکنند.
mkdir -p "${PROTO_DIR}"
rm -rf "${PROTO_DIR}/app" "${PROTO_DIR}/common"

cp -r "${TMP_DIR}/xray-core-src/app" "${PROTO_DIR}/"
cp -r "${TMP_DIR}/xray-core-src/common" "${PROTO_DIR}/"

log_info "Proto files installed into ${PROTO_DIR} (app: ${app_count}, common: ${common_count} .proto files)."
