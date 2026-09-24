#!/bin/bash
# scan: repos with <=4 cljc files whose defs use only plausibly-admitted forms
cd ~/github/com-junkawasaki/orgs/kotoba-lang
for d in */; do
  d=${d%/}
  case "$d" in capability-*|amu|kotoba-lang|identity|giemon) continue;; esac
  files=$(find "$d/src" -name "*.cljc" 2>/dev/null)
  n=$(echo "$files" | grep -c . )
  [ "$n" -gt 0 ] && [ "$n" -le 4 ] || continue
  # skip if closure includes non-local requires
  reqs=$(echo "$files" | xargs grep -h "(:require" -A5 2>/dev/null | grep -o '\[[a-z0-9.-]+\.[a-z0-9.-]+' | grep -v 'clojure' | tr -d '[' )
  bad=0
  for r in $reqs; do case "$r" in $d.*|*$d*) ;; *) bad=1;; esac; done
  [ $bad -eq 1 ] && continue
  # forbidden forms in bodies
  forb=$(echo "$files" | xargs grep -h "(for \|(map \|(mapv \|(reduce\|(filter\|(str/join\|(apply \|(count \|(keys \|(seq \|(into \|(repeat\|(pr-str\|(name \|#(\|(loop \|(recur\|(atom\|(volatile\|(doseq\|(dotimes\|(defprotocol\|(defrecord\|(defmulti\|(case \|float\|0\.0" 2>/dev/null | wc -l | tr -d ' ')
  nd=$(echo "$files" | xargs grep -h "^(defn \|(def " 2>/dev/null | wc -l | tr -d ' ')
  if [ "$forb" -eq 0 ] && [ "$nd" -gt 0 ]; then echo "$d nd=$nd n=$n"; fi
done
