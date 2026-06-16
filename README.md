# Claude Skills

我的 Claude Code 技能集合，用于增强 Claude 的专项能力。

## 技能列表

| 技能 | 说明 |
|------|------|
| **Git 提交助手** (`git-commit-helper`) | 分析未提交变更、按功能域分批提交、自动维护变更日志 |
| **技能创建器** (`skill-creator`) | 创建、测试、评估和优化 Claude Code 技能 |
| **命令提醒** (`命令提醒`) | 用中文描述需求时自动推荐对应的内置技能 |

## 目录结构

```
.claude/skills/
├── README.md
├── .gitignore
├── git-commit-helper/       # Git 提交助手
│   └── SKILL.md
├── skill-creator/           # 技能创建器
│   ├── SKILL.md
│   ├── agents/              # 评估子代理定义
│   ├── eval-viewer/         # 评估结果查看器
│   ├── references/          # 参考文档
│   └── scripts/             # 工具脚本
└── *-workspace/             # 技能测试工作区（不纳入版本控制）
```

## 安装

将本仓库克隆到 `~/.claude/skills/` 目录：

```bash
git clone https://github.com/LiTianYun/claude-skills.git ~/.claude/skills/
```

Claude Code 会自动识别该目录下的技能。

---

## 变更日志

<!-- 新条目添加在最上方 -->

### 2026-06-16

- **feat**: 新增命令提醒技能，用中文描述需求时自动推荐对应的内置技能（`命令提醒`）
- **feat**: 新增 Git 提交助手，支持按功能域分批提交和维护变更日志（`git-commit-helper`）
