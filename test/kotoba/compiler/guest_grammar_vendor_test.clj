(ns kotoba.compiler.guest-grammar-vendor-test
  "This repository ships NO copy of kotoba-lang's `lang/guest-grammar.edn`. It
  reads the copy kotoba-sema ships, across the `deps.edn` pin, and this file is
  what keeps that true.

  ## What was here before, and why it is gone

  Until 2026-09-03 this repository carried its own byte copy at
  `resources/kotoba/lang/guest-grammar.edn`. `:paths` precedes the dependency
  closure on the classpath, so that copy SHADOWED kotoba-sema's: `io/resource`
  answers with the first, and the first was this repository's. kotoba-sema owns
  `kotoba.compiler.frontend`, whose `load-catalog-forbidden` is the production
  reader -- so the frontend's refusal set was decided by a file in a DIFFERENT
  repository from the frontend, updated in a different commit.

  ADR 0327 named that; ADR 0330's postscript recorded what it cost (a pin
  advance and a grammar resync had to be one commit, and when they were two,
  main went red on a merge that was green on each side). The tests here
  enforced the coupling. Deleting the copy removes what the coupling was for:

  - nothing under `src/` ever read the resource -- measured 2026-09-03,
    `grep -rn 'io/resource' src` names no `kotoba/lang/` path, and
    `definition-identity/profile-version` says in its own docstring that it
    repeats the number as a constant because the nbb route has no classpath
    reader at all;
  - the `bin/amu` JDK-free route does not read it either, for the same reason;
  - kotoba-sema is a hard dependency, so its copy is on this classpath whether
    or not this repository ships one.

  So the copy had exactly one effect: it decided which grammar the frontend
  read. With it gone, THE GRAMMAR AND THE FRONTEND TRAVEL IN ONE PIN. A pin
  left behind is then a consistent lag -- an older language, compiled
  coherently -- rather than a frontend reading a grammar it was not built
  against. That distinction is the whole reason for this change: a copy that
  may lag is a copy that can be wrong, and a copy that cannot exist cannot.

  ## What this file checks

  1. This repository ships no copy. A reintroduced one is refused BY PATH,
     before any digest comparison, because a reintroduced copy that happens to
     be byte-identical today is still the shadowing mechanism back.
  2. Exactly one copy is on the classpath, and its URL is kotoba-sema's.
     `COMPARED <n>/1` is printed; zero copies is refused as a run that
     measured nothing (ADR-2608136000).
  3. That copy's sha256 is the last entry of `authority-digest-history`, and
     no copy is a superseded entry -- the digest may stand still while the pin
     advances, but it may never move backwards.
  4. The grammar read names exactly the kernel heads the pinned frontend
     admits."
  (:require [clojure.edn :as edn]
            [clojure.java.io :as io]
            [clojure.set :as set]
            [clojure.string :as str]
            [clojure.test :refer [deftest is testing]]
            [kotoba.sema :as sema]))

(def authority-digest-history
  "Every value this repository has carried for kotoba-lang
  `lang/guest-grammar.edn`, oldest first. The current one is the LAST.

  A VECTOR rather than a single constant, because on 2026-09-03 the constant
  moved BACKWARDS here and nothing could see it. The authority advanced three
  times in an afternoon -- kotoba-lang `543fa62a` (3e3f9748), `904ad318`
  (67561e57), `911c9143` (6e1202fd), each an ancestor of the next -- and two
  PRs set the constant independently an hour apart. #761 vendored 67561e57;
  #762 then wrote the constant back to 3e3f9748, a grammar OLDER than the copy
  already in the tree. main went red, and the failure said only that the copy
  and the constant disagreed -- not which of the two had gone backwards.

  A single constant compared against a single copy is consistent with itself
  at ANY value, so it cannot tell a resync from a regression. The history can:
  going back is a value already in the vector and not at the end, and
  `the-authority-digest-never-moves-backwards` refuses it by name and by
  position.

  This survived the deletion of this repository's own copy. It now describes
  the copy kotoba-sema ships, so it moves ONLY when the `kotoba-sema` pin
  moves -- and a pin advance whose grammar is unchanged appends nothing, which
  is why `deps-edn-claim` recomputes the digest instead of assuming the two
  always move together.

  APPEND to this vector; never substitute."
  ["3e3f9748e245386fc2c89bbadabddfebb4bf02190e137494feacec6a12b4500a"
   "67561e57ad2b135d848eac75b46ab430d4404a463159f43775e01134e569988f"
   "6e1202fd23bc5a2ed6ef432114585c1813f5143d643eb4c8ee9a00b6e798b922"
   "871f3873ae30a33ba7461c8664094b42396c0c4d79612668d11b0b29a2c0172f"
   "9d701ea9a803a4b3d7dc4245274a9a901ab4ac506ebd401282b2acdf7747dd9c"
   "3e41eb84a57a1fcc84dc0ec0b6a5ec1fd535c39e2cf6cfc14418fc1ec4567483"])

(def authority-grammar-sha256
  "sha256 of the grammar this repository reads -- kotoba-sema's copy, at the
  pinned commit. The last entry of `authority-digest-history`."
  (peek authority-digest-history))

(def ^:private resource-path "kotoba/lang/guest-grammar.edn")

(def ^:private retired-local-copy
  "The path this repository shipped until 2026-09-03. Named so its return is a
  named failure rather than a silent restoration of the shadowing."
  (io/file "resources/kotoba/lang/guest-grammar.edn"))

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

(deftest this-repository-ships-no-copy-of-the-grammar
  ;; Checked by PATH, not by digest. A reintroduced copy is the shadowing
  ;; mechanism whether or not today's bytes happen to agree: it puts the
  ;; frontend's refusal set back under a file this repository updates in a
  ;; different commit from the frontend that reads it.
  (is (.isFile (io/file "deps.edn"))
      "deps.edn is not readable from the test working directory, so a relative
       path here proves nothing; refusing rather than reporting a pass on a
       check that could not run")
  (is (not (.isFile retired-local-copy))
      (str "this repository ships " (.getPath retired-local-copy) " again.\n"
           "It SHADOWS kotoba-sema's copy on this classpath, and kotoba-sema"
           " owns the frontend that reads it (`load-catalog-forbidden`), so the"
           " language the compiler admits would again be decided by a file"
           " updated in a different repository's commit. Read kotoba-sema's"
           " copy across the pin instead; if a local copy is genuinely needed,"
           " that is a design change and belongs in an ADR, not in a resync.")))

(deftest exactly-one-grammar-is-on-this-classpath-and-it-is-the-frontends
  (let [copies (classpath-copies)]
    (println (format "COMPARED\t%d/1\tclasspath copies of %s" (count copies) resource-path))
    (is (pos? (count copies))
        (str "no copy of " resource-path " is on the classpath at all. This run"
             " measured nothing, which is not the same as finding nothing"
             " wrong: kotoba-sema is a hard dependency and ships one."))
    (is (= 1 (count copies))
        (str "found " (count copies) " copies of the grammar on this classpath: "
             (pr-str (mapv :url copies)) "\n"
             "Exactly one is the invariant. With two, `io/resource` answers"
             " with whichever comes first and the frontend's refusal set stops"
             " being a property of the frontend's own commit."))
    (doseq [{:keys [url]} copies]
      (is (str/includes? url "kotoba-sema")
          (str "the one grammar on this classpath does not come from"
               " kotoba-sema:\n  " url "\n"
               "kotoba-sema owns `kotoba.compiler.frontend`, so the grammar it"
               " ships is the one the frontend was built against.")))))

(deftest the-authority-digest-never-moves-backwards
  (let [current (peek authority-digest-history)
        superseded (set (butlast authority-digest-history))
        copies (classpath-copies)]
    (println (format "SCANNED\t%d\tauthority digests in the history, current %s"
                     (count authority-digest-history) (subs current 0 12)))
    (is (seq copies)
        "no copy of the grammar is on the classpath; this run measured nothing,
         which is not the same as finding nothing wrong")
    (is (= (count authority-digest-history) (count (set authority-digest-history)))
        "a digest appears twice in the history, so the constant went back to
         bytes this repository had already left")
    (is (= current authority-grammar-sha256)
        "`authority-grammar-sha256` is not the last entry of the history")
    (doseq [{:keys [url sha256]} copies]
      (is (= authority-grammar-sha256 sha256)
          (str "the grammar this repository reads is not the recorded digest\n"
               "  copy     " url "\n"
               "  expected " authority-grammar-sha256 "\n"
               "  actual   " sha256 "\n"
               "Advance the kotoba-sema pin and APPEND the new digest to"
               " `authority-digest-history` in the same commit."))
      (is (not (contains? superseded sha256))
          (str "the grammar on this classpath is a SUPERSEDED authority digest\n"
               "  copy   " url "\n"
               "  sha256 " (subs sha256 0 12) " -- position "
               (.indexOf ^java.util.List authority-digest-history sha256)
               " of " (count authority-digest-history) "\n"
               "Resync FORWARD to " (subs current 0 12)
               "; do not pin a kotoba-sema whose grammar this repository has"
               " already moved past.")))))

(deftest the-grammar-this-repository-reads-names-the-kernel-families
  ;; `io/resource` is what `kotoba.compiler.frontend/load-catalog-forbidden`
  ;; actually calls. Since the deletion above there is only one candidate, so
  ;; this asserts the copy that WINS by being the only one -- which is the
  ;; property the deletion bought.
  (let [grammar (edn/read-string (slurp (io/resource resource-path)))
        builtins (head-names (:admitted-builtins grammar))
        kernel (into #{} (filter #(or (str/starts-with? % "kernel-")
                                      (str/starts-with? % "slice-")))
                     builtins)
        ;; Through kotoba-sema's PUBLIC boundary, not `kotoba.compiler.frontend`:
        ;; requiring the implementation is what
        ;; `namespace-reachability-test/consumers-use-the-public-sema-boundary`
        ;; refuses.
        admitted (head-names sema/kernel-operation-heads)]
    (println (format "SCANNED\t%d\tadmitted-builtins (%d kernel heads; the pinned frontend admits %d)"
                     (count builtins) (count kernel) (count admitted)))
    (is (pos? (count admitted))
        "the pinned frontend admits no kernel head at all; the accessor
         returned nothing, and an empty set would make both comparisons below
         vacuous")
    (is (pos? (count kernel))
        "the grammar names no kernel head at all; an empty set would make both
         comparisons below vacuous in the other direction")
    (is (empty? (set/difference admitted kernel))
        (str "the pinned frontend admits heads the grammar this repository "
             "reads does not name: "
             (pr-str (sort (set/difference admitted kernel)))))
    (is (empty? (set/difference kernel admitted))
        (str "the grammar names heads the pinned frontend does not admit: "
             (pr-str (sort (set/difference kernel admitted)))))
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
;; The tests above compare what is on the classpath to `authority-digest-history`.
;; None of them reads `deps.edn`, so the SENTENCE `deps.edn` writes about the
;; grammar was unchecked prose, and it drifted: measured 2026-09-03 at 6c245f69,
;; the comment asserted 3e3f9748 while the file on disk hashed to 67561e57, and
;; the suite was green. A digest stated in a comment is a claim; a claim nothing
;; recomputes is decoration.
;;
;; It parses the two `;;   <key>  <value>` lines of the THE GRAMMAR, MEASURED
;; block. Parsing prose is normally a bad bargain, but the alternative is to
;; move the digest out of the comment -- and the comment is exactly the thing
;; that drifted, so it is the thing that has to be pinned. An unparseable or
;; absent block is REFUSED rather than skipped (ADR-2608136000): a run that
;; could not find the claim must not return the value of a run that found the
;; claim correct.

(def ^:private deps-edn-file (io/file "deps.edn"))

(defn- stated-claims
  "The `;;   key  value` lines of deps.edn's THE GRAMMAR, MEASURED block."
  [text]
  (into {}
        (keep (fn [line]
                (when-let [[_ k v] (re-matches #"\s*;;\s{3}(grammar-sha256|kotoba-sema-pin)\s+(\S+)\s*" line)]
                  [(keyword k) v])))
        (str/split-lines text)))

(deftest deps-edn-claim
  (is (.isFile deps-edn-file)
      "deps.edn is not readable from the test working directory, so its claim about
       the grammar cannot be checked; refusing rather than reporting a pass")
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
        (str "deps.edn's THE GRAMMAR, MEASURED block did not parse; found "
             (pr-str claims) ". Expected two lines of the form"
             " `;;   grammar-sha256    <64 hex>` and `;;   kotoba-sema-pin   <40 hex>`."
             " Refusing to report a pass on a claim that could not be located."))
    (is (seq copies)
        "no copy of the grammar is on the classpath, so deps.edn's claim about it
         cannot be checked; refusing rather than reporting a pass")

    (testing "the digest deps.edn states is the digest of the bytes read here"
      (when-let [stated (:grammar-sha256 claims)]
        (doseq [{:keys [url sha256]} copies]
          (is (= stated sha256)
              (str "deps.edn states a sha256 that does not describe the file\n"
                   "  copy    " url "\n"
                   "  deps.edn states " stated "\n"
                   "  measured        " sha256 "\n"
                   "The pin and this digest move in ONE commit.")))))

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
