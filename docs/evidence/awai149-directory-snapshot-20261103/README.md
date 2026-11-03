# Darwin bounded directory snapshot diagnostic

The seed packager emits a fixed-function ARM64 Darwin executable. It accepts no arguments, checks that pre-opened FD 3 is a directory, rewinds it, reads at most 4096 bytes of `getdirentries64` records and requires an immediate EOF. It encodes the `ADI1` header, little-endian byte count and records as lowercase hexadecimal followed by a newline. It does not open paths or spawn processes. Failures before output produce a nonzero exit; the caller must verify the exit status and the entire frame even when stdout exists.

On this Mac, a locally generated and ad-hoc signed diagnostic was tested with a directory containing regular files, a symlink and a subdirectory: decoded names and types matched the actual entries. A previously consumed FD was rewound; an extra argument, a regular-file FD, and a directory exceeding the buffer were refused. An empty directory produced a valid frame. This is a bounded snapshot, not a concurrent-mutation guarantee: a private host must bind FD, exit and output to the intended directory and ensure exclusive control for the entire validation and recovery period. It is not wired into model recovery or deployed.

The independent Murakumo inventory parser prototype validates the resulting frame; see kotoba-lang/murakumo#579. No model weights or existing services were touched.
