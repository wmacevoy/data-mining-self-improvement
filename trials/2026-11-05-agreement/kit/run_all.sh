#!/bin/bash
# Eight runs, four per arm, in random order, three at a time. Retries only a run with no finished result, and only once.
Y=/home/paradox/projects/data-mining-self-improvement/trials/2026-11-05-agreement
[ -f $Y/map.csv ] || python3 -c "
import random
a=list('DDDDEEEE'); random.SystemRandom().shuffle(a)
for i,x in enumerate(a,1): print(f's{i},{x}')" > $Y/map.csv
while IFS=, read -r id arm; do python3 $Y/kit/finished.py $Y/out/$id.jsonl 2>/dev/null || $Y/kit/setup_run.sh "$id" "$arm"; done < $Y/map.csv
cut -d, -f1 $Y/map.csv | while read -r id; do python3 $Y/kit/finished.py $Y/out/$id.jsonl 2>/dev/null || echo "$id"; done | xargs -r -P 3 -n 1 $Y/kit/run.sh
for id in $(cut -d, -f1 $Y/map.csv); do python3 $Y/kit/finished.py $Y/out/$id.jsonl || { echo "retrying $id"; $Y/kit/setup_run.sh "$id" "$(grep "^$id," $Y/map.csv | cut -d, -f2)"; $Y/kit/run.sh "$id"; }; done
echo "finished $(date +%T)"
