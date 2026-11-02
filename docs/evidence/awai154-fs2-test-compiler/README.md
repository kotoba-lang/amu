# FS2 candidate test compiler staging

This is a test-only way to exercise the changed runtime without rebuilding the
full compiler: copy the exact pinned ARM64 Linux root and replace its embedded
FS2 source with the candidate source. The root's stored source length stays
unchanged; two comments are removed and the unused tail is padded with spaces.
The script checks the base digest, exactly one original embedded source, size,
and uses exclusive creation for the output. It never changes the original.

With base `914b828a24ced086e09929894bb64806dea103bf79766ef144001a076717b1c4`
and candidate `28534da3`, the staged test compiler SHA-256 is
`1fa2c90b875d9366de6250a7ee74b87bf733bc7e5e98c9e8cc06a9dc76faf66b`.
Two independent staging attempts produced identical bytes. The compiler has
**not yet been run**: the disposable VM could not start while another VM was
active. This is not a signed, reproducible self-build, released compiler, Mac
runtime, or positive test result. Do not use it for production or deployment.

Run the `full-mode` fixture only in a separately isolated and resource-bounded
Linux ARM64 test environment, with 0644, 4644, 2644, 1644, symlink and
directory inputs as described in `seed/X86_64-LINUX-ABI`. Compare the existing
negative control from the unmodified compiler, verify its refusal, and record
source and artifact hashes. The test output must not be treated as Mac
qualification or as an exception to the resource governor requirements.
