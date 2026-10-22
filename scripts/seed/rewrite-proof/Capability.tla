---------------------------- MODULE Capability ----------------------------
EXTENDS Naturals, FiniteSets
CONSTANT Mutate
VARIABLES flags, cached, bad
vars == <<flags, cached, bad>>
Allowed(f) == f = 1..5
Decision(f,c) == IF Mutate THEN c ELSE Allowed(f)
Init == /\ flags = {} /\ cached = FALSE /\ bad = FALSE
SetFlag(i) == /\ flags' = flags \cup {i} /\ UNCHANGED <<cached,bad>>
Revoke(i) == /\ flags' = flags \ {i} /\ UNCHANGED <<cached,bad>>
Issue == /\ Allowed(flags) /\ cached' = TRUE /\ UNCHANGED <<flags,bad>>
Clear == /\ cached' = FALSE /\ UNCHANGED <<flags,bad>>
Use == /\ bad' = (bad \/ (Decision(flags,cached) /\ ~Allowed(flags)))
       /\ UNCHANGED <<flags,cached>>
Next == (\E i \in 1..5: SetFlag(i) \/ Revoke(i)) \/ Issue \/ Clear \/ Use
Spec == Init /\ [][Next]_vars
TypeOK == /\ flags \subseteq 1..5 /\ cached \in BOOLEAN /\ bad \in BOOLEAN
NoUnauthorizedUse == ~bad
=============================================================================
