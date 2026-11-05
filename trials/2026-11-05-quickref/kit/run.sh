#!/bin/bash
# run.sh <run-id> [prompt-file]: one headless session in its project, transcript kept outside it
D=/tmp/claude-1000/-home-paradox-projects-data-mining/e8e5bcab-5a43-4beb-9fa9-c8457b403226/scratchpad; T=$D/trial; mkdir -p $T/out
cd /tmp/pk-$1 || exit 9
PATH=/tmp/pk-env/bin:$PATH CLAUDE_CODE_DISABLE_AUTO_MEMORY=1 timeout 2400 claude -p "$(cat ${2:-$T/TASK.txt})" --model claude-sonnet-5-5 --setting-sources project --strict-mcp-config --no-session-persistence --disable-slash-commands --permission-mode dontAsk --allowedTools "Read,Write,Edit,Glob,Grep,Bash" --disallowedTools "Agent,WebFetch,WebSearch,Skill" --output-format stream-json --verbose < /dev/null > $T/out/$1.jsonl 2> $T/out/$1.err
echo "exit $? $(date +%T)" > $T/out/$1.done
