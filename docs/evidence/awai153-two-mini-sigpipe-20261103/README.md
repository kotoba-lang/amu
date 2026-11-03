# Two-mini native TCP reset observation

On 2026-11-03, task-owned diagnostic Mach-O images on Asher connected to a
one-shot Python TCP reset peer bound to Benjamin's Tailscale address. The peer
observed Asher's expected Tailscale source address. Both Mac minis were reached
via SSH with strict host-key checking. The test used only synthetic bytes and
an ephemeral port; no existing service or model was changed.

The protected direct-syscall image set `SO_NOSIGPIPE` and checked `EPIPE`.
A Python parent on Asher set SIGPIPE to default, waited for its child and
reported native exit 0. A negative-control image skipped the setsockopt
syscall; the same kind of parent reported native return code -13 (SIGPIPE).
One successful run of each was observed; the negative control differs by one
instruction. These are not wire 43–47 tests, inference, credential checks,
independent application identity authentication or evidence of confidential
application transport beyond the use of Tailscale addresses.

Initially copied images had no execute bit; after setting it only on those
files, the positive and negative tests ran. Two earlier direct SSH tests
returned SSH status 0 for the negative image; a controlled self-SIGPIPE
process also returned SSH status 0 in that environment. The child-observing
parent exposed the signal and avoids treating that SSH status as proof of
success. One subsequent protected attempt failed with an SSH banner timeout;
a retry completed with the parent-observed result above. This is an observed
behavior of these specific connections, not a claim about every SSH server.

Cleanup initially failed because SSH banner/proxy connections timed out. A
later connection removed the two exact task-owned images and their unique
directory on Asher, then checked that the directory no longer existed. No
other paths were touched.

The task-specific packager changed only the two IP-address immediate words in
`seed/macos-tcp-nosigpipe-control-packager.kotoba`. Packager source SHA-256
`c709f686bb1b20321ba93ebf7aef71c7dcb4f3aab369942e963e1cdb2c42e9f1`;
protected image `6a7222a5c43b935675dc35b85443da9daab67789ae3b526db255b2dee4d81453`;
negative image `49ff20a3eab88fbe82867df53f372c1b44e57d1c65d153d303a8b4076b28335f`.
The images, build and inline observer are temporary diagnostics and were not
installed as a service. Darwin provider implementation, grants, framing,
timeouts, multi-host fencing and resource governance remain open.
