#!/usr/bin/env nbb
;; The two compiler routes must emit the SAME native object for the same
;; source, byte for byte.
;;
;; `scripts/jdk-free-native-conformance.cljs` cannot make this claim: it
;; shadows `java`/`javac`/`clojure`/`clj` with failing stubs and asserts they
;; are never invoked, which is exactly the right shape for "this route needs no
;; JDK" and structurally unable to compare the two routes' output. So this
;; driver is the other half, and it is the half that needs a JDK.
;;
;; Why the pair is worth having: on 2026-09-02 the routes disagreed about
;; whether an i64 shift could be compiled AT ALL. `kotoba-verifier` re-derives
;; the "shift count must be an integer LITERAL in [0,63]" rule with a
;; predicate, and bare `integer?` is false for the JavaScript bigint every
;; guest literal is under nbb, so the JDK-free route refused every artifact
;; using a shift while the JVM route compiled the same program. A disagreement
;; about admission is a disagreement about bytes -- one route produced none.
;;
;;   nbb scripts/native-route-parity.cljs
;;
;; Exit 0 parity, 1 divergence, 3 could-not-measure. Three codes and not two:
;; a run that never reached the comparison must not be readable as one that
;; reached it and found no difference.

(ns native-route-parity
  (:require [clojure.string :as str]
            ["node:child_process" :as child]
            ["node:crypto" :as crypto]
            ["node:fs" :as fs]
            ["node:os" :as os]
            ["node:path" :as path]))

(def root (.resolve path (.dirname path *file*) ".."))
(def amu (.join path root "bin" "amu"))

(defn- unmeasurable! [message]
  (.error js/console (str "native-route-parity: could not measure: " message))
  (.exit js/process 3))

(defn- diverged! [message]
  (.error js/console (str "native-route-parity: ROUTES DISAGREE: " message))
  (.exit js/process 1))

(def isa
  (let [arch (.arch os)]
    (cond (contains? #{"arm64" "aarch64"} arch) "aarch64"
          (= "x64" arch) "x86_64"
          :else (unmeasurable! (str "unsupported architecture " arch)))))

;; Every fixture whose admission or lowering the two routes could disagree
;; about. Add one whenever a route-specific defect is fixed, so the next one
;; of its kind is caught here rather than by a consumer repository.
(def fixtures
  [{:source "examples/i64-shift.kotoba"
    :why "i64 shift counts are guest literals; kotoba-verifier's gate for them
          was host-specific until 3d7a6f0"}
   {:source "examples/i64-semantics.kotoba"
    :why "the scalar baseline -- if this diverges the disagreement is not
          about any one feature"}])

(defn- run [command args]
  (let [result (.spawnSync child command (clj->js args)
                           #js {:cwd root :encoding "utf8" :maxBuffer 16777216})]
    (when (.-error result)
      (unmeasurable! (str command " could not be started: " (.-message (.-error result)))))
    {:status (if (nil? (.-status result)) 70 (.-status result))
     :stdout (or (.-stdout result) "")
     :stderr (or (.-stderr result) "")}))

(defn- digest [file]
  (when-not (fs/existsSync file)
    (unmeasurable! (str "no artifact at " file)))
  (-> (crypto/createHash "sha256") (.update (fs/readFileSync file)) (.digest "hex")))

;; Refuse before doing any work rather than after, and refuse rather than skip:
;; "the JVM was not available" and "the two routes agree" must not leave the
;; same exit code behind.
(let [probe (.spawnSync child "clojure" #js ["-Sdescribe"] #js {:encoding "utf8"})]
  (when (or (.-error probe) (not= 0 (.-status probe)))
    (unmeasurable! "this driver compares the JDK-free route against the JVM route, and `clojure` is not runnable here")))

(def tmp (.mkdtempSync fs (.join path (.tmpdir os) "amu-native-route-parity-")))

(try
  (doseq [{:keys [source why]} fixtures]
    (let [name (.basename path source ".kotoba")
          src (.join path root source)
          free (.join path tmp (str name "-jvm-free.o"))
          jvm (.join path tmp (str name "-jvm.o"))
          free-result (run js/process.execPath
                           [amu "compile" src "--target" isa "--jvm-free" "--output" free])
          ;; `bin/amu` routes every native target to nbb whatever the flags, so
          ;; the JVM route has to be invoked directly. That is the point: the
          ;; two are different code, and this is the only place they meet.
          jvm-result (run "clojure" ["-M:run" "compile" src "--target" isa "--output" jvm])]
      (when (not= 0 (:status free-result))
        (diverged! (str source ": the JDK-free route refused what the JVM route is being asked to build\n"
                        (str/trim (str (:stdout free-result) (:stderr free-result)))
                        "\n(" (str/replace why #"\s+" " ") ")")))
      (when (not= 0 (:status jvm-result))
        (diverged! (str source ": the JVM route refused\n"
                        (str/trim (str (:stdout jvm-result) (:stderr jvm-result))))))
      (let [a (digest free) b (digest jvm)]
        (when (not= a b)
          (diverged! (str source " on " isa ": jvm-free " a " vs jvm " b)))
        (println (str "SCANNED\t" source "\t" isa "\t" a)))))
  (when-not (pos? (count fixtures))
    (unmeasurable! "no fixtures -- an empty comparison is not a parity result"))
  (println (str "native-route-parity: " (count fixtures) " fixtures, "
                isa ", both routes byte-identical"))
  (finally
    (fs/rmSync tmp #js {:recursive true :force true})))
