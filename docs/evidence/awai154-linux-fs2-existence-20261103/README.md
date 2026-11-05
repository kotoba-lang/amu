# Linux FS2 D existence errors: candidate and control

The shared Linux FS2 source now returns `?` for a D request outside the
granted roots or for a failed `openat2` other than ENOENT. A successful open
returns `1`, ENOENT returns `0`, and close failure still refuses. This is a
source candidate with an intentionally changed error contract. Consumers must
check explicitly for `0` when absence authorizes creation. This does not fix
callers which treat every non-`1` response as absence.

On 2026-11-03, an unprivileged user in an isolated local 1 CPU / 2 GiB ARM64
Linux VM ran native `seed/tests/fs2-product.kotoba`. The harness created a
readable file, an absent path, a mode-000 file, a mode-000 parent containing a
file, an in-scope symlink, an escaping symlink and an existing path outside
the granted root. File and parent permissions were restored after the tests.

| Case | Old runtime | Candidate runtime |
| --- | --- | --- |
| Readable file | `1` | `1` |
| Missing path | `0` | `0` |
| Inaccessible file or parent | `0` | `?` |
| In-scope or escaping symlink | `0` | `?` |
| Outside granted root | `0` | `?` |

The same fixture's `exists-errors` mode returned 0 on the candidate and 29 on
the old-runtime negative control. The existing `original-forms` test passed
on both. This confirms the expected Linux ARM64 behavior for these concrete
cases; it does not prove all errors, close-failure handling, concurrent path
races, x86, full compiler self-build, or a real bot turn.

The original compiler and embedded FS2 source are pinned by the staging helper
in `docs/evidence/awai154-fs2-test-compiler/`. For this experiment the helper
removed full comment lines from the throwaway embedded runtime text to fit the
original slot; it did not remove executable forms. Independent staging produced
identical compiler bytes. These are diagnostic artifacts, not a compiler
release or production deployment.

| Artifact | SHA-256 |
| --- | --- |
| Original ARM64 compiler | `914b828a24ced086e09929894bb64806dea103bf79766ef144001a076717b1c4` |
| Candidate FS2 source | `f1010abef3a92a45e4676bc4aa338ca6355d0863ff36713dff121450626e40c4` |
| Staged test compiler | `4a42e07083beb87337ad56dbf9759890e48d4502154e361d54cfee0b71e89da9` |
| Fixture source | `fa05acb0797099fb469578e8e1f5d8c58a994ca530b9098baca079bb25b0e024` |
| Candidate fixture ELF | `465e39ef4c8437403a5fc3ff22609c50b2b866529b07e5a05e92b85f581b185e` |
| Old-runtime fixture ELF | `1fbf63123c04260a350ab865c1802e67885fe0539bde7f785ea0a59d3065417f` |
