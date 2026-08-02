#!/usr/bin/env bash
set -euo pipefail

input=${1:?usage: still-to-clip.sh INPUT.png OUTPUT.mp4 [SECONDS]}
output=${2:?usage: still-to-clip.sh INPUT.png OUTPUT.mp4 [SECONDS]}
seconds=${3:-12}

if [[ ! -s $input ]]; then
  echo "missing screenshot: $input" >&2
  exit 2
fi
if [[ ! $seconds =~ ^[1-9][0-9]*$ ]]; then
  echo "seconds must be a positive integer" >&2
  exit 2
fi

frames=$((seconds * 30))
ffmpeg -hide_banner -loglevel error -y \
  -loop 1 \
  -i "$input" \
  -vf "scale=1440:900:force_original_aspect_ratio=decrease,pad=1440:900:(ow-iw)/2:(oh-ih)/2,zoompan=z='min(zoom+0.00008,1.025)':d=${frames}:s=1440x900:fps=30,format=yuv420p" \
  -frames:v "$frames" \
  -c:v libx264 \
  -preset medium \
  -crf 20 \
  -pix_fmt yuv420p \
  -movflags +faststart \
  "$output"
