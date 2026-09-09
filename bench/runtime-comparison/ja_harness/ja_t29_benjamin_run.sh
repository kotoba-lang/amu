#!/bin/zsh
# amu-jit tick 29: J-A dispatch-share 5-rep run on benjamin (quiet host).
# Feeds perfgate.core/qualify with >=5 samples for the inclusive share claim.
set -u
cd ~/ja_t29
JAVA=/opt/homebrew/opt/openjdk/bin/java   # OpenJDK 26.0.1
CJ=./wasm-1.7.5.jar:./runtime-1.7.5.jar:.
{ echo "START $(date '+%F %T %Z')"; uptime; } > run4.log
for R in 1 2 3 4 5; do
  echo "=== rep$R $(date '+%F %T %Z') load=$(uptime | awk -F'load averages:' '{print $2}') ===" >> run4.log
  $JAVA -cp "$CJ" JaJfrDispatchShareV2FIX ./kernel.kotoba.wasm 100 200 5 60 >> run4.log 2>&1
  echo "rep$R exit=$?" >> run4.log
  iostat -c 2 | tail -2 >> run4.log 2>&1
done
echo "DONE $(date '+%F %T %Z')" >> run4.log
