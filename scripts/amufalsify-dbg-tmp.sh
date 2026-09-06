#!/bin/sh
ls -la /tmp/amufalsify_jb.txt > /tmp/amufalsify_dbg.txt 2>&1
cat /tmp/amufalsify_jb.txt >> /tmp/amufalsify_dbg.txt 2>&1
ls /tmp | head -50 >> /tmp/amufalsify_dbg.txt 2>&1