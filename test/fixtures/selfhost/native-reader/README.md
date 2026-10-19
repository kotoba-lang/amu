# Native reader metadata fixtures

`private-constant.cljk` uses host-style `^:private` metadata on a constant
declaration. Its Kotoba meaning is the same as the plain `def` in the paired
`.kotoba` file: privacy is controlled by the explicit namespace export list.
The Native reader preserves this bounded metadata as a private-symbol marker;
constant-name validation removes that marker before entering the language-level
constant table. Other metadata remains tagged for refusal unless a consumer
implements its meaning.

Run the pair through:

```text
amu-native compare-hir private-constant.cljk private-constant.kotoba --unpinned --source-path <source-root>...
```
