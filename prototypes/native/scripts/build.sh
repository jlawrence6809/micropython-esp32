#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
target=esp32s3
controller=false
args=()
while (($#)); do
  case "$1" in
    --target) target="${2:?--target requires esp32 or esp32s3}"; shift 2 ;;
    --controller) controller=true; shift ;;
    *) args+=("$1"); shift ;;
  esac
done
case "$target" in
  esp32s3) build_dir=build; defaults=sdkconfig.defaults ;;
  esp32) build_dir=build-esp32; defaults=sdkconfig.esp32.defaults ;;
  *) echo "Unsupported target: $target" >&2; exit 2 ;;
esac
# Keep convenience bench/controller builds separate as well as chip targets.
$controller && build_dir="build-$target-controller"
has_build=false; has_sdk=false; has_defaults=false
for ((i=0;i<${#args[@]};i++)); do
  case "${args[i]}" in
    -B|--build-dir) build_dir="${args[i+1]:?Build directory required}"; has_build=true ;;
    -B?*) build_dir="${args[i]#-B}"; has_build=true ;;
    --build-dir=*) build_dir="${args[i]#*=}"; has_build=true ;;
    -DSDKCONFIG=*) has_sdk=true ;;
    -DSDKCONFIG_DEFAULTS=*) has_defaults=true ;;
    -DIDF_TARGET=*|IDF_TARGET=*) echo "Use --target, not an IDF_TARGET override" >&2; exit 2 ;;
  esac
done
extra=()
$has_build || extra+=(-B "$build_dir")
if ! $has_sdk; then
  case "$build_dir" in /*) sdk="$build_dir/sdkconfig" ;; *) sdk="$PWD/$build_dir/sdkconfig" ;; esac
  extra+=("-DSDKCONFIG=$sdk")
fi
if $controller; then
  if $has_defaults; then echo "Use --controller OR explicit SDKCONFIG_DEFAULTS, not both" >&2; exit 2; fi
  defaults+=';sdkconfig.controller.defaults'
  extra+=(-DPROJECT_VER=relay-profile1)
fi
$has_defaults || extra+=("-DSDKCONFIG_DEFAULTS=$defaults")
export IDF_PATH="${IDF_PATH:-$HOME/.local/share/esp/esp-idf-v5.5.1}"
export IDF_PYTHON_ENV_PATH="${IDF_PYTHON_ENV_PATH:-$HOME/.espressif/python_env/idf5.5_py3.12_env}"
export PATH="$IDF_PYTHON_ENV_PATH/bin:$PATH"
# The upstream export script manages its own shell error handling.
set +u
source "$IDF_PATH/export.sh"
set -u
bash scripts/fetch-lua.sh
# Separate build dirs AND sdkconfigs prevent a target switch from reusing S3
# settings or touching any frozen deployment build. IDF rejects a mismatched cache.
idf.py -DIDF_TARGET="$target" "${extra[@]}" "${args[@]}" build
