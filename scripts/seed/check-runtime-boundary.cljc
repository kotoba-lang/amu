;; JUN-325: guests cannot call or acquire static runtime functions. JUN-336: the runtime cannot call a guest
;; definition that shadows an R1 head. Only native Amu compilers compile sources; this stages bytes, launches
;; processes and compares receipts. Never execute a previously admitted exploit. The caller supplies a fresh
;; disposable output directory. Ported from check-runtime-boundary.py (Basilisp, JUN-974).
;; Run (Linux): basilisp run -p scripts/seed scripts/seed/check-runtime-boundary.cljc -- --compiler F --output DIR
;;      [--previous-root F] [--definition-only-root F] [--payload KSEED]
(ns check-runtime-boundary
  (:require [basilisp.string :as str]
            [gate-util :as u])
  (:import json operator pathlib platform re subprocess sys))

(def root u/root)
(defn rp [rel] (pathlib/Path root rel))
(defn g [m & ks] (reduce (fn [a k] (operator/getitem a k)) m ks))
(defn pin [p] (let [d (.read_bytes (pathlib/Path p))] (u/pydict "bytes" (python/len d) "sha256" (u/sha256-hex d))))
(defn chk [c m] (u/chk c (str m)))
(defn pyenv [& kvs] (apply u/pydict kvs))
(defn b [x] (.encode x "utf-8"))
(defn guest [body] (str "(ns g (:export [main]))\n(defn main [] :i64 " body ")\n"))

(def probes [["syscall", "(kxrt-syscall 172 0 0 0 0 0 0)"], ["load64", "(kxrt-load64 4194304)"], ["store64", "(kxrt-store64 4194304 0)"], ["load8", "(kxrt-load8 4194304)"], ["store8", "(kxrt-store8 4194304 0)"], ["ctx", "(kxrt-ctx)"], ["call-main", "(kxrt-call-main 0)"], ["trap", "(kxrt-trap 0)"], ["call-at", "(kxrt-call-at 0 0 0)"], ["exit", "(kxrt-exit 9)"], ["gl", "(kxrt-gl 72)"], ["gs", "(kxrt-gs 72 0)"], ["allow-bit", "(kxrt-allow-bit 20)"], ["map", "(kxrt-map 4096)"], ["slot-56", "(kxrt-slot-56 0 0 0)"], ["fn-ref-invoke", "(invoke (fn-ref kxrt-exit) 42)"], ["fn-ref-alias", "(let [f (fn-ref kxrt-exit)] (invoke f 42))"], ["bare-alias", "(let [f kxrt-exit] (invoke f 42))"], ["fn-ref-only", "(let [f (fn-ref kxrt-exit)] 42)"], ["fn-ref-ctx", "(invoke (fn-ref kxrt-ctx))"], ["fn-ref-slot", "(invoke (fn-ref kxrt-slot-56) 0 0 0)"], ["qualified-call", "(clojure.core/kxrt-exit 42)"], ["qualified-fn-ref", "(invoke (fn-ref clojure.core/kxrt-exit) 42)"], ["nested-call", "(let [f (fn [x] (kxrt-exit x))] (invoke f 42))"], ["allow-mask", "(let [c (kxrt-ctx) a (kxrt-store64 (+ c 16) -1)] (string-length (typed-cap-call :hash/sha256 :string :string \"x\")))"]])
(def shadows [["shadow-inc", "(defn inc [x :i64] :i64 (+ x 1))\n(defn main [] :i64 (inc 41))\n"], ["shadow-dec", "(defn dec [x :i64] :i64 (- x 1))\n(defn main [] :i64 (dec 43))\n"], ["shadow-not-eq", "(defn not= [a :i64 b :i64] :bool (if (= a b) false true))\n(defn main [] :i64 (if (not= 1 2) 42 0))\n"]])
(def src-shadow-unused "(ns g (:export [main]))\n(defn assoc [x :i64] :i64 (+ x 1))\n(defn main [] :i64 (assoc 41))\n")
(def src-plain "(ns plain (:export [main]))\n(defn- add [x :i64] :i64 (+ x 1))\n(defn main [] :i64 (let [f (fn-ref add) k 1 g (fn [x] (+ x k))] (+ (invoke f 20) (invoke g 20))))\n")
(def formats [["aarch64-linux", "static"], ["aarch64-linux", "runner"], ["aarch64-linux", "launcher"], ["x86_64-linux", "static"], ["x86_64-linux", "kx64-runner"], ["x86_64-linux", "launcher"]])

(defn run-main [compiler output previous-root payload definition-only-root]
  (chk (= (platform/system) "Linux") "run on native Linux")
  (.mkdir output ** :parents true :exist_ok false)
  (let [art (pathlib/Path output "artifacts")
        _ (.mkdir art)
        producers (reduce (fn [m [who source]]
                            (let [dst (pathlib/Path art (str who ".elf"))]
                              (.write_bytes dst (.read_bytes source))
                              (.chmod dst 0755)
                              (assoc m who dst)))
                          {}
                          (concat [["new" compiler]] (when previous-root [["previous" previous-root]])
                                  (when definition-only-root [["definition-only" definition-only-root]])))
        payload (when payload
                  (let [dst (pathlib/Path art "payload.kseed")] (.write_bytes dst (.read_bytes payload)) dst))
        calls (python/list [])
        compile- (fn [who name source target fmt]
                   (let [src (pathlib/Path art (str who "-" name "-" target "-" fmt ".kotoba"))
                         dst (.with_suffix src ".image")
                         _ (.write_text src source)
                         argv (concat [(get producers who) "compile" src "--target" target "--output" dst "--format" fmt]
                                      (when (= fmt "packed") ["--payload" payload]))
                         r (subprocess/run (python/list (map str argv)) ** :cwd art :env (pyenv "PATH" "/nonexistent" "KEXE_CAP_RESOURCES_35" (str art))
                                           :capture_output true :timeout 900)]
                     (.write_bytes (.with_suffix src ".stdout") (.-stdout r))
                     (.write_bytes (.with_suffix src ".stderr") (.-stderr r))
                     (.append calls (pyenv "compiler" who "name" name "target" target "format" fmt "exit" (.-returncode r)
                                           "diagnostic" (.strip (.decode (.-stderr r) "utf-8" "replace"))
                                           "image" (when (.exists dst) (pin dst))))
                     (.write_text (pathlib/Path output "calls.json") (u/json-dump calls))
                     [r dst]))
        last-call (fn [] (operator/getitem calls -1))
        host-target (get {"aarch64" "aarch64-linux" "arm64" "aarch64-linux" "x86_64" "x86_64-linux"} (platform/machine))
        formats (concat formats (when payload [[host-target "packed"]]))
        refused (python/list [])
        positives (python/list [])]
    (doseq [[target fmt] formats]
      (doseq [[name body] probes]
        (let [[r dst] (compile- "new" name (guest body) target fmt)
              ;; A bare private function symbol is already rejected by name resolution; explicit fn-ref must reach the backend boundary.
              diagnostic (if (= name "bare-alias") "E2102" "E7101")]
          (chk (and (not= (.-returncode r) 0) (u/has-bytes? (b diagnostic) (.-stderr r)) (not (.exists dst))) (last-call))
          (.append refused (pyenv "name" name "target" target "format" fmt "diagnostic" diagnostic))))
      (doseq [[name body] shadows]
        (let [[r dst] (compile- "new" name (str "(ns g (:export [main]))\n" body) target fmt)]
          (chk (and (not= (.-returncode r) 0) (u/has-bytes? (b "E7101") (.-stderr r)) (not (.exists dst))) (last-call))
          (.append refused (pyenv "name" name "target" target "format" fmt "diagnostic" "E7101"))))
      (let [[r dst] (compile- "new" "shadow-unused" src-shadow-unused target fmt)]
        (chk (and (= (.-returncode r) 0) (zero? (python/len (.-stderr r))) (.exists dst)) (last-call)))
      (let [[r dst] (compile- "new" "plain" src-plain target fmt)
            _ (chk (and (= (.-returncode r) 0) (zero? (python/len (.-stderr r))) (.exists dst)) (last-call))
            same (when previous-root
                   (let [[r old] (compile- "previous" "plain" src-plain target fmt)]
                     (if (and (= fmt "launcher") (= (.-returncode r) 2) (u/has-bytes? (b "E7100") (.-stderr r)))
                       "n/a: the previous root has no --format launcher"
                       (do (chk (and (= (.-returncode r) 0) (zero? (python/len (.-stderr r))) (u/deq (.read_bytes old) (.read_bytes dst))) (last-call))
                           true))))]
        (.append positives (pyenv "target" target "format" fmt "image" (pin dst) "sameBytes" same))))
    (let [previous (python/list [])]
      (when previous-root
        (doseq [name ["syscall" "fn-ref-invoke"]]
          (let [body (second (first (filter #(= (first %) name) probes)))
                [r dst] (compile- "previous" name (guest body) "aarch64-linux" "static")
                admitted (and (= (.-returncode r) 0) (.exists dst))]
            (if (= name "syscall")
              (chk admitted (last-call))
              (chk (or admitted (and (not= (.-returncode r) 0) (u/has-bytes? (b "E7101") (.-stderr r)) (not (.exists dst)))) (last-call)))
            (.append previous (pyenv "compiler" "previous" "name" name "admitted" admitted "executed" false))))
        ;; Negative control: a root before JUN-336 admits the shadow (recorded, never executed). Pass a pre-JUN-336 root
        ;; as --previous-root; a later one refuses and fails here.
        (let [[r dst] (compile- "previous" "shadow-inc" (str "(ns g (:export [main]))\n" (second (first (filter #(= (first %) "shadow-inc") shadows)))) "aarch64-linux" "static")]
          (chk (and (= (.-returncode r) 0) (.exists dst)) (last-call))
          (.append previous (pyenv "compiler" "previous" "name" "shadow-inc" "admitted" true "executed" false))))
      (when definition-only-root
        (let [[r dst] (compile- "definition-only" "fn-ref-invoke" (guest (second (first (filter #(= (first %) "fn-ref-invoke") probes)))) "aarch64-linux" "static")]
          (chk (and (= (.-returncode r) 0) (.exists dst)) (last-call))
          (.append previous (pyenv "compiler" "definition-only" "name" "fn-ref-invoke" "admitted" true "executed" false))))
      ;; The closest runtime corpus: same result, fuel, and refusals as the repository's immutable expectations.
      ;; Only the native host ISA executes.
      (let [cases (python/list [])]
        (doseq [case (g (json/loads (.read_text (rp "seed/static-cases.json"))) "cases")]
          (let [n (g case "name")
                [r dst] (compile- "new" (str "case-" n) (g case "source") host-target "static")
                _ (chk (and (= (.-returncode r) 0) (zero? (python/len (.-stderr r)))) (last-call))
                _ (.chmod dst 0755)
                r (subprocess/run (python/list [(str dst)]) ** :cwd art :env (pyenv "PATH" "/nonexistent" "KEXE_STRUCTURED_REPORT" "1" "KEXE_ALLOW" "-" "KEXE_FUEL" "1000000")
                                  :capture_output true :timeout 120)
                _ (.write_bytes (pathlib/Path art (str "case-" n ".stdout")) (.-stdout r))
                _ (.write_bytes (pathlib/Path art (str "case-" n ".stderr")) (.-stderr r))
                fuel (re/search (b ":remaining ([0-9]+)") (.-stdout r))
                observed (pyenv "exit" (.-returncode r) "remainingFuel" (when fuel (python/int (.group fuel 1))))]
            (chk (u/deq observed (g case "reference")) [n observed (g case "reference")])
            (if (g case "trap")
              (chk (u/has-bytes? (b ":status :trap") (.-stdout r)) n)
              (chk (= (python/int (.group (re/search (b ":result (-?[0-9]+)") (.-stdout r)) 1)) (g case "result")) n))
            (.append cases (let [row (pyenv "name" n)] (.update row observed) row))))
        (let [report (pyenv "status" "PASS_RUNTIME_BOUNDARY" "compiler" (pin compiler) "previousRoot" (when previous-root (pin previous-root))
                            "host" (python/list [(platform/system) (platform/machine) (platform/release)]) "refused" refused "positives" positives
                            "previous" previous "runtimeCases" cases "payload" (when payload (pin payload))
                            "cCompilerOrLoader" false "JVMNodeOrGraalFallback" false "emulation" false)]
          (.write_text (pathlib/Path output "runtime-boundary.json") (u/json-dump report))
          (println (g report "status") (python/len refused) "refusals/no-image;" (python/len cases) "native runtime cases")
          (.flush sys/stdout)
          report)))))

(defn -main [& args]
  (let [opt-path (fn [k] (when-let [v (u/opt args k)] (.resolve (pathlib/Path v))))]
    (run-main (.resolve (pathlib/Path (or (u/opt args "--compiler") (sys/exit "--compiler is required"))))
              (.resolve (pathlib/Path (or (u/opt args "--output") (sys/exit "--output is required"))))
              (opt-path "--previous-root") (opt-path "--payload") (opt-path "--definition-only-root"))))

(when (some #(or (= % "check-runtime-boundary.cljc") (str/ends-with? % "/check-runtime-boundary.cljc")) sys/argv)
  (apply -main *command-line-args*))
