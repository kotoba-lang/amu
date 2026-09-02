(ns kotoba.compiler.guest-grammar-vendor-test
  "Two copies of kotoba-lang's `lang/guest-grammar.edn` are on this
  repository's classpath: this repository's own `resources/` copy, and
  kotoba-sema's, across the `deps.edn` pin. `io/resource` answers with the
  FIRST, so which one the compiler actually reads is decided by classpath
  order -- and until 2026-09-03 nothing compared them.

  ## What that hid

  Measured 2026-09-03 on the four mains, before the resync wave:

  | copy | lines |
  |---|---|
  | kotoba-lang `lang/guest-grammar.edn` (authority) | 601 |
  | kotoba-lang `resources/…` | 601 |
  | kotoba-sema `resources/…` | 601 |
  | **amu `resources/…`** | **580** |
  | **kotoba `resources/…`** | **401** |
  | **kotoba `vendor/grammar/resources/…`** | **401** |

  This repository's copy was one change behind (local-state slice 1: the
  authority admits a non-escaping `atom`/`swap!`/`reset!` by elaboration and
  had removed them from `:forbidden-heads`; this copy still forbade them). So
  `guest-grammar-conformance-test` above, which asserts that
  `sema/forbidden-heads` is a superset of the catalog's, was reading a catalog
  with three EXTRA forbidden heads and passing -- a superset check cannot see
  a stale copy that forbids too much.

  kotoba-lang has a check for exactly this,
  `local-and-sibling-vendors-match-authority`. It compares against `../amu`,
  `../kotoba`, `../kotoba-sema` and `../grammar` -- west monorepo paths, each
  guarded with `(when (.isFile ...))`, with an absent path reported `:missing`
  and tolerated. In a single-repository clone it compares one file, the
  authority's own copy of itself, and reports green. Three of four copies had
  drifted on main and it said nothing: ADR-2608136000's shape, where a check
  that could not run returns the value of a check that ran and found nothing
  wrong.

  ## What this file checks

  1. Every classpath copy is byte-identical to every other, comparing THIS
     repository's copy against kotoba-sema's ACROSS THE PIN. The copy cannot
     be absent, because it is a classpath resource.
  2. Every copy's sha256 equals the authority digest of the 2026-09-03 wave.
     That literal is pinned in four repositories, so an authority edit not
     carried to all four goes red in the ones left behind.
  3. `COMPARED <n>` is printed and `n < 2` is refused: a run that found one
     copy has not compared anything, and must not read as a pass.

  Failures name the differing HEADS -- the symmetric difference of
  `:admitted-builtins` and of `:forbidden-heads` -- rather than reporting that
  the files differ."
  (:require [clojure.edn :as edn]
            [clojure.set :as set]
            [clojure.string :as str]
            [clojure.test :refer [deftest is testing]]))

(def authority-grammar-sha256
  "sha256 of kotoba-lang `lang/guest-grammar.edn` at the 2026-09-03 resync
  wave. Change it only as part of that wave, in all four repositories."
  "3e3f9748e245386fc2c89bbadabddfebb4bf02190e137494feacec6a12b4500a")

(def ^:private resource-path "kotoba/lang/guest-grammar.edn")

(defn- sha256-hex [^bytes bs]
  (let [d (.digest (java.security.MessageDigest/getInstance "SHA-256") bs)]
    (apply str (map #(format "%02x" %) d))))

(defn- classpath-copies []
  (->> (enumeration-seq (.getResources (clojure.lang.RT/baseLoader) resource-path))
       (mapv (fn [url]
               (let [bytes (with-open [in (.openStream url)] (.readAllBytes in))]
                 {:url (str url)
                  :sha256 (sha256-hex bytes)
                  :grammar (edn/read-string (String. bytes "UTF-8"))})))))

(defn- head-names [x] (into #{} (map name) x))

(defn- differing-heads [a b]
  (into {}
        (keep (fn [k]
                (let [x (head-names (get (:grammar a) k #{}))
                      y (head-names (get (:grammar b) k #{}))]
                  (when (not= x y)
                    [k {:only-in-first (sort (set/difference x y))
                        :only-in-second (sort (set/difference y x))}]))))
        [:admitted-builtins :forbidden-heads]))

(deftest every-classpath-copy-of-the-grammar-is-the-same-grammar
  (let [copies (classpath-copies)]
    (println (format "COMPARED\t%d\tclasspath copies of %s" (count copies) resource-path))
    (is (>= (count copies) 2)
        (str "expected at least two copies on the classpath -- this repository's"
             " own and kotoba-sema's, across the deps.edn pin -- but found "
             (count copies) ": " (pr-str (mapv :url copies))
             ". One copy compares nothing; a run that measured nothing must not"
             " read as a run that found nothing wrong."))
    (let [[head & rest] copies]
      (doseq [other rest]
        (is (= (:sha256 head) (:sha256 other))
            (str "two classpath copies of the grammar disagree; which one the"
                 " compiler reads is decided by classpath order\n"
                 "  " (:url head) "\n    " (:sha256 head) "\n"
                 "  " (:url other) "\n    " (:sha256 other) "\n"
                 "  differing heads: " (pr-str (differing-heads head other))))))))

(deftest every-classpath-copy-is-the-authority-of-the-resync-wave
  ;; Byte-equality between the copies is not enough on its own: all of them
  ;; could be resynced to each other and still be behind kotoba-lang. The
  ;; digest is what ties them to the authority, in a repository that does not
  ;; and should not depend on kotoba-lang.
  (let [copies (classpath-copies)]
    (is (pos? (count copies)) "the grammar resource is not on the classpath at all")
    (doseq [{:keys [url sha256]} copies]
      (is (= authority-grammar-sha256 sha256)
          (str "vendored grammar drifted from the authority\n"
               "  copy     " url "\n"
               "  expected " authority-grammar-sha256 "\n"
               "  actual   " sha256 "\n"
               "Resync from kotoba-lang lang/guest-grammar.edn and carry the"
               " digest to kotoba-lang, amu, kotoba-sema and kotoba together.")))))

(deftest the-grammar-this-repository-reads-names-the-kernel-families
  ;; `io/resource` is what `kotoba.compiler.sema/load-catalog-forbidden`
  ;; actually calls, so this asserts the copy that WINS, not merely a copy.
  ;; The equality against kotoba-sema's frontend tables is asserted there,
  ;; where the tables are; here the counts are pinned so a resync that dropped
  ;; a family is loud in this repository too.
  (let [grammar (edn/read-string (slurp (clojure.java.io/resource resource-path)))
        builtins (head-names (:admitted-builtins grammar))
        kernel (into #{} (filter #(or (str/starts-with? % "kernel-")
                                      (str/starts-with? % "slice-")))
                     builtins)]
    (println (format "SCANNED\t%d\tadmitted-builtins (%d kernel heads)"
                     (count builtins) (count kernel)))
    (is (= 114 (count kernel))
        "kotoba-sema 1afff23 admitted 114 kernel heads on 2026-09-03")
    (testing "local-state slice 1 reached this copy: atom/swap!/reset! are
              admitted by elaboration and are no longer forbidden heads"
      (let [forbidden (head-names (:forbidden-heads grammar))]
        (is (empty? (set/intersection forbidden #{"atom" "swap!" "reset!"}))
            "this copy is behind the authority by local-state slice 1")
        (is (set/subset? #{"ref" "dosync" "volatile!" "binding" "var"} forbidden)
            "the seven heads with no ability model must still be forbidden")))))
