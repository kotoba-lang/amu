;; The Mac diagnostic runtime implements arena-scope (JUN-546).
;;
;; The generated code calls context ABI slots 224 and 232, the scalar arena-scope enter and leave routines. The Mac
;; runtime keeps a bounded LIFO of its four allocator counters (pairs, pool, vector handles, vector items), refuses depth
;; 257 and any inconsistent restore with exit 70, and zeroes the vector items it releases. This gate compiles the
;; repository's scope oracles with the descriptor's compiler, packages them with its packager, signs and runs them
;; natively:
;;
;; * native-arena-scope.kotoba main: 600,000 scoped allocations that only fit if every counter is restored on leave,
;;   nested scopes, f64 results, outer data untouched (exit 0);
;; * deep-main: depth 256 (exit 0); overflow-main: depth 257 (exit 70, one line on stderr); unscoped-main: the same
;;   allocations without scopes must still be refused at the original budget (negative control, any non-zero exit but
;;   not 0);
;; * native-zero-watermark.kotoba: released vector items read back as zero;
;; * leave without enter (a raw main calling slot 232 first): exit 70;
;; * a positive control (a program without scopes) and the smallest scoped program.
;;
;; The compiler and packager are the descriptor's pinned images (the descriptor also pins the packager source, so a
;; runtime change moves through the JUN-545 staged run before this gate sees it). This stages and observes; compiler,
;; packager and the programs are native. Ported from check-macos-arena-scope.py (Basilisp, JUN-974).
;; Run: basilisp run -p scripts/seed scripts/seed/check-macos-arena-scope.cljc -- --output DIR
(ns check-macos-arena-scope
  (:require [basilisp.string :as str]
            [gate-util :as u]
            [macos-image :as image]
            [macos-native-lib :as mac]
            [macos-scope-build :as sb])
  (:import pathlib struct sys))

(def message "seed: arena-scope failed (Mac runtime)\n")
(def scope-oracle (.joinpath u/root "seed/tests/native-arena-scope.kotoba"))
(def zero-oracle (.joinpath u/root "seed/tests/native-zero-watermark.kotoba"))
(def plain "(ns plain (:export [main]))\n(defn main [] :i64 (if true 0 1))\n")
(def small "(ns small (:export [main]))\n(defn main [] :i64 (if (arena-scope true) 0 1))\n")
(def nested (str "(ns nested (:export [main]))\n" "(defn main [] :i64 (arena-scope (+ (arena-scope 40) 2)))\n"))

(defn main [output]
  (when-not (mac/available?) (mac/fail "Apple Silicon native host required"))
  (let [[compiler packager] (image/root-images)
        _ (mac/verify-macho compiler)
        _ (mac/verify-macho packager)
        _ (.mkdir output ** :parents false :mode 0700 :exist_ok false)
        runs (.joinpath output "runs")
        _ (.mkdir runs ** :mode 0700)
        stderr-of (fn [r] (.decode (.-stderr r) "utf-8" "replace"))]
    (doseq [[name source symbol expected refused] [["plain" plain "main" 0 false] ["small" small "main" 0 false]
                                                   ["nested" nested "main" 42 false]
                                                   ["scope-main" scope-oracle "main" 0 false]
                                                   ["scope-deep" scope-oracle "deep-main" 0 false]
                                                   ["scope-overflow" scope-oracle "overflow-main" 70 true]
                                                   ["zero-watermark" zero-oracle "main" 0 false]]]
      (let [img (sb/build compiler packager runs name source symbol)
            result (mac/native-run img runs [] :expected expected)
            stderr (stderr-of result)]
        (when (and refused (not= stderr message)) (mac/fail (str name ": failure text changed: " (pr-str stderr))))
        (when (and (not refused) (seq stderr)) (mac/fail (str name ": unexpected stderr " (pr-str stderr))))
        (println (str name ": exit " expected))
        (.flush sys/stdout)))
    ;; Leave without enter: no source form emits it, so the fixture is a six-word main
    ;; (stp x29,x30; mov x0,x7; ldr x16,[x0,#232]; blr x16; ldp; ret) packaged as raw.
    (.write_bytes (.joinpath runs "underflow.raw")
                  (.join (u/bytes-of) (python/list (for [word [0xa9bf7bfd 0xaa0703e0 0xf9407410 0xd63f0200 0xa8c17bfd 0xd65f03c0]]
                                                     (struct/pack "<I" word)))))
    (mac/native-run packager runs ["underflow-unsigned.macho" "underflow.raw" "fs2-cli-stdio-general" "0"])
    (mac/sign (.joinpath runs "underflow-unsigned.macho") (.joinpath runs "underflow.macho"))
    (let [result (mac/native-run (.joinpath runs "underflow.macho") runs [] :expected 70)]
      (when (not= (stderr-of result) message) (mac/fail "leave without enter did not report the scope failure")))
    (println "underflow: exit 70")
    (.flush sys/stdout)
    ;; Negative control: the same allocations without scopes must still be refused.
    (let [img (sb/build compiler packager runs "unscoped" scope-oracle "unscoped-main")
          result (mac/process [img] :cwd runs :timeout 600)]
      (println "unscoped-main exit" (.-returncode result))
      (.flush sys/stdout)
      (when (zero? (.-returncode result)) (mac/fail "unscoped allocations were not refused at the original budget")))
    (println "PASS_MAC_ARENA_SCOPE exit 0 controls, depth 257 -> 70, unscoped refused")
    (.flush sys/stdout)))

(defn -main [& args]
  (main (.resolve (pathlib/Path (or (u/opt args "--output") (sys/exit "--output is required"))))))

(when (some #(or (= % "check-macos-arena-scope.cljc") (str/ends-with? % "/check-macos-arena-scope.cljc")) sys/argv)
  (apply -main *command-line-args*))
