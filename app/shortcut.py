"""Windows shortcut (.lnk) written as bytes: target, icon, app id. No compiled code.

Why: the toast names + pictures the app whose id it carries. That id lives on a Start Menu
shortcut (System.AppUserModel.ID); WScript.Shell can't set it, IPropertyStore needs Add-Type C#
(unsigned temp DLL: blocked by Smart App Control / Constrained Language Mode). Format:
[MS-SHLLINK] (header, StringData, ExtraData) + [MS-PROPSTORE] (serialized property store).
Target goes in the environment-variables block (no item id list, no link info) - the shell
resolves it from there (PreferEnvironmentPath).
"""
import struct
import uuid

LINK_CLSID = uuid.UUID("00021401-0000-0000-c000-000000000046")
# System.AppUserModel.ID = {9F4C2855-9F79-4B39-A8D0-E1D42DE1D5F3}, 5
APP_ID_FMTID = uuid.UUID("9f4c2855-9f79-4b39-a8d0-e1d42de1d5f3")
APP_ID_PID = 5
VT_LPWSTR = 0x1F

HAS_WORKING_DIR, HAS_ICON_LOCATION, IS_UNICODE = 0x10, 0x40, 0x80
FORCE_NO_LINK_INFO, HAS_EXP_STRING, PREFER_ENVIRONMENT_PATH = 0x100, 0x200, 0x2000000
ENV_BLOCK, PROPERTY_BLOCK = 0xA0000001, 0xA0000009
MAX_PATH = 260
SHOW_MINIMIZED = 7  # .bat launcher's console stays out of sight


def _string(text: str) -> bytes:
    return struct.pack("<H", len(text)) + text.encode("utf-16-le")


def _env_block(target: str) -> bytes:
    if len(target) >= MAX_PATH:
        raise ValueError(f"shortcut target over {MAX_PATH - 1} characters")
    ansi = target.encode("ascii", "replace").ljust(MAX_PATH, b"\0")
    wide = target.encode("utf-16-le").ljust(MAX_PATH * 2, b"\0")
    return struct.pack("<II", 8 + MAX_PATH * 3, ENV_BLOCK) + ansi + wide


def _app_id_block(app_id: str) -> bytes:
    chars = (app_id + "\0").encode("utf-16-le")
    chars += b"\0" * (-len(chars) % 4)
    typed = struct.pack("<HHI", VT_LPWSTR, 0, len(app_id) + 1) + chars
    value = struct.pack("<IIB", 9 + len(typed), APP_ID_PID, 0) + typed
    storage_body = struct.pack("<I", 0x53505331) + APP_ID_FMTID.bytes_le + value + struct.pack("<I", 0)
    storage = struct.pack("<I", 4 + len(storage_body)) + storage_body
    store = storage + struct.pack("<I", 0)
    return struct.pack("<II", 8 + len(store), PROPERTY_BLOCK) + store


def build(target: str, icon: str, working_dir: str, app_id: str, show: int = SHOW_MINIMIZED) -> bytes:
    # icon = file path only; its index sits in the header (",0" is WScript.Shell's notation)
    flags = (HAS_WORKING_DIR | HAS_ICON_LOCATION | IS_UNICODE | FORCE_NO_LINK_INFO | HAS_EXP_STRING
             | PREFER_ENVIRONMENT_PATH)
    header = struct.pack("<I16sII8s8s8sIiIHHII", 0x4C, LINK_CLSID.bytes_le, flags, 0,
                         b"\0" * 8, b"\0" * 8, b"\0" * 8, 0, 0, show, 0, 0, 0, 0)
    strings = _string(working_dir) + _string(icon)
    extra = _env_block(target) + _app_id_block(app_id) + struct.pack("<I", 0)
    return header + strings + extra


def parse(data: bytes) -> dict:
    # reads back what build() writes (tests + up-to-date check); not a general .lnk reader
    size, clsid, flags = struct.unpack_from("<I16sI", data)
    if size != 0x4C or uuid.UUID(bytes_le=clsid) != LINK_CLSID:
        raise ValueError("not a shortcut")
    out = {"show": struct.unpack_from("<I", data, 60)[0], "flags": flags}
    at = 0x4C
    for flag, key in ((HAS_WORKING_DIR, "working_dir"), (HAS_ICON_LOCATION, "icon")):
        if flags & flag:
            n = struct.unpack_from("<H", data, at)[0]
            out[key] = data[at + 2:at + 2 + n * 2].decode("utf-16-le")
            at += 2 + n * 2
    while True:
        block_size = struct.unpack_from("<I", data, at)[0]
        if block_size < 4:
            return out
        signature = struct.unpack_from("<I", data, at + 4)[0]
        body = data[at + 8:at + block_size]
        if signature == ENV_BLOCK:
            out["target"] = body[MAX_PATH:].decode("utf-16-le").split("\0")[0]
        elif signature == PROPERTY_BLOCK:
            out.update(_parse_store(body))
        at += block_size


def _parse_store(store: bytes) -> dict:
    out, at = {}, 0
    while (storage_size := struct.unpack_from("<I", store, at)[0]) >= 4:
        fmtid = uuid.UUID(bytes_le=store[at + 8:at + 24])
        pos = at + 24
        while (value_size := struct.unpack_from("<I", store, pos)[0]) >= 4:
            pid, vt, n = struct.unpack_from("<I", store, pos + 4)[0], *struct.unpack_from("<H2xI", store, pos + 9)
            if (fmtid, pid, vt) == (APP_ID_FMTID, APP_ID_PID, VT_LPWSTR):
                out["app_id"] = store[pos + 17:pos + 17 + n * 2].decode("utf-16-le").rstrip("\0")
            pos += value_size
        at += storage_size
    return out
