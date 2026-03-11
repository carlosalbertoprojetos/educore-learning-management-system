#!/usr/bin/env python3
# Minimal msgfmt in pure Python (UTF-8), with plural/context support.
import sys
import struct
import os
import ast


def read_po(path):
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    messages = {}
    msgctxt = None
    msgid = None
    msgid_plural = None
    msgstrs = {}
    state = None

    def unquote(s):
        s = s.strip()
        if not s:
            return ""
        if s.startswith('"') and s.endswith('"'):
            return ast.literal_eval(s)
        return s

    def commit():
        nonlocal msgctxt, msgid, msgid_plural, msgstrs, state
        if msgid is None:
            return
        if msgid_plural is None:
            key = msgid if msgctxt is None else f"{msgctxt}\x04{msgid}"
            messages[key] = msgstrs.get(0, "")
        else:
            key = f"{msgid}\x00{msgid_plural}"
            if msgctxt is not None:
                key = f"{msgctxt}\x04{key}"
            max_index = max(msgstrs) if msgstrs else 0
            joined = "\x00".join(msgstrs.get(i, "") for i in range(max_index + 1))
            messages[key] = joined
        msgctxt = None
        msgid = None
        msgid_plural = None
        msgstrs = {}
        state = None

    for line in lines:
        line = line.rstrip("\n")
        if line.startswith("#"):
            continue
        if line.startswith("msgctxt "):
            if msgid is not None:
                commit()
            msgctxt = unquote(line[7:].strip())
            state = "msgctxt"
        elif line.startswith("msgid "):
            if msgid is not None:
                commit()
            msgid = unquote(line[5:].strip())
            msgid_plural = None
            msgstrs = {}
            state = "msgid"
        elif line.startswith("msgid_plural "):
            msgid_plural = unquote(line[12:].strip())
            state = "msgid_plural"
        elif line.startswith("msgstr["):
            idx = int(line.split("]", 1)[0][7:])
            value = unquote(line.split("]", 1)[1].strip())
            msgstrs[idx] = value
            state = ("msgstr", idx)
        elif line.startswith("msgstr "):
            msgstrs[0] = unquote(line[6:].strip())
            state = ("msgstr", 0)
        elif line.startswith('"'):
            text = unquote(line)
            if state == "msgctxt":
                msgctxt = (msgctxt or "") + text
            elif state == "msgid":
                msgid = (msgid or "") + text
            elif state == "msgid_plural":
                msgid_plural = (msgid_plural or "") + text
            elif isinstance(state, tuple) and state[0] == "msgstr":
                idx = state[1]
                msgstrs[idx] = msgstrs.get(idx, "") + text
        elif line.strip() == "":
            if msgid is not None:
                commit()

    if msgid is not None:
        commit()

    return messages


def write_mo(messages, outpath):
    # Based on GNU gettext .mo format
    keys = sorted(messages.keys())
    offsets = []
    ids = b""
    strs = b""

    for k in keys:
        k_bytes = k.encode("utf-8")
        s_bytes = messages[k].encode("utf-8")
        offsets.append((len(ids), len(k_bytes), len(strs), len(s_bytes)))
        ids += k_bytes + b"\x00"
        strs += s_bytes + b"\x00"

    keystart = 7 * 4
    valuestart = keystart + len(keys) * 8
    idstart = valuestart + len(keys) * 8
    strstart = idstart + len(ids)

    output = []
    output.append(struct.pack("I", 0x950412de))  # magic
    output.append(struct.pack("I", 0))           # version
    output.append(struct.pack("I", len(keys)))   # number of strings
    output.append(struct.pack("I", keystart))    # offset of key table
    output.append(struct.pack("I", valuestart))  # offset of value table
    output.append(struct.pack("I", 0))           # hash size
    output.append(struct.pack("I", 0))           # hash offset

    for off in offsets:
        output.append(struct.pack("II", off[1], idstart + off[0]))
    for off in offsets:
        output.append(struct.pack("II", off[3], strstart + off[2]))

    output.append(ids)
    output.append(strs)

    with open(outpath, "wb") as f:
        f.write(b"".join(output))


def main():
    if len(sys.argv) < 2:
        print("Usage: msgfmt.py input.po -o output.mo")
        sys.exit(1)

    in_po = sys.argv[1]
    out_mo = None
    if "-o" in sys.argv:
        idx = sys.argv.index("-o")
        if idx + 1 < len(sys.argv):
            out_mo = sys.argv[idx + 1]

    if not out_mo:
        out_mo = os.path.splitext(in_po)[0] + ".mo"

    messages = read_po(in_po)
    write_mo(messages, out_mo)
    print(f"Compiled {in_po} -> {out_mo}")


if __name__ == "__main__":
    main()
