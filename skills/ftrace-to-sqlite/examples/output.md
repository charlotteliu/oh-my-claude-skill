# Example Output

## summary
- 已按 `partial` 模式生成 4 张目标表，跳过其余非目标表。
- 完成 ftrace 与 inode 映射导入，批量写入成功。
- 已输出表级统计与 ino 维度 Top10。

## artifacts
- 数据库：`./output/ftrace_scene.db`
- 统计 SQL：`SELECT COUNT(*) FROM ...`

## verification
- `SELECT name FROM sqlite_master WHERE type='table';`
- `SELECT COUNT(*) FROM mm_filemap_access_history;`
- `SELECT ino, COUNT(*) c FROM mm_filemap_access_history GROUP BY ino ORDER BY c DESC LIMIT 10;`

## next_actions
- 若发现未命中日志，补充/调整正则并回放样本。
- 对大体量数据添加更多组合索引（如 `ino,ofs,timestamp`）。
