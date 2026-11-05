#!/bin/bash
# setup_run.sh <run-id> <A|B|C>: a neutrally named project with that arm's references loaded
set -e; D=/tmp/claude-1000/-home-paradox-projects-data-mining/e8e5bcab-5a43-4beb-9fa9-c8457b403226/scratchpad; T=$D/trial; R=/tmp/pk-$1; REPO=/home/paradox/projects/data-mining
rm -rf "$R"; mkdir -p "$R/refs"; cp -r $T/kit/. "$R/"
cp $REPO/vendor/se1/QUICKREF.md "$R/refs/SE1-QUICKREF.md"
{ echo "The team's reference for how we work is below. Read it; it applies to this project."; echo; echo "@refs/SE1-QUICKREF.md"; } > "$R/CLAUDE.md"
case $2 in
  B) cp $D/DM1-QUICKREF-2.md "$R/refs/DM1-QUICKREF.md"; echo "@refs/DM1-QUICKREF.md" >> "$R/CLAUDE.md";;
  C) mkdir "$R/refs/dm1"; cp $REPO/guide/*.md "$R/refs/dm1/"; for f in "$R"/refs/dm1/*.md; do echo "@refs/dm1/$(basename "$f")" >> "$R/CLAUDE.md"; done;;
esac
(cd "$R" && find data -type f -exec sha256sum {} + | sort -k2) > "$T/hash-$1.txt"
