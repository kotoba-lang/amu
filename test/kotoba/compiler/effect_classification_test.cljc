(ns kotoba.compiler.effect-classification-test
  "Root ADR-2607280100 D5: classification is the type of an EFFECT, and a
  missing declaration is denied at compile time.

  Every refusal below has been shown to fire for the reason it names, by
  breaking the one thing it claims to catch and observing that exactly the
  named tests went red. The two that decide by rank carry a probe EXACTLY at
  the boundary, because a comparison with examples only on either side cannot
  tell `<` from `<=`."
  (:require [clojure.test :refer [deftest is testing]]
            [kotoba.compiler.effect-classification :as classification]
            [kotoba.compiler.effect-row :as effect-row]
            [kotoba.security.information-flow :as flow]))

(def ^:private hash-sha256 [:cap/call 3])       ; :public
(def ^:private log-append [:cap/call 6])        ; :internal
(def ^:private state-transact [:cap/call 8])    ; :confidential
(def ^:private secret-get [:cap/call 21])       ; :restricted
(def ^:private no-such-capability [:cap/call 200])

(defn- check-throws
  "The ex-data of the refusal `f` throws, or nil when it does not throw."
  [f]
  #?(:clj (try (f) nil (catch clojure.lang.ExceptionInfo e (ex-data e)))
     :cljs (try (f) nil (catch ExceptionInfo e (ex-data e)))))

(defn- admit
  "`effect-row/check` over EFFECTS with POLICY, granting exactly EFFECTS."
  ([effects] (admit effects {}))
  ([effects policy]
   (effect-row/check {:effects effects}
                     (merge {:allow (set effects)} policy))))

;; ---------------------------------------------------------------------------
;; The declaration exists, is complete, and is in the one lattice.

(deftest every-declaration-this-host-decides-by-is-rankable
  (let [decls classification/declarations
        labels (vals decls)
        unrankable (flow/unknown-labels (set labels))]
    (is (pos? (count decls))
        "declarations loaded at all -- an empty map would make every count
         below zero while refusing every compilation")
    (is (= 0 (count unrankable))
        (str "labels outside kotoba.security.information-flow/ranks: "
             (pr-str unrankable)))
    (is (= (count decls) (count (filter keyword? labels)))
        "a declaration must be a keyword, not a string that reads like one")))

(deftest the-lattice-is-borrowed-and-not-restated
  ;; ADR-2607280100 D1 exists because there were two copies of this map.
  (is (= #{:public :internal :confidential :personal :restricted}
         (set (keys flow/ranks))))
  (is (every? #(contains? flow/ranks %) (vals classification/declarations))
      "every declaration this host decides by is a label the one lattice ranks"))

#?(:clj
   (deftest cljs-fallback-matches-the-catalog
     ;; ClojureScript cannot read the resource, so it decides by a literal.
     ;; This is the only thing that can notice the two disagreeing, and the
     ;; disagreement would be invisible on the host that runs this test.
     (let [catalog classification/catalog-declarations
           fallback classification/cljs-declarations
           missing (remove #(contains? fallback %) (keys catalog))
           differing (filter (fn [[nm label]]
                               (and (contains? fallback nm)
                                    (not= label (get fallback nm))))
                             catalog)]
       (is (pos? (count catalog)))
       (is (= 0 (count missing))
           (str "in the catalog and not in the ClojureScript fallback: "
                (pr-str missing)))
       (is (= 0 (count differing))
           (str "declared differently on the two hosts: " (pr-str differing)))
       (is (>= (count fallback) (count catalog))
           "the fallback may carry capabilities this repository's catalog copy
            does not yet have; it may not carry fewer"))))

;; ---------------------------------------------------------------------------
;; The refusal. Unconditional -- no policy key reaches it.

(deftest an-effect-with-no-descriptor-is-refused-at-compile-time
  (let [d (check-throws #(classification/check! #{no-such-capability}))]
    (is (some? d) "a capability id no catalog entry names must not compile")
    (is (= #{no-such-capability} (:classification/undeclared d)))
    (is (= 1 (:classification/count d)))
    (is (= :admission (:phase d)))))

(deftest the-refusal-cannot-be-switched-off-by-a-policy
  ;; Problem 3 of ADR-2607280100: every classification route was opt-in and a
  ;; caller that passed nothing was permitted. There is no key here to pass.
  (doseq [policy [{:allow #{no-such-capability}}
                  {:allow #{no-such-capability} :abac {}}
                  {:allow #{no-such-capability}
                   :attributes {:subject {:id :builder :clearance :restricted}}}]]
    (is (some? (check-throws
                #(effect-row/check {:effects #{no-such-capability}} policy)))
        (str "granted, cleared, and still refused: " (pr-str policy)))))

(deftest an-unrankable-declaration-is-refused-separately-from-a-missing-one
  (with-redefs [classification/declarations {:hash/sha256 :top-secret}]
    (let [d (check-throws #(classification/check! #{hash-sha256}))]
      (is (some? d))
      (is (nil? (:classification/undeclared d))
          "a declared-but-unrankable label is not reported as missing")
      (is (= #{:top-secret} (:classification/unrankable d))))))

(deftest the-classification-refusal-is-above-the-missing-grant-refusal
  ;; When both would refuse: `this effect has no declared classification` is
  ;; actionable, `the policy did not grant it` reports a check that was never
  ;; reached, because no policy can admit an effect nobody has classified.
  (let [d (check-throws
           #(effect-row/check {:effects #{no-such-capability}} {:allow #{}}))]
    (is (= #{no-such-capability} (:classification/undeclared d)))
    (is (nil? (:missing d)) "the missing-grant refusal did not win")))

;; ---------------------------------------------------------------------------
;; The row's own label. Object side: unknown rounds UP.

(deftest a-row-that-exercises-no-authority-is-classified-public
  (is (= :public (:classification/effective (classification/classify #{}))))
  (is (= :public (:classification/effective (admit #{})))))

(deftest the-row-label-is-the-join-and-not-the-minimum
  (let [facts (classification/classify #{hash-sha256 secret-get})]
    (is (= #{:public :restricted} (:classification/labels facts)))
    (is (= :restricted (:classification/effective facts))
        "the highest of the row, not the lowest -- an object rounds UP")
    (is (= 2 (count (:classification/declared facts))))))

(defn- no-read-up-denial
  "The ABAC controls admission refused SUBJECT-CLEARANCE with, over EFFECTS,
  or nil when it admitted them. `kotoba.kir.admission/check` THROWS on an ABAC
  denial rather than returning one, so a test that reads `:abac/allowed?` from
  its return value can only ever see `true`."
  ([clearance effects] (no-read-up-denial clearance nil effects))
  ([clearance resource-classification effects]
   (let [attrs (cond-> {:subject {:id :builder :clearance clearance}}
                 (some? resource-classification)
                 (assoc :resource {:classification resource-classification}))]
     (some->> (check-throws #(admit effects {:attributes attrs}))
              :abac/violations
              (mapv :abac/control)))))

(deftest a-caller-cannot-lower-the-row-label-and-can-raise-it
  (testing "a caller-supplied label BELOW the descriptor's is ignored"
    (is (= [:classification] (no-read-up-denial :confidential :public #{secret-get}))
        "secret/get is :restricted whatever the caller says about it"))
  (testing "a caller-supplied label ABOVE the descriptor's is taken"
    (is (= [:classification] (no-read-up-denial :confidential :restricted #{hash-sha256}))))
  (testing "a caller-supplied label the lattice cannot rank rounds UP"
    (is (= [:classification] (no-read-up-denial :confidential :not-a-label #{hash-sha256}))
        "flow/join reads an unknown object label as :restricted"))
  (testing "and the same caller-supplied labels change nothing on their own"
    (is (nil? (no-read-up-denial :restricted :public #{secret-get}))
        "a subject cleared for the descriptor's label is admitted, so the
         denials above are the classification and not the fixture")))

;; ---------------------------------------------------------------------------
;; Subject side: unknown grants NOTHING. Never rounded up.

(deftest no-read-up-is-armed-only-when-the-policy-names-a-subject-clearance
  (is (= :unarmed (:classification/no-read-up (admit #{secret-get})))
      "no subject clearance in the policy: nothing to compare against")
  (is (= :armed (:classification/no-read-up
                 (admit #{secret-get}
                        {:attributes {:subject {:id :builder
                                                :clearance :restricted}}})))))

(deftest the-effective-label-is-reported-even-when-the-comparison-is-unarmed
  ;; An unarmed comparison and a comparison that passed both leave
  ;; `:abac/allowed? true`. The label says which happened.
  (let [r (admit #{secret-get})]
    (is (true? (get-in r [:abac :abac/allowed?])))
    (is (= :restricted (:classification/effective r)))
    (is (= :unarmed (:classification/no-read-up r)))))

(deftest a-subject-cleared-exactly-at-the-requirement-is-admitted
  ;; THE BOUNDARY. abac compares with `<`; with only examples above and below,
  ;; `<` and `<=` are indistinguishable and the operator is invisible.
  (is (= :confidential (:classification/effective (classification/classify
                                                   #{state-transact}))))
  (is (nil? (no-read-up-denial :confidential #{state-transact}))
      "clearance rank EQUALS required rank -- admitted")
  (is (= [:classification] (no-read-up-denial :internal #{state-transact}))
      "exactly one rank below -- denied")
  (is (nil? (no-read-up-denial :restricted #{state-transact}))
      "one rank above -- admitted"))

(deftest a-subject-clearance-the-lattice-cannot-rank-grants-nothing
  (is (= [:classification] (no-read-up-denial :top-secret #{log-append}))
      "an unrankable clearance is NOT rounded up -- rounding a subject up is
       privilege escalation by typo, and :top-secret rounded up would clear
       an :internal effect")
  (is (nil? (no-read-up-denial :internal #{log-append}))
      "the same effect with a RANKABLE clearance at the same intended level is
       admitted, so the denial above is the unrankable label and not the row")
  (is (= :top-secret
         (classification/unknown-subject-clearance
          {:attributes {:subject {:id :builder :clearance :top-secret}}}))
      "the silent safe answer is reported, not only taken")
  (is (nil? (classification/unknown-subject-clearance
             {:attributes {:subject {:id :builder :clearance :confidential}}}))))

(deftest a-rankable-subject-clearance-is-not-reported-as-unknown
  (let [r (admit #{log-append}
                 {:attributes {:subject {:id :builder :clearance :internal}}})]
    (is (nil? (:classification/unknown-subject-clearance r)))
    (is (= :armed (:classification/no-read-up r)))
    (is (true? (get-in r [:abac :abac/allowed?])))))

;; ---------------------------------------------------------------------------
;; Everything admission already decided still decides.

(deftest the-existing-admission-result-is-unchanged
  (let [r (admit #{hash-sha256})]
    (is (true? (:admitted? r)))
    (is (= #{hash-sha256} (:required r)))
    (is (= {:allow #{hash-sha256}} (:minimal-policy r)))
    (is (= #{} (:unused-grants r))))
  (let [d (check-throws #(effect-row/check {:effects #{hash-sha256}}
                                           {:allow #{}}))]
    (is (= #{hash-sha256} (:missing d))
        "a grant that IS classified and is NOT granted still fails on the grant")))

(deftest a-control-effect-still-needs-no-grant-and-no-classification
  ;; `:abort` names no authority, so there is nothing to classify. It is
  ;; narrowed away before this namespace sees the row.
  (let [r (effect-row/check {:effects #{:abort hash-sha256}}
                            {:allow #{hash-sha256}})]
    (is (true? (:admitted? r)))
    (is (= :public (:classification/effective r)))))
