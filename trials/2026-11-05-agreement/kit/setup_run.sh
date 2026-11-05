#!/bin/bash
# setup_run.sh <run-id> <D|E>: a neutrally named project as an adopter would have it
set -e; Y=/home/paradox/projects/data-mining-self-improvement/trials/2026-11-05-agreement; P=/tmp/pk-$1
rm -rf "$P"; mkdir -p "$P"; cp -r /tmp/pk2-kit/. "$P/"; cp $Y/kit/AGENTS.md $Y/kit/AGENTS-DM.md $Y/kit/QUICKREF.md "$P/"
printf '@AGENTS.md\n@AGENTS-DM.md\n@QUICKREF.md\n' > "$P/CLAUDE.md"
[ "$2" = E ] && { cp $Y/kit/DM1-QUICKREF.md "$P/"; echo '@DM1-QUICKREF.md' >> "$P/CLAUDE.md"; }
(cd "$P" && find data -type f -exec sha256sum {} + | sort -k2) > "$Y/out/hash-$1.txt"
