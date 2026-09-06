#!/bin/bash
/bin/uptime > /private/tmp/probe-load.txt 2>&1
echo "uptime-exit:$?" >> /private/tmp/probe-load.txt