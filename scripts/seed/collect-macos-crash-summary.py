#!/usr/bin/env python3
"""Save a narrow, path-free summary of a macOS native crash for CI triage."""

import argparse
import json
from pathlib import Path
import time


def summary(path):
    lines = path.read_text(errors="replace").splitlines()
    if len(lines) < 2:
        raise ValueError("incomplete ips report")
    header = json.loads(lines[0])
    body = json.loads("\n".join(lines[1:]))
    threads = body.get("threads", [])
    faulting = body.get("faultingThread")
    frames = []
    if isinstance(faulting, int) and 0 <= faulting < len(threads):
        for frame in threads[faulting].get("frames", [])[:16]:
            frames.append({key: frame[key] for key in
                           ("imageIndex", "imageOffset", "symbol", "symbolLocation")
                           if key in frame})
    images = body.get("usedImages", [])
    frame_images = {}
    for frame in frames:
        index = frame.get("imageIndex")
        if isinstance(index, int) and 0 <= index < len(images):
            item = images[index]
            frame_images[str(index)] = {
                key: item[key] for key in ("arch", "uuid", "base", "size")
                if key in item}
    return {
        "report": path.name,
        "timestamp": header.get("timestamp"),
        "osVersion": body.get("osVersion"),
        "modelCode": body.get("modelCode"),
        "exception": body.get("exception"),
        "termination": body.get("termination"),
        "faultingThread": faulting,
        "frames": frames,
        "frameImages": frame_images,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--process", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report-dir", type=Path,
                        help="single report directory for local diagnosis")
    args = parser.parse_args()
    if not args.process or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789-" for c in args.process):
        parser.error("process must be a lowercase executable basename")
    deadline = time.monotonic() + 12
    candidates = []
    directories = ([args.report_dir] if args.report_dir else [
        Path.home()/"Library/Logs/DiagnosticReports",
        Path("/Library/Logs/DiagnosticReports")])
    while time.monotonic() < deadline:
        candidates = []
        for directory in directories:
            try:
                candidates.extend(directory.glob(args.process+"*.ips"))
            except PermissionError:
                pass
        candidates.sort(key=lambda path: path.stat().st_mtime, reverse=True)
        if candidates:
            break
        time.sleep(1)
    result = {"schema": "amu.macos-native-crash-summary.v1",
              "process": args.process, "reportFound": bool(candidates)}
    if candidates:
        try:
            result["crash"] = summary(candidates[0])
        except (OSError, ValueError, KeyError, TypeError) as error:
            result["parseError"] = type(error).__name__
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, default=str)+"\n")
    print(json.dumps(result, default=str))


if __name__ == "__main__":
    main()
