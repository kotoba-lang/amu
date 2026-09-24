export MAINT_REPO=kotoba-lang/aiueos
#!/bin/bash
# Shared signal for kotoba OSS maintainer bots (deterministic, timestamp-free).
ghq() { gh "$@" 2>/dev/null; }
echo "=== CI (last 5 runs: $MAINT_REPO) ==="
ghq run list --repo "$MAINT_REPO" --limit 5 --json conclusion,name,headBranch \
  | python3 -c 'import json,sys
d = json.load(sys.stdin)
for r in d:
    print(r.get("conclusion"), r.get("name"), "|", r.get("headBranch",""))'
echo "=== OPEN ISSUES ==="
ghq issue list --repo "$MAINT_REPO" --state open --limit 8 --json number,title \
  | python3 -c 'import json,sys
d = json.load(sys.stdin)
for i in d:
    print("#%s" % i["number"], i["title"][:80])'
echo "=== OPEN PRS ==="
ghq pr list --repo "$MAINT_REPO" --state open --limit 8 --json number,title \
  | python3 -c 'import json,sys
d = json.load(sys.stdin)
for p in d:
    print("#%s" % p["number"], p["title"][:80])'
echo "=== HOST LOAD ==="
uptime
