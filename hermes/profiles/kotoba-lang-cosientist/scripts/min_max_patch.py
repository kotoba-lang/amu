#!/usr/bin/env python3
"""lang-cosientist iteration 7: insert min/max desugar arms after `>=` arm."""
path = "~/github/com-junkawasaki/orgs/kotoba-lang/kotoba-sema/src/kotoba/compiler/frontend.cljc"
src = open(path).read()
old = "             (desugar-comparison-chain '>= args form))\n        and (desugar-and args)"
new = """             (desugar-comparison-chain '>= args form))
        ;; `min`/`max` are two-operand selections, not new lowering: they expand
        ;; to the comparison the author could have written, so the admission
        ;; story stays the existing `if`/`<`/`>` story and the KIR is identical
        ;; to the hand-written twin. Each operand is evaluated once, by binding
        ;; the first the way `desugar-and` binds its left operand.
        min (do (when-not (= 2 (count args))
                  (reject! "min requires exactly two operands" form))
                (let [tmp (desugar-expr (first args))]
                  (list 'let [tmp tmp]
                        (list 'if (list '< tmp (desugar-expr (second args)))
                              tmp
                              (desugar-expr (second args))))))
        max (do (when-not (= 2 (count args))
                  (reject! "max requires exactly two operands" form))
                (let [tmp (desugar-expr (first args))]
                  (list 'let [tmp tmp]
                        (list 'if (list '> tmp (desugar-expr (second args)))
                              tmp
                              (desugar-expr (second args))))))
        and (desugar-and args)"""
assert src.count(old) == 1, src.count(old)
open(path, "w").write(src.replace(old, new))
print("PATCHED")
