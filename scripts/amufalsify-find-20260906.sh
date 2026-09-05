#!/bin/bash
O=/Users/junkawasaki/github/com-junkawasaki/orgs/kotoba-lang/amu/docs/amufalsify-find-20260906.out
{
/usr/bin/find /Users/junkawasaki/github/com-junkawasaki/orgs/kotoba-lang/amu -maxdepth 4 \( -name '*cowork*' -o -name 'amu_cowork*' \) 2>/dev/null
echo "--- scripts dir:"
/bin/ls /Users/junkawasaki/github/com-junkawasaki/orgs/kotoba-lang/amu/scripts 2>&1
echo "--- git status:"
cd /Users/junkawasaki/github/com-junkawasaki/orgs/kotoba-lang/amu && /usr/bin/git status --short 2>&1 | /usr/bin/head -20
} > "$O" 2>&1
