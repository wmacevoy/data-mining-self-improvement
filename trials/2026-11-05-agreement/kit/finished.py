#!/usr/bin/env python3
"""Exit 0 if a stream-json transcript holds a result that is not an error."""
import json, sys
for line in open(sys.argv[1], encoding="utf-8"):
    try:
        o = json.loads(line)
    except ValueError:
        continue
    if o.get("type") == "result" and o.get("is_error") is False:
        sys.exit(0)
sys.exit(1)
