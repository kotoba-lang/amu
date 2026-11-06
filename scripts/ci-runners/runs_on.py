#!/usr/bin/env python3
"""Render and check the variable-driven `runs-on` lines of the amu workflows (ADR 0407).

Every covered job keeps its GitHub-hosted label as the default.  The repo
variable AMU_RUNNER_PROFILE selects self-hosted labels:

  (unset) | hosted   all jobs on GitHub-hosted runners (current behaviour)
  selfhosted-arm     linux-arm64 and macos-arm64 jobs on amu-* runners
  selfhosted         additionally linux-x86_64 jobs on amu-linux-x86_64

A self-hosted label is selected only when the event is not a pull request or
the pull request head is this repository.  Fork pull requests always get the
hosted label.  Jobs that hold secrets are never covered.

  runs_on.py --write   rewrite the covered workflow lines
  runs_on.py --check   fail if any covered line differs from the template
"""
import re, sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / ".github" / "workflows"
# file -> hosted labels that are covered (others stay literal).
COVERED = {
    "selfhost-native.yml": {"ubuntu-24.04-arm", "ubuntu-latest", "${{ matrix.runner }}"},
    "native-definition-graph.yml": {"ubuntu-24.04-arm", "ubuntu-latest", "${{ matrix.runner }}"},
    "native-definition-build.yml": {"${{ matrix.runner }}"},
    "native-definition-cid.yml": {"${{ matrix.runner }}"},
    "native-definition-cids.yml": {"${{ matrix.runner }}"},
    "native-checked-definition.yml": {"${{ matrix.runner }}"},
    "native-checked-source.yml": {"${{ matrix.runner }}"},
    "native-capability-names.yml": {"ubuntu-24.04-arm"},
    "mac-selfhost-aiueos.yml": {"ubuntu-24.04-arm", "ubuntu-latest", "macos-15"},
}
# Never covered, whatever the file: jobs with secrets or write tokens.
# (file, job) that stay hosted: they need Docker-in-job or Chrome, which the runner image does not provide.
HOSTED_ONLY = {("selfhost-native.yml", "qualify-arm64-runtime"), ("selfhost-native.yml", "wasm32-browser-chrome")}
NEVER = {"post-merge-repin.yml"}

ARM_PROFILES = '["selfhosted","selfhosted-arm"]'
GUARD = ("(github.event_name != 'pull_request' || "
         "github.event.pull_request.head.repo.full_name == github.repository)")
ARM = f"contains(fromJSON('{ARM_PROFILES}'), vars.AMU_RUNNER_PROFILE) && {GUARD}"
X86 = f"vars.AMU_RUNNER_PROFILE == 'selfhosted' && {GUARD}"

EXPR = {
    "ubuntu-24.04-arm": "${{ %s && 'amu-linux-arm64' || 'ubuntu-24.04-arm' }}" % ARM,
    "ubuntu-latest": "${{ %s && 'amu-linux-x86_64' || 'ubuntu-latest' }}" % X86,
    "macos-15": "${{ %s && 'amu-macos-arm64' || 'macos-15' }}" % ARM,
    "${{ matrix.runner }}": (
        "${{ matrix.runner == 'ubuntu-24.04-arm' && (%s && 'amu-linux-arm64' || matrix.runner)"
        " || (%s && 'amu-linux-x86_64' || matrix.runner) }}" % (ARM, X86)),
}
LINE = re.compile(r"^(\s*)runs-on: (.*?)(\s+# amu-runner: (.+))?$")


def transform(text, covered, write, fname=""):
    out, problems = [], []
    job = ""
    for n, line in enumerate(text.split("\n"), 1):
        jm = re.match(r"^  ([A-Za-z0-9_-]+):\s*$", line)
        if jm:
            job = jm.group(1)
        m = LINE.match(line)
        if m:
            indent, value, _, tag = m.groups()
            if (fname, job) in HOSTED_ONLY:
                if tag or "amu-" in value:
                    problems.append((n, "hosted-only job carries a self-hosted label"))
                out.append(line)
                continue
            if tag:  # already rendered
                if value != EXPR[tag]:
                    problems.append((n, "differs from template for " + tag))
                elif write:
                    pass
            elif value in covered:
                if write:
                    line = f"{indent}runs-on: {EXPR[value]}  # amu-runner: {value}"
                else:
                    problems.append((n, f"hosted literal {value!r} not rendered"))
            elif any(k in value for k in ("amu-linux", "amu-macos")):
                problems.append((n, "self-hosted label outside the template"))
        out.append(line)
    return "\n".join(out), problems


def main(argv):
    write = "--write" in argv
    bad = 0
    for p in sorted(WORKFLOWS.glob("*.yml")):
        text = p.read_text()
        covered = set() if p.name in NEVER else COVERED.get(p.name, set())
        new, problems = transform(text, covered, write, p.name)
        if p.name in NEVER and re.search(r"amu-(linux|macos)", text):
            problems.append((0, "self-hosted label in a secret-bearing workflow"))
        if write and new != text:
            p.write_text(new)
        for n, why in problems:
            bad += 1
            print(f"{p.name}:{n}: {why}")
    if not write and bad:
        sys.exit(1)
    print("ok" if not bad else f"{bad} problem(s)")


if __name__ == "__main__":
    main(sys.argv[1:])
