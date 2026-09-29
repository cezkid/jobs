"""Two chats at once share one set of files. Two helpers keep them from tripping on each other.

`held` - one short-lived lock file per shared thing, made create-exclusive: works the same on Mac
and Windows, no fcntl. Held only while a command writes, so a second chat waits a moment and goes
on; it never sees the lock unless the first one hangs. A lock older than STALE_S is a crashed or
slept-through run, taken over rather than blocking the user for good.

`write_atomic` - whole file or old file, never half: a chat reading the resume while another
rewrites it gets one of the two, not an empty page.
"""
import contextlib
import os
import time
from pathlib import Path

STALE_S = 300
POLL_S = 0.2


@contextlib.contextmanager
def held(path: Path, busy: str, wait_s: float = 60):
    path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + wait_s
    while True:
        try:
            os.close(os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
            break
        except FileExistsError:
            try:
                if time.time() - path.stat().st_mtime > STALE_S:
                    path.unlink(missing_ok=True)
                    continue
            except FileNotFoundError:
                continue
            if time.monotonic() > deadline:
                raise SystemExit(busy) from None
            time.sleep(POLL_S)
    try:
        yield
    finally:
        path.unlink(missing_ok=True)


def write_atomic(path: Path, text: str) -> None:
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(text, encoding="utf-8")
    # Windows refuses the swap while another process has the file open to read => brief retry
    for _ in range(20):
        try:
            os.replace(tmp, path)
            return
        except PermissionError:
            time.sleep(0.1)
    os.replace(tmp, path)
