# Diagnostic private host: isolated Git system configuration

The `amu-cli-host` diagnostic service already launches children with a fixed
minimal environment. It now adds `GIT_CONFIG_NOSYSTEM=1` to every such child,
so Git does not load machine-wide Git configuration. This changes the child
environment for all private-host programs; it may also remove a Git proxy,
trust configuration or other setting that a host expected. The caller must
explicitly provision and qualify any required transport configuration. The
public guest runtime does not gain a process capability from this change.

On one Mac, the pre-change diagnostic host's Git reported a system-level
`credential.helper` key, causing Murakumo's existing configuration guard to
refuse a synthetic local archive. With the new host, a private-host `/usr/bin/env`
fixture printed only PATH, LANG, task-local TMPDIR and
`GIT_CONFIG_NOSYSTEM=1`; a synthetic parent canary, HOME and a conflicting parent
value did not pass through. Packaging the same host-request fixture as an
ordinary FS2 guest trapped without creating its requested capture file. No
credential values were read. On the same Mac,
a Murakumo test-only archive adapter then captured a synthetic signed Git
checkpoint, archived to and independently fetched from a local bare Git remote,
and restored it. A repo-local `credential.helper` key was still rejected by
the actual configuration guard. See Murakumo's associated evidence for that
fixture and its substitutions.

Source SHA-256 `0c6773118258cd9ce356adada6702a6c820c505f85e4b508ff813f19a88d1a86`;
signed candidate packager
`cb1c67683776113eddd62bcc817bc3a52f2f6b3ae9984cd74c74e2f6874edfa8`;
environment fixture source
`f34c05e55fc41e56db81c7581c25f2dff8ea7b7959dbce85a75ee4df248a140c`;
signed fixture image
`c967fdc87606118897fd41020e65f96bbf39d4e58f37ce41f1325977749076bb`.
The observer is test-only and uses task-specific paths.

This setting is not authentication, egress isolation or a complete Git config
security boundary. No GitHub token, network transfer, bot turn, multi-Mac
workload, child process tree qualification, production host or release runtime
was tested. The private host is privileged and must not be exposed to untrusted
guest code.
