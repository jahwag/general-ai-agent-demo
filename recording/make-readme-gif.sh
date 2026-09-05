#!/usr/bin/env bash
set -euo pipefail

# This edit is specific to the 167-second synthetic ticket-5 demo recording.
# Keep the source video outside Git. Review the output before publishing it.
input=${1:?usage: make-readme-gif.sh SOURCE_VIDEO [OUTPUT_GIF]}
output=${2:-docs/media/cora-workflow.gif}
command -v ffmpeg >/dev/null
command -v gifsicle >/dev/null
mkdir -p "$(dirname "$output")"
raw_gif=$(mktemp --suffix=.gif)
trap 'rm -f -- "$raw_gif"' EXIT

ffmpeg -hide_banner -loglevel error -y -i "$input" -filter_complex "
[0:v]split=4[b][c][a][f];
[b]trim=start=6:end=12,setpts=(PTS-STARTPTS)/1.5,scale=960:600:flags=lanczos,pad=960:656:0:56:color=0x111827,drawtext=text='01  BookStack / Approved knowledge':fontcolor=white:fontsize=24:x=24:y=16,setsar=1[b1];
[c]trim=start=38:end=44,setpts=(PTS-STARTPTS)/2,scale=960:600:flags=lanczos,pad=960:656:0:56:color=0x111827,drawtext=text='02  Cora / Research and validate':fontcolor=white:fontsize=24:x=24:y=16,setsar=1[c1];
[a]trim=start=134:end=146,setpts=(PTS-STARTPTS)/2,scale=960:600:flags=lanczos,pad=960:656:0:56:color=0x111827,drawtext=text='03  AgentBus / Grounded action request':fontcolor=white:fontsize=24:x=24:y=16,setsar=1[a1];
[f]trim=start=151:end=158,setpts=PTS-STARTPTS,crop=960:600:65:225,scale=960:600:flags=lanczos,pad=960:656:0:56:color=0x111827,drawtext=text='04  Freshservice / Private note published':fontcolor=white:fontsize=24:x=24:y=16,setsar=1[f1];
[b1][c1][a1][f1]concat=n=4:v=1:a=0,fps=6,split[v][p];
[p]palettegen=max_colors=128:stats_mode=diff[palette];
[v][palette]paletteuse=dither=none:diff_mode=rectangle[out]
" -map '[out]' -loop 0 "$raw_gif"

gifsicle -O3 --lossy=40 --colors 96 --resize-width 800 "$raw_gif" -o "$output"
