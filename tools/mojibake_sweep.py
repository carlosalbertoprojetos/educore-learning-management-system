from __future__ import annotations

import argparse
import sqlite3
from dataclasses import dataclass
from pathlib import Path


SUSPECT_CODEPOINTS = {0x00C2, 0x00C3, 0xFFFD}  # "Â", "Ã", replacement char


@dataclass
class Hit:
    kind: str  # "file" or "db"
    where: str
    sample: str


def is_likely_mojibake(s: str) -> bool:
    """
    Detect common UTF-8/latin-1 mojibake patterns without flagging legit Portuguese like "NÃO".
    Examples we want to catch (shown as codepoints to avoid terminal encoding issues):
    - "gest" + U+00C3 U+00A3 + "o"
    - "dist" + U+00C3 U+00A2 + "ncia"
    - U+00C2 + " " (often a NBSP rendered as that pair)
    """
    if "\ufffd" in s:
        return True
    for i, ch in enumerate(s[:-1]):
        o = ord(ch)
        n = ord(s[i + 1])
        if o == 0x00C3 and 0x0080 <= n <= 0x00BF:
            return True
        if o == 0x00C2 and (0x0080 <= n <= 0x00BF or n == 0x0020):
            return True
    return False


def try_fix_common_mojibake(s: str) -> str | None:
    """
    Common mojibake fix:
    - text was UTF-8 bytes decoded as latin-1 -> became a Unicode string with Ã/Â
    - fix by encoding as latin-1 and decoding as UTF-8
    """
    if not is_likely_mojibake(s):
        return None
    try:
        fixed = s.encode("latin-1").decode("utf-8")
    except Exception:
        return None
    if fixed == s:
        return None
    # Heuristic: fixed should contain fewer suspect chars.
    if sum(ord(ch) in SUSPECT_CODEPOINTS for ch in fixed) >= sum(ord(ch) in SUSPECT_CODEPOINTS for ch in s):
        return None
    return fixed


def scan_files(root: Path) -> list[Hit]:
    ex_dirs = {".venv", ".git", "node_modules", "media", "htmlcov", "__pycache__"}
    ex_ext = {".mo", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".woff", ".woff2", ".ttf"}
    hits: list[Hit] = []
    for p in root.rglob("*"):
        if any(part in ex_dirs for part in p.parts):
            continue
        if p.is_dir():
            continue
        if p.suffix.lower() in ex_ext:
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except Exception:
            continue
        if is_likely_mojibake(text):
            sample = ""
            for line in text.splitlines():
                if is_likely_mojibake(line):
                    sample = line.strip()[:200]
                    break
            hits.append(Hit(kind="file", where=str(p), sample=sample))
    return hits


def scan_db(db_path: Path) -> tuple[list[Hit], dict[tuple[str, str, int], str]]:
    hits: list[Hit] = []
    fixes: dict[tuple[str, str, int], str] = {}
    if not db_path.exists():
        return hits, fixes
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tables = [r[0] for r in cur.fetchall()]
    for t in tables:
        cur.execute(f'PRAGMA table_info("{t}")')
        cols = []
        for row in cur.fetchall():
            typ = (row["type"] or "").upper()
            if "CHAR" in typ or "TEXT" in typ or "CLOB" in typ:
                cols.append(row["name"])
        if not cols:
            continue
        col_list = ",".join([f'"{c}"' for c in cols])
        cur.execute(f'SELECT rowid as _rid, {col_list} FROM "{t}"')
        for row in cur.fetchall():
            rid = int(row["_rid"])
            for c in cols:
                v = row[c]
                if not isinstance(v, str) or not v:
                    continue
                if is_likely_mojibake(v):
                    sample = v.strip().replace("\n", " ")[:200]
                    hits.append(Hit(kind="db", where=f"{t}.{c}#{rid}", sample=sample))
                    fixed = try_fix_common_mojibake(v)
                    if fixed is not None:
                        fixes[(t, c, rid)] = fixed
    return hits, fixes


def apply_db_fixes(db_path: Path, fixes: dict[tuple[str, str, int], str]) -> int:
    if not fixes:
        return 0
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    applied = 0
    for (t, c, rid), fixed in fixes.items():
        cur.execute(f'UPDATE "{t}" SET "{c}" = ? WHERE rowid = ?', (fixed, rid))
        applied += cur.rowcount
    con.commit()
    con.close()
    return applied


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".", help="Project root to scan (default: .)")
    ap.add_argument("--db", default="db.sqlite3", help="SQLite DB path (default: db.sqlite3)")
    ap.add_argument("--fix-db", action="store_true", help="Attempt to fix mojibake in DB fields.")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    db = Path(args.db).resolve()

    file_hits = scan_files(root)
    db_hits, db_fixes = scan_db(db)

    print(f"file_hits={len(file_hits)} db_hits={len(db_hits)} db_fix_candidates={len(db_fixes)}")
    for h in (file_hits + db_hits)[:40]:
        print(f"[{h.kind}] {h.where}: {h.sample}")

    if args.fix_db:
        applied = apply_db_fixes(db, db_fixes)
        print(f"db_fixes_applied={applied}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
