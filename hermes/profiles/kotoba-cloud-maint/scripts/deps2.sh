#!/bin/bash
{
echo "noble: $(npm view @noble/post-quantum version 2>&1)"
echo "shadow-cljs: $(npm view shadow-cljs version 2>&1)"
echo "worker deploy check (etag/date of /):"
curl -sI --max-time 15 https://kotoba.cloud/ | grep -iE "^(etag|last-modified|cf-ray|age|date):" | head -6
} > ~/.hermes/profiles/kotoba-cloud-maint/scripts/deps2.txt 2>&1
exit 0
