"""Integrity guard for organizer (base-truth) data: SHA-256 verification, read-only loading."""
from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd

from . import config as C


def sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def expected_hashes() -> dict[str, str]:
    out = {}
    for line in C.ORIGINAL_SHA256.read_text().splitlines():
        if line.strip():
            digest, name = line.split(maxsplit=1)
            out[name.strip()] = digest
    return out


def verify_originals() -> dict[str, dict]:
    """Return {file: {expected, actual, ok}}; raises if any organizer file changed."""
    results = {}
    for name, digest in expected_hashes().items():
        actual = sha256(C.ORIGINAL / name)
        results[name] = {"expected": digest, "actual": actual, "ok": actual == digest}
    bad = [k for k, v in results.items() if not v["ok"]]
    if bad:
        raise RuntimeError(f"Organizer data modified or corrupted: {bad}")
    return results


def load_original() -> pd.DataFrame:
    """Load the organizer CSV after hash verification. Returns a fresh DataFrame;
    the file on disk is never written by this project."""
    verify_originals()
    return pd.read_csv(C.ORIGINAL_CSV)
