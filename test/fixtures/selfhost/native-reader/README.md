# Native reader metadata fixtures

`private-constant.cljk` uses host-style `^:private` metadata on a constant
declaration. Its Kotoba meaning is the same as the plain `def` in the paired
`.kotoba` file: privacy is controlled by the explicit namespace export list.
The Native reader preserves this bounded metadata as a private-symbol marker;
constant-name validation removes that marker before entering the language-level
constant table. Other metadata remains tagged for refusal unless a consumer
implements its meaning.

The pair is historical migration evidence. The native product frontend now
accepts canonical `.kotoba` only; the former `compare-hir` entry is retired.
Keep the original metadata case and its recorded meaning for the canonical
reader/refusal corpus. It does not require retaining a CLJK product route.

The canonical candidate entry is:

```text
amu-native check-entry <absolute-source-root>/private-constant.kotoba --unpinned --source-path <absolute-source-root>...
```

The source candidate and this documentation have not been compiled or run as
a qualified Amu selfhost artifact. No current reader/CID/runtime pass is claimed.
