import pytest

import cfg


def test_every_profile_loads_with_defaults():
    profiles = sorted(cfg.PROFILES.glob("*.yml"))
    assert profiles
    for path in profiles:
        config = cfg.load(path)
        assert config["api"]["base"] and config["resume"]["master"], path
        assert config["profile"]["name"] and config["passes"], path


def test_missing_config_names_setup(tmp_path):
    with pytest.raises(SystemExit, match="job-setup"):
        cfg.load(tmp_path / "config.yml")


def test_env_var_selects_config(tmp_path, monkeypatch):
    path = tmp_path / "mine.yml"
    path.write_text("profile: {name: Nurse roles}\npasses: []\n", encoding="utf-8")
    monkeypatch.setenv("JOBS_CONFIG", str(path))
    config = cfg.load()
    assert config["profile"]["name"] == "Nurse roles"
    assert config["api"]["page_limit"] == 100


def test_merge_keeps_sibling_keys_and_replaces_lists():
    merged = cfg.merge({"resume": {"model": "opus", "timeout_s": 180}, "l": [1, 2]}, {"resume": {"model": "sonnet"}, "l": [3]})
    assert merged == {"resume": {"model": "sonnet", "timeout_s": 180}, "l": [3]}


def test_q_forbidden_category_allowed(tmp_path):
    path = tmp_path / "c.yml"
    path.write_text("passes: [{tier: a, label: A, params: {category: [healthcare]}}]\n", encoding="utf-8")
    assert cfg.load(path)["passes"][0]["params"]["category"] == ["healthcare"]
    path.write_text("passes: [{tier: a, label: A, params: {q: nurse}}]\n", encoding="utf-8")
    with pytest.raises(ValueError, match="forbidden"):
        cfg.load(path)


def test_mixed_geography_rejected(tmp_path):
    path = tmp_path / "c.yml"
    path.write_text("passes: [{tier: a, label: A, params: {countries: [us], cities: [Springfield]}}]\n", encoding="utf-8")
    with pytest.raises(ValueError, match="OR together"):
        cfg.load(path)
