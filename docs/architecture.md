# Architecture

本仓库采用「模板驱动 + skill 独立目录」架构。

## 分层

1. `templates/`：沉淀最佳实践模板。
2. `skills/`：每个 skill 一个目录，独立演进。
3. `docs/`：规范、流程、设计决策。

## 生命周期

1. **Scaffold**：从模板复制。
2. **Customize**：补全场景、约束、输入输出。
3. **Validate**：根据 checklist 自检。
4. **Register**：写入 `skills/_registry.md`。
5. **Iterate**：版本化更新与兼容性说明。

## 命名约定

- skill 文件夹：`kebab-case`，例如 `sql-explainer`。
- 资产目录：`assets/`。
- 示例目录：`examples/`。
- 测试/校验目录：`tests/` 或 `checks/`。
