#!/bin/bash
for n in 363 365 366 367; do
  echo "-- PR $n"
  gh pr view $n -R cloud-kotoba/app-kotoba-cloud --json mergeable,mergeStateStatus,author,updatedAt --jq '{mergeable,mergeStateStatus,author:.author.login,updatedAt}' 2>&1
done
echo "-- /en/ redirect"
curl -s -o /dev/null -w "%{redirect_url}\n" --max-time 15 https://kotoba.cloud/en/
