#!/bin/bash
/bin/echo "=== date: $(/bin/date '+%Y-%m-%d %H:%M:%S %z')"
/usr/bin/uptime
echo "=== loadavg raw: $(/bin/cat /proc/loadavg 2>/dev/null || /usr/sbin/sysctl -n vm.loadavg 2>/dev/null)"
echo "=== ls bin:"
/bin/ls /Users/junkawasaki/github/com-junkawasaki/orgs/kotoba-lang/amu/bin 2>&1 | /usr/bin/head -20
echo "=== amu_cowork_state:"
/bin/bash /Users/junkawasaki/github/com-junkawasaki/orgs/kotoba-lang/amu/bin/amu_cowork_state.sh 2>&1 | /usr/bin/head -40
