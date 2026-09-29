import os
import threading
import time

import pytest

import locks


def test_second_holder_waits_for_the_first(tmp_path):
    lock, order = tmp_path / "x.lock", []

    def second():
        with locks.held(lock, "busy", wait_s=5):
            order.append("second")

    with locks.held(lock, "busy"):
        other = threading.Thread(target=second)
        other.start()
        time.sleep(0.5)
        order.append("first")
    other.join()
    assert order == ["first", "second"]
    assert not lock.exists()


def test_still_busy_after_the_wait_says_so_plainly(tmp_path):
    lock = tmp_path / "x.lock"
    with locks.held(lock, "another chat is saving your resume"):
        with pytest.raises(SystemExit, match="another chat is saving your resume"):
            with locks.held(lock, "another chat is saving your resume", wait_s=0.3):
                pass


def test_lock_left_by_a_crashed_run_is_taken_over(tmp_path):
    lock = tmp_path / "x.lock"
    lock.touch()
    old = time.time() - locks.STALE_S - 1
    os.utime(lock, (old, old))
    with locks.held(lock, "busy", wait_s=0):
        pass


def test_atomic_write_replaces_whole_file_and_leaves_no_temp(tmp_path):
    path = tmp_path / "Resume details.yml"
    path.write_text("old", encoding="utf-8")
    locks.write_atomic(path, "new")
    assert path.read_text(encoding="utf-8") == "new"
    assert [p.name for p in tmp_path.iterdir()] == ["Resume details.yml"]
