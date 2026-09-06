#!/bin/bash
OUT=/Users/junkawasaki/github/com-junkawasaki/orgs/kotoba-lang/amu/docs/amufalsify-probe.txt
{
date
sysctl -n vm.loadavg
pwd
} > "$OUT" 2>&1
