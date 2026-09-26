import subprocess
import sys
from collections.abc import Callable
from email.message import EmailMessage
from xml.sax.saxutils import escape, quoteattr

import autorun
import cfg

PROTOCOL = "jobfinder"
# toast needs registered app id; PowerShell's ships w/ Windows
POWERSHELL_APP_ID = r"{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\WindowsPowerShell\v1.0\powershell.exe"
HINT = f'Open {cfg.NAME} and ask: "any new jobs?"'
MAC_SCRIPT = ["-e", "on run argv", "-e", "display notification (item 2 of argv) with title (item 1 of argv)",
              "-e", "end run"]


def toast_xml(title: str, body: str) -> str:
    # click -> jobfinder: protocol, registered by `jobs.py launch`
    return (f'<toast activationType="protocol" launch={quoteattr(PROTOCOL + ":open")}><visual>'
            f'<binding template="ToastGeneric"><text>{escape(title)}</text><text>{escape(body)}</text>'
            "</binding></visual></toast>")


def windows_script(title: str, body: str) -> str:
    xml = toast_xml(title, body).replace("'", "''")
    return f"""$ErrorActionPreference = 'Stop'
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null
$x = New-Object Windows.Data.Xml.Dom.XmlDocument
$x.LoadXml('{xml}')
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('{POWERSHELL_APP_ID}').Show([Windows.UI.Notifications.ToastNotification]::new($x))
"""


def notify(title: str, body: str) -> None:
    if sys.platform == "win32":
        result = autorun.powershell(windows_script(title, body))
        if result.returncode:
            raise RuntimeError(f"notification failed: {result.stderr.strip()}")
    elif sys.platform == "darwin":
        subprocess.run(["osascript", *MAC_SCRIPT, title, body], check=True, capture_output=True)
    else:
        raise RuntimeError("notifications support Windows + macOS; set up email instead")


def sender() -> Callable[[EmailMessage], None]:
    # preview = top titles (alert.build_message) or what to do next; hint when absent
    return lambda msg: notify(msg["Subject"], getattr(msg, "preview", "") or HINT)
