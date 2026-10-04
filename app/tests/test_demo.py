from datetime import datetime, timezone

import pytest

import cfg
import store
import today
import demo


def test_demo_fills_every_today_section(tmp_path, monkeypatch):
    # live looks at the window showed an empty Today page => sections went unchecked
    monkeypatch.setattr(cfg, "ROOT", tmp_path)
    demo.fill(tmp_path)
    config = cfg.load(tmp_path / "My Settings" / "Search settings.yml")
    conn = store.connect(tmp_path / demo.DB)
    page = today.build(conn, config, tmp_path / "My Jobs", datetime.now(timezone.utc), ["x"])
    conn.close()
    for heading in ("## Waiting on you", "## Follow up", "## New since last check", "## Not finished"):
        assert heading in page, heading
    assert "example.com" in page and "@" not in page
    demo.fill(tmp_path)  # rerun = same demo, nothing refused


def test_demo_refuses_the_live_install(tmp_path, monkeypatch):
    # demo jobs over the owner's own folder => their real job list + statuses gone
    live = demo.LIVE_INSTALL
    monkeypatch.setattr(cfg, "ROOT", live)
    with pytest.raises(SystemExit, match="live install"):
        demo.main()
    assert not (live / "My Jobs").exists()


def test_demo_refuses_a_folder_holding_real_files(tmp_path):
    # a real resume in My Resume => overwritten by placeholders, unrecoverable
    (tmp_path / "My Resume").mkdir()
    (tmp_path / "My Resume" / "Original resume.pdf").write_bytes(b"%PDF")
    with pytest.raises(SystemExit, match="not written by the demo"):
        demo.fill(tmp_path)
    assert (tmp_path / "My Resume" / "Original resume.pdf").read_bytes() == b"%PDF"
    assert not (tmp_path / "My Settings").exists()
