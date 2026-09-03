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
  wave. Change it only as part of that wave, in all four repositories.

  Advanced three times on 2026-09-03 as the wave moved: 3e3f9748 (the pair
  #762 landed), 67561e57 (kotoba-lang ca2e595a, which #761 carried into this
  repository's copy alone -- and that skew is what made main red), and this
  one, kotoba-sema 1587f573. Each advance moves the `deps.edn` pin, the
  vendored copy and this literal in ONE commit; ADR 0330 postscript is why.

  NOT advanced by the 2026-09-03 pin advance to kotoba-sema df383ba0. That
  advance carries `conj`/`disj` lowerings, the declared-type guards and the
  exposed kernel heads, and its copy of the grammar is byte-identical to the
  one vendored here -- so the pin moved and this digest did not, which is
  allowed and is the reason `deps-edn-claim` below recomputes rather than
  assuming the two always move together."
  "6e1202fd23bc5a2ed6ef432114585c1813f5143d643eb4c8ee9a00b6e798b922")

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
    ;; 114 -> 115 on 2026-09-03 with the third resync of the wave. The head
    ;; is `kernel-uefi-alloc-region`, and it is a real addition rather than a
    ;; drifting number: kotoba-sema 727f9d6 (its ADR-0030) makes it a
    ;; PROVENANCE ROOT beside `kernel-boot-info` and `kernel-scratch-region`,
    ;; because `AllocatePages` answers through a load and `traceable-base?`
    ;; refuses a base that came from one -- so a Kotoba UEFI application could
    ;; allocate a page and then not write it. Measured across the resync:
    ;; ADDED (kernel-uefi-alloc-region), REMOVED (), so the count moved by
    ;; exactly the head that was added and no family was dropped.
    (is (= 115 (count kernel))
        "kotoba-sema 1587f57 admitted 115 kernel heads on 2026-09-03")
    (testing "local-state slice 1 reached this copy: atom/swap!/reset! are
              admitted by elaboration and are no longer forbidden heads"
      (let [forbidden (head-names (:forbidden-heads grammar))]
        (is (empty? (set/intersection forbidden #{"atom" "swap!" "reset!"}))
            "this copy is behind the authority by local-state slice 1")
        (is (set/subset? #{"ref" "dosync" "volatile!" "binding" "var"} forbidden)
            "the seven heads with no ability model must still be forbidden")))))

;; ---------------------------------------------------------------------------
;; The claim `deps.edn` makes about the file it pins
;; ---------------------------------------------------------------------------
;;
;; The two tests above compare the classpath copies to each other and to
;; `authority-grammar-sha256`. Neither reads `deps.edn`, so the SENTENCE
;; `deps.edn` writes about the grammar was unchecked prose, and it drifted:
;; measured 2026-09-03 at 6c245f69, the comment asserted 3e3f9748 while the
;; file on disk hashed to 67561e57, and the suite was green. A digest stated
;; in a comment is a claim; a claim nothing recomputes is decoration.
;;
;; This closes the three ways the triple can come apart:
;;
;;   1. the digest `deps.edn` states vs. the bytes actually vendored
;;   2. the digest `deps.edn` states vs. `authority-grammar-sha256` above
;;   3. the kotoba-sema sha `deps.edn` states in prose vs. its real `:git/sha`
;;
;; It parses the three `;;   <key>  <value>` lines of the THE PAIR, MEASURED
;; block. Parsing prose is normally a bad bargain, but the alternative is to
;; move the digest out of the comment -- and the comment is exactly the thing
;; that drifted, so it is the thing that has to be pinned. An unparseable or
;; absent block is REFUSED rather than skipped (ADR-2608136000): a run that
;; could not find the claim must not return the value of a run that found the
;; claim correct.

(def ^:private deps-edn-file (java.io.File. "deps.edn"))

(defn- stated-claims
  "The `;;   key  value` lines of deps.edn's THE PAIR, MEASURED block."
  [text]
  (into {}
        (keep (fn [line]
                (when-let [[_ k v] (re-matches #"\s*;;\s{3}(grammar-sha256|kotoba-sema-pin)\s+(\S+)\s*" line)]
                  [(keyword k) v])))
        (str/split-lines text)))

(deftest deps-edn-claim
  (is (.isFile deps-edn-file)
      "deps.edn is not readable from the test working directory, so its claim about
       the vendored grammar cannot be checked; refusing rather than reporting a pass")
  (let [text (slurp deps-edn-file)
        claims (stated-claims text)
        copies (classpath-copies)]
    (println (format "CLAIMS\t%d\tparsed from deps.edn (%s)"
                     (count claims) (pr-str (sort (map name (keys claims)))))) 
    ;; Evidence floor: both keys must be found. If the comment is reworded so
    ;; the block no longer parses, this goes red and someone re-anchors it --
    ;; which is the point. Silently finding nothing would restore exactly the
    ;; unchecked-prose state this test exists to end.
    (is (= #{:grammar-sha256 :kotoba-sema-pin} (set (keys claims)))
        (str "deps.edn's THE PAIR, MEASURED block did not parse; found "
             (pr-str claims) ". Expected two lines of the form"
             " `;;   grammar-sha256    <64 hex>` and `;;   kotoba-sema-pin   <40 hex>`."
             " Refusing to report a pass on a claim that could not be located."))

    (testing "the digest deps.edn states is the digest of the bytes vendored here"
      (when-let [stated (:grammar-sha256 claims)]
        (doseq [{:keys [url sha256]} copies]
          (is (= stated sha256)
              (str "deps.edn states a sha256 that does not describe the file\n"
                   "  copy    " url "\n"
                   "  deps.edn states " stated "\n"
                   "  measured        " sha256 "\n"
                   "The pin, the vendored copy and this digest move in ONE commit"
                   " (ADR 0330 postscript).")))))

    (testing "deps.edn and authority-grammar-sha256 state the same digest"
      (when-let [stated (:grammar-sha256 claims)]
        (is (= authority-grammar-sha256 stated)
            (str "deps.edn's stated digest and this namespace's"
                 " `authority-grammar-sha256` disagree\n"
                 "  deps.edn                 " stated "\n"
                 "  authority-grammar-sha256 " authority-grammar-sha256 "\n"
                 "Two literals for one measurement is how the first one drifted."))))

    (testing "the kotoba-sema sha deps.edn states in prose is the sha it pins"
      (when-let [stated (:kotoba-sema-pin claims)]
        ;; Same shape `aggregate-abi-test/dependency-pin` reads.
        (let [pinned (get-in (edn/read-string text)
                             [:deps 'io.github.kotoba-lang/kotoba-sema :git/sha])]
          (is (some? pinned)
              "could not locate io.github.kotoba-lang/kotoba-sema's :git/sha in deps.edn")
          (is (= stated pinned)
              (str "deps.edn's prose names a different kotoba-sema commit than it pins\n"
                   "  prose says " stated "\n"
                   "  :git/sha   " pinned)))))))
