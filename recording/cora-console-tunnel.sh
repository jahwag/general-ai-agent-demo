#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "$0")/.." && pwd)
ssh_config=${CORA_SSH_CONFIG:-$repo_root/tmp/ssh/demo_config}
ssh_alias=${CORA_SSH_ALIAS:-gaidemo}
local_port=${CORA_CONSOLE_PORT:-17681}
url="http://127.0.0.1:${local_port}/"

if ! curl --fail --silent --show-error "$url" >/dev/null 2>&1; then
  ssh -F "$ssh_config" \
    -o ExitOnForwardFailure=yes \
    -fN \
    -L "${local_port}:127.0.0.1:7681" \
    "$ssh_alias"
fi

curl --fail --silent --show-error "$url" >/dev/null
printf '%s\n' "$url"

if [[ ${1:-} == "--open" ]]; then
  xdg-open "$url" >/dev/null 2>&1 &
fi
