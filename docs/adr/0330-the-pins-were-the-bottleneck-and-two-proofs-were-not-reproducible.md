# ADR-0330: The pins were the bottleneck, and two proofs were not reproducible from landed code

- Status: accepted
- Date: 2026-09-03

## Context

Between 2026-09-01 and 2026-09-03 the K16 pure-native programme landed work in
nine repositories — kotoba-native, kotoba-kir, kotoba-sema, kotoba-verifier,
kotoba-gmir, kotoba-mir, kotoba-codegen, kotoba-object and aiueos — through
about twenty parallel streams. Every one of those streams was told that the
`amu` pin bump was **batched**, and that it should not open its own. So each
stream bumped `deps.edn` in its own worktree, reported the branch name in its
results, and stopped.

The coordinator measured **24 separate amu worktrees** each carrying an unlanded
pin bump, plus four open pull requests (#753, #757, #758, #759) advancing
`kotoba-native` to four different intermediate SHAs.

That is not a tidiness problem. `amu` is what compiles `.kotoba`, so a pin this
repository does not have is a language feature nobody outside a private worktree
can use. Worse: evidence recorded against a private worktree reads exactly like
evidence about main.

Two QEMU proofs turned out to be in that state.

| marker | against amu main | against the stream's own branch |
|---|---|---|
| `AIUEOS_DOT_F32_QEMU_OK` | `COULD-NOT-RUN compile-failed ... aggregate ABI rejected: call-abi-not-admitted` | reproduces (`agent/k16-native-xsave-amu`) |
| `AIUEOS_DEQUANT_KQUANT_QEMU_OK` | `COULD-NOT-RUN compile-failed` | reproduces (`wt/dequantiq/amu`) |

Neither was hidden. The SMOKE-FRESHNESS stream found the first by building a
receipt that can say `COULD-NOT-RUN` rather than returning the same exit code as
"an arm computed a different number" — under the older harness all three
outcomes were exit 1. The DEQUANT-IQ stream reported the second against itself,
in its own results, unprompted. What was missing was not honesty. It was the
commit.

## Decision

Advance every pinned dependency in `deps.edn` to the current `main` of its own
repository, in one commit, with `deps-lock.edn` regenerated in the same commit —
except `io-ipld`, which is **held with its reason written next to it** (ADR
0331).

## The pin table

Measured 2026-09-03. Every advance is a pure fast-forward: `compare` reported
`behind_by: 0` for all sixteen coordinates before any edit was made.

| coordinate | before | after | commits |
|---|---|---|---|
| `kotoba-native` | `24f43e21` | `452422f5` | 44 |
| `kotoba-sema` | `bb0d47c6` | `1a073853` | 33 (2 behind at merge — see below) |
| `kotoba-verifier` | `7a8cdcd9` | `6c66e8b7` | 12 |
| `kotoba-kir` | `afd117d2` | `b2e5d9c4` | 10 |
| `json` | `840c35b5` | `d5137c7b` | 2 |
| `io-multiformats` | `c5963264` | `561fe7df` | 2 |
| `provider` (`:test`, `:native-conformance`) | `407d5af1` | `f040fc07` | 2 |
| `io-ipld` | `1a2e10cf` | **held** | 28 behind — ADR 0331 |
| `abi` | `32ee84b2` | — | already main |
| `artifact` | `912ca0d6` | — | already main |
| `kotoba-script` | `b72a3338` | — | already main |
| `kotoba-hir` | `ac8e7051` | — | already main |
| `kotoba-object` | `9b53a444` | — | already main |
| `kotoba-wasm` | `cc23ea35` | — | already main |
| `kotoba-component` | `68acc723` | — | already main |
| `kototama-native` (`:test`, `:native-run`, `:native-conformance`) | `ec4d182e` | — | already main |

`kotoba-gmir`, `kotoba-mir` and `kotoba-codegen` are **not** direct dependencies
here — they arrive transitively through `kotoba-native`, and `deps-lock.edn` is
the only file that names them:

| transitive coordinate | before | after | pinned by |
|---|---|---|---|
| `kotoba-gmir` | `fe238166` | `323bfc05` | kotoba-native |
| `kotoba-mir` | `e266a862` | `0bb174c8` | kotoba-native |
| `kotoba-codegen` | `68d409fb` | `3a7d7fc2` | kotoba-native |

Containment was **checked, not assumed**. Each stream's own merge SHA went
through `compare/<merge>...<new pin>` and had to answer `ahead` or `identical`:

- kotoba-native `452422f5` contains `279fbc3` (STOREFIX), `a727bf7` (NIC),
  `da3593b5` (XSAVE: CR4 / `xsetbv`), `1baa450` (SHA-STREAM), `70984ea`,
  `2c4d6c3` and `449792d` (Qwen tranches two and three), `1072816` / `bbeed36` /
  `a63faa6` (DEQUANT-IQ), `91033a9` (BOOT-SCRATCH `lea` + label), `49176e0`
  (SLICE-VALUE), `d710558` (reentry home), `a808906` and `a646b20`
  (`kernel-dot-f32`).
- kotoba-verifier `6c66e8b7` contains `b58c009`, `6a743c3`, `bcea4a1`,
  `a87d2b0`, `7c2bdab`.
- kotoba-kir `b2e5d9c4` contains `268e28b`, `d809f28`, `08bdab8b`, `f2783bf`.
- kotoba-sema `1a073853` contains `e7e13ba`, `fd68866`, `60341cc`, `f932c61`,
  `196d581`, `0ee2dff`, `1afff23`.

## The two conflicts this stream was told to expect

### (a) The held kotoba-kir pin — already adjudicated, and not by this stream

ADR 0314 held `kotoba-kir` at `08bdab8b` because kotoba-kir `984a507` (control
effects bridge through as keywords, so `:abort` reaches the sealed row) and this
repository's `definition_identity_test` (ADR 0300 §4: `:abort` names no
authority, so the bridge refuses) decided the same question in opposite
directions on the same day.

**That decision landed before this stream branched**, in `c3e48d0e`, in
kotoba-kir's favour, with its three reasons recorded in `deps.edn` and its
argument in ADR 0326. This commit does not reopen it. The pin was already at
`afd117d2`; the advance here is the ten commits **after** the adjudication,
whose reason to move is the codebook dequant tables.

### (b) The vendored grammar — resynced, because the sema advance forces it

`kotoba-lang/lang/guest-grammar.edn` is vendored into four repositories and a
resync wave was in flight. Measured 2026-09-03:

| copy | sha256 |
|---|---|
| kotoba-lang `lang/guest-grammar.edn` (authority, as kotoba-sema `1a073853` vendored it) | `3e3f9748` |
| kotoba-sema `resources/kotoba/lang/guest-grammar.edn` at `1a073853` | `3e3f9748` |
| this repository, before the ADJUDICATE commit | `61e0f867` |

`61e0f867` is exactly kotoba-sema's copy at the **old** pin `bb0d47c6`, so the
invariant this repository has been maintaining is "the vendored copy equals the
pinned sema's copy". Advancing the pin therefore moves the grammar by
construction.

There was no "newest SHA before the wave" that could have avoided it. The first
grammar-moving commit in the range is `30106c3` (local-state slice 1), and
everything this programme needs is downstream of it — `fd68866` (a second base
in a second family, the fused dequant call shape) and `e7e13ba` (a literal pool
address is a bounded load's region root, the LOADER stream's compiler gap):

| sema SHA | vendored grammar sha256 |
|---|---|
| `bb0d47c6` (old pin) | `61e0f867` |
| `60341cc5` (local-state slice 1) | `1dfb0bb5` |
| `1afff23e` | `1dfb0bb5` |
| `269432be` | `9f4a779c` |
| `1a073853` (new pin) | `3e3f9748` |

So the resolution is **the matching pair**: the vendored copy here holds, byte
for byte, kotoba-sema's copy at the pinned SHA.

The wave then moved again while this commit was in test. Measured at merge time:

| copy | sha256 |
|---|---|
| this repository | `3e3f9748` |
| kotoba-sema `1a073853` (**pinned here**) | `3e3f9748` |
| kotoba-sema `62ecebf0` (its main) | `67561e57` |
| kotoba-lang `ca2e595a` (its main) | `67561e57` |

`kotoba-sema` is therefore **two commits behind on purpose**, and those two
commits are the resync itself. Taking `62ecebf0` without also taking `67561e57`
would put two grammars on one classpath again, which is the whole content of ADR
0327; taking both would mean chasing a wave that is still moving, inside a
20-minute required-check cycle, on a commit whose subject is pins. The invariant
that matters is not "newest" — it is **the copy here equals the copy in the sema
this file pins**, and that holds. The next resync moves both together, or
neither.

The resync itself, the argument for why a stale vendored copy is worse than a
stale description (this repository's `resources` shadows the dependency's own
copy on the classpath, so `forbidden-heads` unions a stale catalog back in on
the JVM route while nbb follows the pinned frontend), and the test that compares
the two copies where they meet, are ADJUDICATE's — ADR 0327 and
`guest_grammar_vendor_test`. This branch carries that commit rather than
re-deriving it, because the sema advance and the grammar resync are not
separable and doing them twice would have produced two answers to one question.

## What the sema advance cost, and why nothing was weakened to pay it

Three suites went red on the advance, all three because a refusal became **more
specific**, not because anything stopped being refused. Repaired in the carried
commit:

| test | before | after |
|---|---|---|
| `ambient-negative-corpus` `:atom` | `:ambient-forbidden` | `:local-state-atom-position` — `atom` left `:forbidden-heads`, so the head is admitted and the *position* is what refuses. `ref` and `volatile!` added as controls: if either ever reports a position code, the distinction is gone |
| `frontend-extensions` typed sets | `(defn contains? ...)` compiled | `contains?` is now an admitted **and reserved** head; the fixture had been borrowing a name the language now owns, and is renamed `has-item?` |
| `wasm-typed` floating collections | one loose `#"direct floating"` across three types | three cases, each pinning its own `:kotoba.error/code` and its own sentence — the shared prefix disappeared when the messages got *better*, which is precisely the negative test ADR-2608136000 warns about |

## What this repairs, and what it does not

Repaired: the two `COULD-NOT-RUN compile-failed` markers above now have the
compiler they were proved against.

Superseded: pull requests #753, #758 and #759, whose kotoba-native SHAs are all
ancestors of `452422f5`. **Not** superseded: #757 (BOOT-SCRATCH) carries source
changes, not only a pin.

Deliberately out of scope:

- Rebuilding aiueos objects. **No aiueos `.o` is rebuilt by this commit** — the
  change is pins, lock and the tests the pins move.

  This one needs an update, because the answer landed while the commit was in
  test. ATTEST (aiueos ADR-0150) found that rebuilding `sha256.o` at any amu
  newer than `9cf3a0ac` produced an object that traps, and could not name the
  cause; BISECT-SHA256 named it on 2026-09-03 in aiueos ADR-0190. It is
  kotoba-native `da3b56b` ("Optimize x86 direct self reentry"): kotoba-mir's
  `store-at-definition` splices a spill store at a value's definition on the
  reasoning that *a definition dominates every use*, and `:mir/recur` is the one
  edge for which that is false — it redefines the parameter homes and branches
  back **after** the entry plan, so the store runs once and every reload in the
  body reads the entry value forever. `round-block`'s loop counter therefore
  never reached 64; the object did not compute a wrong hash, it spun and died at
  whichever fuel guard was executing when the budget ran out. (ADR-0150 read the
  moving trap address as evidence *against* fuel. It is what a non-terminating
  loop looks like.)

  The fix is kotoba-mir `0bb174c8`, pinned by kotoba-native `d710558`, and
  `d710558` is an ancestor of `452422f5` — so **this pin advance carries the
  repair**, and aiueos ADR-0190 reports the full 93-object rebuild booting at
  it. Landing those objects is still the attestation stream's, not this one's.
- `io-ipld`, held; ADR 0331.

## Consequences

- A stream that lands upstream work and stops at "the amu bump is batched" has
  produced evidence about a worktree, not about this repository. The batch has
  to actually happen; until it does, the correct word for such a marker is
  `COULD-NOT-RUN`, and SMOKE-FRESHNESS's receipt is what makes that word
  available instead of a bare exit 1.
- `aggregate_abi_test` asserts three pins as literals. That is what turns a
  forgotten pin into a red required check rather than a silent divergence, and
  it earned its keep here: a partial local run never touches it; CI does.

---

## Postscript, 2026-09-03: this merge left main red for one commit

The pin/grammar pair this ADR argues for was landed as a pair, and then broken
by the next commit — not by a mistake in either commit, but because two green
branches produce a merged tree no check has seen. Recorded here rather than in
its own ADR because it is this commit's immediate consequence, and repaired in
the commit that follows it.

### What happened

On 2026-09-03, within about twenty minutes:

| | change | grammar copy here | `kotoba-sema` pin | its copy |
|---|---|---|---|---|
| `b8e8cc39` | main before both | `61e0f867` | `196d5817` | `1dfb0bb5` |
| #762 `69e922ee` | pins + resync, as a **pair** | `3e3f9748` | `1a073853` | `3e3f9748` |
| #761 `b822a01b` | resync of the **copy alone** | `67561e57` | `196d5817` | *unchanged* |
| `6c245f69` | main after both | `67561e57` | `1a073853` | `3e3f9748` |

Both pull requests were green. #762's thirteen required checks all passed on
`69e922ee`, and its `deps.edn` said in as many words that the copy and the pin
move together or neither moves. #761 was green on `b8e8cc39`, where
`guest_grammar_vendor_test` **did not yet exist** — that file arrived with #762.

The merge of the two is red, on exactly the test that compares them:

```
FAIL in (every-classpath-copy-of-the-grammar-is-the-same-grammar)
two classpath copies of the grammar disagree; which one the compiler reads is
decided by classpath order
  .../amu/resources/kotoba/lang/guest-grammar.edn                67561e57…
  .../kotoba-sema/1a073853/resources/kotoba/lang/guest-grammar.edn 3e3f9748…
  differing heads: {}

FAIL in (every-classpath-copy-is-the-authority-of-the-resync-wave)
  expected 3e3f9748…   actual 67561e57…
```

`differing heads: {}` is the mercy: the two copies name the same
`:forbidden-heads` and the same `:admitted-builtins`, so no program compiled
differently in the window. The 191-line difference is the documentation
`ba9766b0` added to `:admitted-builtins`. The suite on main was `1303 tests /
9453 assertions / 2 failures`, and both failures are these.

### Why no check could have caught it

Neither branch was wrong. Neither branch was untested. **The combination was
never tested, because GitHub's required checks test a head against its own base,
and the merge produces a tree that no run has seen.** A branch protection rule
that required a rebuild against current main would have caught this one; this
repository does not have one, and adding one is a policy question with its own
costs (every merge serialises behind a 20-minute matrix).

That is the general shape and it is not fixable inside either PR. What *is*
fixable is the specific coupling that made a merge-skew into a red suite: two
files in two repositories that must hold the same bytes, moved by different
commits.

### The decision this adds

**The `kotoba-sema` pin, this repository's vendored `guest-grammar.edn`, and
`guest_grammar_vendor_test/authority-grammar-sha256` are one edit.** Any commit
that moves one of the three moves all three, in the same commit. Repaired here
by taking the current consistent triple:

| | sha256 |
|---|---|
| `resources/kotoba/lang/guest-grammar.edn` | `6e1202fd` |
| `kotoba-sema` `1587f573` (the new pin) | `6e1202fd` |
| `authority-grammar-sha256` | `6e1202fd` |

That digest moved **three times in one day** — `3e3f9748`, `67561e57`,
`6e1202fd` — which is why the rule has to be about the edit rather than about
any particular value.

Note what the test does *not* do, deliberately: it never reads kotoba-lang's
live authority. It compares the copies that are actually on this classpath
against a literal. So a consistent triple stays green while the wave keeps
moving, and goes red only when someone moves one leg of it. That is the correct
sensitivity — a wave in flight is not this repository's emergency, but a
classpath with two answers on it is.

### Consequences of that rule

- A resync PR that touches only `resources/kotoba/lang/guest-grammar.edn` is
  incomplete by construction, and this ADR is what to point at when refusing
  one.
- The window in which main was red is recorded rather than quietly closed:
  `6c245f69`, two failing assertions, no semantic drift, repaired in the next
  commit. Rewriting history to hide it would have cost the next reader the
  measurement that produced this rule.
- The general problem — merged trees no check has seen — is left open here on
  purpose. It is a branch-protection decision, not a grammar one.

