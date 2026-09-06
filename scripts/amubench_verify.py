#!/usr/bin/python3
t = open("/Users/junkawasaki/github/com-junkawasaki/orgs/kotoba-lang/amu/docs/codegen-coscientist.md").read()
i = t.rfind("2026-09-06 09:36 JST (amu-bench cron)")
open("/private/tmp/amub_verify.txt", "w").write(t[i:i+200] if i >= 0 else "NOT FOUND")
print("ok", i)
