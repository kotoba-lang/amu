;; R3 expectations for the positives stage-0 REFUSES on native code (see r3.oracle; 'unsupported effect' for abort, 'typed values
;; currently require ...' for typed sets and maps). Not stage-0 measurements: conf/ values are lang/conformance/manifest.edn
;; :expect (kotoba-lang 919232de, executed there on the KIR interpreter); feat/ values are derived by hand from the
;; language rules (lang/abort-ability.edn; typed sets/maps unique and sorted by key, lang/guest-grammar.edn
;; :map-literal :order), one line of arithmetic each in the program's comment or below.
conf/abort-abort_through_callee 104
conf/abort-aborting_call_inside_loop 1003
conf/abort-explicit_catch_type 16
conf/abort-operand_position 108
conf/abort-propagate_through_caller 5
conf/abort-throw_inside_loop 105
conf/coll-map_literal_values 125
conf/coll-set 1
conf/stdlib-keyed 3555086133
feat/22-set-literal 3
feat/23-set-dedupe 22
feat/24-set-equal 1101
feat/25-map-literal 114
feat/26-map-assoc 2113
feat/27-map-keys-vals 2311
feat/28-map-equal 101
feat/29-map-nested 8
feat/31-abort-callee 503
feat/32-abort-propagate 5006
feat/33-abort-i64 7000
feat/34-abort-loop 1003
feat/35-try-in-loop 906
feat/36-abort-result 6
feat/37-abort-operands 108
feat/38-abort-recursive 42
feat/40-set-strings 12
feat/41-set-order 1662087
feat/42-map-order 222
