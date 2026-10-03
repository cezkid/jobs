"""Job Finder's own VS Code extension (`app/vscode/`) packed as a .vsix, in Python - no npm, no vsce.

    uv run app/vscode_ext.py        # prints the built path

Built into `.data/vscode/<publisher>.<name>-<version>.vsix`, installed from there (never from
`app/`: an update replaces `app/` whole, Windows locks open files). VS Code refuses an older or
equal version w/o `--force` but exits 0 (app/docs/app-window.md #4) => any content change bumps
`version`; `releases.txt` holds one `version hash` line per release, append-only, tested.
"""
import hashlib
import json
import sys
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

import cfg

SOURCE = cfg.APP / "vscode"
OUT = cfg.DATA / "vscode"
RELEASES = SOURCE / "releases.txt"
# packed into the vsix; releases.txt stays out (build bookkeeping, not extension content)
SHIPPED = ("package.json", "extension.js", "start.js")

CONTENT_TYPES = """<?xml version="1.0" encoding="utf-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension=".json" ContentType="application/json"/><Default Extension=".js" ContentType="application/javascript"/><Default Extension=".vsixmanifest" ContentType="text/xml"/></Types>
"""


def manifest() -> dict:
    return json.loads((SOURCE / "package.json").read_text(encoding="utf-8"))


def extension_id() -> str:
    pkg = manifest()
    return f"{pkg['publisher']}.{pkg['name']}"


def content_hash() -> str:
    """Hash of what ships, version field left out => same content, same hash, whatever version."""
    digest = hashlib.sha256()
    for name in SHIPPED:
        data = (SOURCE / name).read_bytes()
        if name == "package.json":
            pkg = json.loads(data)
            pkg.pop("version", None)
            data = json.dumps(pkg, sort_keys=True).encode()
        digest.update(name.encode() + b"\0" + data.replace(b"\r\n", b"\n") + b"\0")
    return digest.hexdigest()[:16]


def releases() -> list[tuple[str, str]]:
    lines = RELEASES.read_text(encoding="utf-8").splitlines()
    return [tuple(line.split()) for line in lines if line.strip() and not line.startswith("#")]


def vsix_manifest(pkg: dict) -> str:
    return f"""<?xml version="1.0" encoding="utf-8"?>
<PackageManifest Version="2.0.0" xmlns="http://schemas.microsoft.com/developer/vsx-schema/2011">
 <Metadata>
  <Identity Language="en-US" Id="{escape(pkg['name'])}" Version="{escape(pkg['version'])}" Publisher="{escape(pkg['publisher'])}"/>
  <DisplayName>{escape(pkg['displayName'])}</DisplayName>
  <Description xml:space="preserve">{escape(pkg['description'])}</Description>
  <Properties><Property Id="Microsoft.VisualStudio.Code.Engine" Value="{escape(pkg['engines']['vscode'])}"/></Properties>
 </Metadata>
 <Installation><InstallationTarget Id="Microsoft.VisualStudio.Code"/></Installation>
 <Dependencies/>
 <Assets><Asset Type="Microsoft.VisualStudio.Code.Manifest" Path="extension/package.json" Addressable="true"/></Assets>
</PackageManifest>
"""


def build(out_dir: Path | None = None, package: dict | None = None) -> Path:
    """Write the vsix; `package` overrides package.json (scratch probe builds only)."""
    pkg = package or manifest()
    out_dir = out_dir or OUT
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{pkg['publisher']}.{pkg['name']}-{pkg['version']}.vsix"
    tmp = path.with_suffix(".tmp")
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("extension.vsixmanifest", vsix_manifest(pkg))
        z.writestr("[Content_Types].xml", CONTENT_TYPES)
        z.writestr("extension/package.json", json.dumps(pkg, indent=2) + "\n")
        for name in SHIPPED:
            if name != "package.json":
                z.write(SOURCE / name, f"extension/{name}")
    tmp.replace(path)
    return path


if __name__ == "__main__":
    sys.exit(print(build()))
