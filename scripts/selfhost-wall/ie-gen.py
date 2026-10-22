#!/usr/bin/env python3
# Build the infer differential guest: infer.cljk verbatim (ns renamed, every defn private) + tail.cljk
import re,sys
SRC=sys.argv[1]; TAIL=sys.argv[2]; OUT=sys.argv[3]
s=open(SRC).read()
s=s.replace('(ns kotoba.compiler.frontend.infer\n','(ns kotoba.compiler.frontend.infer-guest\n',1)
m=re.search(r'\(ns [^\n]*\n  "(?:[^"\\]|\\.)*"',s)
s=s[:m.end()]+'\n  {:kotoba/export [ie-diff-run]}'+s[m.end():]
# every top-level defn private (the module is a closed guest; the linked export bound is 1024)
s=re.sub(r'(?m)^\(defn (?!-)','(defn- ',s)
open(OUT,'w').write(s+'\n'+open(TAIL).read())
