#!/bin/bash
set -e
cd ~/github/com-junkawasaki/orgs/kotoba-lang/kotoba-lang
cat >> jvm-dep-ledger.edn << 'EDN_EOF'

 :re-probe-20260905-tick15
 {:as-of "2026-09-05 tick 15 (amu local HEAD 771f3728 = 6 commits behind origin/main 197bdc95; kotoba-lang main ac9f855; sema pin 63d76616 unchanged - pin is still ancestor of sema local HEAD 3ae4959)"
  :method "amu/bin/amu check --jvm-free key blocker probes re-measure (bit-shift p_bsl/p_ubsr/p_bitshift, keys p_keys/p_keys2/p_keys3, contains? p_contains/p_contains2, vector-take p_vt/p_vector_take, pop p_pop) + machine m10 regression + sema pin ancestry merge-base check"
  :result "PASS: p_keys2 (keys on typed map, check only) p_contains2 p_vt p_vector_take p_pop m10. FAIL (exit 65 subset-reject): p_bsl p_ubsr p_bitshift (bit-shift left/right/unsigned all no lowering), p_keys (keys on bounded keyword map literal, :keys-receiver), p_keys3, p_contains (contains? on keyword map). PASS/FAIL set identical to tick12-14, zero diff"
  :pin-status "sema pin 63d76616 confirmed ancestor of sema repo local HEAD (3ae4959, bot/sema-grammar-resync-9d701ea9) via merge-base - string-upper lowering (145e8b5) still ahead of pin, unconnected. bit-shift lowering also unlanded (standing blocker)"
  :verdict "subset unchanged (sema pin advance is the only forward path). no whole-component migration candidate - machine (tick14) blockers (folds/set ops/string compare/serialization) also unchanged. no migration this tick"}
EDN_EOF
git checkout -b bot/ledger-tick15-20260905
git add jvm-dep-ledger.edn
git commit -m "ledger: tick15 re-probe (subset unchanged, sema pin 63d76616 still held)"
git push -u origin bot/ledger-tick15-20260905 2>&1 | tail -3
