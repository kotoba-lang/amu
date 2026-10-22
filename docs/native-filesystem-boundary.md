# Complete canonical filesystem tree and FS2 boundary

Tracking: [JUN-241](https://linear.app/kotobalabs/issue/JUN-241),
[JUN-202](https://linear.app/kotobalabs/issue/JUN-202), Kotoba Labs.

`filesystem_wire.kotoba`, `filesystem.kotoba` and `fs_tree.kotoba` replace the
host filesystem boundary as canonical source candidates. All six fs-tree
public names and one-path arities are present. Nothing here imports Node,
Clojure/JVM, a C loader, a shell or a host filesystem library.

## Complete public surface

| Export | Explicit canonical result and behavior |
| --- | --- |
| exists? | Result<Bool,Document>, nonempty STAT answer; not the historical Node EXISTS regular-file test |
| directory? | Result<Bool,Document>, validated four-field STAT with directory kind one |
| kind | Result<Option<I64>,Document>, absent or no-follow file=0/dir=1/link=2/other=3 |
| entries | Result<List<String>,Document>, every name in provider bytewise order |
| make-directories! | Result<Bool,Document>, missing parents then mkdir, distinguish existing directory from failure |
| remove-tree! | Result<Bool,Document>, inspect root and each child without following links, recurse directories, unlink other kinds, then rmdir |

Host exceptions/nil are replaced by explicit typed Results/Options. Callers
must port those control flows; the old exception-oriented NBB classpath and
package-authoring sources are migration inputs, not integrated native callers.
An empty/NUL-containing path is a typed request error. Canonical confinement
does not inherit the historical existsSync/statSync symlink-follow permission.

Metadata retains the complete unsigned decimal text without parsing unused
size/blocks through a smaller integer helper. The last kind is a bounded
single digit; malformed field count, digit fields, kind or boolean mutation
answer returns an explicit error. Unicode in a malformed protocol header/flag
is inspected as bytes before any substring cut, avoiding an invalid UTF-8
boundary disguised as a missing acknowledgement.

Recursive removal also unlinks a root file/final symlink, implementing the
old documented force-removal intention that the directory-only adapter missed.
An ordinary provider `0` from unlink/rmdir is ignored, preserving force
semantics. Encoding/acknowledgement/response errors propagate; terminal native
authority/shape/byte/cell/provider traps cannot become successful empty trees.
A concurrent directory-to-symlink replacement still depends on the provider's
no-follow/openat2 enforcement; caller-side kind inspection alone is not proof.

## Full framing and provider acknowledgement

The existing raw TAB/LF browse and whole-request `*_SEP` scanning cannot
uniquely represent all valid native string paths/names. The codec uses
`NUL FS2 NUL + A..P + path + NUL + tail` on existing wires 34/35. All sixteen
app-data forms are encoded; browse uses A and an empty tail. Only native-invalid
empty/NUL paths are rejected. TAB, LF, Unicode and former tokens remain data.
Write/append tail text may contain NUL. Per-form bounds stay with the provider.

Every response must begin `NUL FS2 NUL`, even for absence/empty listings.
`answer` checks those bytes before removing the marker. `entries` decodes every
`name NUL ASCII-0/1 NUL` record; it refuses malformed/partial records, empty
names, dot/dot-dot and slash-containing entry names. Names are never trimmed,
normalized, newline-split or restricted to ASCII. The directory flag is
validated, not trusted as no-follow kind. No legacy fallback exists here.

The paired [native #205](https://github.com/kotoba-lang/kotoba-native/pull/205)
contains the actual both-ISA framing parser, full sixteen-form dispatch,
complete browse emission and shared acknowledged response mechanism. Its
framing bytes and result pair consume checked real budgets. Wire 36 stays
the separately owned fs/browse-dir; no capability or grant is manufactured.
See its `docs/linux-static-filesystem-framing.md` for the exact protocol.

## Remaining acceptance

The paired [scope-absence decision](linux-static-native-scope-absence.md) and
native mechanism now cover all sixteen forms, including both rename paths;
their newly compiled matching decision artifact and runtime behavior remain
unqualified. Confinement,
descriptor/race/resource/refusal behavior, whole caller integration and
legacy decoder retirement are open; do not select a forbidden host fallback.
String I/O is not arbitrary raw-byte I/O/digest. That capability/helper work,
the complete native lock writer/replay/farm, source/type/native admission,
Definition CIDs, reviewed owning mains/pins, real compiler/image generations
and complete self-rebuild remain actual dependencies.

Evidence is source AST/API/arity/import/Result/Option/dataflow and source/Git
digest inspection. Five source modules, 42 functions and 15 import calls were
read; all six public names/arities remain and no structural findings were
reported. No filesystem/project/codec/provider implementation, compiler,
generator/assembler, native admission/artifact/runtime or test was executed.
No tests were added. No workflow/protection/service/production route changed.
