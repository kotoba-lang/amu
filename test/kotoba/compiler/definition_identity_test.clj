(ns kotoba.compiler.definition-identity-test
  "ADR 0300. What a definition CID is allowed to depend on, and what it is not.

  Every case here is a claim about the SEALED payload, so each one is written
  as a pair: two modules that must agree, or two that must differ. A test that
  only asserts a CID is a well-formed string would pass for an identity that
  hashed the source text."
  (:require [clojure.edn :as edn]
            [clojure.java.io :as io]
            [clojure.set :as set]
            [clojure.string :as str]
            [clojure.test :refer [deftest is testing]]
            [kotoba.compiler.core :as compiler]
            [kotoba.compiler.definition-identity :as di]
            [kotoba.kir :as ir]
            [kotoba.kir.definition-identity :as kir-id]
            [kotoba.sema :as sema]))

(defn- report [source]
  (let [hir (sema/analyze source {})]
    (di/definitions hir (ir/lower hir))))

(defn- cids [source]
  (into {} (map (fn [[k v]] [k (:cid v)])) (:entries (report source))))

(def ^:private base
  (str "(ns d (:export [main]))\n"
       "(defn helper [a] (+ a 2))\n"
       "(defn main [] (helper 3))\n"))

;; ---------------------------------------------------------------------------
;; The measurement that made this namespace necessary

(deftest kir-normalize-alone-leaks-binder-names
  (testing "kotoba.kir.definition-identity/normalize is a canonical ENCODER, not
  an alpha-normalizer: it maps a symbol to its own name. Two bodies differing
  only in a binder therefore hash differently, which is why the compiler
  renames binders before handing anything to it. If this ever goes green,
  kir has grown de Bruijn normalization and `alpha-normalize` here can be
  reconsidered -- not before."
    (let [payload (fn [body]
                    {:definition/profile-version 6
                     :definition/desugar-contract-version 1
                     :definition/kir {:op :fn :body body}
                     :definition/effect-row #{}
                     :definition/interface {:arity 1 :result :i64}
                     :definition/dependencies []})]
      (is (not= (kir-id/definition-cid (payload '(+ a 1)))
                (kir-id/definition-cid (payload '(+ b 1))))
          "kir's normalize would seal a source-chosen binder name"))))

(deftest a-local-binder-name-is-not-part-of-identity
  (testing "the same measurement, after the compiler's pre-hash step"
    (let [one (cids (str "(ns d (:export [main]))\n"
                         "(defn helper [zzz] (let [q (+ zzz 2)] q))\n"
                         "(defn main [] (helper 3))\n"))
          two (cids (str "(ns d (:export [main]))\n"
                         "(defn helper [www] (let [r (+ www 2)] r))\n"
                         "(defn main [] (helper 3))\n"))]
      (is (= (get one "helper") (get two "helper")))
      (is (= (get one "main") (get two "main"))))))

(deftest binders-are-numbered-by-position-not-by-name
  (testing "a single left-to-right counter that never resets, so the renaming is
  a function of position alone. The literal comes out as the identity's exact
  decimal form, which is what keeps a JVM Long and a JavaScript BigInt on the
  same bytes -- see `canonical-value`."
    (is (= (list 'let ['k1 (list '+ 'k0 (kir-id/i64 2))] 'k1)
           (di/normalized-body '{:params [zzz] :body (let [q (+ zzz 2)] q)})))))

;; ---------------------------------------------------------------------------
;; Names, on both sides of a call

(deftest renaming-a-function-and-its-call-sites-does-not-move-any-cid
  (let [one (cids base)
        two (cids (str "(ns d (:export [main]))\n"
                       "(defn assistant [a] (+ a 2))\n"
                       "(defn main [] (assistant 3))\n"))]
    (is (= (get one "helper") (get two "assistant")))
    (is (= (get one "main") (get two "main"))
        "a caller depends on what it calls, never on what that thing is called")))

(deftest a-changed-body-moves-the-callee-and-its-caller
  (let [one (cids base)
        two (cids (str "(ns d (:export [main]))\n"
                       "(defn helper [a] (+ a 3))\n"
                       "(defn main [] (helper 3))\n"))]
    (is (not= (get one "helper") (get two "helper")))
    (is (not= (get one "main") (get two "main"))
        "the dependency CID is inside the caller's sealed body")))

(deftest a-dependency-is-reported-as-a-cid-not-a-name
  (let [entries (:entries (report base))]
    (is (= [(:cid (get entries "helper"))]
           (:dependencies (get entries "main"))))
    (is (empty? (:dependencies (get entries "helper"))))))

;; ---------------------------------------------------------------------------
;; Recursion

(deftest a-self-recursive-function-has-an-identity
  (let [entries (:entries (report (str "(ns d (:export [main]))\n"
                                       "(defn down [n acc]"
                                       " (if (= n 0) acc (down (- n 1) (+ acc n))))\n"
                                       "(defn main [] (down 5 0))\n")))]
    (is (string? (:cid (get entries "down"))))
    (is (= 0 (:group-index (get entries "down")))
        "a self-loop is a one-member strongly connected component")))

(deftest a-mutually-recursive-group-is-hashed-as-a-unit-and-is-rename-invariant
  (testing "scc-v1: the member ordering is chosen from the canonical bytes, so
  renaming every member of a cycle leaves the group identity alone"
    (let [one (cids (str "(ns d (:export [main]))\n"
                         "(defn ev [n] (if (= n 0) 1 (od (- n 1))))\n"
                         "(defn od [n] (if (= n 0) 0 (ev (- n 1))))\n"
                         "(defn main [] (ev 4))\n"))
          two (cids (str "(ns d (:export [main]))\n"
                         "(defn aa [n] (if (= n 0) 1 (bb (- n 1))))\n"
                         "(defn bb [n] (if (= n 0) 0 (aa (- n 1))))\n"
                         "(defn main [] (aa 4))\n"))]
      (is (= (get one "ev") (get two "aa")))
      (is (= (get one "od") (get two "bb")))
      (is (not= (get one "ev") (get one "od"))
          "two members of one cycle are two definitions, not one")
      (is (= (get one "main") (get two "main"))))))

(deftest a-cycle-is-never-hashed-by-name
  (testing "swapping which member of a cycle is the base case is a different
  program, so the two members' identities must swap with it"
    (let [one (cids (str "(ns d (:export [main]))\n"
                         "(defn ev [n] (if (= n 0) 1 (od (- n 1))))\n"
                         "(defn od [n] (if (= n 0) 0 (ev (- n 1))))\n"
                         "(defn main [] (ev 4))\n"))
          swapped (cids (str "(ns d (:export [main]))\n"
                             "(defn ev [n] (if (= n 0) 0 (od (- n 1))))\n"
                             "(defn od [n] (if (= n 0) 1 (ev (- n 1))))\n"
                             "(defn main [] (ev 4))\n"))]
      (is (not= (get one "ev") (get swapped "ev"))
          "if this passes by name rather than by bytes, the CIDs would not move"))))

;; ---------------------------------------------------------------------------
;; Refusals are answers, and they are not CIDs

;; ---------------------------------------------------------------------------
;; `:abort` in the sealed row -- ADJUDICATED 2026-09-03
;;
;; ADR-0300 section 4 said "`:abort` has no keyword the bridge can seal", and
;; the eight assertions below asserted the consequence: an aborting function
;; got `:definition-cid :unbridged-effect`, its caller got
;; `:dependency-unavailable`, the module yielded no cache material, and
;; `scanned-line` reported `SCANNED 0/2`.
;;
;; kotoba-kir 984a507 decided the opposite on the SAME DAY -- `:abort` bridges
;; through as itself, from a closed set `control-effects` -- and this
;; repository's kotoba-kir pin was held one commit short of it for that
;; reason, with the disagreement written into `deps.edn`.
;;
;; kotoba-lang adjudicated it in
;; `docs/adr/ADR-abort-reaches-the-sealed-effect-row.md`, from the authority
;; rather than from preference: `lang/surface-status.edn` `:explicit-errors`
;; makes `:effect-row-integration` a NAMED PRECONDITION of the sanctioned
;; widening path, and a row member that cannot reach a definition identity is
;; refused at the row's boundary rather than integrated into it. Under the
;; refusal reading no aborting definition could ever be pinned by a lock or
;; served from a definition-keyed cache -- which closes the path the
;; precondition exists to open. The shielding axis is
;; :control-effect-tracking, and the identity is the last boundary the effect
;; crosses.
;;
;; What section 4 got right survives and is asserted below: a CID is still
;; never invented for a hole (passing `:abort` through invents nothing -- the
;; keyword IS the sealed vocabulary), and a partial identity is still not an
;; identity (every member outside `control-effects` is still refused, still
;; blocks its callers, still yields no cache material, still prints
;; `SCANNED 0/2`). Section 4 was a true MEASUREMENT of the bridge at
;; kotoba-kir 1e00f830 written up as a decision about the language; the
;; measurement is what moved. See ADR-0326.

(deftest an-aborting-definition-has-an-identity-and-it-is-not-the-pure-ones
  (testing "`:abort` reaches the sealed row, so an aborting function is
  identifiable -- and identifiable AS ABORTING. That second half is the point:
  a function that can abort has interface [:result T E] where one that cannot
  has T, so had the bridge STRIPPED the keyword instead, the two would have
  shared an identity and a lock pinning the pure one would admit the aborting
  one."
    (let [entries (:entries (report (slurp (io/file "test/nbb/fixtures/abort-callee.kotoba"))))
          safe-div (get entries "safe-div")
          main (get entries "main")]
      (is (string? (:cid safe-div))
          "the aborting callee has a definition CID")
      (is (nil? (:definition-cid safe-div))
          "and no refusal marker: a CID and a marker are never both present")
      (is (string? (:cid main))
          "so its caller is identifiable too -- the closure has no hole in it")
      (is (nil? (:definition-cid main)))
      (is (not= (:cid safe-div) (:cid main)))))
  (testing "the row that reaches the payload holds the keyword itself"
    (let [hir (sema/analyze (slurp (io/file "test/nbb/fixtures/abort-callee.kotoba")) {})
          safe-div (first (filter #(= 'safe-div (:name %)) (:functions (ir/lower hir))))]
      (is (contains? (:effects safe-div) :abort)
          "the fixture must actually carry :abort, or this file proves nothing")
      (is (= #{:abort}
             (kir-id/effect-row-from-hir {:effects (:effects safe-div)}
                                         {:id->name {}}))))))

(deftest the-sealed-control-effect-vocabulary-agrees-across-the-pin
  ;; HYGIENE-1's shape (kotoba-native ADR-0050, kotoba-verifier ADR-0024): the
  ;; producer exports the set it branches on, the consumer derives its OWN and
  ;; asserts equality across the pin. Neither repository imports the other's
  ;; answer, so the comparison is real -- and the day one side moves, the pin
  ;; advance that carries the move is what goes red, rather than a test
  ;; stranded behind a pin nobody dares advance. That is exactly what happened
  ;; here between 2026-09-02 and 2026-09-03, for want of this test.
  ;;
  ;; Placed here rather than in kotoba-verifier, which HYGIENE-1 used, because
  ;; kotoba-verifier has no part in definition identity at all. The consumer
  ;; that diverged is the one that has to compare.
  (let [expected #{:abort}
        actual kir-id/control-effects]
    (println (format "COMPARED\t%d\tsealed control effects against kotoba-kir"
                     (count actual)))
    (is (seq actual)
        "kotoba.kir.definition-identity/control-effects is empty; an empty set
         would make every control effect unbridgeable again, and a comparison
         against nothing is not a comparison")
    (is (= expected actual)
        (str "this repository and kotoba-kir disagree about which effect-row "
             "members bridge as themselves.\n"
             "  only here: " (pr-str (set/difference expected actual)) "\n"
             "  only in kotoba-kir: " (pr-str (set/difference actual expected)) "\n"
             "Adjudicate it (kotoba-lang lang/surface-status.edn "
             ":explicit-errors :widening-path) before advancing the pin."))
    (testing "the set is closed: it is not merely non-empty, it is exactly this"
      (is (every? keyword? actual))
      (is (not (contains? actual :cap/call))))))

(deftest a-member-outside-the-closed-set-is-still-refused
  ;; ADR-0300's refusal machinery is not deleted, it is given a correct
  ;; domain. A keyword the compiler did not mean as a control effect still
  ;; gets no CID, still blocks its callers, and still says so by name.
  (let [catalog {8 :state/transact}
        bridge (fn [effects]
                 (try (kir-id/effect-row-from-hir {:effects effects} {:id->name catalog})
                      (catch clojure.lang.ExceptionInfo e
                        {:message (ex-message e) :problem (:problem (ex-data e))})))]
    (is (= #{:abort} (bridge #{:abort})))
    (let [refused (bridge #{:not/a-control-effect})]
      (is (str/includes? (:message refused) "not a wire capability call")
          "the reason literal, pinned: a widening of the closed set must be a
           decision and not a keyword arriving")
      (is (= :definition/effect-row-unbridged (:problem refused))))
    (let [refused (bridge #{[:cap/call 4242]})]
      (is (str/includes? (:message refused) "has no catalog name")
          "an unknown wire id is a different refusal with a different reason"))))

(deftest a-module-with-a-refused-definition-yields-no-cache-material
  ;; The claim ADR-0300 made -- "a partial identity is not an identity; a cache
  ;; keyed on one would serve one module's artifact for another" -- survives
  ;; the adjudication untouched. What changed is which rows are partial.
  ;; Built from synthetic KIR, because after the adjudication no COMPILABLE
  ;; source produces an unbridgeable row: `cap-call` with a literal id is the
  ;; only way to reach one, and the fixture that used to do this with `:abort`
  ;; is now identifiable.
  (let [hir {:named-operations #{} :exports '[caller]}
        kir {:functions [{:name 'callee :params '[] :result :i64
                          :effects #{[:cap/call 4242]} :body '(quote 1)}
                         {:name 'caller :params '[] :result :i64
                          :effects #{} :body '(callee)}]}
        entries (:entries (di/definitions hir kir))]
    (is (= :unbridged-effect (:definition-cid (get entries "callee")))
        "a wire id no catalog names is unbridgeable")
    (is (nil? (:cid (get entries "callee")))
        "a refusal never carries a CID as well as a marker")
    (is (= :dependency-unavailable (:definition-cid (get entries "caller")))
        "a caller of an unidentifiable definition is unidentifiable too")
    (is (nil? (di/cache-material (di/definitions hir kir) (:exports hir)))
        "a partial identity is not an identity; a cache keyed on one would serve
        one module's artifact for another")))

(deftest the-scanned-floor-distinguishes-nothing-identified-from-all-identified
  (let [clean (report base)
        aborting (report (slurp (io/file "test/nbb/fixtures/abort-callee.kotoba")))
        refused (di/definitions {:named-operations #{} :exports '[caller]}
                                {:functions [{:name 'callee :params '[] :result :i64
                                              :effects #{[:cap/call 4242]} :body '(quote 1)}
                                             {:name 'caller :params '[] :result :i64
                                              :effects #{} :body '(callee)}]})]
    (is (= "SCANNED\t2/2" (di/scanned-line clean)))
    (is (= "SCANNED\t2/2" (di/scanned-line aborting))
        "an aborting module is fully identified after the adjudication")
    (is (= "SCANNED\t0/2" (di/scanned-line refused)))
    (is (not= (di/scanned-line clean) (di/scanned-line refused)))))

(deftest a-refused-definition-is-listed-rather-than-omitted
  (let [lines (di/format-lines
               (di/definitions {:named-operations #{} :exports '[caller]}
                               {:functions [{:name 'callee :params '[] :result :i64
                                             :effects #{[:cap/call 4242]} :body '(quote 1)}
                                            {:name 'caller :params '[] :result :i64
                                             :effects #{} :body '(callee)}]}))]
    (is (= 2 (count lines)) "a listing that dropped what it could not identify
        would report a clean module")
    (is (every? #(str/includes? % "REFUSED:") lines)))
  (testing "and the aborting fixture is now listed with CIDs, not refusals"
    (let [lines (di/format-lines
                 (report (slurp (io/file "test/nbb/fixtures/abort-callee.kotoba"))))]
      (is (= 2 (count lines)))
      (is (not-any? #(str/includes? % "REFUSED:") lines)))))

(deftest describe-names-its-reason-rather-than-reporting-an-empty-module
  (is (= {:contract :kotoba.definition-identity/v1 :entries :unavailable :reason :no-hir}
         (di/describe {:hir nil :kir nil})))
  (is (= {:contract :kotoba.definition-identity/v1 :entries :unavailable
          :reason :no-typed-kir}
         (di/describe {:hir {:functions []} :kir {:functions []}}))))

(deftest a-schema-definition-is-part-of-the-interface

  (testing "adding a field to a record changes what a function taking that
  record MEANS, while leaving every body textually identical. If the schema
  were not sealed, such a change would move no CID and a cache keyed on those
  CIDs would serve the old artifact for the new program.

  Built from synthetic KIR rather than from source: the frontend refuses a
  record whose constructor does not exactly match its descriptor, so no
  compilable pair of programs differs in the schema alone."
    (let [module (fn [fields]
                   {:hir {:named-operations #{} :exports '[f]}
                    :kir {:schemas {:s/rec [:record :s/rec fields]}
                          :functions [{:name 'f :params '[x]
                                       :param-types [[:ref :s/rec]]
                                       :result :i64 :effects #{}
                                       :body '(+ x 1)}]}})
          cid (fn [m] (get-in (di/definitions (:hir m) (:kir m)) [:entries "f" :cid]))]
      (is (string? (cid (module [[:a :i64]]))))
      (is (= (cid (module [[:a :i64]])) (cid (module [[:a :i64]])))
          "deterministic")
      (is (not= (cid (module [[:a :i64]]))
                (cid (module [[:a :i64] [:b :i64]])))
          "a widened record is a different interface"))))

(deftest parameter-types-are-part-of-the-interface
  (testing "two functions of the same arity and result whose parameters are
  differently typed are two definitions. Sealing only `:arity` would give them
  one identity."
    (let [module (fn [param-type]
                   {:hir {:named-operations #{} :exports '[f]}
                    :kir {:functions [{:name 'f :params '[x] :param-types [param-type]
                                       :result :i64 :effects #{} :body '(+ x 1)}]}})
          cid (fn [m] (get-in (di/definitions (:hir m) (:kir m)) [:entries "f" :cid]))]
      (is (not= (cid (module :i64)) (cid (module :f64)))))))

;; ---------------------------------------------------------------------------
;; The two version constants

(deftest profile-version-matches-the-grammar-authority
  (testing "the constant exists because the authority is a JVM classpath
  resource and the nbb route has no classpath reader. This is the assertion
  that makes it a copy rather than a guess."
    (let [grammar (edn/read-string
                   (slurp (io/resource "kotoba/lang/guest-grammar.edn")))]
      (is (= (:kotoba.lang.guest-grammar/profile-version grammar)
             di/profile-version)
          "bump `kotoba.compiler.definition-identity/profile-version` with the
          grammar, and expect every definition CID to move -- that is what the
          sealed input means"))))

(deftest desugar-contract-version-is-pinned-because-no-authority-declares-one
  (testing "MEASURED GAP 2026-09-02: nothing in this repository, kotoba-sema or
  kotoba-lang numbers the desugar contract. The value is 1 because the frozen
  vectors in kotoba-lang lang/code-identity-vectors.edn use 1. This test exists
  so that the day an authority does declare a version, the choice is reviewed
  rather than quietly left behind."
    (is (= 1 di/desugar-contract-version))))

(deftest both-versions-are-sealed-so-changing-either-moves-every-cid
  (let [payload (fn [profile desugar]
                  {:definition/profile-version profile
                   :definition/desugar-contract-version desugar
                   :definition/kir {:op :fn :body '(+ k0 1)}
                   :definition/effect-row #{}
                   :definition/interface {:arity 1 :result :i64}
                   :definition/dependencies []})]
    (is (not= (kir-id/definition-cid (payload 6 1))
              (kir-id/definition-cid (payload 7 1))))
    (is (not= (kir-id/definition-cid (payload 6 1))
              (kir-id/definition-cid (payload 6 2))))))

;; ---------------------------------------------------------------------------
;; Cache material

(deftest cache-material-carries-the-ordered-cids-and-the-export-names
  (let [hir (sema/analyze base {})
        material (di/cache-material (di/definitions hir (ir/lower hir)) (:exports hir))]
    (is (= 2 (di/definition-count material)))
    (is (= ["main"] (:exports material)))
    (is (= (mapv #(get (cids base) %) ["helper" "main"]) (:definitions material)))))

(deftest declaration-order-is-in-the-cache-material
  (testing "MEASURED 2026-09-02 against emitted Wasm: renaming two private
  functions leaves the bytes byte-identical, but SWAPPING their declaration
  order does not. A material keyed on the SET of CIDs would serve one module's
  artifact for the other."
    (let [one (str "(ns d (:export [main]))\n"
                   "(defn h1 [a] (+ a 2))\n"
                   "(defn h2 [a] (* a 5))\n"
                   "(defn main [] (+ (h1 3) (h2 4)))\n")
          swapped (str "(ns d (:export [main]))\n"
                       "(defn h2 [a] (* a 5))\n"
                       "(defn h1 [a] (+ a 2))\n"
                       "(defn main [] (+ (h1 3) (h2 4)))\n")
          material (fn [s] (let [h (sema/analyze s {})]
                             (di/cache-material (di/definitions h (ir/lower h)) (:exports h))))]
      (is (= (set (:definitions (material one)))
             (set (:definitions (material swapped))))
          "the same three definitions")
      (is (not= (:definitions (material one)) (:definitions (material swapped)))
          "in a different order, and the order is load-bearing"))))

(deftest an-exported-name-is-in-the-cache-material
  (testing "an export name reaches the emitted bytes, so renaming an export
  must NOT be served from cache"
    (let [material (fn [s] (let [h (sema/analyze s {})]
                             (di/cache-material (di/definitions h (ir/lower h)) (:exports h))))
          one (material base)
          two (material (str "(ns d (:export [main other]))\n"
                             "(defn helper [a] (+ a 2))\n"
                             "(defn other [a] (+ a 2))\n"
                             "(defn main [] (helper 3))\n"))]
      (is (not= (:exports one) (:exports two))))))

;; ---------------------------------------------------------------------------
;; Provenance

(deftest provenance-carries-the-definition-graph
  (let [result (compiler/compile-source base :wasm32-kotoba-v1)
        definitions (get-in result [:provenance :definitions])]
    (is (= :kotoba.definition-identity/v1 (:contract definitions)))
    (is (= (cids base) (into {} (map (fn [[k v]] [k (:cid v)])) (:entries definitions))))
    (is (= ["helper" "main"] (:order definitions)))))
