#!/usr/bin/env python3
# Strip accidental <file>...</file> markup tags from tick-201 entry text.
import io
path = "/Users/junkawasaki/github/com-junkawasaki/orgs/kotoba-lang/amu/docs/codegen-coscientist.md"
with io.open(path, "r", encoding="utf-8") as f:
    s = f.read()
s = s.replace("<file>ls scripts/quiet-host.cljs</file>", "ls scripts/quiet-host.cljs")
s = s.replace("<file>ls scripts/remote-bench.cljs</file>", "ls scripts/remote-bench.cljs")
with io.open(path, "w", encoding="utf-8") as f:
    f.write(s)
print("cleaned")