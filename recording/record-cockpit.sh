#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "$0")/.." && pwd)
cd "$repo_root"

server_pid=""
stop_server() {
  if [[ -n $server_pid ]] && kill -0 "$server_pid" 2>/dev/null; then
    kill "$server_pid"
    wait "$server_pid" 2>/dev/null || true
  fi
}
trap stop_server EXIT HUP INT TERM

if ! curl --fail --silent --show-error http://127.0.0.1:8765/ >/dev/null 2>&1; then
  python3 -m http.server 8765 --bind 127.0.0.1 >tmp/cockpit-http.log 2>&1 &
  server_pid=$!
  for _ in {1..50}; do
    curl --fail --silent --show-error http://127.0.0.1:8765/ >/dev/null 2>&1 && break
    sleep 0.1
  done
fi

webm=artifacts/ai-driven-cockpit.webm
output=artifacts/ai-driven-freshservice-demo.mp4

if [[ ${SKIP_AGENTBUS_EVIDENCE:-0} != 1 ]]; then
  recording/agentbus-evidence.sh
fi
node recording/record-cockpit.mjs "$webm"
ffmpeg -hide_banner -loglevel error -y \
  -i "$webm" \
  -c:v libx264 \
  -preset medium \
  -crf 20 \
  -pix_fmt yuv420p \
  -movflags +faststart \
  "$output"

ffprobe -v error \
  -show_entries format=duration,size \
  -show_entries stream=codec_name,width,height,pix_fmt,r_frame_rate \
  -of json \
  "$output"
