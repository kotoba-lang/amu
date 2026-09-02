#!/usr/bin/env nbb
;; ADR 0300. The JVM route and the JDK-free nbb route must mint the SAME
;; definition CID for the same source.
;;
;; This is the claim the whole mechanism rests on. A definition CID that
;; depended on which runtime compiled it would be a build identifier wearing
;; the shape of a content address: a lock pinning one would refuse the other,
;; and a cache keyed on one would miss for a reason nobody could see.
;;
;; The comparison is on the CID STRINGS, per definition, not on "both routes
;; answered". A test that only asserted both exited 0 would pass for two
;; routes that disagreed about every definition in the module.
;;
;;   nbb scripts/test-definition-cid-parity.cljs

(ns scripts.test-definition-cid-parity
  (:require [clojure.string :as str]
            [scripts.lib :as lib]))

(def directory (lib/temp-dir "kotoba-defcid-parity-"))

(def sources
  {"plain.kotoba"
   (str "(ns d (:export [main]))\n"
        "(defn helper [a] (+ a 2))\n"
        "(defn main [] (helper 3))\n")
   ;; A `let`, so the alpha-normalization runs on both routes.
   "binders.kotoba"
   (str "(ns d (:export [main]))\n"
        "(defn helper [zzz] (let [q (+ zzz 2)] (if (> q 5) q 0)))\n"
        "(defn main [] (helper 3))\n")
   ;; Mutual recursion, so scc-v1's permutation choice runs on both routes.
   ;; The ordering is picked from canonical bytes; if the two routes encoded
   ;; differently they would pick different orderings and every member CID
   ;; would move.
   "cycle.kotoba"
   (str "(ns d (:export [main]))\n"
        "(defn ev [n] (if (= n 0) 1 (od (- n 1))))\n"
        "(defn od [n] (if (= n 0) 0 (ev (- n 1))))\n"
        "(defn main [] (ev 4))\n")
   ;; A large literal: the JVM holds it as a Long and nbb as a BigInt, which is
   ;; the one place the two hosts hold the same value in different types.
   "wide.kotoba"
   (str "(ns d (:export [main]))\n"
        "(defn main [] (+ 1234605616436508552 1))\n")
   ;; A capability, so the effect-row bridge runs on both routes -- under nbb
   ;; the wire id is a BigInt, and a catalog lookup without normalisation finds
   ;; nothing and refuses.
   "capability.kotoba"
   (str "(ns d (:export [main]))\n"
        "(defn main [] :string (hash/sha256 \"x\"))\n")})

(doseq [[nm text] sources] (lib/write-text! (lib/join directory nm) text))

(def failures (atom []))
(defn check! [ok? message]
  (println (if ok? "PASS" "FAIL") message)
  (when-not ok? (swap! failures conj message)))

(defn- lines-of [text]
  (when-let [m (re-find #":lines \[(.*?)\], :payload-version" text)]
    (->> (re-seq #"\"([^\"]+)\"" (second m))
         (mapv second))))

(defn- route [command args]
  (let [result (lib/run (first command) (into (vec (rest command)) args)
                        {:allow-failure? true})]
    (when-not (zero? (:status result))
      (throw (js/Error. (str "route failed: " (pr-str command) " " (pr-str args)
                             "\n" (:stdout result) (:stderr result)))))
    (:stdout result)))

(doseq [nm (sort (keys sources))]
  (let [file (lib/join directory nm)
        nbb-out (route [js/process.execPath (lib/join lib/root "bin" "amu")]
                       ["definition-cids" file "--jvm-free"])
        jvm-out (route ["clojure" "-M:run"] ["definition-cids" file])
        nbb-lines (lines-of nbb-out)
        jvm-lines (lines-of jvm-out)]
    (check! (seq nbb-lines) (str nm ": the nbb route listed definitions"))
    (check! (seq jvm-lines) (str nm ": the JVM route listed definitions"))
    (check! (= nbb-lines jvm-lines)
            (str nm ": both routes mint identical definition CIDs"
                 (when (not= nbb-lines jvm-lines)
                   (str "\n  nbb " (pr-str nbb-lines) "\n  jvm " (pr-str jvm-lines)))))
    (check! (not-any? #(str/includes? % "REFUSED:") nbb-lines)
            (str nm ": every definition was identified (a fixture whose every"
                 " definition is refused would make the equality above vacuous)"))))

(lib/remove-tree! directory)
(println (count @failures) "failed")
(when (seq @failures) (.exit js/process 1))
