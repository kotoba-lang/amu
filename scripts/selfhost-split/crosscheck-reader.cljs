;; Cross-checks the Python parser against the repo reader (kotoba.sema/read-forms): same number of top-level
;; forms, and every form the reader returns with source metadata starts inside the line span the Python tool gives it.
;;   node --stack-size=4096 nbb/cli.js --classpath "<sema>/src:<cp-10>" crosscheck-reader.cljs SRC.cljk graph.edn
(ns crosscheck-reader
  (:require [kotoba.sema :as sema] [cljs.reader :as edn] ["fs" :as fs]))
(let [args (vec (take-last 2 (js->clj (.-argv js/process))))
      src (first args) graph (second args)
      forms (sema/read-forms (str (fs/readFileSync src)))
      g (edn/read-string (str (fs/readFileSync graph)))
      nodes (:nodes g)
      with-meta (keep-indexed (fn [i f] (when-let [m (meta f)] [i (:line m)])) forms)
      mism (remove (fn [[i line]] (let [n (nth nodes i)] ; a #?(...) wrapper starts before the form the reader resolves it to
                                       (<= (:line n) line (+ (:line n) (:lines n) -1)))) with-meta)]
  (println "reader forms:" (count forms) "python forms:" (count nodes)
           "forms with source metadata:" (count with-meta) "line mismatches:" (count mism))
  (println "first mismatches (index reader-line python-line):"
           (pr-str (map (fn [[i l]] [i l (:line (nth nodes i))]) (take 5 mism))))
  (println (if (and (= (count forms) (count nodes)) (empty? mism)) "READER-CROSSCHECK-OK" "READER-CROSSCHECK-FAILED")))
