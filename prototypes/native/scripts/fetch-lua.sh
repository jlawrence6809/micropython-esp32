#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
commit=6e22fedb74cf0c9b6656e9fce8b7331db847c605
if [[ ! -d components/lua/vendor ]]; then
  git clone --depth 1 --branch v5.4.8 https://github.com/lua/lua.git components/lua/vendor
fi
[[ $(git -C components/lua/vendor rev-parse HEAD) == "$commit" ]] || {
  echo 'Unexpected Lua revision; refusing to use it' >&2; exit 1;
}
[[ -z $(git -C components/lua/vendor status --porcelain) ]] || {
  echo 'Lua vendor checkout is modified; refusing to use it' >&2; exit 1;
}
