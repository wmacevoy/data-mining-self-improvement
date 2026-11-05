#!/bin/bash
# Nine runs, three per arm, in random order, three at a time. Run IDs hide the arm; the map stays here.
T=/tmp/claude-1000/-home-paradox-projects-data-mining/e8e5bcab-5a43-4beb-9fa9-c8457b403226/scratchpad/trial
[ -f $T/map.csv ] || python3 - > $T/map.csv <<'PY'
import random
arms = list("AAABBBCCC"); random.SystemRandom().shuffle(arms)
for i, a in enumerate(arms, 1): print(f"r{i},{a}")
PY
while IFS=, read -r id arm; do $T/setup_run.sh "$id" "$arm"; done < $T/map.csv
cut -d, -f1 $T/map.csv | xargs -P 3 -n 1 $T/run.sh
# one retry for any run the API cut short
for id in $(cut -d, -f1 $T/map.csv); do
  python3 $T/finished.py $T/out/$id.jsonl || { echo "retrying $id"; arm=$(grep "^$id," $T/map.csv | cut -d, -f2); $T/setup_run.sh "$id" "$arm"; $T/run.sh "$id"; }
done
echo "finished $(date +%T)"; for id in $(cut -d, -f1 $T/map.csv); do printf '%s ' "$id"; cat $T/out/$id.done; done
