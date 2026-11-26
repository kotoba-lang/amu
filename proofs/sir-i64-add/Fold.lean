import Init.Data.BitVec.Lemmas

namespace SirI64Add

abbrev Word := BitVec 64
abbrev ValueId := Nat

inductive Op where
  | const (dst : ValueId) (value : Word)
  | add (dst lhs rhs : ValueId)
  | fuel
  | trap (code : Nat)
  deriving DecidableEq

inductive Trap where
  | exhausted
  | explicit (code : Nat)

structure State (Context : Type) where
  value : ValueId → Word
  fuel : Nat
  context : Context

inductive Observation (Context : Type) where
  | next (values : List Word) (fuel : Nat) (context : Context)
  | trapped (trap : Trap) (fuel : Nat) (context : Context)

def State.write (s : State Context) (dst : ValueId) (value : Word) : State Context :=
  { s with value := fun id => if id = dst then value else s.value id }

def observe (live : List ValueId) (s : State Context) : List Op → Observation Context
  | [] => .next (live.map s.value) s.fuel s.context
  | .const dst value :: rest => observe live (s.write dst value) rest
  | .add dst lhs rhs :: rest => observe live (s.write dst (s.value lhs + s.value rhs)) rest
  | .fuel :: rest =>
      match s.fuel with
      | 0 => .trapped .exhausted 0 s.context
      | n + 1 => observe live { s with fuel := n } rest
  | .trap code :: _ => .trapped (.explicit code) s.fuel s.context

theorem add_mod (x y : Word) : (x + y).toNat = (x.toNat + y.toNat) % 2^64 :=
  BitVec.toNat_add _ _

private def foldWord (x y : Word) : Word := BitVec.ofNat 64 (x.toNat + y.toNat)

private theorem foldWord_eq_add (x y : Word) : foldWord x y = x + y := by
  apply BitVec.eq_of_toNat_eq
  simp [foldWord, add_mod]

/-- The SSA replacement redirects uses of `dst`. Keep both operand definitions
    in the model whenever they are observable across the region's exit. -/
def folded (live : List ValueId) (lhs rhs dst : ValueId) (x y : Word) : List Op :=
  (if lhs ∈ live then [.const lhs x] else []) ++
  (if rhs ∈ live then [.const rhs y] else []) ++ [.const dst (foldWord x y)]

/-- Check one closed, adjacent slice of a single block, after resolving SSA IDs. -/
def accepts (live : List ValueId) (before after : List Op) : Bool :=
  match before with
  | [.const lhs x, .const rhs y, .add dst a b] =>
      decide (lhs = a ∧ rhs = b ∧ lhs ≠ rhs ∧ dst ≠ lhs ∧ dst ≠ rhs ∧
        after = folded live lhs rhs dst x y)
  | _ => false

private theorem observe_folded (s : State Context) (live : List ValueId)
    (lhs rhs dst : ValueId) (x y : Word) (distinct : lhs ≠ rhs) :
    observe live s [.const lhs x, .const rhs y, .add dst lhs rhs] =
      observe live s (folded live lhs rhs dst x y) := by
  simp only [observe, State.write, distinct, if_false, if_true, ↓reduceIte]
  unfold folded
  rw [foldWord_eq_add]
  by_cases hl : lhs ∈ live <;> by_cases hr : rhs ∈ live <;>
    simp only [hl, hr, if_true, if_false, List.nil_append, List.cons_append, observe, State.write]
  all_goals
    congr 1
    apply List.map_congr_left
    intro id hid
    by_cases hd : id = dst <;> by_cases hleft : id = lhs <;> by_cases hright : id = rhs <;>
      simp_all

/-- All incoming values, fuel amounts, and opaque context states are quantified.
    An exit observer receives only the live SSA values, fuel and context (or a trap). -/
theorem accepts_sound (live : List ValueId) (before after : List Op)
    (accepted : accepts live before after = true) (s : State Context) :
    observe live s before = observe live s after := by
  unfold accepts at accepted
  split at accepted
  next lhs x rhs y dst a b =>
    obtain ⟨rfl, rfl, distinct, _, _, rfl⟩ := of_decide_eq_true accepted
    exact observe_folded s live lhs rhs dst x y distinct
  next => contradiction

theorem continuation_sound (live : List ValueId) (before after : List Op)
    (accepted : accepts live before after = true) (s : State Context)
    (observeExit : Observation Context → Result) :
    observeExit (observe live s before) = observeExit (observe live s after) :=
  congrArg observeExit (accepts_sound live before after accepted s)

private def sum (x y : Word) : List Op := [.const 1 x, .const 2 y, .add 3 1 2]

-- Signed max + 1: sign bit changes. All ones + 1: wraps to zero.
example : accepts [3] (sum 0x7fffffffffffffff 1) [.const 3 0x8000000000000000] = true := by decide
example : accepts [3] (sum 0xffffffffffffffff 1) [.const 3 0] = true := by decide
example : accepts [2, 3] (sum 40 2) [.const 2 2, .const 3 42] = true := by decide

-- Wrong sum, discarded live rhs, and a window crossing a fuel charge or trap.
example : accepts [3] (sum 40 2) [.const 3 43] = false := by decide
example : accepts [2, 3] (sum 40 2) [.const 3 42] = false := by decide
example : accepts [3] [.const 1 40, .fuel, .const 2 2, .add 3 1 2] [.const 3 42] = false := by decide
example : accepts [3] [.const 1 40, .fuel, .const 2 2, .add 3 1 2] [.const 3 42, .fuel] = false := by decide
example : accepts [3] [.const 1 40, .trap 8, .const 2 2, .add 3 1 2] [.const 3 42] = false := by decide

/-- info: 'SirI64Add.add_mod' depends on axioms: [propext] -/
#guard_msgs in
#print axioms add_mod

/-- info: 'SirI64Add.accepts_sound' depends on axioms: [propext, Quot.sound] -/
#guard_msgs in
#print axioms accepts_sound

/-- info: 'SirI64Add.continuation_sound' depends on axioms: [propext, Quot.sound] -/
#guard_msgs in
#print axioms continuation_sound

end SirI64Add
