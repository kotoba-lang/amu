#!/usr/bin/env python3
"""Stage .cljk sources and build the Amu CLI as a GraalVM Native Image."""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
from pathlib import Path


def staged_name(path: Path) -> Path:
    name = path.name
    if name.endswith(".clj.cljk"):
        return path.with_name(name[:-5])
    if name.endswith(".cljc.cljk"):
        return path.with_name(name[:-5])
    if name.endswith(".cljs.cljk"):
        return path.with_name(name[:-5])
    if name.endswith(".cljk"):
        return path.with_name(name[:-5] + ".cljc")
    return path


def ns_form_end(text: str) -> int:
    """Index just past the first top-level (ns ...) form, or -1."""
    start = re.search(r"^\(ns\s", text, re.M)
    if not start:
        return -1
    depth = 0
    i = start.start()
    n = len(text)
    while i < n:
        c = text[i]
        if c == ";":
            while i < n and text[i] != "\n":
                i += 1
            continue
        if c == "\\":
            i += 2
            continue
        if c == '"':
            i += 1
            while i < n and text[i] != '"':
                i += 2 if text[i] == "\\" else 1
        elif c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return -1


def quote_ns_exports(text: str) -> str:
    end = ns_form_end(text)
    if end < 0:
        return text
    head = text[:end]
    head = re.sub(r":kotoba/export\s+(?=[\[#])", ":kotoba/export '", head)
    return head + text[end:]


def stage_directory(source: Path, destination: Path) -> None:
    for current, directories, files in os.walk(source):
        directories[:] = [d for d in directories if d not in {".git", ".cpcache", "target", "node_modules"}]
        relative = Path(current).relative_to(source)
        for filename in files:
            original = Path(current) / filename
            target = staged_name(destination / relative / filename)
            target.parent.mkdir(parents=True, exist_ok=True)
            if original.suffix == ".cljk":
                text = original.read_text()
                # JVM Clojure evaluates bare symbols in ns metadata. Kotoba's
                # export vector is data, so quote it in the staged JVM source.
                # The value may also be a reader conditional that picks the
                # vector per host (`#?(:kotoba [..] :default [..])`). Only inside the
                # `(ns ...)` form: a later `{:kotoba/export [..]}` is a runtime map that a
                # form builder (the frontend's fold probe) constructs and must stay evaluated.
                text = quote_ns_exports(text)
                # A codemod (556605b) spelled the catch-all `js/Error` in shared
                # sources; on the JVM that is Throwable.
                text = re.sub(r"\(catch\s+(?:js/Error|:default)\s", "(catch Throwable ", text)
                if original.name == "edn.cljk" and original.parent.name == "lang":
                    # daf0e7a spelled character literals as one-character
                    # strings; `.charAt` yields a Character on the JVM, so every
                    # `(= ch ";")` in the lexer is false there. Compare strings.
                    text = re.sub(r"\(\.charAt (\^String )?(\w+) (\w+|\(inc \w+\)|0)\)",
                                  lambda m: "(str (.charAt %s%s %s))" % (m.group(1) or "", m.group(2), m.group(3)),
                                  text)
                target.write_text(text)
            else:
                shutil.copy2(original, target)


def run(command: list[str], cwd: Path, env: dict[str, str]) -> None:
    subprocess.run(command, cwd=cwd, env=env, check=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--graal-home", type=Path, default=Path("/opt/homebrew/opt/graalvm"))
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--opt", choices=("b", "0", "1", "2", "3"), default="2")
    # Bootstrap-reference only (docs/selfhost-priority.md rules 2 and 4): build
    # from a checked-out worktree classpath (the selfhost-wall `wall-cp-N.txt`
    # list, colon separated) instead of the pinned deps.edn closure. The
    # `clojure -Spath` entries are appended as a fallback so that anything the
    # list does not name still resolves; earlier entries win.
    parser.add_argument("--classpath-file", type=Path, default=None)
    parser.add_argument("--first-source", type=Path, default=None)
    parser.add_argument("--main", default="kotoba.compiler.cli")
    # Extra native-image arguments (e.g. -H:ConfigurationFileDirectories=<agent output>)
    # and a switch to stop after the AOT step (to run the tracing agent over it).
    parser.add_argument("--native-arg", action="append", default=[])
    parser.add_argument("--no-native", action="store_true")
    args = parser.parse_args()

    root = Path.cwd()
    work = args.work_dir.resolve()
    staged = work / "staged"
    classes = work / "classes"
    if work.exists():
        shutil.rmtree(work)
    staged.mkdir(parents=True)
    classes.mkdir()

    env = dict(os.environ)
    env["JAVA_HOME"] = str(args.graal_home)
    raw_classpath = subprocess.check_output(["clojure", "-Spath"], cwd=root, env=env, text=True).strip()
    staged_entries: list[str] = []
    entries = raw_classpath.split(os.pathsep)
    if args.classpath_file is not None:
        listed = [e for e in args.classpath_file.read_text().strip().split(os.pathsep) if e]
        if args.first_source is not None:
            listed.insert(0, str(args.first_source))
        seen = set()
        merged = []
        for e in listed + entries:
            if e not in seen:
                seen.add(e)
                merged.append(e)
        entries = merged
    for index, item in enumerate(entries):
        source = (root / item).resolve() if not Path(item).is_absolute() else Path(item)
        if source.is_dir():
            destination = staged / f"{index:03d}"
            stage_directory(source, destination)
            staged_entries.append(str(destination))
        else:
            staged_entries.append(str(source))
    classpath = os.pathsep.join(staged_entries)
    (work / "classpath.txt").write_text(classpath)

    java = args.graal_home / "bin" / "java"
    native_image = args.graal_home / "bin" / "native-image"
    run([str(java), f"-Dclojure.compile.path={classes}", "-cp", classpath,
         "clojure.lang.Compile", args.main], root, env)
    if args.no_native:
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    run([str(native_image), f"-O{args.opt}", *args.native_arg, "--initialize-at-build-time",
         "-H:+ReportExceptionStackTraces",
         "-H:IncludeResources=.*\\.(edn|wit|json|txt|clj|cljc)$",
         "-cp", f"{classes}{os.pathsep}{classpath}", "-o", str(args.output.resolve()),
         args.main], root, env)


if __name__ == "__main__":
    main()
