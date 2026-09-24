#!/bin/bash
# t15 fail-closed messages + sema regression suite
grep -o "requires an initial option[^\"]*" /tmp/langcos/chk-t15-fail0.txt /tmp/langcos/chk-t15-fail0l.txt > /tmp/t15-fc2.txt 2>&1
CP=$(cat /tmp/langcos/cp-t15.txt)
CP2="$CP:/tmp/langcos/sema-t15/test"
cd /tmp/langcos/sema-t15
node --stack-size=4096 ~/github/com-junkawasaki/orgs/kotoba-lang/amu/node_modules/nbb/cli.js --classpath "$CP2" run-tests.cljs > /tmp/langcos/t15-sema-tests.txt 2>&1
echo "tests exit:$?" >> /tmp/langcos/t15-sema-tests.txt
grep -E 'tests,|assertions,|failures|errors' /tmp/langcos/t15-sema-tests.txt | tail -6 >> /tmp/langcos/t15-sema-tests.txt
