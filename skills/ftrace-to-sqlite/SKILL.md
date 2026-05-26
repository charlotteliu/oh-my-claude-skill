# ftrace-to-sqlite

## Purpose
将 ftrace/smaps/ark/inode/stepinfo 等原始数据解析并落库到 sqlite3，支持“全量建表”与“按需部分建表”，并在导入后输出统计信息。

## Trigger
- 用户显式提到：`ftrace-to-sqlite`、`ftrace 转 sqlite`、`ftrace db`。
- 或任务明显匹配：需要把内核 trace 文本解析成结构化 sqlite 表，并做导入统计。

## Inputs
- `input_paths`:
  - `ftrace_files` 或 `ftrace_folder`
  - `inode_mapping_file`（可选）
  - `step_info_file`（可选）
  - `smaps_root_folder`（可选）
  - `ark_disasm_file`（可选）
  - `hap_file`（可选）
- `db_output_path`: 输出 sqlite 文件路径。
- `table_mode`:
  - `all`：创建并填充全部表。
  - `partial`：仅处理 `selected_tables`。
- `selected_tables`（partial 时必填）：
  - `mm_filemap_add_to_page_cache`
  - `mm_filemap_delete_from_page_cache`
  - `tracing_mark_fabit`
  - `mm_filemap_access_history`
  - `mm_filemap_label_page_cache`
  - `inode_mapping`
  - `timestep`
  - `process_smaps`
  - `ark_symbol_dump`
  - `bitmap_page_info`
  - `zeroaccess_page`
- `stats`:
  - `enabled`（默认 true）
  - `group_by`（可选）：`table` / `ino` / `pid`

## Runtime
- 可执行脚本：`skills/ftrace-to-sqlite/scripts/ftrace_to_sqlite.py`
- 建议优先通过 CLI 参数控制 `all/partial` 与统计维度，避免手改源码。

## Workflow
1. **Clarify**
   - 检查输入路径是否存在，确认是否全量建表或部分建表。
   - 若 `table_mode=partial`，验证 `selected_tables` 非空且合法。
2. **Plan**
   - 按依赖关系排定导入顺序：`inode_mapping -> timestep -> process_smaps -> ark_symbol_dump -> ftrace 相关表 -> zeroaccess_page -> index`。
3. **Execute**
   - 初始化 DB（仅创建目标表；未选择的表不创建或仅保留最小依赖）。
   - 调用解析器将数据批量写入 sqlite（executemany + 分批 commit）。
   - `zeroaccess_page` 仅在依赖表存在且具备必要字段时计算。
4. **Validate**
   - 对每个已生成表执行 `SELECT COUNT(*)`。
   - 验证关键索引是否创建成功（`sqlite_master` 检查）。
   - 抽样校验字段类型/空值（例如 `timestamp`、`ino`、`ofs`）。
5. **Deliver**
   - 输出“已生成表/跳过表/失败表”。
   - 输出统计信息：总记录数、各表记录数、可选分组统计。
   - 输出已知风险（缺失输入、编码异常、正则未命中）及下一步建议。

## Output Contract
- `summary`: 3-5 条摘要（处理范围、建表模式、结果概览）。
- `artifacts`: 产物（db 路径、日志路径、统计输出）。
- `verification`: SQL 校验命令与结果。
- `next_actions`: 下一步（补齐输入、扩展正则、加索引策略）。

## Guardrails
- 不臆造解析结果；路径不存在时必须显式报错并给最小可行降级。
- `partial` 模式下禁止偷偷创建未选表（依赖表除外，且需说明）。
- 批量处理大文件时优先流式读取和分批提交，避免一次性加载全部内容。
- 使用固定正则并记录未匹配样本比例，便于回归。

## Definition of Done
- 提供可执行脚本并可通过 `--help` 查看参数。

- 支持 `all/partial` 两种建表模式。
- 导入后提供表级统计，且可选提供 ino/pid 维度统计。
- 提供至少一组验证 SQL 并可复现。
