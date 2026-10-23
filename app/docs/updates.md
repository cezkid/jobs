# Updates: signed releases, undo, what's new

Design note (plan-gsy). Why: `app/update.py` downloads the whole main zip (~4.5 MB) at every launch. No version check, checksum, signature or undo. No CI: every merge reaches every user at next launch. A wrong updater strands every install, so decide once, in writing.

## Design

1. **Channel** = GitHub Releases on `cezkid/jobs`. Tag `v<app/VERSION>`. Assets: git-archive zip, `SHA256SUMS`, `SHA256SUMS.sig`.
2. **Version** = tracked `app/VERSION`. `release.py` refuses unless tag == VERSION.
3. **Signature** = Ed25519 over `SHA256SUMS`, checked by a vendored pure-Python RFC 8032 module. No new dependency: a broken dependency install would block update and undo.
4. **Keys** = `app/update-keys.txt`: signing key + offline backup key. Rotation = a release signed by the old key ships the new keys file.
5. **Check** = `releases/latest` with ETag / If-None-Match, cached in `.data/`. 304 -> no download. 403 (rate limit, shared campus IPs) or offline -> continue with this version, never an error.
6. **Loop prevention** (below).
7. **Fail-safe**: no keys file -> exactly today's main.zip behaviour. Merging the epic can never strand an install; the release path turns on only once the owner commits the keys.
8. **Undo** = update keeps a copy of every entry it replaces (`app/`, `pyproject.toml`, `uv.lock`, `AGENTS.md`, `CLAUDE.md`, `.claude/`, `.agents/`, `Guides/`, `START HERE.md`) in `.data/previous/`. One step restores them.
9. **What's new** = a "## For users" plain-words section in the release notes, shown once per release.
10. **Installers** (`install-mac.sh`, `install-windows.ps1`) fetch the latest release zip + `SHA256SUMS`, check sha256 (`shasum` / `Get-FileHash`). Signature is checked by the first update run.
11. **Owner process** after keys land: main moves only at releases. Other work merges to a `next` branch, fast-forwarded into main when released, because laggard installs on the old updater still pull main.zip.
12. **Privacy**: the version check at each start sends nothing about the user. It stays inside the existing "Installing and updating" line of the privacy page (test_docs asserts exactly 5 ledger rows). Update `claims.yml` `terms-updates`, terms, privacy page and AGENTS.md table in the same change as the code.

## Loop prevention

- `release.py` refuses a tree whose `app/update.py` lacks the signed-release path.
- `update.py` refuses a release whose zip lacks it.
- First release is tagged at the merge commit.
- Missing `.data/app-version` -> read `app/VERSION`.
- Refuse a downgrade (release version <= installed).
- Start scripts: the .bat is swapped mid-run by update; keep its note.

## Rejected

- **Signed git tags / commits**: need git + gpg on user machines.
- **Pinning a checksum in the repo only**: same trust root as the zip; no protection if the repo is hit.
- **PyPI `cryptography` / PyNaCl for verify**: dependency install can break, which would block update and undo.
- **Minisign / sigstore**: extra binary or network service on each start.
- **Keep main.zip, add a version check only**: every merge still ships unreviewed.
- **Auto-update without undo**: a bad release leaves non-technical users stuck.
- **New privacy ledger row**: nothing about the user is sent; a row would mislead.
