#!/bin/bash
# run.sh <run-id>: one headless session in its project, inside the sandbox; the transcript stays outside it
R=/home/paradox/projects/data-mining-self-improvement; Y=$R/trials/2026-11-05-agreement
CL=$(readlink -f "$HOME/.local/bin/claude")
export SANDBOX_PYTHON=/tmp/pk-env SANDBOX_CLAUDE_DIR=$HOME/.local/share/claude SANDBOX_CREDENTIALS=$HOME/.claude/.credentials.json
PATH=/tmp/pk-env/bin:$PATH CLAUDE_CODE_DISABLE_AUTO_MEMORY=1 timeout 2400 $R/sandbox/bwrap-run.sh /tmp/pk-$1 "$CL" -p "$(cat $Y/kit/TASK.txt)" --model claude-sonnet-5-5 --setting-sources project --strict-mcp-config --no-session-persistence --disable-slash-commands --permission-mode dontAsk --allowedTools "Read,Write,Edit,Glob,Grep,Bash" --disallowedTools "Agent,WebFetch,WebSearch,Skill" --output-format stream-json --verbose < /dev/null > $Y/out/$1.jsonl 2> $Y/out/$1.err
echo "exit $? $(date +%T)" > $Y/out/$1.done
