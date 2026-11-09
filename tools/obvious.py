#!/usr/bin/env python3
"""Captain Obvious: three checks that do something before announcing they did."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from urllib.parse import urlsplit

DIGEST = re.compile(r"[0-9a-f]{64}\Z")
REPO = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
    manifest = Path(args.manifest).absolute()
    if manifest.is_symlink():
        raise ValueError("manifest must not be a symlink")
    files = {}
    for raw in args.files:
        name, target = safe_relative_file(root, raw)
        if target.resolve() == manifest:
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
    manifest = Path(args.manifest)
    if manifest.is_symlink():
        raise ValueError("manifest must not be a symlink")
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
    seen = set()
    for raw in args.evidence:
        path = Path(raw)
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"not a regular non-symlink file: {raw!r}")
        resolved = path.resolve(strict=True)
        if resolved in seen:
            raise ValueError(f"duplicate evidence file: {raw}")
        seen.add(resolved)
        results.append({"path": str(path), "bytes": path.stat().st_size,
                        "sha256": sha256_file(path)})
    report({
        "check": "evidence-receipt", "status": "RECORDED_NOT_VERIFIED",
        "claim": args.claim, "evidence": sorted(results, key=lambda row: row["path"]),
        "note": "Hashes identify submitted bytes. They do not prove the claim.",
    })


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
    args = parser.parse_args()
    try:
        args.run(args)
    except (ValueError, OSError, json.JSONDecodeError, subprocess.TimeoutExpired) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
