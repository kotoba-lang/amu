cd ~/github/wt/aiueos-maint-273 && timeout 900 clojure -M:ci > /tmp/ci-test-run.txt 2>&1; echo "exit=$?" >> /tmp/ci-test-run.txt; tail -5 /tmp/ci-test-run.txt >> /tmp/ci-test-tail.txt
