#!/usr/bin/env python3
"""Stage .cljk sources and build the Amu CLI as a GraalVM Native Image."""

from __future__ import annotations

import argparse
import os
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


def stage_directory(source: Path, destination: Path) -> None:
    for current, directories, files in os.walk(source):
        directories[:] = [d for d in directories if d not in {".git", ".cpcache", "target", "node_modules"}]
        relative = Path(current).relative_to(source)
        for filename in files:
            original = Path(current) / filename
            # A `.cljk` is the authority for its `.cljc` twin: staging renames
            # it onto the twin's path, so copying the raw twin as well would
            # race it and can leave the unquoted export vector on the JVM path.
            if original.suffix == ".cljc" and original.with_suffix(".cljk").exists():
                continue
            target = staged_name(destination / relative / filename)
            target.parent.mkdir(parents=True, exist_ok=True)
            if original.suffix == ".cljk":
                text = original.read_text()
                # JVM Clojure evaluates bare symbols in ns metadata. Kotoba's
                # export vector is data, so quote it in the staged JVM source.
                text = text.replace("{:kotoba/export [", "{:kotoba/export '[")
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
    for index, item in enumerate(raw_classpath.split(os.pathsep)):
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
         "clojure.lang.Compile", "kotoba.compiler.cli"], root, env)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    run([str(native_image), f"-O{args.opt}", "--initialize-at-build-time",
         "-H:+ReportExceptionStackTraces",
         "-H:IncludeResources=.*\\.(edn|wit|json|txt|clj|cljc)$",
         "-cp", f"{classes}{os.pathsep}{classpath}", "-o", str(args.output.resolve()),
         "kotoba.compiler.cli"], root, env)


if __name__ == "__main__":
    main()
