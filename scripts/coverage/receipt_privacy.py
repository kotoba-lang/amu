"""Publication checks for structured receipts and text evidence."""

import argparse
import collections
import hashlib
import json
from pathlib import Path
import re
import subprocess


ROOTS = ("docs/evidence", "docs/qualification")
CUSTODY = Path("docs/evidence/receipt-path-redactions-20261128.json")
STRUCTURED_SUFFIXES = {".json", ".receipt"}
EVIDENCE_SUFFIXES = STRUCTURED_SUFFIXES | {".txt"}
HOST_PATH_START = r"(?:(?<![\w./\\-])|(?<=file://)|(?<=-[ILF]))"
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
    (re.compile(HOST_PATH_START + r"(?:" + prefix + r""")(?=[/\\\s:;,)\]"']|$)""", re.I), replacement)
    for prefix, replacement in PATHS
)
HOST_PATH_HINTS = ("/users/", "/home/", "/root/", "/volumes/", "var/folders/", "/tmp/",
                   "/run/user/", "/__w/", "/builds/", "/documents and settings/")
EMAIL = re.compile(r"(?<![\w.%+-])[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}\b", re.I)
SECRET_LABEL = (
    r"api[ _-]?key|password|access[ _-]?token|client[ _-]?secret|"
    r"gh_token|github_token|npm_token|aws_secret_access_key|aws_session_token|"
    r"openai_api_key|azure_client_secret|ssh_password"
)
CREDENTIAL = re.compile(
    r"-----BEGIN (?:[A-Z]+ )*PRIVATE KEY-----"
    r"|\b(?:gh[pousr]_[a-zA-Z0-9]{30,}|github_pat_[a-zA-Z0-9_]{40,}|AKIA[A-Z0-9]{16}"
    r"|xox[baprs]-[a-zA-Z0-9-]{16,}|sk-(?:proj-|svcacct-)[a-zA-Z0-9_-]{24,})\b"
    r"|(?i:https?|ssh)://[^/\s\":]+:[^/\s\"@]+@"
    r"|(?i:\b(?:authorization|proxy-authorization)\s*[:=]\s*(?:bearer|basic)\s+[a-z0-9+/_.=-]{8,})"
    r"|(?i:\b(?:" + SECRET_LABEL + r""")\b\s*[:=]\s*["']?[a-z0-9+/_.=-]{8,})"""
)
CREDENTIAL_HINTS = ("private key", "ghp_", "gho_", "ghu_", "ghs_", "ghr_", "github_pat_",
                    "akia", "xox", "sk-", "://", "authorization", "api", "password", "token", "secret")
CREDENTIAL_FIELD = re.compile(r"api[_-]?key|password|access[_-]?token|client[_-]?secret", re.I)
PERSONAL_FIELD = re.compile(r"(?:home|mailing|street)[_-]?address|phone[_-]?number", re.I)
PERSONAL_TEXT = re.compile(
    r"""\b(?:(?:phone(?:[ _-]?number)?|mobile(?:[ _-]?number)?|tel)\s*[:=]\s*["']?\+?[0-9][0-9(). -]{6,}[0-9]"""
    r"""|(?:home|mailing|street)[ _-]?address\s*[:=]\s*["']?\d+[^\S\r\n]+\w)""",
    re.I,
)
JSON_STRING = re.compile(r'"(?:[^"\\]|\\.)*"')


class ReceiptPrivacyError(ValueError):
    pass


def find_problems(text, plaintext=False):
    lower = text.lower()
    problems = set()
    if any(hint in lower for hint in CREDENTIAL_HINTS) and CREDENTIAL.search(text):
        problems.add("credential")
    if "@" in text and EMAIL.search(text):
        problems.add("email")
    if plaintext and any(hint in lower for hint in ("phone", "mobile", "tel", "address")) and PERSONAL_TEXT.search(text):
        problems.add("personal information")
    return problems


def redact_paths(text):
    lower = text.lower().replace("\\", "/")
    if not any(hint in lower for hint in HOST_PATH_HINTS):
        return text
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
        problems = find_problems(value, plaintext=not structured)
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


def tracked_evidence():
    raw_paths = subprocess.check_output(["git", "ls-files", "-z", "--", *ROOTS])
    paths = (Path(raw.decode()) for raw in raw_paths.split(b"\0") if raw)
    return [path for path in paths if path.suffix in EVIDENCE_SUFFIXES]


def audit_tracked(paths):
    totals = {"structured": collections.Counter(), "text": collections.Counter()}
    violations = collections.Counter()
    for path in paths:
        category = "text" if path.suffix == ".txt" else "structured"
        totals[category][path.parts[1]] += 1
        name_problems = find_problems(str(path), plaintext=True)
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
    for category, counts in totals.items():
        print(f"Scanned {category}", dict(counts))
    print("Findings", dict(violations))
    return bool(violations)


def custody_pin(data):
    return {"sha256": sha256(data), "bytes": len(data)}


def verify_custody(paths, originals):
    try:
        manifest = json.loads(CUSTODY.read_bytes())
        revision = manifest["originalGitRevision"]
        copies = manifest["copies"]
        if (manifest["schema"] != "amu.evidence-receipt-path-redactions.v1"
                or not re.fullmatch("[0-9a-f]{40}", revision) or not copies):
            raise ValueError
        tracked = set(paths)
        for name, receipt in copies.items():
            path = Path(name)
            if path not in tracked or name != path.as_posix():
                raise ValueError
            if custody_pin(path.read_bytes()) != receipt["published"]:
                raise ReceiptPrivacyError("published custody pin differs")
            if originals:
                original = subprocess.check_output(
                    ["git", "show", f"{revision}:{name}"], stderr=subprocess.DEVNULL
                )
                if custody_pin(original) != receipt["original"]:
                    raise ReceiptPrivacyError("original custody pin differs")
    except ReceiptPrivacyError as error:
        print(error)
        return True
    except (KeyError, ValueError, TypeError, AttributeError, OSError, subprocess.CalledProcessError):
        print("Cannot verify receipt custody manifest or original revision")
        return True
    print(f"Verified {len(copies)} published custody pins" + (" and their originals" if originals else ""))
    return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-originals", action="store_true",
                        help="also compare original pins against the recorded local Git revision")
    args = parser.parse_args()
    paths = tracked_evidence()
    raise SystemExit(audit_tracked(paths) or verify_custody(paths, args.verify_originals))
