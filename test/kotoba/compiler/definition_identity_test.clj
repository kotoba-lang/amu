(ns kotoba.compiler.definition-identity-test
  "ADR 0300. What a definition CID is allowed to depend on, and what it is not.

  Every case here is a claim about the SEALED payload, so each one is written
  as a pair: two modules that must agree, or two that must differ. A test that
  only asserts a CID is a well-formed string would pass for an identity that
  hashed the source text."
  (:require [clojure.edn :as edn]
            [clojure.java.io :as io]
            [clojure.string :as str]
            [clojure.test :refer [deftest is testing]]
            [kotoba.compiler.core :as compiler]
            [kotoba.compiler.definition-identity :as di]
            [kotoba.kir :as ir]
            [kotoba.kir.alpha-normalization :as an]
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
  only in a binder therefore hash differently, which is why binders are renamed
  before anything is handed to it.

  Still true after the 2026-09-02 convergence, and that is the point. The walk
  moved into kotoba-kir as `kotoba.kir.alpha-normalization`, a SEPARATE
  namespace that `definition-cid` deliberately does not call: identity hashes a
  payload whose :kir may be a const or a do-block, renaming must precede
  dependency linking rather than follow it, and verification needs the caller's
  call targets. So normalization is still an explicit step, and this is still
  the measurement that says why it has to be one. If it ever goes green,
  `definition-cid` has started normalizing internally and the ordering above
  needs re-deciding -- not before."
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

(def ^:private unnameable-capability-id
  "A wire id no capability catalog entry names. The effect-row bridge refuses a
  member it cannot translate, which is the only remaining way to reach the
  refusal markers from this side -- see `abort-now-reaches-the-sealed-row`."
  9999)

(defn- unbridgeable-module
  "A two-function module whose callee carries an untranslatable effect row.

  Synthetic rather than compiled from source, for the same reason the schema
  tests are: no `.kotoba` program produces a wire id the catalog does not name,
  which is exactly what makes the refusal worth pinning."
  []
  {:hir {:named-operations #{} :exports '[main]}
   :kir {:functions [{:name 'callee :params '[x] :param-types [:i64]
                      :result :i64 :effects #{[:cap/call unnameable-capability-id]}
                      :body '(+ x 1)}
                     ;; main's own row is empty on purpose: its only problem is
                     ;; that its callee has no identity, so the marker it gets
                     ;; distinguishes :dependency-unavailable from
                     ;; :unbridged-effect rather than conflating them.
                     {:name 'main :params '[] :param-types []
                      :result :i64 :effects #{}
                      :body '(callee 3)}]}})

(defn- unbridgeable-report []
  (let [m (unbridgeable-module)] (di/definitions (:hir m) (:kir m))))

(deftest an-unbridgeable-effect-row-is-refused-with-a-marker
  (testing "the row the identity seals is the SEMANTIC vocabulary -- named
  operations as keywords -- so a wire id the catalog cannot name has no
  translation. The compiler records the refusal instead of inventing a row, and
  a marker is not a CID: :cid is absent, so a consumer reading it gets nothing
  rather than something plausible."
    (let [entries (:entries (unbridgeable-report))]
      (is (= :unbridged-effect (:definition-cid (get entries "callee"))))
      (is (nil? (:cid (get entries "callee")))
          "a refusal never carries a CID as well as a marker")
      (is (= :dependency-unavailable (:definition-cid (get entries "main")))
          "a caller of an unidentifiable definition is unidentifiable too")
      (is (nil? (:cid (get entries "main")))))))

(deftest abort-now-reaches-the-sealed-row
  (testing "MEASURED 2026-09-02, and this test was the opposite assertion until
  then. `:abort` was refused as `not a wire capability call`, and these tests
  used an aborting fixture to reach the refusal markers. kotoba-kir d082a57
  made control effects bridge through unchanged: `:abort` has no capability and
  no wire id because there is no numeric ABI behind a control effect, but the
  difference between a function that can leave its caller by aborting and one
  that cannot is semantic -- their interfaces are `[:result T E]` against `T` --
  so it must reach the sealed row. Restating the old refusal here would be
  asserting something the upstream change deliberately made false."
    (let [entries (:entries (report (slurp (io/file "test/nbb/fixtures/abort-callee.kotoba"))))]
      (is (every? string? (map :cid (vals entries)))
          "every definition in an aborting module is identified")
      (is (every? nil? (map :definition-cid (vals entries)))
          "and none of them carries a refusal marker")))
  (testing "and it is sealed, not merely tolerated: the same body with and
  without the ability is two definitions"
    (let [module (fn [effects]
                   {:hir {:named-operations #{} :exports '[f]}
                    :kir {:functions [{:name 'f :params '[x] :param-types [:i64]
                                       :result :i64 :effects effects
                                       :body '(+ x 1)}]}})
          cid (fn [m] (get-in (di/definitions (:hir m) (:kir m)) [:entries "f" :cid]))]
      (is (string? (cid (module #{:abort}))))
      (is (not= (cid (module #{})) (cid (module #{:abort})))))))

(deftest a-module-with-a-refused-definition-yields-no-cache-material
  (let [m (unbridgeable-module)]
    (is (nil? (di/cache-material (di/definitions (:hir m) (:kir m)) (:exports (:hir m))))
        "a partial identity is not an identity; a cache keyed on one would serve
        one module's artifact for another")))

(deftest the-scanned-floor-distinguishes-nothing-identified-from-all-identified
  (let [clean (report base)
        refused (unbridgeable-report)]
    (is (= "SCANNED\t2/2" (di/scanned-line clean)))
    (is (= "SCANNED\t0/2" (di/scanned-line refused)))
    (is (not= (di/scanned-line clean) (di/scanned-line refused)))))

(deftest a-refused-definition-is-listed-rather-than-omitted
  (let [lines (di/format-lines (unbridgeable-report))]
    (is (= 2 (count lines)) "a listing that dropped what it could not identify
        would report a clean module")
    (is (every? #(str/includes? % "REFUSED:") lines))))

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

(deftest desugar-contract-version-matches-the-elaboration-pipeline-authority
  (testing "was `desugar-contract-version-is-pinned-because-no-authority-
  declares-one`, and the gap that named it was mis-stated. kotoba-lang
  lang/elaboration-pipeline.edn [:contract-versions :desugar-contract] had
  declared this number since W0 and had read 2 since 2026-09-01, when `eval`
  moved out of :forbidden-heads and into the desugar table. So the compiler was
  not sealing an unowned number; it was sealing a STALE one, and two definitions
  compiled either side of a desugar change claimed one identity. This is now the
  same assertion profile-version has: read the resource, compare the constant."
    (let [pipeline (edn/read-string
                    (slurp (io/resource "kotoba/lang/elaboration-pipeline.edn")))]
      (is (= (get-in pipeline [:contract-versions :desugar-contract])
             di/desugar-contract-version)
          "bump `kotoba.compiler.definition-identity/desugar-contract-version`
          with the authority, and expect every definition CID to move -- that is
          what the sealed input means"))))

(deftest the-frozen-vectors-never-declared-a-desugar-contract-version
  (testing "the retired pin read 1 `because the frozen vectors use 1`. They do
  not declare a current value: a vector carries the version as an INPUT and pins
  the CID it produces, and two of them carry different inputs on purpose. This
  is the reason raising the authority moved every CID this compiler mints and
  not one frozen vector."
    (let [payload (fn [desugar]
                    {:definition/profile-version 6
                     :definition/desugar-contract-version desugar
                     :definition/kir {:op :const :value 1}
                     :definition/effect-row #{}
                     :definition/interface {:arity 0 :result :i64}
                     :definition/dependencies []})]
      (is (not= (kir-id/definition-cid (payload 1))
                (kir-id/definition-cid (payload 2)))
          "both are valid inputs with valid CIDs; neither is `the` version"))))

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

(deftest alpha-normalization-is-delegated-not-reimplemented
  (testing "this namespace and kotoba.codebase.typed-code each carried the same
  five-binder walk against the same KIR, which kotoba-lang lang/code-identity.edn
  recorded as a residual risk of :ci8. The walk now lives in kotoba-kir. What
  stays here is the leaf -- under nbb a .kotoba integer literal is a JavaScript
  BigInt, which is neither integer? nor number?, so a walk that left it alone
  would refuse every module loudly for the wrong reason -- and it is passed as
  an argument, not reimplemented around a private copy."
    (is (= (an/alpha-normalize {:params '[x] :body '(+ x 1)}
                               {:scalar #'kotoba.compiler.definition-identity/canonical-value})
           (di/alpha-normalize {:params '[x] :body '(+ x 1)}))
        "the compiler's alpha-normalize IS kir's, with this repository's leaf")
    (is (= '[k0] (:params (di/alpha-normalize {:params '[x] :body 'x})))))
  (testing "the refusal keeps this namespace's problem keyword"
    (let [ex (try (#'di/verify-normalized!
                   (di/alpha-normalize {:params '[] :body '(pair (let [a 1] a) a)})
                   #{})
                  nil
                  (catch Exception e e))]
      (is (some? ex) "refused")
      (is (= :definition/binder-not-normalized (:problem (ex-data ex)))))))
