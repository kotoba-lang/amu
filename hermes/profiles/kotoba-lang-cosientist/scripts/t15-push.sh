#!/bin/bash
cd ~/github/com-junkawasaki/orgs/kotoba-lang/kotoba-sema
git fetch kotoba-lang > /tmp/t15-fetch.txt 2>&1 || true
git branch -f bot/lang-some-thread-canonical-20260906 ac5381a >> /tmp/t15-fetch.txt 2>&1
git push kotoba-lang ac5381a:refs/heads/bot/lang-some-thread-canonical-20260906 >> /tmp/t15-fetch.txt 2>&1
echo "push exit:$?" >> /tmp/t15-fetch.txt
tail -5 /tmp/t15-fetch.txt
