"""Local test form for plan-29g.7 (127.0.0.1 only; never shipped). Two servers = two sites:
home (127.0.0.1:<p1>) serves the form, other (localhost:<p2>) serves a form in a cross-site frame
(Chromium isolates by site => its own process + target when site isolation is on). Every request
logged (method, path); writes (POST/PUT/...) answered 204 + logged as writes. The page records
whether each input/key/click it saw was trusted (`isTrusted`) and what file it got."""
import http.server
import threading
import time

log, lock = [], threading.Lock()

FORM = """<!doctype html><html><head><meta charset="utf-8"><title>{title}</title><style>
body {{ font: 15px/1.5 -apple-system, system-ui, sans-serif; margin: 0; background: #f6f7f9; color: #1d2433 }}
main {{ max-width: 720px; margin: 24px auto; background: #fff; border: 1px solid #dde1e7; border-radius: 8px; padding: 20px 28px }}
label {{ display: block; margin-top: 12px; font-weight: 600 }} input, select, textarea {{ font: inherit; padding: 6px 8px; width: 100% ; box-sizing: border-box }}
input[type=checkbox], input[type=radio] {{ width: auto }} .inline label {{ display: inline; font-weight: 400; margin-right: 14px }}
#combo-list {{ border: 1px solid #ccd; display: none }} #combo-list div {{ padding: 4px 8px; cursor: pointer }} #combo-list div:hover {{ background: #eef }}
iframe {{ width: 100%; height: 150px; border: 1px dashed #99a; margin-top: 12px }}
button {{ margin-top: 16px; padding: 8px 18px }}
</style></head><body><main>
<h1>Data Analyst - application</h1><p>Test form served on this computer for a Job Finder measurement - not a real job.</p>
<form id="app" method="post" action="/w/submit">
<label for="first_name">First name *</label><input id="first_name" name="first_name">
<label for="email">Email *</label><input id="email" name="email" type="email">
<label for="why">Why this job?</label><textarea id="why" name="why" rows="3"></textarea>
<label for="country">Country</label><select id="country" name="country"><option value="">Select...</option><option>Canada</option><option>Mexico</option><option>United States</option></select>
<label for="combo">Location (City) - type, then pick</label><input id="combo" role="combobox" aria-expanded="false" autocomplete="off">
<div id="combo-list" role="listbox"></div>
<div class="inline"><label><input type="checkbox" id="agree" name="agree"> I agree to the privacy notice</label></div>
<div class="inline">Authorized to work in the US? <label><input type="radio" name="auth" id="auth_yes" value="yes"> Yes</label><label><input type="radio" name="auth" id="auth_no" value="no"> No</label></div>
<label for="resume">Resume/CV</label><input id="resume" name="resume" type="file">
<iframe id="other" src="{other}/frame-form" title="other site form"></iframe>
<button type="button" id="trapbtn">Check (runs a debugger statement)</button>
<button type="submit" id="submit">Submit application</button>
</form></main>
<script>
const seen = {{input: {{}}, keys: [], clicks: [], files: {{}}, combo: null}};
document.addEventListener("input", (e) => {{ seen.input[e.target.id || e.target.name] = e.isTrusted; }}, true);
document.addEventListener("change", (e) => {{ seen.input[(e.target.id || e.target.name) + ":change"] = e.isTrusted; }}, true);
document.addEventListener("keydown", (e) => {{ if (seen.keys.length < 40) seen.keys.push(e.isTrusted); }}, true);
document.addEventListener("mousedown", (e) => {{ seen.clicks.push([e.target.id || e.target.textContent.slice(0, 20), e.isTrusted]); }}, true);
const places = ["Springfield, Illinois, United States", "Springfield, Missouri, United States", "Portland, Oregon, United States"];
const box = document.getElementById("combo"), list = document.getElementById("combo-list");
box.addEventListener("input", () => {{
  const q = box.value.toLowerCase(); list.innerHTML = "";
  for (const p of places.filter((p) => q && p.toLowerCase().startsWith(q))) {{
    const d = document.createElement("div"); d.setAttribute("role", "option"); d.textContent = p;
    d.addEventListener("mousedown", (e) => {{ e.preventDefault(); box.value = p; seen.combo = {{value: p, trusted: e.isTrusted}}; list.style.display = "none"; }});
    list.appendChild(d);
  }}
  list.style.display = list.children.length ? "block" : "none"; box.setAttribute("aria-expanded", String(!!list.children.length));
}});
document.getElementById("resume").addEventListener("change", async (e) => {{
  const f = e.target.files[0]; if (!f) return;
  seen.files.resume = {{name: f.name, size: f.size, head: (await f.text()).slice(0, 40), trusted: e.isTrusted}};
  new Image().src = "/beacon?k=file&name=" + encodeURIComponent(f.name) + "&size=" + f.size;
}});
document.getElementById("trapbtn").addEventListener("click", () => {{
  const t = performance.now(); debugger;
  new Image().src = "/beacon?k=trap-passed&ms=" + Math.round(performance.now() - t);
}});
window.formState = () => ({{first_name: first_name.value, email: email.value, why: why.value, country: country.value,
  combo: box.value, agree: agree.checked, auth: (document.querySelector("input[name=auth]:checked") || {{}}).value || null,
  resume: seen.files.resume || null, seen}});
</script></body></html>"""

FRAME_FORM = """<!doctype html><html><head><meta charset="utf-8"><title>frame form</title></head><body style="font: 14px system-ui">
<label for="frame_name">Name in the other site's frame</label><input id="frame_name">
<label for="frame_resume">Resume in the frame</label><input id="frame_resume" type="file">
<script>
const fseen = {{input: {{}}, file: null}};
document.addEventListener("input", (e) => {{ fseen.input[e.target.id] = e.isTrusted; }}, true);
document.getElementById("frame_resume").addEventListener("change", async (e) => {{
  const f = e.target.files[0]; if (f) fseen.file = {{name: f.name, size: f.size, head: (await f.text()).slice(0, 40)}};
}});
window.frameState = () => ({{name: document.getElementById("frame_name").value, file: fseen.file, seen: fseen}});
</script></body></html>"""


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def note(self, write=False):
        with lock:
            log.append({"t": round(time.time(), 3), "host": self.headers.get("Host"), "method": self.command, "path": self.path,
                        "write": write, "ws": self.headers.get("Upgrade", "").lower() == "websocket",
                        "ua": self.headers.get("User-Agent")})

    def reply(self, body: str, status=200, ctype="text/html; charset=utf-8"):
        data = body.encode()
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.headers.get("Upgrade", "").lower() == "websocket":
            self.note(write=True)
            return self.send_error(400)
        self.note()
        path = self.path.split("?")[0]
        if path == "/form":
            return self.reply(FORM.format(title=self.server.title, other=self.server.other))
        if path == "/frame-form":
            return self.reply(FRAME_FORM.format())
        if path.startswith("/blank"):
            return self.reply(f"<!doctype html><title>{self.server.title} blank</title><p>blank")
        if path == "/beacon":
            return self.reply("", 204, "text/plain")
        self.reply("", 404, "text/plain")

    def write(self):
        self.note(write=True)
        self.reply("", 204, "text/plain")

    do_POST = do_PUT = do_PATCH = do_DELETE = write


def serve(title: str):
    """-> (home, other, close): home = http://127.0.0.1:<p1>, other = http://localhost:<p2>."""
    servers = [http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler) for _ in range(2)]
    home = f"http://127.0.0.1:{servers[0].server_port}"
    other = f"http://localhost:{servers[1].server_port}"
    for s in servers:
        s.title, s.other = title, other
        threading.Thread(target=s.serve_forever, daemon=True).start()

    def close():
        for s in servers:
            s.shutdown()
            s.server_close()
    return home, other, close
