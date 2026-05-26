# <Skill Name>

## Purpose
一句话说明该 skill 解决的问题与价值。

## Trigger
- 用户显式提到：`<skill-name>`
- 或任务明显匹配：<适用场景>

## Inputs
- `context`: 背景信息
- `goal`: 用户目标
- `constraints`: 限制条件（时间、工具、权限）

## Workflow
1. **Clarify**：补全关键缺失信息（若无法补全，给最小可行方案）。
2. **Plan**：输出可执行步骤（短路径优先）。
3. **Execute**：按步骤执行，记录关键产物。
4. **Validate**：对结果做最小验证（正确性、完整性、边界）。
5. **Deliver**：给出结果 + 风险 + 下一步建议。

## Output Contract
- `summary`: 结果摘要（3-5 点）
- `artifacts`: 产物列表（文件、命令、链接）
- `verification`: 验证方式和结果
- `next_actions`: 建议下一步

## Guardrails
- 不编造不存在的文件/命令结果。
- 不跳过失败处理：失败时必须给回退方案。
- 涉及高风险领域（法律/医疗/金融）时，输出仅作信息参考并提示专业咨询。

## Definition of Done
- 输出结构完整且可复现。
- 提供至少一个验证步骤。
- 给出已知限制与风险。
