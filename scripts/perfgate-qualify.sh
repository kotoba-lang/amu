#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
test "$#" -gt 0 || { echo "usage: perfgate-qualify.sh <benchmark.json> | --validate-manifest-v2 <manifest.json>" >&2; exit 2; }
exec clojure -Sdeps "$(cat <<'EOF'
{:paths ["scripts"]
 :deps {org.clojure/clojure {:mvn/version "1.12.0"}
        org.clojure/data.json {:mvn/version "2.5.1"}
        io.github.kotoba-lang/perfgate
        {:git/url "https://github.com/kotoba-lang/perfgate.git"
         :git/sha "d4417d77c2333047dd4e478675e5ed13e1c6b1b8"}
        io.github.kotoba-lang/machine
        {:git/url "https://github.com/kotoba-lang/machine.git"
         :git/sha "e7235657c6f6bc4e43e7e6126c1c0912e8dbf5f4"}}}
EOF
)" -M -m perfgate-qualify "$@"
