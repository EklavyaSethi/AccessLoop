"""Local accounts, reviewer identities and signatures.

* Each account has a password (scrypt hash, standard library) and an Ed25519 key pair. The private key is stored
  encrypted with a key derived from the password (scrypt + AES-GCM) and is only decrypted in memory after login.
* Every decision a signed-in reviewer makes is signed with their key and stored in the hash-chained audit log, so a
  reviewer's approval cannot be forged or edited later without detection (ledger.verify checks the signatures).
* Evidence files can be signed and verified the same way (sign_document / verify_document).
* Roles: reviewer (approves fixes), approver (confirms them when four-eyes approval is on), admin (manages accounts).

Accounts live in $ACCESSLOOP_HOME/users.json (default ~/.accessloop). Accounts are switched on as soon as that file
holds at least one account. Single sign-on (SAML/OIDC) would replace the password step only; see docs/ACCOUNTS.md.
"""
from __future__ import annotations
import base64
import hashlib
import hmac
import json
import os
import re
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

ROLES = ('reviewer', 'approver', 'admin')


class AccountError(ValueError):
    pass


def home() -> Path:
    return Path(os.getenv('ACCESSLOOP_HOME', str(Path.home() / '.accessloop')))


def users_path() -> Path:
    return home() / 'users.json'


def _b64(b: bytes) -> str:
    return base64.b64encode(b).decode()


def _unb64(s: str) -> bytes:
    return base64.b64decode(s.encode())


def _crypto():
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        from cryptography.hazmat.primitives import serialization
        return Ed25519PrivateKey, Ed25519PublicKey, AESGCM, serialization
    except ImportError as error:  # pragma: no cover - listed in requirements.txt
        raise AccountError('Signing needs the "cryptography" package: pip install -r requirements.txt') from error


def _kdf(password: str, salt: bytes, n: int = 2 ** 14) -> bytes:
    return hashlib.scrypt(password.encode('utf-8'), salt=salt, n=n, r=8, p=1, dklen=32)


def _load() -> dict:
    p = users_path()
    if not p.exists():
        return {'users': {}}
    return json.loads(p.read_text(encoding='utf-8'))


def _save(data: dict) -> None:
    p = users_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix('.tmp')
    tmp.write_text(json.dumps(data, indent=1), encoding='utf-8')
    os.chmod(tmp, 0o600)
    os.replace(tmp, p)


def enabled() -> bool:
    return bool(_load().get('users'))


def slug(name: str) -> str:
    s = re.sub(r'[^a-z0-9._-]+', '-', name.strip().lower()).strip('-')
    if not 2 <= len(s) <= 40:
        raise AccountError('User name must be 2 to 40 letters, digits, dots, dashes or underscores.')
    return s


def create_user(username: str, display: str, password: str, role: str = 'reviewer') -> dict:
    Ed25519PrivateKey, _, AESGCM, serialization = _crypto()
    if role not in ROLES:
        raise AccountError(f'Role must be one of {", ".join(ROLES)}.')
    if len(password) < 10:
        raise AccountError('Use a password of at least 10 characters.')
    data = _load()
    user = slug(username)
    if user in data['users']:
        raise AccountError('That user already exists.')
    salt, ksalt, nonce = secrets.token_bytes(16), secrets.token_bytes(16), secrets.token_bytes(12)
    key = Ed25519PrivateKey.generate()
    raw = key.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption())
    pub = key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    enc = AESGCM(_kdf(password, ksalt)).encrypt(nonce, raw, user.encode())
    data['users'][user] = {
        'display': display.strip()[:80] or user, 'role': role, 'created_utc': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'pw_salt': _b64(salt), 'pw_hash': _b64(_kdf(password, salt)), 'key_salt': _b64(ksalt), 'key_nonce': _b64(nonce),
        'private_key_enc': _b64(enc), 'public_key': _b64(pub),
    }
    _save(data)
    return public_info(user)


def public_info(user: str) -> dict:
    u = _load()['users'][user]
    return {'user': user, 'display': u['display'], 'role': u['role'], 'public_key': u['public_key']}


def list_users() -> list[dict]:
    return [public_info(u) for u in sorted(_load()['users'])]


@dataclass
class Identity:
    """A signed-in reviewer. Holds the decrypted private key in memory only."""
    user: str
    display: str
    role: str
    public_key: str
    _key: object = None

    def sign(self, message: bytes) -> str:
        return _b64(self._key.sign(message))   # type: ignore[union-attr]

    @property
    def label(self) -> str:
        return f'{self.display} ({self.user})'


def login(username: str, password: str) -> Identity:
    Ed25519PrivateKey, _, AESGCM, _ser = _crypto()
    data = _load()
    user = slug(username) if username else ''
    u = data['users'].get(user)
    # constant-time comparison; a missing user still costs a hash so timing does not reveal which names exist
    expected = _unb64(u['pw_hash']) if u else b'\0' * 32
    got = _kdf(password, _unb64(u['pw_salt']) if u else b'0' * 16)
    if not u or not hmac.compare_digest(expected, got):
        raise AccountError('Wrong user name or password.')
    raw = AESGCM(_kdf(password, _unb64(u['key_salt']))).decrypt(_unb64(u['key_nonce']), _unb64(u['private_key_enc']),
                                                                 user.encode())
    return Identity(user, u['display'], u['role'], u['public_key'], Ed25519PrivateKey.from_private_bytes(raw))


def verify_signature(public_key_b64: str, message: bytes, signature_b64: str) -> bool:
    _, Ed25519PublicKey, _, _ = _crypto()
    try:
        Ed25519PublicKey.from_public_bytes(_unb64(public_key_b64)).verify(_unb64(signature_b64), message)
        return True
    except Exception:  # noqa: BLE001 - any failure is "not valid"
        return False


def known_key(public_key_b64: str) -> str | None:
    """The account a public key belongs to on this installation, if any."""
    for user, u in _load().get('users', {}).items():
        if u['public_key'] == public_key_b64:
            return user
    return None


# ---- signed documents (evidence JSON) ----------------------------------------------------------------------------
def canonical(doc: dict) -> bytes:
    body = {k: v for k, v in doc.items() if k != 'signature'}
    return json.dumps(body, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode('utf-8')


def sign_document(doc: dict, identity: Identity) -> dict:
    signed = dict(doc)
    signed['signature'] = {'algorithm': 'Ed25519', 'signer': identity.label, 'public_key': identity.public_key,
                           'signed_utc': datetime.now(timezone.utc).isoformat(timespec='seconds')}
    signed['signature']['value'] = identity.sign(canonical({**signed, 'signature': None}))
    return signed


def verify_document(doc: dict) -> tuple[bool, str]:
    sig = doc.get('signature') or {}
    if not sig.get('value'):
        return False, 'The document is not signed.'
    message = canonical({**doc, 'signature': None})
    if not verify_signature(sig.get('public_key', ''), message, sig['value']):
        return False, 'The signature does not match: the document was changed after it was signed.'
    who = known_key(sig.get('public_key', ''))
    trust = f'key belongs to account "{who}" on this computer' if who else 'key is not an account on this computer'
    return True, f'Valid Ed25519 signature by {sig.get("signer")} ({trust}).'
