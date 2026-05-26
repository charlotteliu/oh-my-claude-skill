# Example Input

请使用 ftrace-to-sqlite：
1. 输入目录：`./trace_inputs/init_trace.log`
2. 输出数据库：`./output/ftrace_scene.db`
3. 模式：`partial`
4. 只生成以下表：
   - `mm_filemap_add_to_page_cache`
   - `mm_filemap_access_history`
   - `bitmap_page_info`
   - `inode_mapping`
5. 导入后输出：
   - 每张表 `count(*)`
   - `mm_filemap_access_history` 按 `ino` 的 Top 10 统计
