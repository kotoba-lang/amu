# Native `.cljk` syntax-sugar corpus

Each `.cljk` file is paired with its canonical `.kotoba` core spelling. Run
each pair through the Native CLI:

```text
amu-native compare-hir <case>.cljk <case>.kotoba --unpinned --source-path <source-root>...
```

The expected result is exit 0 and `semantic equivalent: HIR equal`. The
positive corpus covers `->`, `->>`, `as->`, `cond->`, `cond->>`, `some->`,
and `some->>`. The remaining pairs check that quoted data stays unchanged and
that generated conditional temporary names avoid a source binding collision.

The nine pairs were executed by the G3 Seed-built Native CLI on 2026-10-17.
That confirms Native HIR equality for these cases only. It is not Definition
CID parity, full surface conformance, or evidence that Amu built the compiler.
Add a pair here for every newly admitted `.cljk` sugar form.

`project-import/smoke/main.cljk` threads a value through an imported alias
(`ops/inc`); its `.kotoba` partner spells the resulting call directly. Run the
pair with `project-import` as a source root plus the compiler dependency roots.
This checks that the linker lowers surface calls before rewriting import
aliases. The same CLI also refuses an author-written `__kotoba_` name and an
incomplete `some->`, while allowing that prefix inside quoted data.

`reserved-source.cljk` and `unsupported-empty-some-thread.cljk` are refusal
fixtures (exit 65). `quoted-reserved-data.cljk` is an accepted `check-entry`
fixture (exit 0).
