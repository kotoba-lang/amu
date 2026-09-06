#!/bin/sh
ls bench/runtime-comparison/ > /tmp/amufalsify_ls.txt 2>&1
ls bench/runtime-comparison/ | grep -i jb >> /tmp/amufalsify_ls.txt 2>&1