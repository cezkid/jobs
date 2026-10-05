import os
import subprocess
import sys
from collections.abc import Callable
from email.message import EmailMessage
from pathlib import Path
from xml.sax.saxutils import escape, quoteattr

import autorun
import cfg

PROTOCOL = "jobfinder"
# toast needs registered app id; PowerShell's ships w/ Windows
POWERSHELL_APP_ID = r"{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\WindowsPowerShell\v1.0\powershell.exe"
# ours => toast says CEZ Job Finder w/ its icon; registered by the Start Menu shortcut the
# launcher writes (launch.ensure_start_shortcut). No shortcut => PowerShell's, never no toast
APP_ID = "CEZ.JobFinder"
OFF_REASON = "Windows notifications are switched off - turn them on in Settings > System > Notifications"
HINT = f'Open {cfg.NAME} and ask: "any new jobs?"'
# macOS delivers osascript's notification as Script Editor's, so a click opens Script Editor, not
# Job Finder (usernoted log, macOS 26.4.1). An applet posting its own is refused outright; a
# helper app needs a paid Developer ID. Accepted limitation => the pop-up itself says how to open
MAC_SUBTITLE = f"To open: double-click {cfg.NAME} on your Desktop"
MAC_SCRIPT = ["-e", "on run argv", "-e",
              "display notification (item 2 of argv) with title (item 1 of argv) subtitle (item 3 of argv)",
              "-e", "end run"]


def start_shortcut() -> Path:
    programs = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    return programs / "Microsoft" / "Windows" / "Start Menu" / "Programs" / f"{cfg.NAME}.lnk"


def app_id(shortcut: Path | None = None) -> str:
    return APP_ID if (shortcut or start_shortcut()).is_file() else POWERSHELL_APP_ID


def toast_xml(title: str, body: str) -> str:
    # click -> jobfinder: protocol, registered by `jobs.py launch`
    return (f'<toast activationType="protocol" launch={quoteattr(PROTOCOL + ":open")}><visual>'
            f'<binding template="ToastGeneric"><text>{escape(title)}</text><text>{escape(body)}</text>'
            "</binding></visual></toast>")


def windows_script(title: str, body: str, ours: str = POWERSHELL_APP_ID) -> str:
    xml = toast_xml(title, body).replace("'", "''")
    return f"""$ErrorActionPreference = 'Stop'
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null
$x = New-Object Windows.Data.Xml.Dom.XmlDocument
$x.LoadXml('{xml}')
$m = [Windows.UI.Notifications.ToastNotificationManager]
# our id refused (shortcut not picked up yet; unmeasured) => PowerShell's, never no toast
try {{ $n = $m::CreateToastNotifier('{ours}'); $null = $n.Setting }} catch {{ $n = $m::CreateToastNotifier('{POWERSHELL_APP_ID}') }}
# switched off => Show() discards toast w/o error
if ($n.Setting -ne 'Enabled') {{ [Console]::Error.WriteLine("{OFF_REASON} ($($n.Setting))"); exit 3 }}
$n.Show([Windows.UI.Notifications.ToastNotification]::new($x))
"""


def notify(title: str, body: str) -> None:
    if sys.platform == "win32":
        result = autorun.powershell(windows_script(title, body, app_id()))
        if result.returncode:
            raise RuntimeError(f"notification failed: {result.stderr.strip()}")
    elif sys.platform == "darwin":
        subprocess.run(["osascript", *MAC_SCRIPT, title, body, MAC_SUBTITLE], check=True, capture_output=True)
    else:
        raise RuntimeError("notifications support Windows + macOS; set up email instead")


def sender() -> Callable[[EmailMessage], None]:
    # preview = top titles (alert.build_message) or what to do next; hint when absent
    return lambda msg: notify(msg["Subject"], getattr(msg, "preview", "") or HINT)
