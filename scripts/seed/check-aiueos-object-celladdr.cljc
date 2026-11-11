;; The aiueos kernel object route can hand out the address of a data cell (JUN-556 D6, ADR 0382).
;;
;; A private function cell-addr-<k> [] (k canonical decimal below 64, body the placeholder 0) returns the address of
;; cell k: `lea rax,[rip+disp32]` with an R_X86_64_PC32 relocation against the context symbol, addend 80 + 8k - 4, the
;; same relocation as a cell access. It is how an extern function is given somewhere to write: the cells k, k+1, ...
;; the function also loads are the region, and .data holds exactly the cells some stub names. The address is an
;; ordinary value, not a rooted base, so no window access and no record access accepts it.
;; Compiles sources with a native Amu compiler and reads the objects back with the independent ELF parser
;; (aiueos_object_lib/read-elf). Positive: an export that passes cell-addr-1 to a declared extern and reads cells 1
;; and 2; the lea site is checked byte by byte and its relocation (offset, PC32, addend 84) is found exactly once.
;; Refused: a malformed name or a parameter (E7102), the address used as a window base or a record base (E7106), the
;; image route (E7102). In every refusal nothing is written.
;; No x86 machine ran this object in this gate; the QEMU differential check in the kotoba repository runs the consumer.
;; Ported from check-aiueos-object-celladdr.py (Basilisp, JUN-974).
;; Run: basilisp run -p scripts/seed scripts/seed/check-aiueos-object-celladdr.cljc -- --compiler C --output DIR
(ns check-aiueos-object-celladdr
  (:require [basilisp.string :as str]
            [aiueos-object-lib :as lib]
            [gate-util :as u]
            [macos-native-lib :as mac])
  (:import sys))

(def positive
  (str "(ns celladdr (:export [f]))\n"
       "(defn- extern-sink [a :i64] :i64 0)\n"
       "(defn- cell-addr-1 [] :i64 0)\n(defn- cell-load-1 [] :i64 0)\n(defn- cell-load-2 [] :i64 0)\n"
       "(defn f [x :i64] :i64 (+ (extern-sink (cell-addr-1)) (+ (cell-load-1) (cell-load-2))))\n"))
(def lea (u/hex->bytes "488d0500000000"))
(def context-pc32 (bit-or (bit-shift-left 1 32) 2))
(defn refused-source
  ([decl call] (refused-source decl call "x :i64"))
  ([decl call params]
   (str "(ns r (:export [f]))\n(defn- extern-sink [a :i64] :i64 0)\n" decl "\n(defn f [" params "] :i64 " call ")\n")))
(def cases-7102
  [["k-64" (refused-source "(defn- cell-addr-64 [] :i64 0)" "(extern-sink (cell-addr-64))")]
   ["leading-zero" (refused-source "(defn- cell-addr-01 [] :i64 0)" "(extern-sink (cell-addr-01))")]
   ["not-a-number" (refused-source "(defn- cell-addr-x [] :i64 0)" "(extern-sink (cell-addr-x))")]
   ["with-param" (refused-source "(defn- cell-addr-1 [v :i64] :i64 0)" "(extern-sink (cell-addr-1 x))")]
   ["body-not-zero" (refused-source "(defn- cell-addr-1 [] :i64 7)" "(extern-sink (cell-addr-1))")]])
(def cases-7106
  [["address-as-window-base" (refused-source "(defn- cell-addr-1 [] :i64 0)" "(kernel-load-u32 (cell-addr-1) n 0)" "n :i64")]
   ["address-as-record-base" (refused-source "(defn- cell-addr-1 [] :i64 0)\n(defn- record-load-u32-0-40 [b :i64] :i64 0)"
                                              "(record-load-u32-0-40 (cell-addr-1))")]])

(defn check [path]
  (let [obj (lib/read-elf path)
        text (:text obj)]
    (when (not= 1 (.count text lea))
      (mac/fail (str "expected exactly one lea rax,[rip+0], found " (.count text lea))))
    (let [site (+ (.index text lea) 3)
          addends (sort (for [[off info a] (:relas obj) :when (and (= off site) (= info context-pc32))] a))]
      (when (not= addends [(- (+ 80 (* 8 1)) 4)])
        (mac/fail (str "the lea site " site " has relocations " addends ", want one PC32 against context with addend 84")))
      (let [others (sort (for [[off info a] (:relas obj) :when (and (= info context-pc32) (not= off site) (not= a -4))] [off a]))]
        (when (not= (sort (map second others)) [84 92])
          (mac/fail (str "cell access relocations " others ", want addends 84 and 92")))))))

(defn main [compiler output]
  (lib/start! compiler output)
  (let [report (u/pydict)
        [_ path] (lib/compile-source compiler output "celladdr" positive)]
    (check path)
    (.__setitem__ report "celladdr" (u/pydict "bytes" (.-st_size (.stat path))))
    (doseq [[name src] cases-7102] (lib/check-refusals! compiler output report [[name src]] "E7102"))
    (doseq [[name src] cases-7106] (lib/check-refusals! compiler output report [[name src]] "E7106"))
    (.write_text (.joinpath output "image.kotoba")
                 "(ns i (:export [main]))\n(defn- cell-addr-1 [] :i64 0)\n(defn main [] :i64 (cell-addr-1))\n")
    (let [result (mac/native-run compiler output ["compile" "image.kotoba" "--target" "x86_64-aiueos-kernel-v1" "--artifact" "image"
                                                  "--output" "image.elf" "--fuel" "1024"] :expected 1)]
      (when (or (.exists (.joinpath output "image.elf")) (not (.__contains__ (lib/message-of result) "E7102")))
        (mac/fail "a cell-addr declaration on the image route was not refused with E7102"))
      (.__setitem__ report "image" "refused E7102"))
    (lib/emit! output report "PASS_AIUEOS_OBJECT_CELLADDR")))

(defn -main [& args] (lib/cli-main args main))

(when (some #(or (= % "check-aiueos-object-celladdr.cljc") (str/ends-with? % "/check-aiueos-object-celladdr.cljc")) sys/argv)
  (apply -main *command-line-args*))
