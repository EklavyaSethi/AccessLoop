"""Append-only, hash-chained audit log (tamper-evident).

Every event is one JSON line. Each line carries the SHA-256 of the previous line's record (`prev`) and its own
hash over a canonical encoding of everything else (`hash`). Changing, deleting, reordering or inserting any line
breaks the chain, and `verify()` says exactly where. The log is never rewritten: Reset is an event, not a wipe.

This proves the log was not edited after the fact by anyone who cannot also recompute every later hash. For
protection against someone who can, publish or sign the head hash (it is printed in every report).
"""
from __future__ import annotations
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

GENESIS = '0' * 64


def _canonical(record: dict[str, Any]) -> bytes:
    body = {k: v for k, v in record.items() if k != 'hash'}
    return json.dumps(body, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode('utf-8')


def signed_bytes(record: dict[str, Any]) -> bytes:
    body = {k: v for k, v in record.items() if k not in ('hash', 'sig')}
    return json.dumps(body, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode('utf-8')


def record_hash(record: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical(record)).hexdigest()


class Ledger:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.records: list[dict[str, Any]] = []
        if self.path.exists():
            ok, message, records = verify(self.path)
            if not ok:
                raise ValueError(f'Audit log failed verification: {message}')
            self.records = records

    @property
    def head(self) -> str:
        return self.records[-1]['hash'] if self.records else GENESIS

    def append(self, event: str, detail: str, signer: Any = None, **fields: Any) -> dict[str, Any]:
        record: dict[str, Any] = {
            'seq': len(self.records) + 1,
            'timestamp_utc': datetime.now(timezone.utc).isoformat(timespec='seconds'),
            'event': event,
            'detail': detail,
            **{k: v for k, v in fields.items() if v is not None},
            'prev': self.head,
        }
        if signer is not None:
            # The reviewer's Ed25519 signature covers everything in the entry, including the link to the previous one.
            record['signer'] = {'user': signer.user, 'display': signer.display, 'public_key': signer.public_key}
            record['sig'] = signer.sign(signed_bytes(record))
        record['hash'] = record_hash(record)
        line = json.dumps(record, ensure_ascii=False, sort_keys=True) + '\n'
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # O_APPEND: the operating system only ever adds to the end of the file.
        fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        try:
            os.write(fd, line.encode('utf-8'))
            os.fsync(fd)
        finally:
            os.close(fd)
        self.records.append(record)
        return record


def verify(path: Path) -> tuple[bool, str, list[dict[str, Any]]]:
    """Re-check every line. Returns (ok, message, records read)."""
    path = Path(path)
    if not path.exists():
        return True, 'No audit log yet.', []
    records: list[dict[str, Any]] = []
    prev = GENESIS
    signed = 0
    with path.open('r', encoding='utf-8') as handle:
        for n, line in enumerate(handle, start=1):
            if not line.strip():
                return False, f'Line {n} is blank (lines were removed or inserted).', records
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                return False, f'Line {n} is not valid JSON (the file was edited).', records
            if rec.get('seq') != n:
                return False, f'Line {n} has sequence number {rec.get("seq")} (lines were removed, added or reordered).', records
            if rec.get('prev') != prev:
                return False, f'Line {n} does not link to line {n - 1} (the chain is broken).', records
            if rec.get('hash') != record_hash(rec):
                return False, f'Line {n} was changed after it was written (its hash does not match).', records
            if rec.get('sig') is not None:
                from .accounts import AccountError, verify_signature
                try:
                    good = verify_signature((rec.get('signer') or {}).get('public_key', ''), signed_bytes(rec), rec['sig'])
                except AccountError:
                    good = None
                if good is False:
                    return False, f'Line {n} carries a reviewer signature that does not match.', records
                if good:
                    signed += 1
            records.append(rec)
            prev = rec['hash']
    extra = f', {signed} signed by reviewers' if signed else ''
    return True, f'All {len(records)} entries verified{extra}; head {prev[:16]}…', records
