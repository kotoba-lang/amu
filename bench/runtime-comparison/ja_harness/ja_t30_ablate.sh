#!/bin/zsh
# amu-jit tick 30: J-A leaf-attribution stability ablation on benjamin.
# Question (tick-27 caveat (a)): is the dominant JFR LEAF name an artifact of
# JIT inlining across tiers? Ablate the compiler:
#   ABL1 = -XX:-Inline           (full tiering, inlining off)
#   ABL2 = -XX:TieredStopAtLevel=1 (C1-only, interpreter + shallow compile)
# Baseline = tick-29 5 reps, default flags (full tiering): leaf
#   InterpreterMachine.numberOfParams 75.3-80.2%, StackFrame.<init> 7.6-10.5%,
#   eval 3.0-5.1%, call 3.2-3.7%, ValType.sizeOf 2.5-3.2%,
#   doControlTransfer 0.7-1.5%; on-stack call 98.2-99.2%, eval 82.0-84.4%.
# Short 20s records (diagnostic; tick-29 5x60s already sealed for the quiet run).
set -u
cd ~/ja_t29
JAVA=/opt/homebrew/opt/openjdk/bin/java
CJ=./wasm-1.7.5.jar:./runtime-1.7.5.jar:.
{ echo "START $(date '+%F %T %Z')"; uptime; } > ablate_t30.log
for R in 1 2; do
  echo "=== ABL1-noInline rep$R $(date '+%T') load=$(uptime | awk -F'load averages:' '{print $2}') ===" >> ablate_t30.log
  $JAVA -XX:-Inline -cp "$CJ" JaJfrDispatchShareV2FIX ./kernel.kotoba.wasm 100 200 5 20 >> ablate_t30.log 2>&1
  echo "ABL1-r$R exit=$?" >> ablate_t30.log
  echo "=== ABL2-c1only rep$R $(date '+%T') load=$(uptime | awk -F'load averages:' '{print $2}') ===" >> ablate_t30.log
  $JAVA -XX:TieredStopAtLevel=1 -cp "$CJ" JaJfrDispatchShareV2FIX ./kernel.kotoba.wasm 100 200 5 20 >> ablate_t30.log 2>&1
  echo "ABL2-r$R exit=$?" >> ablate_t30.log
done
uptime >> ablate_t30.log
echo "DONE $(date '+%F %T %Z')" >> ablate_t30.log
