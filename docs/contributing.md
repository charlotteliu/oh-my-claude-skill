# Contributing Guide

## 新增 skill 流程

1. 从 `templates/skill-template` 复制：
   ```bash
   cp -R templates/skill-template skills/<skill-name>
   ```
2. 完成以下内容：
   - `SKILL.md`：角色、触发条件、步骤、输出契约、边界。
   - `README.md`：快速使用、参数、限制、FAQ。
   - `examples/`：最少 2 组（成功/失败）。
3. 更新 `skills/_registry.md`。
4. 自检 `checks/checklist.md`。

## 质量标准

- 明确输入与输出格式。
- 明确失败处理与回退策略。
- 避免过度承诺（输出必须可执行、可验证）。
- 避免隐式依赖（路径、工具、权限需写清楚）。
