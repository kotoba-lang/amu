#!/bin/bash
F=/Users/junkawasaki/github/com-junkawasaki/orgs/kotoba-lang/amu/docs/codegen-coscientist.md
grep -n 'H-B' "$F" > /Users/junkawasaki/github/com-junkawasaki/orgs/kotoba-lang/amu/docs/amufalsify-grep.txt 2>&1
echo "exit=$?" >> /Users/junkawasaki/github/com-junkawasaki/orgs/kotoba-lang/amu/docs/amufalsify-grep.txt
