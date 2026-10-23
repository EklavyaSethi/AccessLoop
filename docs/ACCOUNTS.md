# Accounts, signatures and four-eyes approval

AccessLoop works without accounts for a single person on a laptop. As soon as one account exists, everyone must sign in
and every decision is signed.

```bash
python -m accessloop users add asha --display "Asha Rao" --role reviewer
python -m accessloop users add vikram --display "Vikram S" --role approver
python -m accessloop users list
```

| Role | Can |
|---|---|
| reviewer | load, scan, approve fixes, record manual checks |
| approver | everything a reviewer can, plus confirm fixes when four-eyes approval is on, and switch it off |
| admin | same as approver (account management is done with the command above) |

**What is stored** (`$ACCESSLOOP_HOME/users.json`, default `~/.accessloop`, file mode 600): user name, display name,
role, a scrypt password hash, an Ed25519 public key, and the private key encrypted with a key derived from the password
(scrypt + AES-GCM). Passwords and decrypted keys are never written to disk; the key is decrypted in memory at sign-in.

**Signatures.** Every audit-log entry a signed-in person causes carries their public key and an Ed25519 signature over
the whole entry, including the link to the previous entry. `python -m accessloop audit verify <audit.jsonl>` checks the
hash chain and every signature. Downloaded evidence (`Evidence record` while signed in) is signed too; check it with
`python -m accessloop audit verify-evidence <file.json>`, which also says whether the key belongs to an account on
this computer.

**Four-eyes (maker-checker) approval.** Switch it on in the Review page (or `ACCESSLOOP_FOUR_EYES=1`). An approval
then only records a request; a different person must confirm it before anything is written. The same person can never
do both, and with accounts on the confirmer must be an approver or admin. Both names are recorded on the change.

**Workspaces.** Each account gets its own workspace folder under `.accessloop_workspaces/<user>/`. Folders not used
for `ACCESSLOOP_WORKSPACE_TTL_HOURS` (default 24) are deleted automatically when the app starts.

**Single sign-on.** Company SSO (SAML or OpenID Connect) replaces only the password step: after the identity provider
confirms who the person is, AccessLoop unlocks that person's signing key. That needs a connection to your identity
provider and is not configured in this build.
