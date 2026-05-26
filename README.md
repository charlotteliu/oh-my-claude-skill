# oh-my-claude-skill

一个用于 **开发、收集、维护 Claude Agent Skills** 的仓库。

## 目标

- 建立统一、可扩展的 skills 目录结构。
- 提供可直接复用的 **state-of-the-art skill 模板**。
- 让每个 skill 以独立文件夹管理，便于版本迭代、协作与发布。

## 目录结构

```text
.
├── README.md
├── docs/
│   ├── architecture.md
│   └── contributing.md
├── templates/
│   └── skill-template/
│       ├── SKILL.md
│       ├── README.md
│       ├── examples/
│       │   ├── input.md
│       │   └── output.md
│       └── checks/
│           └── checklist.md
└── skills/
    ├── _registry.md
    └── <skill-name>/
        ├── SKILL.md
        ├── README.md
        ├── examples/
        ├── assets/
        └── tests/
```

## 快速开始

1. 复制模板创建新 skill：
   - 从 `templates/skill-template` 复制一份到 `skills/<your-skill-name>`。
2. 按模板填写：
   - `SKILL.md`（核心行为与执行规则）
   - `README.md`（使用说明）
   - `examples/`（输入输出示例）
3. 在 `skills/_registry.md` 登记 skill 元信息。
4. 按 `docs/contributing.md` 的规范进行评审与迭代。

## 设计原则

- **单一职责**：每个 skill 聚焦一个高价值场景。
- **可测试**：必须提供至少一个正向与一个反向示例。
- **可组合**：支持与其他 skill 协作，不产生上下文污染。
- **低耦合**：skill 内部说明自洽，减少对外部隐式依赖。
- **可维护**：版本、变更记录、约束明确。
