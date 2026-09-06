#!/usr/bin/python3
import os
p = "/Users/junkawasaki/github/com-junkawasaki/orgs/kotoba-lang/amu/docs/codegen-coscientist.md"
t = open(p).read()
open("/private/tmp/amub_tail.txt","w").write(t[-9000:])
print("ok")
