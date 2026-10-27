# Historical syntax migration corpus

Each old `.cljk` file is paired with its canonical `.kotoba` core spelling.
Preserve these files and recorded positive/refusal meanings as migration
evidence. They do not require a retained CLJK syntax-sugar surface. The native
product CLI's former `compare-hir` command and CLJK frontend APIs are retired.

The canonical candidate entry is:

```text
amu-native check-entry <absolute-source-root>/<case>.kotoba --unpinned --source-path <absolute-source-root>...
```

The old positive corpus covered `->`, `->>`, `as->`, `cond->`, `cond->>`, `some->`,
and `some->>`. The remaining pairs check that quoted data stays unchanged and
that generated conditional temporary names avoid a source binding collision.

The nine pairs were executed by the G3 Seed-built Native CLI on 2026-10-17.
That confirms Native HIR equality for these cases only. It is not Definition
CID parity, full surface conformance, or evidence that Amu built the compiler.
Canonical positive/refusal coverage still needs native qualification; do not
extend the retired CLJK product interface as an acceptance condition.

`project-import/smoke/main.cljk` threads a value through an imported alias
(`ops/inc`); its `.kotoba` partner spells the resulting call directly. The old
paired run checked lowering before import alias rewriting. Current canonical
alias/refer and reserved-name checks remain; the complete reserved-name guard
now lives independently in `kotoba.compiler.source-names`, preserving quoted
data and case-literal handling. Actual native qualification remains open.

`reserved-source.cljk` and `unsupported-empty-some-thread.cljk` are refusal
fixtures with historical exit 65. `quoted-reserved-data.cljk` had historical
exit 0. Those exits describe the retired entrypoints, not current acceptance
of legacy source. No fixture source or recorded case was deleted, and no
test/build/native execution was performed for this cleanup.
