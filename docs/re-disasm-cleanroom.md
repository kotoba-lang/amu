# re-disasm: cleanroom architecture for a Hopper / Ghidra / IDA alternative

Status: design + M0–M2 implemented (`re_disasm/disasm.kotoba`), native
kexe verified under the reviewed C loader with no JVM/GraalVM/Node in the
runtime tree (`re_disasm/build-native.mjs`).
Owner context: mithril.fund mission — give hacking / fraud victims the
ability to identify their attacker. Attacker tooling analysis (droppers,
packed payloads, Mach-O/ELF/PE malware, phishing-kit binaries) is the use
case. This document answers: how do we build a disassembler / decompiler
stack in the Mithril language (Kotoba, compiled by amu selfhost) without
licensing contamination, and what are the milestones.

## 1. Why cleanroom — license analysis

A disassembler/decompiler is the one RE component where license contamination
is a real product risk: we intend to ship this inside mithril.fund (and
possibly commercially), and the incumbent tools have incompatible terms.

| Candidate | License | Verdict for us |
| --- | --- | --- |
| Ghidra | Apache-2.0 (NSA) | Usable with attribution/NOTICE, but copying code or data files into ours imports Apache obligations and blurs "our own". Do not read its source while writing ours. |
| IDA / Hex-Rays | Proprietary, no source | Never. Reverse-engineering *their* binaries is out of scope; no code, no tables, no output copying. |
| Hopper | Proprietary (Hopper SDK is public API only) | Same as IDA. The `HOPPER_LAUNCHER_PATH` integration in `mithril-rea-reverse-engineering` calls it as an external engine — that is a user-supplied dependency, not our code. |
| radare2 / Rizin | LGPL-3 | Linking forces LGPL on the combined work; transcribing tables is a derivative work. Avoid entirely. |
| binutils objdump / gdb | GPL-3 | Same — no linking, no transcription. (amu's own verification notes merely *invoke* objdump; that is a tool use, not incorporation.) |
| Capstone / Keystone | BSD-3 | Linkable, but (a) it is C, not Kotoba — breaks the selfhost goal, (b) tests that assert against Capstone output would make Capstone our de-facto spec. Not used. |
| LLVM MC | Apache-2.0 with LLVM exception | Same selfhost objection as Capstone. |
| Intel SDM / Arm ARM | Specification documents (facts) | **The clean source.** Instruction encodings are facts about the hardware; implementing from the manual is textbook cleanroom and is what every project above also did. |

So: cleanroom from the ISA manuals is not just "nice" — it is the only path
that (1) keeps the code 100% ours (no attribution stack, no copyleft), and
(2) keeps the implementation in Kotoba, which is the actual mission
constraint ("mithril言語 (amu selfhost) ベースで").

### Cleanroom rules we hold

1. **Spec-only transcription.** Encoding fields come from the Arm ARM / Intel
   SDM. When a rule here disagrees with a disassembler, the manual decides.
2. **No output capture.** Test vectors are hand-computed from spec encodings.
   We never run Ghidra/Hopper/IDA/objdump/Capstone and paste results into
   fixtures — that is de-facto copying of their table work.
3. **No foreign source in the tree.** Not even "for reference". If a reader
   consults a competitor implementation, that fact is recorded here and the
   affected code is rewritten from the manual by a different pass.
4. **Two-person discipline where it matters.** For large tables (full x86-64
   decode), the preferred shape is: one pass extracts field descriptions from
   the manual into a neutral table document, a second pass implements from
   that document only. Agent sessions approximate this by "write the table
   document first, then implement from the document, without re-reading the
   manual mid-implementation".
5. **External engines stay external.** The existing `mithril-rea-*` MCP
   (wrapping `rea` CLI → Ghidra/Hopper/IDA) is a front-end to user-licensed
   engines. It is not cleanroom input and must never feed tables or output
   back into re-disasm. When re-disasm matures, it becomes a new `provider`
   alongside them, not a replacement that absorbs them.

## 2. Architecture

Layered, each layer a pure Kotoba module with its own `test-*`:

```
L4  UI / surfaces        mithril surfaces, graph-viewer CFG rendering
L3  Analysis             recursive descent, function boundaries, CFG,
                         strings, imports/exports, xrefs graph
L2  Decoders             aarch64 (M0) -> x86-64 -> (later: wasm, arm32)
L1  Object loaders       Mach-O, ELF, PE -> segments/symbols/entry
L0  Carriers             bytes / vector-i64 / kexe (amu's own format)
```

M0 (`re_disasm/disasm.kotoba`) is the L2 core for A64 plus a loader seed
(`words-from-bytes`) and sweep primitives (L3's first steps). Everything is
pure: words in, i64/string out, no I/O — which is what makes the tests
portable across the JVM oracle, ESM and Wasm probes.

Design decisions taken:

- **Class + extractors, not a full IR.** `insn-class` returns a class id and
  per-class extractors return fields. A structured instruction record can be
  layered later without changing the decode tables.
- **Unknown is honest.** Unmatched encodings return `class-unknown` and text
  `udf #0x…`; we never guess a mnemonic. (An A64 decoder that invents a
  plausible mnemonic is worse than one that says "unknown".)
- **Targets are computed, not stored.** `insn-target` re-derives from the
  word + pc, so xrefs and CFG never carry stale copies.
- **Definition CIDs work in our favour.** amu's per-definition content
  identity means a decode-table change invalidates exactly the dependent
  definitions — the compile cache and the provenance chain track the
  cleanroom revision of every table.

## 3. Milestones

- **M0 (done)** — A64 decode core (22 classes), field extractors, targets,
  one-line text, LE word loader, sweep + xrefs count. Tests green on
  :jvm-kir / :js / :wasm.
- **M1 (done)** — logical/addsub shifted register, load/store register
  offset, LDP/STP (64-bit), instruction record, targets edge vector,
  listing text, shift/extend operand rendering, ADRP+ADD literal-pool
  resolution (`adrp-add-target` / `literal-targets`).
- **M2 (landed)** — object loaders: Mach-O 64 (LC_SEGMENT_64, LC_SYMTAB),
  ELF64 ET_DYN/ET_EXEC, PE32+ — recognize, image base, entry, section and
  symbol rows with string tables; fixtures are hand-built from the format
  layouts in the published format specs. Symmetric with the kexe loader
  work in `tools/kexe_loader*.kotoba`. Still open inside M2: MH_DYLIB and
  ET_EXEC fixtures, PE delay-import/section-reloc tables.
- **M3 (landed)** — analysis: recursive-descent reachability
  (`reachable-vector`), function entries and entry-delimited bounds with
  prologue + tail-call edges, CFG basic blocks + edges, xrefs edge list
  (`xrefs-edges`), strings and undefined-external (import) symbol
  predicates. All pure vector data. Still open inside M3: reachability-
  refined bounds, PE import-table walk, large-blob windowing for strings.
- **M4** — x86-64 decoder (Intel SDM; the two-person table discipline above).
- **M5** — surfaces: listing/CFG in the mithril web UI (graph-viewer), REPL
  CLI (`bin/re-disasm`), and a `provider=amu` lane in the rea MCP so victim
  workflows can run fully self-hosted without Ghidra/Hopper/IDA.
- **M6 (research)** — decompiler (typed KIR as the IR is the long game:
  amu already lowers through typed KIR, so lifting machine code back toward
  KIR is the natural decompile target).

## 4. Relationship to the mission

- Victims bring attacker binaries (droppers, phishing kits, wallet
  stealers). A self-hosted, license-clean disassembler lets the support and
  OSINT bots analyze them without shipping a Ghidra install or depending on
  a proprietary Hopper license per analyst.
- The rea-based MCP remains for users who already own those engines;
  re-disasm is the sovereign path.
- Conclusions about attacker identity remain the owner's (human) domain, per
  the standing mission split: bots produce evidence and analysis artifacts,
  humans make the call.
