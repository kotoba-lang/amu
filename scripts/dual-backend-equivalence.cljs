(ns scripts.dual-backend-equivalence
  "Independent-rebuild verification: compile ONE input through TWO backends and
  compare THE VALUES THE ARTIFACTS PRODUCE.

  `output_attestation.cljs` signs who built an artifact. It cannot say the
  artifact is right, and a content-addressed source tree cannot either: if the
  compiler is compromised the output is compromised and source review sees
  nothing (the Ken Thompson shape). The only thing that detects that is a
  second path disagreeing. This is the first increment of that: it builds each
  corpus program for `wasm32` and for `js` (restricted ESM), RUNS both, and
  compares every exported zero-arity probe value by value.

  Why running matters rather than diffing exit codes: on 2026-09-06
  (kotoba-lang/amu#835) a module COMPILED, RAN, and gave a WRONG ANSWER on
  aarch64-macos -- keyword `=` was always false while i64 `=` was correct in
  the same build, so every branch went the wrong way. Two green builds would
  have agreed perfectly. Only the values disagree.

  For the same reason this reports COUNTS, never a boolean. A boolean cannot
  distinguish one regression from a broken build; #835 was caught only because
  the failing module returned a count.

  WHAT THIS DOES NOT COVER, stated so nobody reads more from a green run than
  is in it:

    * The two backends share the frontend, the desugarer and the KIR. This
      detects LOWERING divergence. A compromised frontend would compromise
      both paths identically and this would stay green. Closing that needs a
      third path that does not share the front half.
    * The corpus is small and hand-written, not generated. It is a floor, not
      a proof.
    * Only probes that are zero-arity and return an i64 are comparable across
      the two value ABIs. A probe returning a typed reference is reported as
      UNCOMPARABLE, never as agreement.

  Exit-code contract -- three answers, not two:

    0  every program both backends built agreed on every comparable probe,
       AND at least one probe actually ran.
    1  at least one probe DISAGREED, or one side's export set differs.
    2  COULD NOT ANSWER. No probe ran, the corpus is empty or unreadable, the
       host runtime is missing, or a compile failed in a way that is not a
       refusal the compiler named. Never 0 -- a check that could not run must
       not return the value of a check that ran and found nothing.

  Usage:

    nbb scripts/dual-backend-equivalence.cljs
    nbb scripts/dual-backend-equivalence.cljs --corpus test/dual-backend --json
    nbb scripts/dual-backend-equivalence.cljs --keep   # leave artifacts in place"
  (:require ["node:child_process" :as cp]
            ["node:fs" :as fs]
            ["node:os" :as os]
            ["node:path" :as path]
            [clojure.string :as str]))

;; ---------------------------------------------------------------------------
;; The two paths under comparison.
;;
;; `--target wasm32` reaches kotoba-native's Wasm encoder and runs under
;; `runtime/browser-host.mjs`, which owns the `kotoba:typed` ABI. `--target js`
;; reaches kotoba-lang/kotoba-script's restricted-ESM emitter and runs as an
;; ES module. Different emitters, different value representations, different
;; runtimes -- which is the whole point: agreement between them is evidence,
;; agreement between two invocations of one emitter is not.

(def ^:private paths
  [{:id :wasm32 :target "wasm32" :suffix ".wasm"}
   {:id :js     :target "js"     :suffix ".mjs"}])

(def ^:private exit-agreed 0)
(def ^:private exit-disagreed 1)
(def ^:private exit-cannot-answer 2)

;; ---------------------------------------------------------------------------

(defn- argv [] (vec (drop 2 (js->clj js/process.argv))))

(defn- flag-value [args flag default]
  (let [i (.indexOf (clj->js args) flag)]
    (if (neg? i) default (nth args (inc i) default))))

(defn- flag? [args flag] (some #(= flag %) args))

(defn- die! [code & lines]
  (doseq [l lines] (.error js/console l))
  (.exit js/process code))

(defn- exists? [p] (.existsSync fs p))

;; ---------------------------------------------------------------------------
;; Compiling. Each compile is a separate `bin/amu` process, so a crash on one
;; program cannot take the run with it, and the refusal text is kept: a
;; backend that REFUSES a program is a measurement, and it must not be
;; recorded the same way as a backend that built one.

(defn- compile-one [root src out target]
  (let [r (.spawnSync cp js/process.execPath
                      (clj->js [(path/join root "bin" "amu") "compile" src
                                "--target" target "--output" out])
            #js {:cwd root :encoding "utf8" :maxBuffer (* 32 1024 1024)})
        status (.-status r)
        text (str (.-stdout r) (.-stderr r))]
    (cond
      (.-error r) {:ok? false :kind :infrastructure
                   :message (.. r -error -message)}
      (zero? status) (if (exists? out)
                       {:ok? true :kind :built}
                       ;; exit 0 and no artifact is not a pass. It is the exact
                       ;; shape this file exists to refuse: a check that did not
                       ;; run returning the value of one that did.
                       {:ok? false :kind :infrastructure
                        :message "compiler exited 0 but wrote no artifact"})
      ;; The compiler's own refusal codes. 64/65/70 all print a
      ;; `:kotoba.cli-error/v1` map naming the reason; anything else is not a
      ;; refusal we can read, so it is infrastructure, not a measurement.
      (contains? #{64 65 70} status)
      {:ok? false :kind :refused :status status
       :message (or (second (re-find #":message \"([^\"]*)\"" text))
                    (str "exit " status))}
      :else {:ok? false :kind :infrastructure
             :message (str "exit " status " :: "
                           (str/join " / " (take-last 2 (remove str/blank?
                                                               (str/split-lines text)))))})))

;; ---------------------------------------------------------------------------
;; Running. Both artifacts are loaded in THIS process and their exports called
;; directly, so what is compared is the value each backend actually computes,
;; not a string either of them printed.

(defn- host-module [root]
  (js/import (str "file://" (path/join root "runtime" "browser-host.mjs"))))

(defn- instantiate-wasm [root artifact]
  (-> (host-module root)
      (.then (fn [host]
               (.instantiateKotoba host (.readFileSync fs artifact) #js {})))
      (.then (fn [r] (.. r -instance -exports)))))

(defn- instantiate-js [artifact]
  (-> (js/import (str "file://" artifact))
      (.then (fn [m] (.instantiateKotoba m #js {})))))

;; A probe's value is normalised to a string BEFORE comparison so that two
;; representations of the same number compare equal (wasm returns BigInt,
;; restricted ESM returns BigInt too, but the host wrappers are free to differ)
;; and so that a thrown trap compares as itself rather than as a missing value.
;; A value that is neither is reported UNCOMPARABLE -- it is not agreement.

(defn- js-tag
  "`Object.prototype.toString.call` rather than `typeof`, because it is total:
  it answers for null and undefined too, and it distinguishes a BigInt
  primitive from a Number without either backend having to agree on boxing."
  [v]
  (.call (.. js/Object -prototype -toString) v))

(defn- arity [exports name]
  (let [f (aget exports name)]
    (if (fn? f) (.-length f) -1)))

;; Only zero-arity probes are called. A probe that takes arguments would need
;; the harness to invent them, and inventing them on two different value ABIs
;; is how a comparison starts measuring the harness instead of the compiler --
;; measured here first: calling `fact`/`fib` with no arguments trapped on both
;; sides with DIFFERENT host wording, and the run reported a mismatch on an
;; operation that had never executed. That is a false positive, and a
;; comparison that produces them cannot be trusted when it produces a real one.
;; Arity is read from `Function.length`, which both hosts report, and a
;; DIFFERENCE in arity between the two sides is itself a disagreement.

(defn- probe-value [exports name]
  (let [f (aget exports name)]
    (if-not (fn? f)
      {:kind :absent :text "absent"}
      (try
        (let [v (f)
              tag (js-tag v)]
          (case tag
            "[object BigInt]"  {:kind :i64 :text (str v)}
            "[object Number]"  {:kind :i64 :text (str v)}
            "[object Boolean]" {:kind :bool :text (str v)}
            {:kind :uncomparable :text tag}))
        (catch :default e
          {:kind :trap :text (str "trap:" (or (.-message e) (str e)))})))))

(defn- export-names [exports]
  (sort (js->clj (.keys js/Object exports))))

;; ---------------------------------------------------------------------------

(defn- compare-program [root src work]
  (let [base (str/replace (path/basename src ".kotoba") #"[^A-Za-z0-9_.-]" "_")
        builds (into {}
                     (map (fn [{:keys [id target suffix]}]
                            (let [out (path/join work (str base "." (name id) suffix))]
                              [id (assoc (compile-one root src out target)
                                         :artifact out :target target)])))
                     paths)]
    (cond
      (some #(= :infrastructure (:kind %)) (vals builds))
      (js/Promise.resolve
       {:program base :status :infrastructure
        :detail (into {} (map (fn [[k v]] [k (:message v)]))
                      (filter #(= :infrastructure (:kind (val %))) builds))})

      (every? :ok? (vals builds))
      (-> (js/Promise.all
           #js [(instantiate-wasm root (:artifact (:wasm32 builds)))
                (instantiate-js (:artifact (:js builds)))])
          (.then
           (fn [pair]
             (let [w (aget pair 0) j (aget pair 1)
                   wn (export-names w) jn (export-names j)
                   only-wasm (remove (set jn) wn)
                   only-js (remove (set wn) jn)
                   shared (filter (set jn) wn)
                   probes (for [n shared
                                :let [wa (arity w n) ja (arity j n)]]
                            (if (not= wa ja)
                              {:probe n :verdict :arity-split
                               :wasm32 {:kind :arity :text (str "arity " wa)}
                               :js {:kind :arity :text (str "arity " ja)}}
                              (if (pos? wa)
                                {:probe n :verdict :skipped-arity
                                 :wasm32 {:kind :arity :text (str "arity " wa)}
                                 :js {:kind :arity :text (str "arity " ja)}}
                                (let [wv (probe-value w n) jv (probe-value j n)]
                                  {:probe n :wasm32 wv :js jv
                                   :verdict (cond
                                              (or (= :uncomparable (:kind wv))
                                                  (= :uncomparable (:kind jv))) :uncomparable
                                              (= (:text wv) (:text jv)) :agreed
                                              :else :disagreed)}))))]
               {:program base :status :compared
                :only-wasm (vec only-wasm) :only-js (vec only-js)
                :probes (vec probes)})))
          (.catch (fn [e]
                    {:program base :status :infrastructure
                     :detail {:run (or (.-message e) (str e))}})))

      :else
      (js/Promise.resolve
       {:program base :status :one-side-refused
        :detail (into {} (map (fn [[k v]] [k (if (:ok? v) "built" (:message v))])) builds)}))))

;; ---------------------------------------------------------------------------

(defn- report! [results json?]
  (let [compared (filter #(= :compared (:status %)) results)
        probes (mapcat :probes compared)
        agreed (filter #(= :agreed (:verdict %)) probes)
        disagreed (filter #(= :disagreed (:verdict %)) probes)
        uncomparable (filter #(= :uncomparable (:verdict %)) probes)
        arity-splits (filter #(= :arity-split (:verdict %)) probes)
        skipped (filter #(= :skipped-arity (:verdict %)) probes)
        export-splits (filter #(or (seq (:only-wasm %)) (seq (:only-js %))) compared)
        refused (filter #(= :one-side-refused (:status %)) results)
        broken (filter #(= :infrastructure (:status %)) results)
        summary {:programs-seen (count results)
                 :programs-compared (count compared)
                 :programs-uncompilable-by-one-side (count refused)
                 :programs-infrastructure-error (count broken)
                 :probes-seen (count probes)
                 :probes-run (+ (count agreed) (count disagreed))
                 :probes-agreed (count agreed)
                 :probes-disagreed (count disagreed)
                 :probes-uncomparable (count uncomparable)
                 :probes-skipped-nonzero-arity (count skipped)
                 :probes-arity-split (count arity-splits)
                 :export-set-splits (count export-splits)}]
    (if json?
      (println (js/JSON.stringify (clj->js {:summary summary :results results}) nil 2))
      (do
        (doseq [r results]
          (case (:status r)
            :compared
            (let [d (concat (filter #(= :disagreed (:verdict %)) (:probes r))
                            (filter #(= :arity-split (:verdict %)) (:probes r)))
                  u (filter #(= :uncomparable (:verdict %)) (:probes r))
                  sk (filter #(= :skipped-arity (:verdict %)) (:probes r))]
              (println (str (if (seq d) "DISAGREED " "agreed    ")
                            (:program r)
                            "  ran=" (count (filter #(contains? #{:agreed :disagreed} (:verdict %))
                                                    (:probes r)))
                            " agreed=" (count (filter #(= :agreed (:verdict %)) (:probes r)))
                            " disagreed=" (count d)
                            (when (seq sk) (str " skipped-nonzero-arity=" (count sk)))
                            (when (seq u) (str " uncomparable=" (count u)))))
              (doseq [p d]
                (println (str "    MISMATCH " (:program r) "/" (:probe p)
                              "  wasm32=" (:text (:wasm32 p))
                              "  js=" (:text (:js p)))))
              (doseq [p u]
                (println (str "    UNCOMPARABLE " (:program r) "/" (:probe p)
                              " (wasm32 " (name (:kind (:wasm32 p)))
                              ", js " (name (:kind (:js p))) ")")))
              (doseq [n (:only-wasm r)]
                (println (str "    EXPORT-ONLY-WASM32 " (:program r) "/" n)))
              (doseq [n (:only-js r)]
                (println (str "    EXPORT-ONLY-JS " (:program r) "/" n))))
            :one-side-refused
            (println (str "NOT MEASURED " (:program r) "  "
                          (str/join "  " (map (fn [[k v]] (str (name k) "=" v))
                                              (:detail r)))))
            :infrastructure
            (println (str "REFUSED-TO-ANSWER " (:program r) "  "
                          (str/join "  " (map (fn [[k v]] (str (name k) ": " v))
                                              (:detail r)))))))
        (println)
        (println (str "SUMMARY"
                      " programs-seen=" (:programs-seen summary)
                      " compared=" (:programs-compared summary)
                      " uncompilable-by-one-side=" (:programs-uncompilable-by-one-side summary)
                      " infrastructure-errors=" (:programs-infrastructure-error summary)))
        (println (str "PROBES"
                      " seen=" (:probes-seen summary)
                      " run=" (:probes-run summary)
                      " agreed=" (:probes-agreed summary)
                      " disagreed=" (:probes-disagreed summary)
                      " skipped-nonzero-arity=" (:probes-skipped-nonzero-arity summary)
                      " arity-splits=" (:probes-arity-split summary)
                      " uncomparable=" (:probes-uncomparable summary)
                      " export-set-splits=" (:export-set-splits summary)))))
    summary))

(defn- decide [summary]
  ;; Evidence floor first. `probes-run = 0` with nothing disagreeing is the
  ;; shape of a check that never ran, and it must not exit 0.
  (cond
    (pos? (:programs-infrastructure-error summary))
    [exit-cannot-answer "REFUSED: a program failed for a reason that is not a compiler refusal."]

    (zero? (:probes-run summary))
    [exit-cannot-answer "REFUSED: no probe executed; nothing was compared."]

    (or (pos? (:probes-disagreed summary))
        (pos? (:probes-arity-split summary))
        (pos? (:export-set-splits summary)))
    [exit-disagreed "DISAGREEMENT: the two backends do not compute the same values."]

    :else
    [exit-agreed "AGREED on every comparable probe that ran."]))

;; ---------------------------------------------------------------------------

(defn -main []
  (let [args (argv)
        root (path/resolve (flag-value args "--root" (.cwd js/process)))
        corpus (path/resolve (flag-value args "--corpus"
                                         (path/join root "test" "dual-backend")))
        json? (flag? args "--json")
        keep? (flag? args "--keep")
        work (flag-value args "--work"
                         (.mkdtempSync fs (path/join (os/tmpdir) "amu-dual-")))]
    (when-not (exists? (path/join root "bin" "amu"))
      (die! exit-cannot-answer
            (str "REFUSED: " root " has no bin/amu. Run this from the amu repo root, "
                 "or pass --root.")))
    (when-not (exists? (path/join root "runtime" "browser-host.mjs"))
      (die! exit-cannot-answer
            (str "REFUSED: " root " has no runtime/browser-host.mjs; the wasm32 "
                 "artifacts cannot be executed and no comparison is possible.")))
    (when-not (exists? corpus)
      (die! exit-cannot-answer (str "REFUSED: corpus directory not found: " corpus)))
    (.mkdirSync fs work #js {:recursive true})
    (let [sources (->> (js->clj (.readdirSync fs corpus))
                       (filter #(str/ends-with? % ".kotoba"))
                       sort
                       (mapv #(path/join corpus %)))]
      (when (empty? sources)
        (die! exit-cannot-answer (str "REFUSED: no .kotoba programs in " corpus)))
      (println (str "corpus=" corpus "  programs=" (count sources)
                    "  work=" work))
      (println (str "paths=" (str/join " x " (map :target paths))))
      (println)
      (-> (reduce (fn [p src]
                    (.then p (fn [acc]
                               (.then (compare-program root src work)
                                      (fn [r] (conj acc r))))))
                  (js/Promise.resolve [])
                  sources)
          (.then (fn [results]
                   (let [summary (report! (vec results) json?)
                         [code line] (decide summary)]
                     (println)
                     (println line)
                     (when-not keep?
                       (try (.rmSync fs work #js {:recursive true :force true})
                            (catch :default _ nil)))
                     (.exit js/process code))))
          (.catch (fn [e]
                    (die! exit-cannot-answer
                          (str "REFUSED: harness itself failed: "
                               (or (.-message e) (str e))))))))))

(-main)
