#!/bin/bash
# kotoba.cloud health probe
echo "date: $(date)"
for u in "https://kotoba.cloud/" "https://kotoba.cloud/en/" "https://kotoba.cloud/health" "https://kotoba.cloud/.well-known/kotoba-cloud.json" "https://kotoba.cloud/no-such-page-xyz" "https://kotoba.cloud/404-page" "https://api.kotoba.cloud/v1/control-plane"; do
  code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 20 "$u")
  echo "$code $u"
done
curl -s --max-time 20 https://kotoba.cloud/health | head -c 300
echo
echo "git:"
cd ~/github/com-junkawasaki/orgs/kotoba-lang/app-kotoba-cloud
git status -sb | head -3
git log --oneline -3
