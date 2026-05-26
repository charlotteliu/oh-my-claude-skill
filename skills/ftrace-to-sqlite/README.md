# ftrace-to-sqlite

## What it does
提供一个可直接运行的 Python 工具：`scripts/ftrace_to_sqlite.py`，把 ftrace、smaps、ark、inode、stepinfo 等原始文本解析成 sqlite3 数据库。支持全量建表和部分建表，并可在导入后输出统计信息。

## Runnable entrypoint
```bash
python skills/ftrace-to-sqlite/scripts/ftrace_to_sqlite.py --help
```

## Quick start
### 1) 全量建表
```bash
python skills/ftrace-to-sqlite/scripts/ftrace_to_sqlite.py \
  --db ./output/ftrace_scene.db \
  --mode all \
  --ftrace-folder ./trace_inputs/ftrace \
  --inode-mapping ./trace_inputs/inode.txt \
  --step-info ./trace_inputs/stepinfo.txt \
  --ark ./trace_inputs/modules_disasm.txt \
  --stats table
```

### 2) 部分建表
```bash
python skills/ftrace-to-sqlite/scripts/ftrace_to_sqlite.py \
  --db ./output/ftrace_partial.db \
  --mode partial \
  --tables mm_filemap_access_history bitmap_page_info inode_mapping \
  --ftrace-files ./trace_inputs/init_trace.log \
  --inode-mapping ./trace_inputs/inode.txt \
  --stats ino
```

## Supported tables
- mm_filemap_add_to_page_cache
- mm_filemap_delete_from_page_cache
- tracing_mark_fabit
- mm_filemap_access_history
- mm_filemap_label_page_cache
- inode_mapping
- timestep
- process_smaps（schema 已预留；当前脚本主流程聚焦 ftrace/ark/step/inode）
- ark_symbol_dump
- bitmap_page_info
- zeroaccess_page（由基础表计算得到）

## Stats options
- `--stats table`: 输出每张表记录数
- `--stats ino`: 输出表记录数 + access 表按 ino Top20
- `--stats pid`: 输出表记录数 + access 表按 pid Top20
- `--stats none`: 不输出统计

## Limitations
- 原始日志格式需要与当前正则兼容；若内核 trace 文本变形，需要扩展脚本中的正则。
- `zeroaccess_page` 依赖 add/del/fabit/access/label/inode 表，脚本会自动补齐这些依赖表。

## Changelog
- `v0.2.0`: Added runnable converter script with actual table parsing/writing logic.
- `v0.1.0`: Initial documentation draft.
