#!/usr/bin/env python3
"""Captain Obvious: three checks that do something before announcing they did."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile
from urllib.parse import urlsplit

DIGEST = re.compile(r"[0-9a-f]{64}\Z")
REPO = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z")


def sha256_stream(source) -> str:
    digest = hashlib.sha256()
    for chunk in iter(lambda: source.read(1024 * 1024), b""):
        digest.update(chunk)
    return digest.hexdigest()


def sha256_file(path: Path) -> str:
    with path.open("rb") as source:
        return sha256_stream(source)


def reject_symlink_components(path: Path, label: str) -> None:
    """Fail closed if an explicit path component is a symlink."""
    absolute = path.absolute()
    if any(component.is_symlink() for component in (absolute, *absolute.parents)):
        raise ValueError(f"symlinks are not accepted in {label} path: {str(path)!r}")


def canonical_manifest(raw: str) -> Path:
    path = Path(raw).absolute()
    reject_symlink_components(path, "manifest")
    return path.resolve(strict=False)


def report(data: dict) -> None:
    print(json.dumps(data, indent=2, sort_keys=True))


def git(path: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(path), *args], text=True, capture_output=True,
        timeout=15, check=False,
    )
    if proc.returncode:
        raise ValueError(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout.strip()


def parse_origin(origin: str) -> str:
    """Only recognise an explicitly GitHub-hosted origin; never guess."""
    if origin.startswith("git@github.com:"):
        name = origin[len("git@github.com:"):]
    else:
        url = urlsplit(origin)
        if url.scheme not in ("https", "ssh") or url.hostname != "github.com":
            raise ValueError("origin is not an explicitly GitHub-hosted URL")
        name = url.path.lstrip("/")
    if name.endswith(".git"):
        name = name[:-4]
    if not REPO.fullmatch(name):
        raise ValueError("origin is not an owner/repository path")
    return name


def check_repo(args: argparse.Namespace) -> None:
    expected = args.expected.removesuffix(".git")
    if not REPO.fullmatch(expected):
        raise ValueError("--expected must be an OWNER/REPO value")
    path = Path(args.path).resolve(strict=True)
    observed = parse_origin(git(path, "remote", "get-url", "origin"))
    if observed.lower() != expected.lower():
        raise ValueError(f"WRONG REPOSITORY: expected {expected}, observed {observed}")
    dirty = bool(git(path, "status", "--porcelain", "--untracked-files=normal"))
    if args.require_clean and dirty:
        raise ValueError("repository identity is correct but worktree is not clean")
    report({
        "check": "repository-identity", "status": "PASS",
        "expected": expected, "observed": observed, "worktree_dirty": dirty,
        "note": "Remote identity, not authorization to merge or deploy.",
    })


def redact_origin(origin: str) -> str:
    """Never echo credentials embedded in an origin URL into evidence."""
    url = urlsplit(origin)
    if url.scheme and "@" in url.netloc:
        host = url.netloc.rsplit("@", 1)[1]
        return url._replace(netloc=f"***@{host}").geturl()
    return origin


def read_origin(path: Path) -> str | None:
    """Read remote.origin.url from local Git config. No fetch, no network."""
    proc = subprocess.run(
        ["git", "-C", str(path), "config", "--get", "remote.origin.url"],
        text=True, capture_output=True, timeout=15, check=False,
        env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
    )
    if proc.returncode == 1 and not proc.stderr.strip():
        return None
    if proc.returncode:
        raise ValueError(f"git config failed: {proc.stderr.strip()}")
    return proc.stdout.strip() or None


def is_checkout(path: Path) -> bool:
    try:
        metadata = os.lstat(path / ".git")
    except OSError:
        return False
    return stat.S_ISDIR(metadata.st_mode) or stat.S_ISREG(metadata.st_mode)


def find_repo(args: argparse.Namespace) -> int:
    expected = args.expected.removesuffix(".git")
    if not REPO.fullmatch(expected):
        raise ValueError("--expected must be an OWNER/REPO value")
    if not args.search:
        raise ValueError("at least one explicitly authorised --search directory is required")
    if not 0 <= args.max_depth <= 32:
        raise ValueError("--max-depth must be between 0 and 32")
    if args.max_directories < 1:
        raise ValueError("--max-directories must be positive")
    roots = []
    for raw in args.search:
        root = Path(raw).resolve(strict=True)
        if not root.is_dir():
            raise ValueError(f"search root is not a directory: {raw!r}")
        roots.append(root)
    roots = sorted(set(roots))
    repo_name = expected.split("/", 1)[1].lower()
    seen_dirs, seen_checkouts = set(), set()
    checkouts, symlinks, unreadable = [], set(), set()
    depth_limit = truncated = False
    scanned = 0
    for root in roots:
        stack = [(root, 0)]
        while stack and not truncated:
            directory, depth = stack.pop()
            try:
                metadata = os.stat(directory, follow_symlinks=False)
            except OSError:
                unreadable.add(str(directory))
                continue
            identity = (metadata.st_dev, metadata.st_ino)
            if identity in seen_dirs:
                continue
            seen_dirs.add(identity)
            if scanned >= args.max_directories:
                truncated = True
                break
            scanned += 1
            if is_checkout(directory) and identity not in seen_checkouts:
                seen_checkouts.add(identity)
                row = {"path": str(directory), "origin": None, "observed": None,
                       "reason": None}
                try:
                    origin = read_origin(directory)
                    if origin is None:
                        row["reason"] = "no origin remote configured"
                    else:
                        row["origin"] = redact_origin(origin)
                        row["observed"] = parse_origin(origin)
                except (ValueError, OSError, subprocess.TimeoutExpired) as error:
                    row["reason"] = str(error)
                checkouts.append(row)
            try:
                with os.scandir(directory) as entries:
                    children = sorted(entries, key=lambda entry: entry.name, reverse=True)
            except OSError:
                unreadable.add(str(directory))
                continue
            for entry in children:
                if entry.name == ".git":
                    continue
                try:
                    if entry.is_symlink():
                        if entry.is_dir():
                            symlinks.add(entry.path)
                        continue
                    if not entry.is_dir(follow_symlinks=False):
                        continue
                except OSError:
                    unreadable.add(entry.path)
                    continue
                if depth + 1 > args.max_depth:
                    depth_limit = True
                    continue
                stack.append((Path(entry.path), depth + 1))
    checkouts.sort(key=lambda row: row["path"])
    matches, wrong = [], []
    for row in checkouts:
        observed = row["observed"]
        if observed and observed.lower() == expected.lower():
            matches.append(row["path"])
        elif (Path(row["path"]).name.lower() == repo_name or
              (observed and observed.split("/", 1)[1].lower() == repo_name)):
            wrong.append({"path": row["path"], "observed": observed,
                          "origin": row["origin"], "reason": row["reason"]})
    if len(matches) > 1:
        status = "AMBIGUOUS"
    elif matches:
        status = "MATCH"
    elif wrong:
        status = "WRONG_REMOTE"
    else:
        status = "NOT_FOUND"
    hints = {
        "MATCH": "Run the repo check inside the matched checkout before changing anything.",
        "AMBIGUOUS": "Several checkouts match. Ask the operator which path is intended; do not pick one.",
        "WRONG_REMOTE": "A similarly named checkout has a different origin. Do not edit remotes without approval.",
        "NOT_FOUND": (
            "No checkout with this origin exists under the authorised roots. The repository "
            "has most likely not been cloned. Only with explicit operator approval: "
            f"git clone https://github.com/{expected}.git"
        ),
    }
    caveats = []
    if depth_limit:
        caveats.append("depth limit reached; deeper directories were not inspected")
    if truncated:
        caveats.append("directory limit reached; the scan is incomplete")
    if unreadable:
        caveats.append("some directories could not be read")
    report({
        "check": "repository-archaeology", "status": status, "expected": expected,
        "search_roots": [str(root) for root in roots], "max_depth": args.max_depth,
        "matches": matches, "wrong_remotes": wrong, "checkouts": checkouts,
        "checkouts_inspected": len(checkouts), "directories_scanned": scanned,
        "depth_limit_reached": depth_limit, "truncated": truncated,
        "symlinks_skipped": sorted(symlinks), "unreadable": sorted(unreadable),
        "caveats": caveats, "probably_not_cloned": status == "NOT_FOUND",
        "hint": hints[status],
        "note": ("Read-only scan of authorised local directories. No clone, fetch or "
                 "other network access was attempted."),
    })
    return 0 if status == "MATCH" else 1


def safe_relative_file(root: Path, raw: str) -> tuple[str, Path]:
    name = Path(raw)
    if (name.is_absolute() or not name.parts or
            any(part in (".", "..") for part in name.parts)):
        raise ValueError(f"unsafe relative path: {raw!r}")
    for size in range(1, len(name.parts) + 1):
        if root.joinpath(*name.parts[:size]).is_symlink():
            raise ValueError(f"symlinks are not accepted: {raw!r}")
    target = root / name
    if not target.is_file() or not target.resolve().is_relative_to(root):
        raise ValueError(f"missing file or path escapes root: {raw!r}")
    return name.as_posix(), target


def write_pin(args: argparse.Namespace) -> None:
    root = Path(args.root).resolve(strict=True)
    if not root.is_dir():
        raise ValueError("root must be a directory")
    manifest = canonical_manifest(args.manifest)
    files = {}
    for raw in args.files:
        name, target = safe_relative_file(root, raw)
        if target.resolve(strict=True) == manifest or (
            manifest.exists() and os.path.samefile(target, manifest)
        ):
            raise ValueError("cannot pin a manifest to itself")
        if name in files:
            raise ValueError(f"duplicate pin path: {name}")
        files[name] = sha256_file(target)
    record = {
        "schema": 1,
        "algorithm": "sha256",
        "files": [{"path": name, "sha256": files[name]} for name in sorted(files)],
    }
    manifest.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=".obvious-", dir=manifest.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as output:
            json.dump(record, output, indent=2, sort_keys=True)
            output.write("\n")
        os.replace(temp, manifest)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)
    report({"check": "pin-write", "status": "RECORDED", "files": len(files),
            "manifest": str(manifest), "note": "A baseline, not proof of correct behaviour."})


def verify_pin(args: argparse.Namespace) -> None:
    root = Path(args.root).resolve(strict=True)
    manifest = canonical_manifest(args.manifest)
    record = json.loads(manifest.read_text(encoding="utf-8"))
    if not isinstance(record, dict) or set(record) != {"schema", "algorithm", "files"}:
        raise ValueError("unsupported manifest structure")
    if record["schema"] != 1 or record["algorithm"] != "sha256":
        raise ValueError("unsupported pin schema or algorithm")
    pins = record["files"]
    if not isinstance(pins, list) or not pins:
        raise ValueError("pin list must be nonempty")
    seen = set()
    for item in pins:
        if not isinstance(item, dict) or set(item) != {"path", "sha256"}:
            raise ValueError("malformed pin entry")
        raw, expected = item["path"], item["sha256"]
        if not isinstance(raw, str) or not isinstance(expected, str) or not DIGEST.fullmatch(expected):
            raise ValueError("invalid pin path or digest")
        name, target = safe_relative_file(root, raw)
        if name in seen:
            raise ValueError(f"duplicate pin path: {name}")
        seen.add(name)
        actual = sha256_file(target)
        if actual != expected:
            raise ValueError(f"PARITY FAILURE: {name}: expected {expected}, got {actual}")
    report({"check": "pin-verify", "status": "PASS", "files": len(seen),
            "note": "Byte parity only; run simulation tests to establish deterministic ticks."})


def receipt(args: argparse.Namespace) -> None:
    results = []
    seen_paths = set()
    seen_inodes = set()
    for raw in args.evidence:
        path = Path(raw)
        reject_symlink_components(path, "evidence")
        if not path.is_file():
            raise ValueError(f"not a regular non-symlink file: {raw!r}")
        with path.open("rb") as source:
            metadata = os.fstat(source.fileno())
            if not stat.S_ISREG(metadata.st_mode):
                raise ValueError(f"not a regular evidence file: {raw!r}")
            resolved = path.resolve(strict=True)
            identity = (metadata.st_dev, metadata.st_ino)
            if resolved in seen_paths or (
                metadata.st_ino and identity in seen_inodes
            ):
                raise ValueError(f"duplicate evidence file: {raw}")
            seen_paths.add(resolved)
            if metadata.st_ino:
                seen_inodes.add(identity)
            results.append({"path": str(path), "bytes": metadata.st_size,
                            "sha256": sha256_stream(source)})
    report({
        "check": "evidence-receipt", "status": "RECORDED_NOT_VERIFIED",
        "claim": args.claim, "evidence": sorted(results, key=lambda row: row["path"]),
        "note": "Hashes identify submitted bytes. They do not prove the claim.",
    })


def restore_file(args: argparse.Namespace) -> None:
    """Copy fixture bytes with Python file operations; never through a shell alias."""
    expected = args.expected_sha256.lower() if args.expected_sha256 else None
    if expected is not None and not DIGEST.fullmatch(expected):
        raise ValueError("--expected-sha256 must be 64 hexadecimal characters")
    source, dest = Path(args.source), Path(args.dest)
    reject_symlink_components(source, "source")
    reject_symlink_components(dest, "destination")
    if not source.is_file():
        raise ValueError(f"source is not an existing regular file: {args.source!r}")
    parent = dest.absolute().parent
    if not parent.is_dir():
        raise ValueError(f"destination directory does not exist: {str(parent)!r}")
    existed = os.path.lexists(dest)
    if existed and not dest.is_file():
        raise ValueError(f"destination exists and is not a regular file: {args.dest!r}")
    if existed and os.path.samefile(source, dest):
        raise ValueError("source and destination are the same file; refusing self-copy")
    if existed and not args.overwrite:
        raise ValueError("destination exists; pass --overwrite to authorise replacing it")
    previous = sha256_file(dest) if existed else None
    with source.open("rb") as reader:
        metadata = os.fstat(reader.fileno())
        if not stat.S_ISREG(metadata.st_mode):
            raise ValueError(f"source is not a regular file: {args.source!r}")
        fd, temp = tempfile.mkstemp(prefix=".obvious-", dir=parent)
        try:
            digest, size = hashlib.sha256(), 0
            with os.fdopen(fd, "wb") as writer:
                for chunk in iter(lambda: reader.read(1024 * 1024), b""):
                    digest.update(chunk)
                    writer.write(chunk)
                    size += len(chunk)
                writer.flush()
                os.fsync(writer.fileno())
            os.chmod(temp, stat.S_IMODE(metadata.st_mode))
            source_digest = digest.hexdigest()
            if sha256_file(Path(temp)) != source_digest:
                raise ValueError("temporary copy does not match the bytes read from source")
            if expected is not None and source_digest != expected:
                raise ValueError(f"source sha256 {source_digest} does not match expected {expected}")
            if existed:
                os.replace(temp, dest)
            else:
                try:
                    # Create without clobbering: fails if the destination appeared meanwhile.
                    os.link(temp, dest)
                except FileExistsError:
                    raise ValueError("destination appeared during restore; refusing to overwrite") from None
                except OSError:
                    if os.path.lexists(dest):
                        raise ValueError("destination appeared during restore; refusing to overwrite") from None
                    os.replace(temp, dest)
        finally:
            if os.path.lexists(temp):
                os.unlink(temp)
    final = sha256_file(dest)
    if final != source_digest:
        raise ValueError(f"destination sha256 {final} does not match source {source_digest}")
    report({
        "check": "fixture-restore", "status": "RESTORED_AND_VERIFIED",
        "source": str(source), "destination": str(dest), "bytes": size,
        "sha256": final, "expected_sha256": expected, "overwritten": existed,
        "previous_sha256": previous,
        "note": "Copied with Python file operations and re-hashed at the destination. No shell, alias or function was consulted.",
    })


SKILL_NAME = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
FRONT_KEY = re.compile(r"([A-Za-z][A-Za-z0-9_-]*):(?:[ \t]+(.*))?\Z")
INTERPRETER_REF = re.compile(
    r"(?<![\w./-])(?:python3?|bash|sh|zsh|node|ruby|perl)"
    r"(?:[ \t]+-[A-Za-z][^\s]*)*[ \t]+([^\s`\"'|;&<>()]+)")
DOT_SLASH_REF = re.compile(r"(?<![\w./-])(\./[\w./-]+\.(?:py|sh|bash|pl|rb|js))\b")
SCRIPT_SUFFIXES = (".py", ".sh", ".bash", ".pl", ".rb", ".js")
PLACEHOLDER = re.compile(r"\b(?:TODO|TBD|FIXME)\b|lorem ipsum", re.IGNORECASE)
LOADING_NOTE = (
    "DISCOVERABLE_ON_DISK means a SKILL.md with parsable frontmatter exists where Claude Code "
    "looks for project skills. ACTUALLY_LOADED_BY_CLAUDE cannot be observed by a static file "
    "audit: confirm it inside a Claude Code session started at the repository root, for "
    "example by seeing the skill listed or invoking it as /<name>."
)


def parse_frontmatter(text: str) -> tuple[dict, str, list]:
    """Parse a deliberately small subset: single-line `key: value` scalars only."""
    findings = []
    lines = text.lstrip("﻿").splitlines()
    if not lines or lines[0].rstrip() != "---":
        return {}, text, [("MISSING_FRONTMATTER", "SKILL.md must start with a '---' line")]
    try:
        end = next(i for i in range(1, len(lines)) if lines[i].rstrip() == "---")
    except StopIteration:
        return {}, text, [("UNTERMINATED_FRONTMATTER", "no closing '---' line")]
    fields = {}
    for number, line in enumerate(lines[1:end], start=2):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = FRONT_KEY.fullmatch(line.rstrip())
        if not match:
            findings.append(("UNSUPPORTED_FRONTMATTER",
                             f"line {number}: only single-line 'key: value' entries are supported"))
            continue
        key, value = match.group(1), (match.group(2) or "").strip()
        if key in fields:
            findings.append(("DUPLICATE_KEY", f"line {number}: duplicate key {key!r}"))
            continue
        if len(value) >= 2 and value[0] == value[-1] == '"' and "\\" not in value:
            value = value[1:-1]
        elif len(value) >= 2 and value[0] == value[-1] == "'":
            value = value[1:-1].replace("''", "'")
        elif (value[:1] in ('"', "'", "[", "{", "|", ">", "&", "*", "!", "%", "@", "`")
              or ": " in value or " #" in value):
            findings.append(("UNSUPPORTED_FRONTMATTER",
                             f"line {number}: value of {key!r} needs YAML features this auditor does not implement"))
            continue
        fields[key] = value
    return fields, "\n".join(lines[end + 1:]), findings


def strip_code_spans(text: str) -> str:
    return re.sub(r"`[^`\n]*`", " ", text)


def audit_one_skill(root: Path, folder: Path, allow_instruction_only: bool) -> dict:
    name = folder.name
    row = {"directory": name, "path": folder.relative_to(root).as_posix(), "name": None,
           "description": None, "frontmatter_keys": [], "referenced_executables": [],
           "discovery": "NOT_DISCOVERABLE", "actually_loaded_by_claude": None,
           "findings": []}
    errors, warnings = [], []
    def add(code, message, level="error"):
        (errors if level == "error" else warnings).append(
            {"code": code, "level": level, "message": message})
    document = folder / "SKILL.md"
    if folder.is_symlink():
        add("SYMLINKED_SKILL", "skill directory is a symlink; this auditor does not follow it")
    elif not document.exists() and not document.is_symlink():
        add("MISSING_SKILL_MD", "directory has no SKILL.md, so it is not a skill")
    elif document.is_symlink() or not document.is_file():
        add("SYMLINKED_SKILL", "SKILL.md is not a regular non-symlink file")
    else:
        try:
            text = document.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as error:
            text = None
            add("UNREADABLE_SKILL_MD", str(error))
        if text is not None:
            fields, body, parsed = parse_frontmatter(text)
            for code, message in parsed:
                add(code, message)
            row["frontmatter_keys"] = sorted(fields)
            row["name"] = fields.get("name")
            row["description"] = fields.get("description")
            framed = not any(code in ("MISSING_FRONTMATTER", "UNTERMINATED_FRONTMATTER")
                             for code, _ in parsed)
            if framed and row["name"]:
                row["discovery"] = "DISCOVERABLE_ON_DISK"
            if framed:
                audit_fields(row, name, add)
                audit_body(root, folder, body, row, add, allow_instruction_only)
    row["findings"] = sorted(errors + warnings, key=lambda f: (f["code"], f["message"]))
    row["status"] = "FAIL" if errors else "PASS"
    return row


def audit_fields(row: dict, directory: str, add) -> None:
    name, description = row["name"], row["description"]
    if name is None:
        add("MISSING_NAME", "frontmatter has no 'name'")
    elif not SKILL_NAME.fullmatch(name) or len(name) > 64:
        add("INVALID_NAME", f"name {name!r} must be lowercase letters, digits and hyphens (max 64)")
    if name is not None and name != directory:
        add("NAME_MISMATCH", f"name {name!r} does not match directory {directory!r}")
    if description is None:
        add("MISSING_DESCRIPTION", "frontmatter has no 'description'")
    elif not description.strip():
        add("EMPTY_DESCRIPTION", "description is empty")
    elif len(description.split()) < 4:
        add("SHORT_DESCRIPTION", "description is too short to tell Claude when to use the skill")
    elif len(description) > 1024:
        add("DESCRIPTION_TOO_LONG", "description exceeds 1024 characters")


def audit_body(root: Path, folder: Path, body: str, row: dict, add,
               allow_instruction_only: bool) -> None:
    prose = re.sub(r"[#*_>`\-]", " ", body)
    words = len(prose.split())
    steps = len(re.findall(r"(?m)^[ \t]*\d+[.)][ \t]+\S", body))
    if words <= 12 and steps == 0:
        add("PLATITUDE_ONLY", f"the entire body is {words} word(s) of encouragement")
    if steps < 2 or words < 60:
        add("INSUFFICIENT_PROCEDURE",
            f"needs at least 2 numbered steps and 60 words; found {steps} step(s), {words} word(s)")
    if PLACEHOLDER.search(strip_code_spans(body)):
        add("PLACEHOLDER_TEXT", "body contains placeholder text such as TODO, TBD or FIXME")
    references = set(INTERPRETER_REF.findall(body)) | set(DOT_SLASH_REF.findall(body))
    found = set()
    for raw in sorted(references):
        skill_relative = raw.startswith("${CLAUDE_SKILL_DIR}/")
        if not ("/" in raw or raw.endswith(SCRIPT_SUFFIXES)):
            continue  # e.g. `python3 -m unittest` or prose such as "python3 is required"
        if raw.startswith("$") and not skill_relative:
            add("UNRESOLVED_REFERENCE", f"{raw} depends on a variable this auditor does not expand",
                level="warning")
            continue
        if skill_relative:
            candidates = [folder / raw[len("${CLAUDE_SKILL_DIR}/"):]]
        elif raw.startswith(("/", "~")):
            add("EXTERNAL_REFERENCE", f"{raw} is outside the repository and was not checked",
                level="warning")
            continue
        else:
            candidates = [root / raw, folder / raw]
        resolved = None
        for candidate in candidates:
            target = Path(os.path.normpath(candidate))
            if not target.is_relative_to(root):
                add("UNSAFE_REFERENCE", f"{raw} resolves outside the repository")
                resolved = False
                break
            if os.path.lexists(target):
                resolved = target
                break
        if resolved is False:
            continue
        if resolved is None:
            add("MISSING_UTILITY", f"referenced executable {raw} does not exist")
            continue
        relative = resolved.relative_to(root)
        if any((root / Path(*relative.parts[:size])).is_symlink()
               for size in range(1, len(relative.parts) + 1)):
            add("UNSAFE_REFERENCE", f"{raw} passes through a symlink")
            continue
        if not resolved.is_file():
            add("MISSING_UTILITY", f"referenced executable {raw} is not a regular file")
            continue
        if raw.startswith("./") and not os.access(resolved, os.X_OK):
            add("NOT_EXECUTABLE", f"{raw} is invoked directly but is not executable")
        found.add(relative.as_posix())
    row["referenced_executables"] = sorted(found)
    if not found:
        add("NO_LOCAL_EXECUTABLE",
            "no existing local script is referenced; the skill is instructions only",
            level="warning" if allow_instruction_only else "error")


def audit_skills(args: argparse.Namespace) -> int:
    """Static audit only: reads files, never executes Markdown or embedded commands."""
    root = Path(args.root).resolve(strict=True)
    if not root.is_dir():
        raise ValueError("--root must be a directory")
    skills_dir = root / ".claude" / "skills"
    findings, skills = [], []
    if skills_dir.is_symlink() or (root / ".claude").is_symlink():
        findings.append({"code": "SKILLS_DIR_SYMLINK", "level": "error",
                         "message": ".claude/skills is reached through a symlink; not followed"})
    elif not skills_dir.is_dir():
        findings.append({"code": "SKILLS_DIR_MISSING", "level": "error",
                         "message": ".claude/skills does not exist"})
    else:
        for entry in sorted(skills_dir.iterdir(), key=lambda p: p.name):
            if entry.is_dir() or entry.is_symlink():
                skills.append(audit_one_skill(root, entry, args.allow_instruction_only))
            else:
                findings.append({"code": "STRAY_FILE", "level": "warning",
                                 "message": f"{entry.name} is a file, not a skill directory"})
        if not skills:
            findings.append({"code": "NO_SKILLS", "level": "error",
                             "message": ".claude/skills contains no skill directories"})
    failed = any(f["level"] == "error" for f in findings) or any(
        s["status"] == "FAIL" for s in skills)
    report({
        "check": "skill-audit", "status": "FAIL" if failed else "PASS",
        "skills_dir": ".claude/skills", "findings": findings, "skills": skills,
        "summary": {"skills": len(skills),
                    "pass": sum(s["status"] == "PASS" for s in skills),
                    "fail": sum(s["status"] == "FAIL" for s in skills),
                    "discoverable_on_disk": sum(s["discovery"] == "DISCOVERABLE_ON_DISK"
                                                for s in skills)},
        "claude_loading": LOADING_NOTE, "commands_executed": 0,
        "note": "Static analysis of SKILL.md text and referenced paths. Nothing was executed.",
    })
    return 1 if failed else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Captain Obvious performs actual checks.")
    commands = parser.add_subparsers(dest="command", required=True)
    repo = commands.add_parser("repo", help="verify the GitHub origin before editing")
    repo.add_argument("--path", default=".")
    repo.add_argument("--expected", required=True)
    repo.add_argument("--require-clean", action="store_true")
    repo.set_defaults(run=check_repo)
    receipt_cmd = commands.add_parser("receipt", help="hash concrete claim evidence")
    receipt_cmd.add_argument("--claim", required=True)
    receipt_cmd.add_argument("--evidence", nargs="+", required=True)
    receipt_cmd.set_defaults(run=receipt)
    pin = commands.add_parser("pin", help="record or compare byte-level parity")
    pin_commands = pin.add_subparsers(dest="pin_command", required=True)
    write = pin_commands.add_parser("write")
    write.add_argument("--root", default=".")
    write.add_argument("--manifest", required=True)
    write.add_argument("files", nargs="+")
    write.set_defaults(run=write_pin)
    verify = pin_commands.add_parser("verify")
    verify.add_argument("--root", default=".")
    verify.add_argument("--manifest", required=True)
    verify.set_defaults(run=verify_pin)
    find = commands.add_parser(
        "find-repo", help="locate a local checkout of OWNER/REPO without network access")
    find.add_argument("--expected", required=True)
    find.add_argument("--search", action="append",
                      help="explicitly authorised directory to scan (repeatable)")
    find.add_argument("--max-depth", type=int, default=4)
    find.add_argument("--max-directories", type=int, default=50000)
    find.set_defaults(run=find_repo)
    restore = commands.add_parser(
        "restore", help="restore a fixture file with Python and verify its SHA-256")
    restore.add_argument("--source", required=True)
    restore.add_argument("--dest", required=True)
    restore.add_argument("--overwrite", action="store_true",
                         help="explicitly authorise replacing an existing destination")
    restore.add_argument("--expected-sha256")
    restore.set_defaults(run=restore_file)
    audit = commands.add_parser(
        "audit-skills", help="statically audit .claude/skills without executing anything")
    audit.add_argument("--root", default=".")
    audit.add_argument("--allow-instruction-only", action="store_true",
                       help="downgrade 'no local executable referenced' to a warning")
    audit.set_defaults(run=audit_skills)
    args = parser.parse_args()
    try:
        # Commands return 1 for a reported negative outcome (JSON on stdout).
        return args.run(args) or 0
    except (ValueError, OSError, json.JSONDecodeError, subprocess.TimeoutExpired) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
