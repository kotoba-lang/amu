"""Publication checks for structured receipts. Diagnostics never include matched text."""

import argparse
import collections
import hashlib
import json
from pathlib import Path
import re
import subprocess


ROOTS = ("docs/evidence", "docs/qualification")
PATHS = (
    (r"/(?:Users|home)/[^/\s]+", "<host-home>"),
    (r"/root(?=/)", "<host-home>"),
    (r"/Volumes/[^/\s]+", "<host-volume>"),
    (r"/(?:private/)?var/folders/[^/\s]+/[^/\s]+(?:/[A-Z](?=/|$))?", "<host-temp>"),
    (r"/(?:(?:private|var)/)?tmp/[^/\s]+", "<host-temp>"),
    (r"/run/user/\d+", "<host-temp>"),
    (r"/(?:__w|builds)/[^/\s]+", "<host-workspace>"),
    (r"[a-z]:[\\/](?:Users|Documents and Settings)[\\/][^\\/\s]+", "<host-home>"),
)
HOST_PATHS = tuple(
    (re.compile(r"(?<![\w./\\-])(?:" + prefix + r""")(?=[/\\\s:;,)\]"']|$)""", re.I), replacement)
    for prefix, replacement in PATHS
)
EMAIL = re.compile(r"(?<![\w.%+-])[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}\b", re.I)
CREDENTIAL = re.compile(
    r"-----BEGIN (?:[A-Z]+ )*PRIVATE KEY-----"
    r"|\b(?:gh[pousr]_[a-zA-Z0-9]{30,}|github_pat_[a-zA-Z0-9_]{40,}|AKIA[A-Z0-9]{16}"
    r"|xox[baprs]-[a-zA-Z0-9-]{16,}|sk-(?:proj-|svcacct-)[a-zA-Z0-9_-]{24,})\b"
    r"|(?i:https?|ssh)://[^/\s\":]+:[^/\s\"@]+@"
    r"|(?i:\b(?:authorization|proxy-authorization)\s*[:=]\s*(?:bearer|basic)\s+[a-z0-9+/_.=-]{8,})"
    r"|(?i:\b(?:api[_-]?key|password|access[_-]?token|client[_-]?secret)\s*[:=]\s*[a-z0-9_=-]{8,})"
)
CREDENTIAL_FIELD = re.compile(r"api[_-]?key|password|access[_-]?token|client[_-]?secret", re.I)
PERSONAL_FIELD = re.compile(r"(?:home|mailing|street)[_-]?address|phone[_-]?number", re.I)
JSON_STRING = re.compile(r'"(?:[^"\\]|\\.)*"')


class ReceiptPrivacyError(ValueError):
    pass


def find_problems(text):
    return {kind for kind, pattern in (("credential", CREDENTIAL), ("email", EMAIL))
            if pattern.search(text)}


def redact_paths(text):
    for pattern, replacement in HOST_PATHS:
        text = pattern.sub(replacement, text)
    return text


def unique_object(fields):
    value = dict(fields)
    if len(value) != len(fields):
        raise ReceiptPrivacyError("duplicate receipt field")
    for key, member in fields:
        if not isinstance(member, str) or not member:
            continue
        if CREDENTIAL_FIELD.fullmatch(key) or (
            key.lower() == "authorization" and re.fullmatch(r"[a-z0-9+/_.=-]{8,}", member, re.I)
        ):
            raise ReceiptPrivacyError("credential")
        if PERSONAL_FIELD.fullmatch(key):
            raise ReceiptPrivacyError("personal information")
    return value


def publication_text(text, structured=True):
    """Validate and redact local path prefixes while retaining receipt formatting."""
    def redact(value):
        problems = find_problems(value)
        if problems:
            raise ReceiptPrivacyError(", ".join(sorted(problems)))
        return redact_paths(value)

    if not structured:
        return redact(text)

    def replace(match):
        original = json.loads(match[0])
        redacted = redact(original)
        return match[0] if original == redacted else json.dumps(redacted)

    json.loads(text, object_pairs_hook=unique_object)
    updated = JSON_STRING.sub(replace, text)
    if updated != text:
        json.loads(updated, object_pairs_hook=unique_object)
    return updated


def publication_bytes(data, structured=True):
    try:
        return publication_text(data.decode("utf-8"), structured).encode("utf-8")
    except (UnicodeError, json.JSONDecodeError) as error:
        raise ReceiptPrivacyError("invalid receipt encoding or JSON") from error


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def audit_tracked():
    raw_paths = subprocess.check_output(["git", "ls-files", "-z", "--", *ROOTS])
    totals = collections.Counter()
    violations = collections.Counter()
    for raw_path in filter(None, raw_paths.split(b"\0")):
        path = Path(raw_path.decode())
        if path.suffix not in {".json", ".receipt"}:
            continue
        totals[path.parts[1]] += 1
        name_problems = find_problems(str(path))
        try:
            if name_problems:
                raise ReceiptPrivacyError(", ".join(sorted(name_problems)) + " in filename")
            if not path.is_file() or path.is_symlink():
                raise ReceiptPrivacyError("receipt must be a regular file")
            data = path.read_bytes()
            if publication_bytes(data, structured=path.suffix == ".json") != data:
                raise ReceiptPrivacyError("host path")
        except ReceiptPrivacyError as error:
            name = "<withheld>" if name_problems else str(path)
            print(f"{name}: {error}")
            violations[str(error)] += 1
    print("Scanned", dict(totals), "findings", dict(violations))
    return bool(violations)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    raise SystemExit(audit_tracked())
