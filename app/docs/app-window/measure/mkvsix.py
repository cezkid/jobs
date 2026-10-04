"""Minimal .vsix: zip w/ extension.vsixmanifest + [Content_Types].xml + extension/..."""
import json, sys, zipfile
out, version, body = sys.argv[1], sys.argv[2], sys.argv[3]
pub, name = "cez-job-finder", "window"
pkg = {"name": name, "publisher": pub, "version": version, "displayName": "CEZ Job Finder window",
       "engines": {"vscode": "^1.90.0"}, "main": "./extension.js", "activationEvents": ["onStartupFinished"]}
manifest = f"""<?xml version="1.0" encoding="utf-8"?>
<PackageManifest Version="2.0.0" xmlns="http://schemas.microsoft.com/developer/vsx-schema/2011">
 <Metadata><Identity Language="en-US" Id="{name}" Version="{version}" Publisher="{pub}"/>
  <DisplayName>CEZ Job Finder window</DisplayName><Description xml:space="preserve">local</Description>
  <Properties><Property Id="Microsoft.VisualStudio.Code.Engine" Value="^1.90.0"/></Properties></Metadata>
 <Installation><InstallationTarget Id="Microsoft.VisualStudio.Code"/></Installation><Dependencies/>
 <Assets><Asset Type="Microsoft.VisualStudio.Code.Manifest" Path="extension/package.json" Addressable="true"/></Assets>
</PackageManifest>"""
types = """<?xml version="1.0" encoding="utf-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension=".json" ContentType="application/json"/><Default Extension=".js" ContentType="application/javascript"/><Default Extension=".vsixmanifest" ContentType="text/xml"/></Types>"""
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    z.writestr("extension.vsixmanifest", manifest)
    z.writestr("[Content_Types].xml", types)
    z.writestr("extension/package.json", json.dumps(pkg, indent=1))
    z.writestr("extension/extension.js", f"// {body}\nexports.activate = () => {{}};\n")
