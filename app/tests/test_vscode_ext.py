import json
import re
import shutil
import subprocess
import zipfile
from pathlib import Path
from xml.etree import ElementTree

import pytest

import vscode_ext

NS = {"v": "http://schemas.microsoft.com/developer/vsx-schema/2011"}


def test_changed_extension_content_carries_a_new_version():
    # same version, new content => VS Code keeps the old build on an update, exit 0, no word said
    last_version, last_hash = vscode_ext.releases()[-1]
    assert vscode_ext.content_hash() == last_hash, (
        "app/vscode changed: bump version in package.json + append '<version> "
        f"{vscode_ext.content_hash()}' to releases.txt")
    assert vscode_ext.manifest()["version"] == last_version


def test_extension_versions_only_go_up():
    # an older version is refused on install (exit 0 anyway) => user keeps the stale build
    versions = [tuple(int(n) for n in v.split(".")) for v, _ in vscode_ext.releases()]
    assert versions == sorted(set(versions))
    hashes = [h for _, h in vscode_ext.releases()]
    assert len(hashes) == len(set(hashes))


def test_released_extension_lines_never_rewritten():
    # rewriting a past line's hash would let content change under a version already shipped
    shown = subprocess.run(["git", "show", f"HEAD:app/vscode/{vscode_ext.RELEASES.name}"],
                           cwd=vscode_ext.cfg.ROOT, capture_output=True, text=True)
    if shown.returncode:
        return  # not committed yet, or no git (zip install)
    committed = [tuple(l.split()) for l in shown.stdout.splitlines() if l.strip() and not l.startswith("#")]
    assert vscode_ext.releases()[:len(committed)] == committed


def test_vsix_holds_a_manifest_vscode_accepts(tmp_path):
    # malformed vsix => install fails at launch and the window opens without its start page
    path = vscode_ext.build(tmp_path)
    pkg = vscode_ext.manifest()
    assert path.name == f"cez-job-finder.window-{pkg['version']}.vsix"
    with zipfile.ZipFile(path) as z:
        assert sorted(z.namelist()) == ["[Content_Types].xml", "extension.vsixmanifest",
                                        "extension/extension.js", "extension/package.json", "extension/start.js"]
        identity = ElementTree.fromstring(z.read("extension.vsixmanifest")).find("v:Metadata/v:Identity", NS)
        ElementTree.fromstring(z.read("[Content_Types].xml"))
        packed = json.loads(z.read("extension/package.json"))
    assert (identity.get("Publisher"), identity.get("Id"), identity.get("Version")) == (
        pkg["publisher"], pkg["name"], pkg["version"])
    assert packed == pkg
    assert not list(tmp_path.glob("*.tmp"))


def test_extension_never_reads_files_from_the_program_folder():
    # Windows locks app/ files an extension holds open => the program update fails half way
    for name in vscode_ext.SHIPPED:
        if not name.endswith(".js"):
            continue
        source = (vscode_ext.SOURCE / name).read_text(encoding="utf-8")
        local = re.findall(r"require\(\s*['\"](\.[^'\"]*)", source)
        assert all(f"{Path(r).name}.js" in vscode_ext.SHIPPED for r in local), f"{name}: local require not shipped"
        assert "__dirname" not in source and "extensionPath" not in source and "extensionUri" not in source
        # the one file read: the launcher's start-page marker under .data/, never app/
        assert re.findall(r"readFile\w*\(([^,)]+)", source) == (["at(start.MARKER"] if name == "extension.js" else [])
    assert 'MARKER = path.join(".data", ' in (vscode_ext.SOURCE / "start.js").read_text(encoding="utf-8")


def test_extension_probe_runs_only_when_a_measurement_asks():
    # probe quits the window => on a user's computer it would close Job Finder at every start
    source = (vscode_ext.SOURCE / "extension.js").read_text(encoding="utf-8")
    body = source.split("function activate(context) {", 1)[1].split("\n}\n", 1)[0]
    assert body.lstrip().startswith("const out = process.env[PROBE_ENV];")
    assert body.index("if (!out) return;") < body.index("probe(context, out)")
    assert body.count("probe(") == 1


@pytest.mark.skipif(not shutil.which("node"), reason="node not installed")
def test_extension_logic_node_tests_pass():
    # start page logic broken => window opens on the wrong page, or Today rebuilt twice at once
    run = subprocess.run(["node", "--test", *map(str, sorted((vscode_ext.SOURCE / "test").glob("*.test.js")))],
                         capture_output=True, text=True, timeout=120)
    assert run.returncode == 0, run.stdout + run.stderr
    print(next(line for line in run.stdout.splitlines() if line.startswith("ℹ pass")))
