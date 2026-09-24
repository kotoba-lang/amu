#!/bin/bash
for u in https://docs.kotoba.cloud/ https://docs.kotoba.cloud/graph/ https://kotoba.cloud/llms.txt https://kotoba.cloud/agent-quickstart.md https://twin.kotoba.cloud/ https://boot.kotoba.cloud/ ; do
  echo -n "$u -> "; curl -s -o /dev/null -w "%{http_code}\n" --max-time 15 "$u"
done
