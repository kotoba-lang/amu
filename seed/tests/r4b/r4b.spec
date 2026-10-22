;; R4B expectations for the positives stage-0 REFUSES (see r4b.oracle); values derived by hand.
;; 21: stage-0 "runtime KIR record construction rejected" (a record with an [:option [:ref R]] field built natively).
;;     name-score root 1 + 10 * name-score inner (:leaf -> 2) + w of b2 400 + 1000 * count 2 = 2421
feat/21-mutual-schemas 2421
;; 22: stage-0 refuses a [:ref :kw] that no ns :schemas entry declares ("value type references a schema outside the closed
;;     namespace table"); the seed also registers INLINE schemas ([:record :kw ..] anywhere in the file), the shape of KIR,
;;     which keeps its :schemas outside the functions (seed/CONTRACT-REQUESTS.md R4B lines). (1 + 1) + 100 * (20 + 3) = 2302
feat/22-inline-ref 2302
