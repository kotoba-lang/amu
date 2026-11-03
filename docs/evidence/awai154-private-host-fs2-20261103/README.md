# Darwin private host and scoped FS2 diagnostic

The `amu-cli-host` diagnostic service now sends FS2 string and string-to-bytes
calls, and byte calls with a complete FS2 prefix, to the existing scoped FS2
dispatcher. Its separate `AMUH` private host protocol continues to handle the
host CLI's process and file operations. This routing change applies only to
the private host image; it does not add host process authority to an ordinary
program. Invalid frames remain errors or traps in the relevant dispatcher.

On one Mac, a [fixture](git-block-fixture.kotoba) used the private host API to
run `/usr/bin/git -C <task-owned repo> rev-parse --show-toplevel`, then used
unchanged checkpoint block helper functions and framed FS2 to store and
read back an 8,197-byte synthetic CID block. The [receipt](receipt.json) pins
the compiler, packager, source, artifacts and outcomes. The prior host image
ran Git but exited with EHOST at its FS2 request. A diagnostic FS2-only image
and a public `amu-program` image refused the same private host execution
request and created no capture file. Additional host-mode probes covered
string and byte FS2 dispatch and scope escape refusal.

The fixture explicitly supplies both the physical Git path and the virtual
FD3-relative FS2 path for the same task-owned tree. It does not implement a
production path mapping or the checkpoint's legacy `ARG_SEP` spawn protocol.
The private host is privileged and is **not a guest security boundary**; do
not give this service to untrusted bot code. Full Git capture/restore, process
lifetime and descendant control, credentials, GitHub, independent Macs,
resource governance and the release closure remain unqualified. This small
local Git query involved no remote transport and no existing repository.
