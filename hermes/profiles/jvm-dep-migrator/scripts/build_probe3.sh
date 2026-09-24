#!/bin/bash
# tick8 probe rebuild: gap probes for amu --jvm-free admitted-subset re-probe
set -u
D=/tmp/q9probe3
rm -rf "$D"; mkdir -p "$D"

cat > "$D/p01-cond.kotoba" <<'EOF'
(ns q9probe3.p01)
(defn f [x] (if (> x 10) 1 (if (> x 5) 2 3)))
(defn main [] 0)
EOF

cat > "$D/p02-cond-macro.kotoba" <<'EOF'
(ns q9probe3.p02)
(defn f [x] (cond (> x 10) 1 (> x 5) 2 :else 3))
(defn main [] 0)
EOF

cat > "$D/p03-bitshift.kotoba" <<'EOF'
(ns q9probe3.p03)
(defn f [x] (bit-shift-right x 1))
(defn main [] 0)
EOF

cat > "$D/p04-unsigned-shift.kotoba" <<'EOF'
(ns q9probe3.p04)
(defn f [x] (unsigned-bit-shift-right x 4))
(defn main [] 0)
EOF

cat > "$D/p05-str-alias.kotoba" <<'EOF'
(ns q9probe3.p05)
(defn f [x] (str x))
(defn main [] 0)
EOF

cat > "$D/p06-string-lit.kotoba" <<'EOF'
(ns q9probe3.p06)
(defn f [x] (string-concat "id-" x))
(defn main [] 0)
EOF

cat > "$D/p07-string-upper.kotoba" <<'EOF'
(ns q9probe3.p07)
(defn f [x] (string-upper x))
(defn main [] 0)
EOF

cat > "$D/p08-mapv.kotoba" <<'EOF'
(ns q9probe3.p08)
(defn f [x] (mapv (fn [v] (+ v 1)) x))
(defn main [] 0)
EOF

cat > "$D/p09-fn-literal.kotoba" <<'EOF'
(ns q9probe3.p09)
(defn f [x] (#(+ % 1) x))
(defn main [] 0)
EOF

cat > "$D/p10-vector-of-maps.kotoba" <<'EOF'
(ns q9probe3.p10)
(defn f [rows] (reduce (fn [acc r] (+ acc (get r :amount 0))) 0 rows))
(defn main [] 0)
EOF

cat > "$D/p11-conj-vector.kotoba" <<'EOF'
(ns q9probe3.p11)
(defn f [x v] (conj v x))
(defn main [] 0)
EOF

cat > "$D/p12-reduce-param-vector.kotoba" <<'EOF'
(ns q9probe3.p12)
(defn f [xs] (reduce + 0 xs))
(defn main [] 0)
EOF

cat > "$D/p13-reduce-bounded.kotoba" <<'EOF'
(ns q9probe3.p13)
(defn f [] (reduce + 0 [1 2 3]))
(defn main [] (f))
EOF

cat > "$D/p14-keys-fold.kotoba" <<'EOF'
(ns q9probe3.p14)
(defn f [m] (reduce (fn [acc k] (+ acc 1)) 0 (keys m)))
(defn main [] 0)
EOF

cat > "$D/p15-dyn-protocol.kotoba" <<'EOF'
(ns q9probe3.p15)
(defprotocol Matcher (match [this x]))
(defn f [m x] (match m x))
(defn main [] 0)
EOF

cat > "$D/p16-typed-map.kotoba" <<'EOF'
(ns q9probe3.p16)
(defn mk [a b] {:name a :limit b})
(defn get-limit [m] (get m :limit 0))
(defn main [] 0)
EOF

cat > "$D/p17-string-compare.kotoba" <<'EOF'
(ns q9probe3.p17)
(defn f [a b] (string=? a b))
(defn main [] 0)
EOF

cat > "$D/p18-fold-case.kotoba" <<'EOF'
(ns q9probe3.p18)
(defn f [x] (string-fold-case x))
(defn main [] 0)
EOF

cat > "$D/p19-min.kotoba" <<'EOF'
(ns q9probe3.p19)
(defn f [a b] (min a b))
(defn main [] 0)
EOF

cat > "$D/p20-into.kotoba" <<'EOF'
(ns q9probe3.p20)
(defn f [v] (into [] v))
(defn main [] 0)
EOF

echo "built $(/bin/ls "$D" | wc -l) probes in $D"
