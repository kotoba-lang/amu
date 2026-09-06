#!/bin/bash
uptime
sysctl vm.loadavg
ps -A -o %cpu | awk '{s+=$1} END {print "sum_cpu_percent:", s}'
sysctl -n hw.ncpu
date '+%Y-%m-%d %H:%M:%S %z'
