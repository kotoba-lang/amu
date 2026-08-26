(ns kotoba.compiler.wasm32-kotoba-v1-qualification-test
  "One closed answer per kit for `who has been proved on which host surface`.

  Nothing in src/ reads :qualification. It is a claim addressed to people, so
  the only thing standing between it and a lie is this file. The rule is that a
  name may not appear in the proved sets below without a backend test that runs
  a guest across the seam it names.

  Two seams, deliberately not merged:

    :wasm32-kotoba-v1  clock's i64 kotoba:cap/call host-time surface.
                       Still clock alone.
    :wasm-aot          the typed kit ABI, kotoba:typed/cap-call, where a kit's
                       OWN variant/record request-result schema crosses whole.

  A kit can compile to the wasm32 target and still not be on the i64 surface --
  storage does exactly that -- so compiling somewhere is never the claim.

  Native is a third, independent seam, and it is NOT closed to kits: dataspace
  and ui are qualified on it. But :pending there does not have ONE meaning, and this
  file used to say it did. Two reasons are live, and a reader who cannot tell
  them apart keeps a self-restriction after the thing that caused it is gone
  (superproject ADR-2608650000):

    schema           log and storage are refused at :phase :target because
                     their own request/result types are not one-word values.
                     Narrowing the schema moves the key.
    host authority   clock's schema is SEALED and admitted, the backend emits
                     it, and it compiles -- the kexe loader simply has no clock
                     source and no ADR grants it one (ADR 0261). Nothing about
                     clock-v1.edn can move that key.

  So a kit at :native-aot :pending must say WHICH, and the second kind carries
  a :native-aot-blocked-by block naming the ADRs and the exit condition.

  Proved on the typed kit ABI, each by a named test:

    dataspace-v1.edn  kotoba.compiler.dataspace-wasm-aot-test
    storage-v1.edn    kotoba.compiler.storage-wasm-aot-test
    log-v1.edn        kotoba.compiler.log-wasm-aot-test
    http-v1.edn       kotoba.compiler.http-wasm-aot-test
    llm-v1.edn        kotoba.compiler.llm-wasm-aot-test
    state-v1.edn      kotoba.compiler.state-wasm-aot-test
    ui-v1.edn         kotoba.compiler.ui-wasm-aot-test

  Kits declare capabilities in two shapes -- :capability for one, :capabilities
  for several -- and their surfaces mirror that, flat or under :grants. The
  check below reads both as a set of [id grant] pairs, so a two-capability kit
  cannot qualify by proving one wire and leaving the other claimed but
  unmeasured. Log is the first such kit; before it the distinction had no
  instance, which is why the earlier single-capability form looked general."
  (:require [clojure.edn :as edn]
            [clojure.java.io :as io]
            [clojure.test :refer [deftest is testing]]))

(def application-kit-files
  ["clock-v1.edn" "http-v1.edn" "http-ingress-v1.edn" "storage-v1.edn"
   "log-v1.edn" "llm-v1.edn" "ui-v1.edn" "state-v1.edn" "dataspace-v1.edn"
   "stream-ingress-v1.edn"])

(def kits-outside-this-vocabulary
  "stream-object-v1 answers a different question -- :wit-03, :ownership-check,
  :component-core, :jvm-host -- so the keys below do not apply to it and this
  file does not govern it. Named rather than omitted: a hand-kept list that
  silently skips a kit is how stream-ingress carried an unguarded
  :qualification until 2026-08-18."
  #{"stream-object-v1.edn"})

(def typed-kit-abi-wasm-aot-kits
  "Adding a name here without a test that actually runs the guest is the
  failure this file exists to prevent."
  #{"dataspace-v1.edn" "storage-v1.edn" "log-v1.edn"
    "http-v1.edn" "llm-v1.edn" "state-v1.edn" "ui-v1.edn"})

(def wasmtime-component-wasm-aot-kits
  "A THIRD seam, and the same rule: a name here needs a test that runs the
  guest on it. These two kits reach :wasm-aot not through the browser typed
  ABI above but through a wasm COMPONENT executed by wasmtime, so they carry
  no :wasm-aot-surface -- that block describes kotoba:typed/cap-call, and
  describing this seam with it would be false in a way nothing else here
  would catch.

    http-ingress-v1.edn  host inject -> accept over a closed composition.
                         kotoba.compiler.http-ingress-wasm-aot-qualification-test

  The suite fails rather than skips on an under-spec engine, so a name here
  cannot stay green on a machine that never ran the component.

  clock-v1.edn is deliberately NOT here. ADR 0263 proposes it and a suite was
  written for it, but the composed component does not link on wasmtime 43.0.2
  or 45.0.3 -- instance export `now` has the wrong type -- so the claim has no
  run behind it. See the note in clock-v1.edn."
  #{"http-ingress-v1.edn"})

(defn- wasm-aot-proved? [filename]
  (or (typed-kit-abi-wasm-aot-kits filename)
      (wasmtime-component-wasm-aot-kits filename)))

(defn- kit-files-on-disk []
  (->> (io/file (io/resource "kotoba/lang/capability-kits"))
       .listFiles
       (map #(.getName %))
       (filter #(.endsWith ^String % ".edn"))
       set))

(defn- load-kit [filename]
  (edn/read-string
   (slurp (io/resource (str "kotoba/lang/capability-kits/" filename)))))

(defn- declared-wires
  "[id grant] pairs the kit itself declares, in either shape."
  [kit]
  (set (map (juxt :id :name)
            (or (:capabilities kit) [(:capability kit)]))))

(defn- surface-wires
  "[id grant] pairs the :wasm-aot-surface names, flat or under :grants."
  [surface]
  (set (map (juxt :capability-id :grant)
            (or (:grants surface) [surface]))))

(deftest all-reference-kits-share-one-closed-qualification
  (doseq [filename application-kit-files]
    (testing filename
      (is (= :implemented (:reference (:qualification (load-kit filename))))))))

(deftest only-clock-claims-wasm32-kotoba-v1
  (let [q (:qualification (load-kit "clock-v1.edn"))]
    (is (= :implemented (:wasm32-kotoba-v1 q)))))

(deftest clock-surface-names-the-i64-seam
  (let [surface (:wasm32-kotoba-v1-surface (load-kit "clock-v1.edn"))]
    (is (= ["kotoba:cap" "call"] (:import surface)))
    (is (= [:i64 :i64 :i64] (:signature surface)))
    (is (= 7 (:capability-id surface)))
    (is (= :clock-monotonic (:grant surface)))
    (is (= "(typed-cap-call 7 :i64 :i64 seed)" (:elaboration surface)))))

(deftest other-application-kits-keep-wasm32-kotoba-v1-pending
  (doseq [filename (remove #{"clock-v1.edn"} application-kit-files)]
    (testing filename
      (let [q (:qualification (load-kit filename))]
        (is (= :pending (:wasm32-kotoba-v1 q)))
        (when-not (wasm-aot-proved? filename)
          (is (= :pending (:wasm-aot q))))))))

(deftest only-proved-kits-claim-typed-kit-wasm-aot
  (doseq [filename application-kit-files]
    (testing filename
      (let [kit (load-kit filename)
            claimed (:wasm-aot (:qualification kit))]
        (if (wasm-aot-proved? filename)
          (is (= :implemented claimed))
          (is (= :pending claimed)))))))

(deftest every-typed-wasm-aot-kit-carries-a-surface-block
  "A :wasm-aot claim must name the seam it runs on, and must account for every
  wire the kit declares -- not just the one that was convenient to prove."
  (doseq [filename typed-kit-abi-wasm-aot-kits]
    (testing filename
      (let [kit (load-kit filename)
            surface (:wasm-aot-surface kit)]
        (is (= ["kotoba:typed" "cap-call"] (:import surface))
            "a :wasm-aot claim must name the typed kit ABI it runs on")
        (is (= :wasm32-browser-kotoba-v1 (:target surface)))
        (is (= (declared-wires kit) (surface-wires surface))
            "the surface must cover exactly the capabilities the kit declares")))))

(deftest kits-without-a-typed-wasm-aot-claim-carry-no-surface-block
  "The two must move together, so a leftover block cannot outlive its claim."
  (doseq [filename (remove typed-kit-abi-wasm-aot-kits application-kit-files)]
    (testing filename
      (is (nil? (:wasm-aot-surface (load-kit filename)))))))

(def native-aot-kits
  "Kits proved on a native target by a named process test:
  dataspace-v1.edn  kotoba.compiler.dataspace-native-aot-test
  ui-v1.edn         kotoba.compiler.ui-native-aot-test
  Native is NOT categorically closed to capability kits -- dataspace and ui
  cross it -- so a kit sitting at :pending here is never a statement about
  the backend being absent. It is a statement about that kit's own schema,
  or about host authority nobody has granted; see the two-reason table above."
  #{"dataspace-v1.edn" "ui-v1.edn"})

(def native-aot-blocked-kits
  "Kits whose :native-aot :pending is NOT about their own schema, and which
  therefore must carry a :native-aot-blocked-by block. Adding a name here
  without a measured trap and named ADRs is the failure this guards."
  #{"clock-v1.edn"})

(deftest native-aot-is-claimed-only-where-a-native-test-ran
  (doseq [filename application-kit-files]
    (testing filename
      (let [claimed (:native-aot (:qualification (load-kit filename)))]
        (if (native-aot-kits filename)
          (is (= :implemented claimed))
          (is (= :pending claimed)))))))

(deftest kits-pending-on-native-are-pending-for-a-schema-reason
  "log and storage are refused by the native targets at :phase :target because
  their own request/result schemas are not one-word values -- log's :fields and
  :entries are [:set [:record ...]], storage's expected-version is
  [:option :i64]. Each records that measured rejection in a test, so the gap
  cannot be read as a backend nobody tried. Whoever narrows one of those
  schemas is the one who gets to move the key.

  These two, and only these two, are the schema kind. Clock is not here: its
  schema is admitted and it reaches a real process (ADR 0261)."
  (doseq [filename ["log-v1.edn" "storage-v1.edn"]]
    (testing filename
      (is (= :pending (:native-aot (:qualification (load-kit filename)))))
      (is (nil? (:native-aot-blocked-by (load-kit filename)))
          "a schema-pending kit must not claim a host-authority blocker"))))

(deftest clock-is-pending-on-native-for-a-host-authority-reason
  "The distinction ADR 0261 exists to make visible. Clock compiles to the
  native ISA and traps in the loader, so :pending here is not the same fact
  as log's and storage's :pending, and must not be recorded as though it were.
  The block has to name what would clear it, or it is a shrug with citations."
  (let [kit (load-kit "clock-v1.edn")
        blocked (:native-aot-blocked-by kit)]
    (is (= :pending (:native-aot (:qualification kit))))
    (is (some? blocked) "clock must say WHY it is pending on native")
    (is (= :undecided-host-authority (:kind blocked)))
    (is (= :schema (:not blocked))
        "the one reading it must be told which reason this is NOT")
    (is (= :SIGILL (:process-result (:measured blocked)))
        "the claim is measured -- a real process ran and trapped")
    (is (every? (set (:adr blocked)) [261 240 84 227])
        "the refusal must cite the decisions it rests on")
    (is (string? (:exit-condition blocked))
        "a blocker with no exit condition is permanent by accident")))

(deftest only-blocked-kits-carry-a-native-aot-blocked-by-block
  "Block and claim move together, the same rule :wasm-aot-surface follows: a
  kit that reaches :implemented, or that is pending for its own schema, must
  not leave a stale blocker behind explaining a gap that closed."
  (doseq [filename application-kit-files]
    (testing filename
      (let [blocked (:native-aot-blocked-by (load-kit filename))]
        (if (native-aot-blocked-kits filename)
          (is (some? blocked))
          (is (nil? blocked)))))))

(deftest every-kit-on-disk-is-either-governed-here-or-named-as-out-of-scope
  "The list above is hand-kept, so this is what stops a new kit from carrying
  an unguarded :qualification simply by not being added to it."
  (is (= (kit-files-on-disk)
         (into kits-outside-this-vocabulary application-kit-files))))

(deftest kits-in-this-vocabulary-answer-all-five-keys
  "A missing key reads the same as an unproved one at a glance, so absence is
  not allowed to stand in for :pending."
  (doseq [filename application-kit-files]
    (testing filename
      (let [q (:qualification (load-kit filename))]
        (is (= #{:reference :wasm-aot :wasm32-kotoba-v1 :native-aot :jit}
               (set (keys q))))))))
