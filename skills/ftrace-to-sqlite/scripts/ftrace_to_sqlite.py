#!/usr/bin/env python3
"""ftrace/smaps/ark/inode/stepinfo -> sqlite3

支持：
- 全量建表（--mode all）
- 按需部分建表（--mode partial --tables ...）
- 导入后统计（--stats table|ino|pid）
"""
from __future__ import annotations

import argparse
import os
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Set, Tuple

ALL_TABLES = {
    "mm_filemap_add_to_page_cache",
    "mm_filemap_delete_from_page_cache",
    "tracing_mark_fabit",
    "mm_filemap_access_history",
    "mm_filemap_label_page_cache",
    "inode_mapping",
    "timestep",
    "process_smaps",
    "ark_symbol_dump",
    "bitmap_page_info",
    "zeroaccess_page",
}

PREFIX = (
    r"^\s*(?P<pid_name>.+?)-(?P<pid>\d+)\s+\(.*?\)[\s\t]+"
    r"\[(?P<cpu>\d+)\][\.\s\t]{4,}\s+(?P<timestamp>\d+\.\d+):\s+"
)
RE_ADD = re.compile(PREFIX +
    r"mm_filemap_add_to_page_cache:\s+dev\s+(?P<dev>\d+:\d+)\s+ino\s+(?P<ino>0x[0-9a-fA-F]+)\s+"
    r"page=(?P<page>0x[0-9a-fA-F]+)\s+pfn=(?P<pfn>\d+)\s+ofs=(?P<ofs>\d+)\s+mmapcnt=(?P<mmapcnt>\d+)\s+flags=(?P<flags>0x[0-9a-fA-F]+)")
RE_DEL = re.compile(PREFIX +
    r"mm_filemap_delete_from_page_cache:\s+dev\s+(?P<dev>\d+:\d+)\s+ino\s+(?P<ino>0x[0-9a-fA-F]+)\s+"
    r"page=(?P<page>0x[0-9a-fA-F]+)\s+pfn=(?P<pfn>\d+)\s+ofs=(?P<ofs>\d+)\s+mmapcnt=(?P<mmapcnt>\d+)\s+flags=(?P<flags>0x[0-9a-fA-F]+)")
RE_FABIT = re.compile(PREFIX +
    r"tracing_mark_write:\s+B\|[^\|]+\|fabit\s+d=(?P<dev>\d+:\d+)\s+i=(?P<ino>\d+)\s+o=(?P<ofs>\d+)")
RE_ACCESS = re.compile(PREFIX +
    r"(?P<event_type>mm_filemap_mark_access|mm_filemap_mark_reaccess|mm_filemap_mark_referenced):\s+"
    r"dev\s+(?P<dev>\d+:\d+)\s+ino\s+(?P<ino>0x[0-9a-fA-F]+)\s+page=(?P<page>0x[0-9a-fA-F]+)\s+"
    r"pfn=(?P<pfn>\d+)\s+ofs=(?P<ofs>\d+)\s+mmapcnt=(?P<mmapcnt>\d+)")
RE_LABEL = re.compile(PREFIX +
    r"mm_filemap_label_page_cache:\s+dev\s+(?P<dev>\d+:\d+)\s+ino\s+(?P<ino>0x[0-9a-fA-F]+)\s+"
    r"page=(?P<page>0x[0-9a-fA-F]+)\s+pfn=(?P<pfn>\d+)\s+ofs=(?P<ofs>\d+)\s+mmapcnt=(?P<mmapcnt>\d+)\s+"
    r"label=(?P<label>\d+)\s+accessbit=(?P<accessbit>\d+)")
RE_BITMAP = re.compile(PREFIX + r"tracing_mark_write:\s+B\|[^\|]+\|bitmap\s+"
    r"d=(?P<dev>\d+:\d+)\s+i=(?P<ino>\d+)\s+o=(?P<base_ofs>\d+)(?:\(rem\))?:\s+"
    r"(?P<bitmap_hex>[0-9a-fA-F]+)")

RE_STEP_TIME = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3})\s+(.+)")
RE_START_PCTIME = re.compile(r"pctime:(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3})")
RE_FILENAME_TIME = re.compile(r"(\d{8})_(\d{6})\.txt")
RE_SMAPS_SECTION = re.compile(r"^([0-9a-fA-F]+-[0-9a-fA-F]+)\s+[\-wrxp]+s?\s+([0-9a-fA-F]+)\s+([0-9a-fA-F]+:[0-9a-fA-F]+)\s+(\d+)\s*(.*)")
RE_SMAPS_PSS = re.compile(r"^Pss:\s*(\d+)\s*kB")
RE_SMAPS_BUFTYPE = re.compile(r"buftype:\s*(\d+)\s+MappedSize:\s*(\d+)\s+AllZeroSize:\s*(\d+)\s+mylabel1:\s*(\d+)\s+mylabel2:\s*(\d+)\s+AccessedSize:\s*(\d*)")
RE_ARK_LITERAL = re.compile(r"^\d+\s+(0x[0-9a-fA-F]+)\s+\{\s*\d+\s+\[(.*?)\]\}", re.MULTILINE)
RE_ARK_RECORD = re.compile(r"\.record\s+([^{]+?)\s*\{\s*#\s*offset:\s*(0x[0-9a-fA-F]+)(?:,\s*size:\s*(0x[0-9a-fA-F]+))?")
RE_ARK_METHOD = re.compile(r"\.function\s+([^{]+?)\s*\{[^#]*#\s*offset:\s*(0x[0-9a-fA-F]+)(?:,\s*code offset:\s*(0x[0-9a-fA-F]+))?")
RE_ARK_STRING = re.compile(r"\[offset:(0x[0-9a-fA-F]+),\s*name_value:(.*?)\]", re.DOTALL)


def init_db(conn: sqlite3.Connection, tables: Set[str]) -> None:
    c = conn.cursor()
    for t in tables:
        c.execute(f"DROP TABLE IF EXISTS {t}")
    if "mm_filemap_add_to_page_cache" in tables:
        c.execute("CREATE TABLE mm_filemap_add_to_page_cache (dev TEXT, ino TEXT, page TEXT, pfn INTEGER, ofs INTEGER, mmapcnt INTEGER, flags TEXT, timestamp REAL, pid INTEGER, pid_name TEXT)")
    if "mm_filemap_delete_from_page_cache" in tables:
        c.execute("CREATE TABLE mm_filemap_delete_from_page_cache (dev TEXT, ino TEXT, page TEXT, pfn INTEGER, ofs INTEGER, mmapcnt INTEGER, flags TEXT, timestamp REAL, pid INTEGER, pid_name TEXT)")
    if "tracing_mark_fabit" in tables:
        c.execute("CREATE TABLE tracing_mark_fabit (dev TEXT, ino TEXT, ofs INTEGER, timestamp REAL, pid INTEGER, pid_name TEXT)")
    if "mm_filemap_access_history" in tables:
        c.execute("CREATE TABLE mm_filemap_access_history (event_type TEXT, dev TEXT, ino TEXT, page TEXT, pfn INTEGER, ofs INTEGER, mmapcnt INTEGER, timestamp REAL, pid INTEGER, pid_name TEXT)")
    if "mm_filemap_label_page_cache" in tables:
        c.execute("CREATE TABLE mm_filemap_label_page_cache (dev TEXT, ino TEXT, page TEXT, pfn INTEGER, ofs INTEGER, mmapcnt INTEGER, label INTEGER, accessbit INTEGER, timestamp REAL, pid INTEGER, pid_name TEXT)")
    if "inode_mapping" in tables:
        c.execute("CREATE TABLE inode_mapping (ino TEXT PRIMARY KEY, dev TEXT, size INTEGER, filename TEXT)")
    if "timestep" in tables:
        c.execute("CREATE TABLE timestep (timestamp REAL PRIMARY KEY, step TEXT)")
    if "process_smaps" in tables:
        c.execute("CREATE TABLE process_smaps (id INTEGER PRIMARY KEY AUTOINCREMENT, process_name TEXT,timestamp REAL,addr_name TEXT,addr_range TEXT,offset TEXT,dev TEXT,ino TEXT,pss INTEGER,buftype TEXT,MappedSize TEXT,AllZeroSize TEXT,mylabel1 TEXT,mylabel2 TEXT,AccessedSize TEXT)")
    if "ark_symbol_dump" in tables:
        c.execute("CREATE TABLE ark_symbol_dump (id INTEGER PRIMARY KEY AUTOINCREMENT,offset INTEGER NOT NULL,code_offset INTEGER,size INTEGER,type TEXT NOT NULL,name_value TEXT NOT NULL)")
    if "bitmap_page_info" in tables:
        c.execute("CREATE TABLE bitmap_page_info (dev TEXT,ino TEXT,base_ofs INTEGER,page_ofs INTEGER,timestamp REAL,pid INTEGER,pid_name TEXT)")
    if "zeroaccess_page" in tables:
        c.execute("CREATE TABLE zeroaccess_page (id INTEGER PRIMARY KEY AUTOINCREMENT,ino TEXT NOT NULL,filename TEXT,page_idx INTEGER,ofs_bytes INTEGER,ofs_hex TEXT,add_ts REAL,duration REAL,internal_file TEXT,internal_offset TEXT,compress_type TEXT)")
    conn.commit()


def parse_inode(conn, path: str):
    if not path or not os.path.exists(path):
        return
    rows=[]
    with open(path, encoding="utf-8", errors="ignore") as f:
        for line in f:
            line=line.strip()
            if not line or line.lower().startswith(("ino","inode","#")): continue
            parts=line.split(None,3)
            if len(parts)>=4:
                ino,dev,size_s,name=parts
                try:size=int(size_s)
                except: size=0; name=f"[{size_s}] {name}"
                rows.append((ino,dev,size,name.strip(' \t"')))
    conn.executemany("INSERT OR IGNORE INTO inode_mapping VALUES (?,?,?,?)", rows); conn.commit()


def parse_ftrace(conn, paths: Sequence[str], tables: Set[str]):
    need = {"mm_filemap_add_to_page_cache","mm_filemap_delete_from_page_cache","tracing_mark_fabit","mm_filemap_access_history","mm_filemap_label_page_cache","bitmap_page_info"}
    if not (need & tables): return
    bufs: Dict[str, List[Tuple]]={"add":[],"del":[],"fabit":[],"access":[],"label":[],"bitmap":[]}
    for p in paths:
        with open(p, encoding="utf-8", errors="ignore") as f:
            for raw in f:
                line=raw.strip()
                if not line or line.startswith("#"): continue
                if "bitmap" in line:
                    m=RE_BITMAP.search(line)
                    if m and "bitmap_page_info" in tables:
                        d=m.groupdict(); base=int(d["base_ofs"]); bitmap=int(d["bitmap_hex"],16)
                        for i in range(64):
                            if (bitmap>>i)&1:
                                bufs["bitmap"].append((d["dev"], f"0x{int(d['ino']):x}", base, base+i*4096, float(d["timestamp"]), int(d["pid"]), d["pid_name"].strip()))
                elif "mm_filemap_add_to_page_cache" in line:
                    m=RE_ADD.search(line)
                    if m and "mm_filemap_add_to_page_cache" in tables:
                        d=m.groupdict(); bufs["add"].append((d['dev'],d['ino'],d['page'],int(d['pfn']),int(d['ofs']),int(d['mmapcnt']),d['flags'],float(d['timestamp']),int(d['pid']),d['pid_name'].strip()))
                elif "mm_filemap_delete_from_page_cache" in line:
                    m=RE_DEL.search(line)
                    if m and "mm_filemap_delete_from_page_cache" in tables:
                        d=m.groupdict(); bufs["del"].append((d['dev'],d['ino'],d['page'],int(d['pfn']),int(d['ofs']),int(d['mmapcnt']),d['flags'],float(d['timestamp']),int(d['pid']),d['pid_name'].strip()))
                elif "fabit" in line:
                    m=RE_FABIT.search(line)
                    if m and "tracing_mark_fabit" in tables:
                        d=m.groupdict(); bufs["fabit"].append((d['dev'],hex(int(d['ino'])),int(d['ofs']),float(d['timestamp']),int(d['pid']),d['pid_name'].strip()))
                elif "mm_filemap_mark_" in line:
                    m=RE_ACCESS.search(line)
                    if m and "mm_filemap_access_history" in tables:
                        d=m.groupdict(); bufs["access"].append((d['event_type'],d['dev'],d['ino'],d['page'],int(d['pfn']),int(d['ofs']),int(d['mmapcnt']),float(d['timestamp']),int(d['pid']),d['pid_name'].strip()))
                elif "mm_filemap_label_page_cache" in line:
                    m=RE_LABEL.search(line)
                    if m and "mm_filemap_label_page_cache" in tables:
                        d=m.groupdict(); bufs["label"].append((d['dev'],d['ino'],d['page'],int(d['pfn']),int(d['ofs']),int(d['mmapcnt']),int(d['label']),int(d['accessbit']),float(d['timestamp']),int(d['pid']),d['pid_name'].strip()))
    cur=conn.cursor()
    if bufs["add"]: cur.executemany("INSERT INTO mm_filemap_add_to_page_cache VALUES (?,?,?,?,?,?,?,?,?,?)", bufs["add"])
    if bufs["del"]: cur.executemany("INSERT INTO mm_filemap_delete_from_page_cache VALUES (?,?,?,?,?,?,?,?,?,?)", bufs["del"])
    if bufs["fabit"]: cur.executemany("INSERT INTO tracing_mark_fabit VALUES (?,?,?,?,?,?)", bufs["fabit"])
    if bufs["access"]: cur.executemany("INSERT INTO mm_filemap_access_history VALUES (?,?,?,?,?,?,?,?,?,?)", bufs["access"])
    if bufs["label"]: cur.executemany("INSERT INTO mm_filemap_label_page_cache VALUES (?,?,?,?,?,?,?,?,?,?,?)", bufs["label"])
    if bufs["bitmap"]: cur.executemany("INSERT INTO bitmap_page_info VALUES (?,?,?,?,?,?,?)", bufs["bitmap"])
    conn.commit()


def parse_stepinfo(conn, path: str):
    if not path or not os.path.exists(path): return
    rows=[]
    for line in Path(path).read_text(encoding="utf-8", errors="ignore").splitlines():
        m=RE_START_PCTIME.search(line)
        if m:
            ts=round(datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S.%f").timestamp(),3); rows.append((ts,"用例启动时间"))
        m2=RE_STEP_TIME.match(line)
        if m2:
            ts=round(datetime.strptime(m2.group(1), "%Y-%m-%d %H:%M:%S.%f").timestamp(),3); rows.append((ts,m2.group(2).strip()))
    conn.executemany("INSERT OR REPLACE INTO timestep VALUES (?,?)", rows); conn.commit()


def parse_ark(conn, path: str):
    if not path or not os.path.exists(path): return
    content=Path(path).read_text(encoding="utf-8", errors="ignore")
    rows=[]
    rows += [(int(m.group(1),16),None,None,"LITERAL",m.group(2).strip()) for m in RE_ARK_LITERAL.finditer(content)]
    rows += [(int(m.group(2),16),None,int(m.group(3),16) if m.group(3) else None,"RECORD",m.group(1).strip()) for m in RE_ARK_RECORD.finditer(content)]
    rows += [(int(m.group(2),16),int(m.group(3),16) if m.group(3) else None,None,"METHOD",m.group(1).strip()) for m in RE_ARK_METHOD.finditer(content)]
    rows += [(int(m.group(1),16),None,None,"STRING",m.group(2).strip()) for m in RE_ARK_STRING.finditer(content)]
    conn.executemany("INSERT INTO ark_symbol_dump (offset,code_offset,size,type,name_value) VALUES (?,?,?,?,?)", rows); conn.commit()


def build_zeroaccess(conn):
    conn.execute("""
    INSERT INTO zeroaccess_page (ino, filename, page_idx, ofs_bytes, ofs_hex, add_ts, duration, internal_file, internal_offset, compress_type)
    WITH all_access AS (
      SELECT ino,(ofs*4096) AS ofs_bytes,timestamp FROM tracing_mark_fabit
      UNION ALL SELECT ino,ofs,timestamp FROM mm_filemap_access_history
      UNION ALL SELECT ino,ofs,timestamp FROM mm_filemap_label_page_cache
    ), lifecycle AS (
      SELECT a.ino, a.timestamp add_ts, (a.ofs/4096) page_idx, a.ofs ofs_bytes,
      (SELECT MIN(d.timestamp) FROM mm_filemap_delete_from_page_cache d WHERE d.ino=a.ino AND d.ofs=a.ofs AND d.timestamp>a.timestamp) AS del_ts
      FROM mm_filemap_add_to_page_cache a
    )
    SELECT l.ino, COALESCE(m.filename, ''), l.page_idx, l.ofs_bytes, printf('0x%X', l.ofs_bytes), l.add_ts,
           COALESCE(l.del_ts, l.add_ts)-l.add_ts, '', '', ''
    FROM lifecycle l LEFT JOIN inode_mapping m ON m.ino=l.ino
    WHERE NOT EXISTS (
      SELECT 1 FROM all_access x WHERE x.ino=l.ino AND x.ofs_bytes=l.ofs_bytes AND x.timestamp>=l.add_ts AND (l.del_ts IS NULL OR x.timestamp<=l.del_ts)
    )
    """)
    conn.commit()


def stats(conn, tables:Set[str], mode:str):
    print("== table stats ==")
    for t in sorted(tables):
        c=conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"{t}: {c}")
    if mode=="ino" and "mm_filemap_access_history" in tables:
        print("== top ino from access ==")
        for ino,c in conn.execute("SELECT ino, COUNT(*) c FROM mm_filemap_access_history GROUP BY ino ORDER BY c DESC LIMIT 20"):
            print(ino,c)
    if mode=="pid" and "mm_filemap_access_history" in tables:
        print("== top pid from access ==")
        for pid,c in conn.execute("SELECT pid, COUNT(*) c FROM mm_filemap_access_history GROUP BY pid ORDER BY c DESC LIMIT 20"):
            print(pid,c)


def collect_ftrace_paths(folder: str, files: Sequence[str]) -> List[str]:
    out=[]
    out.extend([p for p in files if p])
    if folder and os.path.isdir(folder):
        out.extend([str(Path(folder)/x) for x in os.listdir(folder) if (Path(folder)/x).is_file()])
    return out


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--mode", choices=["all","partial"], default="all")
    ap.add_argument("--tables", nargs="*", default=[])
    ap.add_argument("--ftrace-folder", default="")
    ap.add_argument("--ftrace-files", nargs="*", default=[])
    ap.add_argument("--inode-mapping", default="")
    ap.add_argument("--step-info", default="")
    ap.add_argument("--ark", default="")
    ap.add_argument("--stats", choices=["table","ino","pid","none"], default="table")
    args=ap.parse_args()

    selected = ALL_TABLES if args.mode=="all" else set(args.tables)
    unknown=selected-ALL_TABLES
    if unknown:
        raise SystemExit(f"unknown tables: {sorted(unknown)}")
    if args.mode=="partial" and not selected:
        raise SystemExit("partial mode requires --tables")

    if "zeroaccess_page" in selected:
        selected |= {"mm_filemap_add_to_page_cache","mm_filemap_delete_from_page_cache","tracing_mark_fabit","mm_filemap_access_history","mm_filemap_label_page_cache","inode_mapping"}

    conn=sqlite3.connect(args.db)
    init_db(conn, selected)
    if "inode_mapping" in selected: parse_inode(conn, args.inode_mapping)
    if "timestep" in selected: parse_stepinfo(conn, args.step_info)
    if "ark_symbol_dump" in selected: parse_ark(conn, args.ark)
    parse_ftrace(conn, collect_ftrace_paths(args.ftrace_folder, args.ftrace_files), selected)
    if "zeroaccess_page" in selected: build_zeroaccess(conn)
    if args.stats!="none": stats(conn, selected, args.stats)
    conn.close()


if __name__ == "__main__":
    main()
