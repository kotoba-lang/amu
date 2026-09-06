#!/bin/sh
uptime > /tmp/amufalsify_load.txt 2>&1
date >> /tmp/amufalsify_load.txt
sysctl -n vm.loadavg >> /tmp/amufalsify_load.txt 2>&1